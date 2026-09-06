"""
Geo-coded photo field verification -- the literal ask in PS-26015's title
("...to interpret Geo-Coded Images..."), which nothing else in this project
touches. Upload a geo-tagged photo (GPS extracted automatically from its
EXIF metadata, or entered manually if a photo has none); the app fetches
fresh satellite imagery for that exact point, runs Model 1, and shows the
photo next to the satellite-predicted class -- a human confirms or flags a
mismatch, and every check is logged, building a real validation record over
time (model_plan.md section 2.8: "cross-check predictions against your own
geo-tagged field photos at known points").

Deliberately NOT a second ML model guessing what the photo shows -- this
project's whole design philosophy is explainable/human-auditable over
black-box (see the rule-based recommendation engine). A human looks at the
photo and the prediction and makes the call; the tool's job is just to put
the right two things side by side, fast.
"""

import csv
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import streamlit as st
from PIL import Image, ExifTags

from config import DATA_PROCESSED, CLASS_NAMES, CLASS_COLORS, NODATA_CLASS
from data_download import search_scene, clip_scene_to_stack
from preprocessing import build_6channel_stack
from inference_demo import predict_class_map
from aoi_picker import bbox_around
import design

VALIDATION_LOG = DATA_PROCESSED.parent / "field_validation_log.csv"
LOG_FIELDS = ["timestamp_utc", "lat", "lon", "predicted_class", "human_verdict", "note"]

_GPS_TAG_ID = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), 34853)


def _dms_to_decimal(dms, ref: str) -> float:
    """EXIF GPS stores (degrees, minutes, seconds) -- convert to signed decimal degrees."""
    degrees, minutes, seconds = (float(v) for v in dms)
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_gps_from_exif(image_bytes: bytes):
    """Returns (lat, lon) if the image has embedded GPS EXIF data, else None."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif = img.getexif()
        gps_ifd = exif.get_ifd(_GPS_TAG_ID) if exif else None
        if not gps_ifd:
            return None
        lat = _dms_to_decimal(gps_ifd[2], gps_ifd[1])  # GPSLatitude, GPSLatitudeRef
        lon = _dms_to_decimal(gps_ifd[4], gps_ifd[3])  # GPSLongitude, GPSLongitudeRef
        return lat, lon
    except Exception:
        return None


def predict_class_at_point(lat: float, lon: float, model, device):
    """Fetches one recent low-cloud Sentinel-2 scene for a small box around
    (lat, lon) and returns Model 1's predicted class at that point (mode of
    the small patch, robust to being off by a pixel or two)."""
    import numpy as np

    bbox = bbox_around(lat, lon, half_km=1.0)  # small box is enough for one point
    label = f"fieldcheck_{lat:.4f}_{lon:.4f}"
    item = search_scene(bbox, "S1")  # "recent, single date" window -- no pairing needed here
    live_dir = DATA_PROCESSED / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    raw_path = live_dir / f"{label}_rgbnir.tif"
    clip_scene_to_stack(item, bbox, raw_path)
    stack_path = live_dir / f"{label}_stack6.tif"
    profile = build_6channel_stack(raw_path, stack_path)
    class_map, _, _ = predict_class_map(model, stack_path, device)
    h, w = class_map.shape
    center_patch = class_map[max(0, h // 2 - 2):h // 2 + 2, max(0, w // 2 - 2):w // 2 + 2]
    real = center_patch[center_patch != NODATA_CLASS]
    if real.size == 0:
        return NODATA_CLASS, item.datetime.date()
    values, counts = np.unique(real, return_counts=True)
    predicted_class = int(values[counts.argmax()])
    return predicted_class, item.datetime.date()


def log_validation(lat, lon, predicted_class_name, verdict, note):
    VALIDATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not VALIDATION_LOG.exists()
    with open(VALIDATION_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lat": lat, "lon": lon, "predicted_class": predicted_class_name,
            "human_verdict": verdict, "note": note,
        })


def read_validation_log():
    if not VALIDATION_LOG.exists():
        return []
    with open(VALIDATION_LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def render_field_verification_tab(model1, device):
    st.html(
        f"""<div class="wsig-panel">
