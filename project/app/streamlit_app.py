"""
GeoDhara — PS-26015 demo app.

Wraps the trained pipeline (Model 1 LULC U-Net, Tier-1 rule-based change
detection, rule-based recommendation engine) in an interactive UI. A single
location picker (3 trained-site presets, or search/enter any coordinates)
drives every tab — Land Cover, Change, Condition & Alerts, and Map all render
whatever AOI is currently active in st.session_state["active_aoi"].

Only the trained Model 1 checkpoint needs to be brought in manually (train it
in the Colab notebook, then upload it here); imagery for every AOI — presets
included — is fetched live on demand, the same code path either way.

Run:  .venv/Scripts/python.exe -m streamlit run app/streamlit_app.py

Note: all raw HTML/CSS/SVG is rendered via st.html() / st.sidebar.html(), not
st.markdown(..., unsafe_allow_html=True) -- the latter runs content through a
CommonMark parser first, which terminates "raw HTML block" recognition at the
first blank line, silently leaking the rest as visible escaped text. st.html()
bypasses markdown parsing entirely and is the correct tool for this.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rasterio
import streamlit as st
import torch

from config import CLASS_COLORS, CLASS_NAMES, MODELS_DIR
from model1_unet import build_model as build_model1
from tier1_fallback import summarize_changes
from inference_demo import render_lulc_map, render_change_map
import matplotlib.pyplot as plt
from rasterio.warp import transform_bounds
import design
from aoi_picker import render_picker
from geo_photo import render_field_verification_tab, read_validation_log
import intervention_registry as reg

st.set_page_config(
    page_title="GeoDhara · PS-26015", layout="wide",
    page_icon=str(design.LOGO_PATH),
)
st.html(design.inject_css())

MODEL1_PATH = MODELS_DIR / "model1_lulc_unet.pt"


# ---------------------------------------------------------------- model + active-AOI state

@st.cache_resource
def load_model1():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model1().to(device)
    try:
        ckpt = torch.load(MODEL1_PATH, map_location=device, weights_only=True)
    except Exception as e:
        raise RuntimeError(
            f"Could not load checkpoint at {MODEL1_PATH} ({e}). If this file was "
            "uploaded or copied mid-write, delete it and re-upload a complete "
            "model1_lulc_unet.pt, then reload the page."
        )
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, device, ckpt["epoch"], ckpt.get("val_loss", ckpt.get("val_mean_iou", 0.0))


# ---------------------------------------------------------------- sidebar / model intake

st.sidebar.html(
    f'<div style="display:flex; align-items:center; gap:10px;">'
    f'{design.render_logo(30)}'
    f'<div style="font-family:{design.FONT_DISPLAY}; font-size:20px; font-weight:700;">GeoDhara</div>'
    f'</div>'
    f'<div class="wsig-eyebrow" style="margin-top:6px;">Model intake</div>'
)
st.sidebar.divider()

st.sidebar.html('<div class="wsig-eyebrow">Model checkpoint</div>')
st.sidebar.caption(f"`{MODEL1_PATH.relative_to(MODELS_DIR.parents[0])}`")
if not MODEL1_PATH.exists():
    up_model = st.sidebar.file_uploader("Add model1_lulc_unet.pt", type=["pt"], label_visibility="collapsed")
    if up_model is not None:
        MODEL1_PATH.write_bytes(up_model.getvalue())
        load_model1.clear()  # cache is keyed on zero args, not file content -- without this the old weights persist
        st.sidebar.success("Checkpoint saved.")
        st.rerun()
else:
    st.sidebar.html(f'<span style="color:{design.SAGE};">● found</span>')
    with st.sidebar.expander("Replace checkpoint"):
        up_replace = st.file_uploader("Replace model1_lulc_unet.pt", type=["pt"], label_visibility="collapsed")
        if up_replace is not None:
            MODEL1_PATH.write_bytes(up_replace.getvalue())
            load_model1.clear()
            st.sidebar.success("Checkpoint replaced.")
            st.rerun()

st.sidebar.caption(
    "Imagery isn't uploaded — every location (presets included) is fetched live from Sentinel-2 "
    "on demand, using the coordinates below."
)

if not MODEL1_PATH.exists():
    st.html(design.render_masthead())
    st.html(
        f"""<div class="wsig-panel" style="max-width:560px;">
