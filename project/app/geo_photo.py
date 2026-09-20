"""
Geo-coded photo field verification -- integrates field photography with
satellite imagery, DEM-derived watershed delineation, nearby interventions,
and multi-source evidence fusion.

Upload a geo-tagged photo (GPS read from EXIF, or entered manually); the app
queries satellite imagery, evaluates local land cover and temporal change,
verifies drainage connectivity, identifies the host watershed, matches nearby
interventions within 500m, and presents an explainable decision card.
"""

import csv
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
from PIL import Image, ExifTags

# streamlit is only needed for the UI (render_field_verification_tab). The API
# server imports read_validation_log from here, which is pure CSV I/O, so the
# Docker image can omit streamlit.
try:
    import streamlit as st
except ImportError:
    st = None

from config import DATA_PROCESSED, CLASS_NAMES, CLASS_COLORS, CHANGE_CLASS_NAMES, NODATA_CLASS
from data_download import search_scene, clip_scene_to_stack
from preprocessing import build_6channel_stack
from inference_demo import predict_class_map
from aoi_picker import bbox_around
from evidence_fusion import fuse_evidence
from intervention_registry import sample_evidence_at_point, read_interventions, latlon_to_pixel, _haversine_m
from watershed_delineation import get_watershed_context
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
    (lat, lon) and returns Model 1's predicted class and spectral info at that point."""
    bbox = bbox_around(lat, lon, half_km=1.0)
    label = f"fieldcheck_{lat:.4f}_{lon:.4f}"
    item = search_scene(bbox, "S1")
    live_dir = DATA_PROCESSED / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    raw_path = live_dir / f"{label}_rgbnir.tif"
    clip_scene_to_stack(item, bbox, raw_path)
    stack_path = live_dir / f"{label}_stack6.tif"
    profile = build_6channel_stack(raw_path, stack_path)
    class_map, img, _ = predict_class_map(model, stack_path, device)
    h, w = class_map.shape
    center_patch = class_map[max(0, h // 2 - 2):h // 2 + 2, max(0, w // 2 - 2):w // 2 + 2]
    real = center_patch[center_patch != NODATA_CLASS]
    if real.size == 0:
        predicted_class = NODATA_CLASS
    else:
        values, counts = np.unique(real, return_counts=True)
        predicted_class = int(values[counts.argmax()])

    ndvi_patch = img[4, max(0, h // 2 - 2):h // 2 + 2, max(0, w // 2 - 2):w // 2 + 2]
    ndwi_patch = img[5, max(0, h // 2 - 2):h // 2 + 2, max(0, w // 2 - 2):w // 2 + 2]
    ndvi_val = float(np.mean(ndvi_patch)) if ndvi_patch.size > 0 else 0.0
    ndwi_val = float(np.mean(ndwi_patch)) if ndwi_patch.size > 0 else 0.0

    return {
        "predicted_class": predicted_class,
        "scene_date": str(item.datetime.date()),
        "profile": profile,
        "ndvi": ndvi_val,
        "ndwi": ndwi_val,
        "class_map": class_map,
        "img": img,
        "bbox": bbox,
    }


def _find_nearest_intervention(lat: float, lon: float, max_dist_m: float = 500.0) -> dict | None:
    interventions = read_interventions()
    nearest = None
    min_dist = max_dist_m
    for iv in interventions:
        try:
            d = _haversine_m(lat, lon, float(iv["lat"]), float(iv["lon"]))
            if d <= min_dist:
                min_dist = d
                nearest = {**iv, "distance_m": round(d, 1)}
        except (ValueError, KeyError):
            continue
    return nearest


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
<div class="wsig-eyebrow">Geo-coded field observation interpretation</div>
<p style="color:{design.INK_MUTED}; margin:4px 0 0 0; font-size:14px;">
Upload a geo-tagged field photo. Its GPS location is read from the photo EXIF metadata automatically;
the system extracts multi-temporal satellite evidence, DEM watershed context, and nearby intervention
records, and generates an integrated assessment card. Confirm or flag any discrepancy to maintain the
validation log.
</p>
</div>"""
    )
    st.write("")

    up_photo = st.file_uploader("Upload a geo-tagged photo", type=["jpg", "jpeg", "png"])
    if up_photo is None:
        _render_log_summary()
        return

    # Invalidate cached observation if photo changes
    if st.session_state.get("field_photo_name") != up_photo.name:
        st.session_state.pop("field_observation", None)
        st.session_state["field_photo_name"] = up_photo.name

    photo_bytes = up_photo.getvalue()
    st.image(photo_bytes, caption=up_photo.name, width=400)

    gps = extract_gps_from_exif(photo_bytes)
    col_lat, col_lon = st.columns(2)
    if gps is not None:
        st.success(f"GPS found in photo metadata: {gps[0]:.5f} N, {gps[1]:.5f} E")
        lat = col_lat.number_input("Latitude", value=gps[0], format="%.5f")
        lon = col_lon.number_input("Longitude", value=gps[1], format="%.5f")
    else:
        st.warning("No GPS data found in this photo's EXIF metadata. Please specify the coordinates manually.")
        lat = col_lat.number_input("Latitude", value=19.8830, format="%.5f")
        lon = col_lon.number_input("Longitude", value=75.9910, format="%.5f")

    if st.button("Analyze field observation against satellite data", type="primary"):
        with st.spinner("Fetching satellite imagery, DEM watershed context, and fusing evidence..."):
            try:
                active_aoi = st.session_state.get("active_aoi")
                in_active = False

                # 1. Fetch satellite prediction at point
                predict_res = predict_class_at_point(lat, lon, model1, device)

                # Check if point falls within active AOI
                if active_aoi is not None and active_aoi.get("profile") is not None:
                    pixel = latlon_to_pixel(lat, lon, active_aoi["profile"])
                    if pixel is not None:
                        in_active = True

                if in_active and active_aoi is not None:
                    ev = sample_evidence_at_point(lat, lon, active_aoi)
                    class_t2 = ev["class_t2"]
                    class_t2_name = ev["class_t2_name"]
                    class_t1 = ev["class_t1"]
                    class_t1_name = ev["class_t1_name"]
                    ndvi_t1 = ev["ndvi_t1"]
                    ndvi_t2 = ev["ndvi_t2"]
                    ndwi_t1 = ev["ndwi_t1"]
                    ndwi_t2 = ev["ndwi_t2"]
                    scene_date = str(ev.get("t2_date", predict_res["scene_date"]))

                    # Sample change class
                    row, col = latlon_to_pixel(lat, lon, active_aoi["profile"])
                    h, w = active_aoi["class_t2"].shape
                    r0, r1 = max(0, row - 2), min(h, row + 3)
                    c0, c1 = max(0, col - 2), min(w, col + 3)
                    change_patch = active_aoi["change_map"][r0:r1, c0:c1]
                    vals, cnts = np.unique(change_patch, return_counts=True)
                    change_cls = int(vals[cnts.argmax()]) if vals.size > 0 else 0
                    change_name = CHANGE_CLASS_NAMES.get(change_cls, "No change")

                    # Drainage connectivity
                    drainage_mask = active_aoi.get("drainage_network")
                    drainage_connected = bool(np.any(drainage_mask[r0:r1, c0:c1])) if drainage_mask is not None else False

                    # Watershed context
                    watershed_meta = active_aoi.get("watershed_context")
                    if not watershed_meta:
                        watershed_meta = get_watershed_context(bbox_around(lat, lon, 1.0), active_aoi["profile"])

                    health_score = active_aoi.get("health")
                    ndvi_trend = active_aoi.get("trend")
                else:
                    class_t2 = predict_res["predicted_class"]
                    class_t2_name = CLASS_NAMES.get(class_t2, "No data")
                    class_t1 = None
                    class_t1_name = None
                    ndvi_t1 = None
                    ndvi_t2 = predict_res["ndvi"]
                    ndwi_t1 = None
                    ndwi_t2 = predict_res["ndwi"]
                    scene_date = predict_res["scene_date"]
                    change_cls = 0
                    change_name = "Baseline observation (single date)"
                    health_score = None
                    ndvi_trend = None

                    # Watershed context from DEM
                    watershed_meta = get_watershed_context(predict_res["bbox"], predict_res["profile"])
                    drainage_mask = watershed_meta.get("drainage_network")
                    h, w = predict_res["class_map"].shape
                    r0, r1 = max(0, h // 2 - 2), min(h, h // 2 + 3)
                    c0, c1 = max(0, w // 2 - 2), min(w, w // 2 + 3)
                    drainage_connected = bool(np.any(drainage_mask[r0:r1, c0:c1])) if drainage_mask is not None else False

                # Nearest intervention within 500m
                nearest_iv = _find_nearest_intervention(lat, lon, max_dist_m=500.0)

                # Fuse evidence
                assessment = fuse_evidence(
                    lulc_t2=class_t2,
                    ndvi_t1=ndvi_t1,
                    ndvi_t2=ndvi_t2,
                    ndwi_t1=ndwi_t1,
                    ndwi_t2=ndwi_t2,
                    change_class=change_cls,
                    drainage_connected=drainage_connected,
                    health_score=health_score,
                    ndvi_trend=ndvi_trend,
                )

                spatial_evidence = {
                    "class_t2_name": class_t2_name,
                    "class_t1_name": class_t1_name,
                    "ndvi_t1": ndvi_t1,
                    "ndvi_t2": ndvi_t2,
                    "ndwi_t1": ndwi_t1,
                    "ndwi_t2": ndwi_t2,
                    "drainage_connected": drainage_connected,
                    "change_name": change_name,
                }

                st.session_state["field_observation"] = {
                    "photo_caption": up_photo.name,
                    "lat": lat,
                    "lon": lon,
                    "scene_date": scene_date,
                    "watershed_meta": watershed_meta,
                    "nearest_intervention": nearest_iv,
                    "spatial_evidence": spatial_evidence,
                    "assessment": assessment,
                    "predicted_class_name": class_t2_name,
                }
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

    obs = st.session_state.get("field_observation")
    if obs:
        st.html(design.render_observation_card(
            photo_caption=obs["photo_caption"],
            lat=obs["lat"],
            lon=obs["lon"],
            scene_date=obs["scene_date"],
            watershed_meta=obs["watershed_meta"],
            nearest_intervention=obs["nearest_intervention"],
            spatial_evidence=obs["spatial_evidence"],
            assessment=obs["assessment"],
        ))

        st.write("")
        st.html('<div class="wsig-eyebrow" style="margin-top:16px;">Ground Verification Entry</div>')
        verdict = st.radio(
            "Does the uploaded ground photo match the satellite classification?",
            ["Matches", "Doesn't match", "Unsure"],
            horizontal=True,
        )
        note = st.text_input("Verification notes (optional)")
        if st.button("Log ground verification"):
            log_validation(obs["lat"], obs["lon"], obs["predicted_class_name"], verdict, note)
            st.success("Verification check successfully recorded in log.")
            st.session_state.pop("field_observation", None)
            st.rerun()

    _render_log_summary()


def _render_log_summary():
    rows = read_validation_log()
    if not rows:
        return
    st.html('<div class="wsig-eyebrow" style="margin-top:28px;">Field Validation Registry</div>')
    matches = sum(1 for r in rows if r.get("human_verdict") == "Matches")
    total_decided = sum(1 for r in rows if r.get("human_verdict") in ("Matches", "Doesn't match"))

    col1, col2 = st.columns([2, 1])
    with col1:
        if total_decided > 0:
            rate_pct = 100.0 * matches / total_decided
            st.html(design.render_readout_stat(
                "Photo Interpretation Agreement Rate",
                f"{matches}/{total_decided} ({rate_pct:.1f}%)",
                accent=design.SAGE if rate_pct >= 70 else design.AMBER,
            ))
        else:
            st.html(design.render_readout_stat("Photo Interpretation Agreement Rate", "Pending Reviews"))

    with col2:
        # Download validation log as CSV (Task 2.2)
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        st.write("")
        st.download_button(
            label="Download validation log (CSV)",
            data=csv_buffer.getvalue(),
            file_name="field_validation_log.csv",
            mime="text/csv",
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)