<div class="wsig-eyebrow">Geo-coded image interpretation</div>
<p style="color:{design.INK_MUTED}; margin:4px 0 0 0; font-size:14px;">
Upload a geo-tagged field photo. Its GPS location is read from the photo automatically where
available; the model's prediction for that exact spot is fetched live from satellite imagery,
and you confirm whether they agree. Every check is logged &mdash; this is the actual
"interpret geo-coded images" validation the PS asks for, not a second model guessing at the
photo.
</p>
<p style="color:{design.INK_MUTED}; margin:4px 0 0 0; font-size:12px;">
Note: on the hosted demo the validation log persists for this session only (it resets on
app reboot/redeploy).
</p>
</div>"""
    )
    st.write("")

    up_photo = st.file_uploader("Upload a geo-tagged photo", type=["jpg", "jpeg", "png"])
    if up_photo is None:
        _render_log_summary()
        return

    # A new upload invalidates any previous check panel (photo and/or coordinates changed).
    if st.session_state.get("field_photo_name") != up_photo.name:
        st.session_state.pop("field_check", None)
        st.session_state["field_photo_name"] = up_photo.name

    photo_bytes = up_photo.getvalue()
    st.image(photo_bytes, caption=up_photo.name, width=400)

    gps = extract_gps_from_exif(photo_bytes)
    col_lat, col_lon = st.columns(2)
    if gps is not None:
        st.success(f"GPS found in photo: {gps[0]:.5f}, {gps[1]:.5f}")
        lat = col_lat.number_input("Latitude", value=gps[0], format="%.5f")
        lon = col_lon.number_input("Longitude", value=gps[1], format="%.5f")
    else:
        st.warning("No GPS data in this photo's EXIF — enter the location manually.")
        lat = col_lat.number_input("Latitude", value=19.8830, format="%.5f")
        lon = col_lon.number_input("Longitude", value=75.9910, format="%.5f")

    if st.button("Check against satellite prediction", type="primary"):
        try:
            with st.spinner("Fetching satellite imagery for this point and running the model..."):
                predicted_class, scene_date = predict_class_at_point(lat, lon, model1, device)
        except Exception as e:
            st.error(f"Couldn't complete this check: {e}")
            return
        st.session_state["field_check"] = {
            "lat": lat, "lon": lon, "predicted_class": predicted_class, "scene_date": scene_date,
        }

    check = st.session_state.get("field_check")
    if check:
        if check["predicted_class"] == NODATA_CLASS:
            st.warning(
                "The satellite scene had no coverage at this point (scene footprint "
                "gap, not a land-cover reading) — no prediction to verify. Try a "
                "nearby point inside the fetched scene."
            )
        else:
            name = CLASS_NAMES[check["predicted_class"]]
            r, g, b = CLASS_COLORS[check["predicted_class"]]
            st.html(
                f"""<div class="wsig-panel">
<div class="wsig-eyebrow">Satellite prediction at this point &middot; {check['scene_date']}</div>
<div style="display:flex; align-items:center; gap:8px; margin-top:6px;">
<div style="width:16px; height:16px; border-radius:3px; background:rgb({r},{g},{b}); border:1px solid rgba(0,0,0,0.15);"></div>
<span style="font-size:18px; color:{design.INK};">{name}</span>
</div>
</div>"""
            )
            st.write("")
            verdict = st.radio("Does the photo match this prediction?", ["Matches", "Doesn't match", "Unsure"], horizontal=True)
            note = st.text_input("Note (optional)")
            if st.button("Log this check"):
                log_validation(check["lat"], check["lon"], name, verdict, note)
                st.success("Logged.")
                del st.session_state["field_check"]
                st.rerun()

    _render_log_summary()


def _render_log_summary():
    rows = read_validation_log()
    if not rows:
        return
    st.html('<div class="wsig-eyebrow" style="margin-top:24px;">Validation log</div>')
    matches = sum(1 for r in rows if r["human_verdict"] == "Matches")
    total_decided = sum(1 for r in rows if r["human_verdict"] in ("Matches", "Doesn't match"))
    if total_decided:
        st.html(design.render_readout_stat(
            "Field-verified agreement rate",
            f"{matches}/{total_decided} ({100*matches/total_decided:.0f}%)",
        ))
    st.dataframe(rows, use_container_width=True, hide_index=True)