<div class="wsig-eyebrow">No signal yet</div>
<p style="color:{design.TEXT}; margin:6px 0 0 0;">
Train Model 1 in the Colab notebook (<code>notebooks/watershed_pipeline.ipynb</code>), then bring
the checkpoint here:
</p>
<ul style="color:{design.TEXT_MUTED}; margin:8px 0 0 0;">
<li>copy <code>models/model1_lulc_unet.pt</code> from your Drive
(<code>MyDrive/watershed_ps26015/</code>) into the matching local folder, or</li>
<li>add it directly with the uploader in the sidebar.</li>
</ul>
</div>"""
    )
    st.stop()


# ---------------------------------------------------------------- model load (definition is above, with sidebar)


model1, device, epoch, val_loss = load_model1()

if "active_aoi" not in st.session_state:
    st.session_state["active_aoi"] = None  # nothing picked yet -- don't auto-fetch a default

aoi = st.session_state["active_aoi"]


# ---------------------------------------------------------------- UI

if aoi is None:
    st.html(design.render_header(None, None, None, epoch, val_loss, device))
else:
    st.html(design.render_header(aoi["display_name"], aoi["lat"], aoi["lon"], epoch, val_loss, device, aoi["trained"]))

render_picker(model1, device)
aoi = st.session_state["active_aoi"]  # picker may have just set/replaced it

if aoi is None:
    st.write("")
    st.html(design.render_pick_location_prompt())
    st.stop()

st.write("")

tab_lulc, tab_change, tab_health, tab_map, tab_field, tab_interventions, tab_about = st.tabs(
    ["Land Cover", "Change", "Condition & Alerts", "Map", "Field Verification", "Interventions", "About"]
)

with tab_lulc:
    st.html(f'<div class="wsig-eyebrow">Model 1 · Land use / land cover · '
            f'T1 {aoi["t1_date"]} &rarr; T2 {aoi["t2_date"]}</div>')
    with plt.style.context({**design.MPL_LIGHT_RC}):
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        render_lulc_map(aoi["class_t1"], axes[0], "T1")
        render_lulc_map(aoi["class_t2"], axes[1], "T2")
        fig.patch.set_facecolor(design.PAPER)
        st.pyplot(fig)
        plt.close(fig)
    st.html(design.render_legend(CLASS_NAMES, CLASS_COLORS))

with tab_change:
    st.html('<div class="wsig-eyebrow">Tier-1 rule-based diff · T1 &rarr; T2</div>')
    with plt.style.context({**design.MPL_LIGHT_RC}):
        fig, ax = plt.subplots(figsize=(6, 5))
        render_change_map(aoi["change_map"], ax, "")
        fig.patch.set_facecolor(design.PAPER)
        st.pyplot(fig)
        plt.close(fig)

    st.html('<div class="wsig-eyebrow" style="margin-top:8px;">Area by change type</div>')
    summary = summarize_changes(aoi["change_map"])
    st.table({name: f"{stats['hectares']} ha" for name, stats in summary.items()})

with tab_health:
    col1, col2 = st.columns([1, 2])
    with col1:
        gauge_fig = design.render_gauge_fig(aoi["health"])
        st.pyplot(gauge_fig)
        plt.close(gauge_fig)
    with col2:
        trend = aoi["trend"]
        trend_word = "improving" if trend > 0.01 else ("declining" if trend < -0.01 else "stable")
        trend_color = design.SAGE if trend > 0.01 else (design.DANGER if trend < -0.01 else design.TEXT_MUTED)
        st.html(design.render_readout_stat("NDVI trend, T1 &rarr; T2", f"{trend:+.4f} &middot; {trend_word}", trend_color))
        st.html("<div style='height:10px;'></div>")
        st.html(design.render_readout_stat("Watershed condition score", f"{aoi['health']:.1f} / 100"))

    st.html('<div class="wsig-eyebrow" style="margin-top:20px;">Alerts &amp; recommendations</div>')
    for alert in aoi["alerts"]:
        st.html(design.render_alert_card(alert["severity"], alert["message"], alert["area_ha"], alert.get("evidence")))

with tab_map:
    st.html('<div class="wsig-eyebrow">Interactive LULC overlay · T2</div>')
    import numpy as np
    from streamlit_folium import st_folium
    import folium

    if aoi.get("watershed_caveat"):
        st.caption(f"{aoi['watershed_caveat']}")

    class_t2, profile = aoi["class_t2"], aoi["profile"]
    height, width = class_t2.shape
    color_img = np.zeros((height, width, 3), dtype="uint8")
    for cls, rgb in CLASS_COLORS.items():
        color_img[class_t2 == cls] = rgb
    bounds = rasterio.transform.array_bounds(height, width, profile["transform"])
    minx, miny, maxx, maxy = transform_bounds(profile["crs"], "EPSG:4326", *bounds)

    # Plain OpenStreetMap tiles, not CartoDB -- CartoDB's free tile service caps out at a
    # certain zoom level and then prompts for an API key mid-use, which is a bad thing to
    # hit live in a demo. OSM has no such cap.
    fmap = folium.Map(
        location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=14,
        tiles="OpenStreetMap",
    )
    folium.raster_layers.ImageOverlay(
        image=color_img, bounds=[[miny, minx], [maxy, maxx]], opacity=0.7, name="LULC (Model 1)",
    ).add_to(fmap)

    # Watershed boundary + drainage network, DEM-derived (watershed_delineation.py).
    # Rendered as their own toggle-able overlays (RGBA, transparent where absent)
    # rather than baked into color_img, so they read as an outline/lines on top
    # of the LULC fill instead of obscuring it.
    if aoi.get("watershed_mask") is not None:
        from scipy import ndimage
        boundary = aoi["watershed_mask"] & ~ndimage.binary_erosion(aoi["watershed_mask"], iterations=2)
        boundary_rgba = np.zeros((height, width, 4), dtype="uint8")
        boundary_rgba[boundary] = (255, 140, 0, 255)
        folium.raster_layers.ImageOverlay(
            image=boundary_rgba, bounds=[[miny, minx], [maxy, maxx]], opacity=1.0,
            name="Watershed boundary (approx., DEM-derived)",
        ).add_to(fmap)
    if aoi.get("drainage_network") is not None:
        drainage_rgba = np.zeros((height, width, 4), dtype="uint8")
        drainage_rgba[aoi["drainage_network"]] = (0, 200, 255, 255)
        folium.raster_layers.ImageOverlay(
            image=drainage_rgba, bounds=[[miny, minx], [maxy, maxx]], opacity=1.0,
            name="Drainage network (DEM-derived)",
        ).add_to(fmap)

    folium.LayerControl().add_to(fmap)
    # returned_objects=[] -- without this, st_folium reports back bounds/zoom/center on
    # every render, which are never bit-for-bit identical run to run, so Streamlit treats
    # it as a changed widget value and reruns the script mid-interaction. That rerun is
    # what dims ("fades") the map while you're hovering/panning it. A stable key (tied to
    # the active AOI) keeps the same component instance across reruns instead of remounting.
    st_folium(
        fmap, width=None, height=550, use_container_width=True,
        returned_objects=[], key=f"lulc_map_{aoi['key']}",
    )

with tab_field:
    render_field_verification_tab(model1, device)

with tab_interventions:
    st.html(
        f"""<div class="wsig-panel">
<div class="wsig-eyebrow">Intervention registry</div>
<p style="color:{design.INK_MUTED}; margin:4px 0 0 0; font-size:14px;">
Track individual watershed structures (check dams, farm ponds, percolation tanks) as real
records, each connected to the currently-active AOI's satellite evidence at its exact location
&mdash; and to any geo-tagged Field Verification photo taken nearby. This is the actual
"integrated spatial analysis," not just documentation, the PS asks for.
</p>
<p style="color:{design.INK_MUTED}; margin:4px 0 0 0; font-size:12px;">
Note: on the hosted demo these records persist for this session only (the log resets on
app reboot/redeploy) — export anything you need before leaving.
</p>
</div>"""
    )
    st.write("")

    with st.expander("Add an intervention", expanded=not reg.read_interventions()):
        c1, c2 = st.columns(2)
        iv_name = c1.text_input("Name", placeholder="e.g. Check Dam #3")
        iv_type = c2.selectbox("Type", reg.INTERVENTION_TYPES)
        c3, c4 = st.columns(2)
        iv_lat = c3.number_input("Latitude", value=aoi["lat"], format="%.5f", key=f"iv_lat_{aoi['key']}")
        iv_lon = c4.number_input("Longitude", value=aoi["lon"], format="%.5f", key=f"iv_lon_{aoi['key']}")
        iv_notes = st.text_input("Notes (optional)")
        if st.button("Add intervention", type="primary") and iv_name:
            reg.add_intervention(iv_name, iv_type, iv_lat, iv_lon, iv_notes)
            st.success(f'Added "{iv_name}".')
            st.rerun()

    interventions = reg.read_interventions()
    if not interventions:
        st.caption("No interventions recorded yet.")
    else:
        st.html('<div class="wsig-eyebrow" style="margin-top:16px;">Recorded interventions</div>')
        st.dataframe(interventions, use_container_width=True, hide_index=True)

        labels = [f'{r["name"]} ({r["type"]})' for r in interventions]
        picked_idx = st.selectbox(
            "Select an intervention to see its evidence", range(len(interventions)),
            format_func=lambda i: labels[i],
        )
        iv = interventions[picked_idx]
        iv_lat, iv_lon = float(iv["lat"]), float(iv["lon"])

        evidence = reg.sample_evidence_at_point(iv_lat, iv_lon, aoi)
        if not evidence["in_aoi"]:
            st.warning(
                f'"{iv["name"]}" is outside the currently active AOI ({aoi["display_name"]}) -- '
                "pick the location it actually falls within to see satellite evidence for it."
            )
        else:
            st.caption(
                f"Condition over the available imagery window (T1 {evidence['t1_date']} → "
                f"T2 {evidence['t2_date']}) at this point -- not a claim of before/after the "
                "intervention itself; Kadwanchi's real structures predate this imagery by "
                "15+ years, so genuine pre/post-construction comparison isn't possible with "
                "Sentinel-2 data."
            )
            ec1, ec2 = st.columns(2)
            with ec1:
                st.html(design.render_readout_stat("Land cover, T1", evidence["class_t1_name"]))
                st.html("<div style='height:8px;'></div>")
                st.html(design.render_readout_stat("NDVI, T1", f"{evidence['ndvi_t1']:+.3f}"))
            with ec2:
                st.html(design.render_readout_stat("Land cover, T2", evidence["class_t2_name"]))
                st.html("<div style='height:8px;'></div>")
                st.html(design.render_readout_stat("NDVI, T2", f"{evidence['ndvi_t2']:+.3f}"))

            # Intervention outcome assessment (Task 2.5)
            outcome = reg.compute_intervention_outcome(evidence)
            st.html('<div class="wsig-eyebrow" style="margin-top:18px;">Spatial Outcome Assessment</div>')
            outcome_accent = design.SAGE if ("Positive" in outcome["verdict"] or "Strong" in outcome["verdict"]) else (design.AMBER if "Some" in outcome["verdict"] else design.INK_MUTED)
            st.html(design.render_readout_stat("Observed Spatial Outcome", outcome["verdict"], accent=outcome_accent))
            st.html(f'<p style="font-size:13px; color:{design.INK_MUTED}; margin-top:6px; line-height:1.4;">{outcome["note"]}</p>')

            photo_rows = read_validation_log()
            linked = reg.link_nearby_photos(iv_lat, iv_lon, photo_rows)
            st.html('<div class="wsig-eyebrow" style="margin-top:16px;">Linked field-verification photos</div>')
            if linked:
                st.dataframe(linked, use_container_width=True, hide_index=True)
            else:
                st.caption(
                    f"None within {reg.PHOTO_LINK_THRESHOLD_M:.0f}m yet -- log a geo-tagged photo "
                    "near this point in the Field Verification tab to connect one."
                )

with tab_about:
    st.html(
        f"""<div class="wsig-panel">
<div class="wsig-eyebrow">Problem statement PS-26015</div>
<p style="color:{design.TEXT}; margin-top:4px;">
Geospatial techniques for visualization and analysis, interpreting geo-coded images
to improve watershed development outcomes — Ministry of Rural Development, Smart India
Hackathon 2026.
</p>
<div class="wsig-eyebrow" style="margin-top:18px;">System Architecture</div>
<ul style="color:{design.TEXT_MUTED};">
<li><b style="color:{design.TEXT};">Model 1 (LULC Segmentation)</b> — a U-Net with ResNet18 encoder reads a 6-channel
satellite stack (R, G, B, NIR, NDVI, NDWI) and classifies every 10m pixel into one of
7 land-cover categories. Trained across diverse benchmark sites (Kadwanchi, Tamhini Ghat, Donimalai,
Jayakwadi Dam) to address class imbalance.</li>
<li><b style="color:{design.TEXT};">Temporal Change Detection</b> — rule-based bi-temporal diff comparing
classified Sentinel-2 scenes, isolating vegetation gain, new water retention, excavation, and degradation.</li>
<li><b style="color:{design.TEXT};">Catchment &amp; Drainage Delineation</b> — physical hydrological boundaries
and drainage flow paths derived from Copernicus GLO-30 DEM elevation rasters (30m resolution),
rather than arbitrary geometric bounding boxes.</li>
<li><b style="color:{design.TEXT};">Intervention Registry</b> — connects geo-located watershed conservation
assets (check dams, ponds, bunds) directly with temporal satellite evidence and ground photos.</li>
<li><b style="color:{design.TEXT};">Multi-Source Evidence Fusion</b> — transparent, deterministic rule fusion
combining land-cover classification, NDVI trends, NDWI water extent, and drainage network position.</li>
</ul>
</div>"""
    )

    # Scientific Validation Section (Task 2.1 & 2.3)
    import json
    lulc_val_path = OUTPUTS_DIR / "lulc_validation.json"
    cm_png_path = OUTPUTS_DIR / "lulc_confusion_matrix.png"
    change_val_path = OUTPUTS_DIR / "change_validation.json"

    st.write("")
    st.html('<div class="wsig-eyebrow" style="margin-top:20px;">Scientific Validation &amp; Metrics</div>')

    if lulc_val_path.exists():
        with open(lulc_val_path, encoding="utf-8") as f:
            l_val = json.load(f)

        c_m1, c_m2, c_m3 = st.columns(3)
        with c_m1:
            st.html(design.render_readout_stat("Model 1 Pixel Accuracy", f"{l_val['pixel_accuracy']*100:.1f}%", accent=design.SAGE))
        with c_m2:
            st.html(design.render_readout_stat("Model 1 Mean IoU", f"{l_val['mean_iou']*100:.1f}%", accent=design.SAGE))
        with c_m3:
            st.html(design.render_readout_stat("Validation Scheme", "7 Classes · 10m Res"))

        st.html('<div class="wsig-eyebrow" style="margin-top:16px;">Model 1 Per-Class Performance</div>')
        rows = []
        for c_name, m_dict in l_val.get("per_class", {}).items():
            if m_dict.get("support", 0) > 0:
                rows.append({
                    "Class": c_name,
                    "Support (px)": f"{m_dict['support']:,}",
                    "Precision": f"{m_dict['precision']:.3f}",
                    "Recall": f"{m_dict['recall']:.3f}",
                    "IoU": f"{m_dict['iou']:.3f}",
                    "F1 Score": f"{m_dict['f1']:.3f}",
                })
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)

        if cm_png_path.exists():
            st.html('<div class="wsig-eyebrow" style="margin-top:16px;">Model 1 Confusion Matrix (Row-Normalized)</div>')
            st.image(str(cm_png_path), width=650)

    if change_val_path.exists():
        with open(change_val_path, encoding="utf-8") as f:
            c_val = json.load(f)

        st.html('<div class="wsig-eyebrow" style="margin-top:24px;">Change Detection Validation (20 Reference Regions)</div>')
        ch1, ch2, ch3, ch4 = st.columns(4)
        with ch1:
            st.html(design.render_readout_stat("Precision", f"{c_val['precision']:.3f}", accent=design.SAGE))
        with ch2:
            st.html(design.render_readout_stat("Recall", f"{c_val['recall']:.3f}", accent=design.SAGE))
        with ch3:
            st.html(design.render_readout_stat("F1 Score", f"{c_val['f1']:.3f}", accent=design.SAGE))
        with ch4:
            st.html(design.render_readout_stat("Intersection / Union", f"{c_val['iou']:.3f}", accent=design.SAGE))

    # Government Data Adapter Architecture & Limitation Notice (Task 3.2)
    st.write("")
    st.html(
        f"""<div class="wsig-panel" style="margin-top:20px;">
<div class="wsig-eyebrow">Data Sources &amp; Government Platform Integration</div>
<p style="color:{design.INK}; font-size:14px; margin-top:6px; line-height:1.6;">
Due to unavailable or unauthorized access to certain government datasets and APIs during development,
this prototype uses equivalent open-access and reference datasets to demonstrate the analytical workflow.
The data ingestion layer is designed to accept authorized SRISHTI-DRISHTI, Bhuvan, and Bhoonidhi data sources
when access becomes available.
</p>
<div style="font-size:12px; color:{design.INK_MUTED}; margin-top:8px;">
Reference Datasets: Sentinel-2 L2A (10m multispectral via Earth Search / AWS Open Data), ESA WorldCover (10m global reference baseline), Copernicus GLO-30 DEM (30m elevation model).
</div>
</div>"""
    )
