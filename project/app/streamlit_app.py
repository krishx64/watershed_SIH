"""
Watershed Signal — PS-26015 demo app.

Wraps the trained pipeline (Model 1 LULC U-Net, Tier-1 rule-based change
detection, rule-based recommendation engine) in an interactive UI. A single
location picker (3 trained-site presets, or search/enter any coordinates)
drives every tab — Land Cover, Change, Health & Alerts, and Map all render
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
from geo_photo import render_field_verification_tab

st.set_page_config(
    page_title="Watershed Signal · PS-26015", layout="wide",
    page_icon=str(design.LOGO_PATH),
)
st.html(design.inject_css())

MODEL1_PATH = MODELS_DIR / "model1_lulc_unet.pt"


# ---------------------------------------------------------------- sidebar / model intake

st.sidebar.html(
    f'<div style="display:flex; align-items:center; gap:10px;">'
    f'{design.render_logo(30)}'
    f'<div style="font-family:{design.FONT_DISPLAY}; font-size:20px; font-weight:700;">Watershed Signal</div>'
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
        st.sidebar.success("Checkpoint saved.")
        st.rerun()
else:
    st.sidebar.html(f'<span style="color:{design.SAGE};">● found</span>')

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


# ---------------------------------------------------------------- model + active-AOI state

@st.cache_resource
def load_model1():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_model1().to(device)
    ckpt = torch.load(MODEL1_PATH, map_location=device)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    return model, device, ckpt["epoch"], ckpt["val_loss"]


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

tab_lulc, tab_change, tab_health, tab_map, tab_field, tab_about = st.tabs(
    ["Land Cover", "Change", "Health & Alerts", "Map", "Field Verification", "About"]
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
    st.html(design.render_legend(CLASS_NAMES, CLASS_COLORS))

with tab_change:
    st.html('<div class="wsig-eyebrow">Tier-1 rule-based diff · T1 &rarr; T2</div>')
    with plt.style.context({**design.MPL_LIGHT_RC}):
        fig, ax = plt.subplots(figsize=(6, 5))
        render_change_map(aoi["change_map"], ax, "")
        fig.patch.set_facecolor(design.PAPER)
        st.pyplot(fig)

    st.html('<div class="wsig-eyebrow" style="margin-top:8px;">Area by change type</div>')
    summary = summarize_changes(aoi["change_map"])
    st.table({name: f"{stats['hectares']} ha" for name, stats in summary.items()})

with tab_health:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.pyplot(design.render_gauge_fig(aoi["health"]))
    with col2:
        trend = aoi["trend"]
        trend_word = "improving" if trend > 0.01 else ("declining" if trend < -0.01 else "stable")
        trend_color = design.SAGE if trend > 0.01 else (design.DANGER if trend < -0.01 else design.TEXT_MUTED)
        st.html(design.render_readout_stat("NDVI trend, T1 &rarr; T2", f"{trend:+.4f} &middot; {trend_word}", trend_color))
        st.html("<div style='height:10px;'></div>")
        st.html(design.render_readout_stat("Watershed health", f"{aoi['health']:.1f} / 100"))

    st.html('<div class="wsig-eyebrow" style="margin-top:20px;">Alerts &amp; recommendations</div>')
    for alert in aoi["alerts"]:
        st.html(design.render_alert_card(alert["severity"], alert["message"], alert["area_ha"]))

with tab_map:
    st.html('<div class="wsig-eyebrow">Interactive LULC overlay · T2</div>')
    import numpy as np
    from streamlit_folium import st_folium
    import folium

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

with tab_about:
    st.html(
        f"""<div class="wsig-panel">
<div class="wsig-eyebrow">Problem statement PS-26015</div>
<p style="color:{design.TEXT}; margin-top:4px;">
Geospatial techniques for visualization and analysis, interpreting geo-coded images
to improve watershed development outcomes — Ministry of Rural Development, Smart India
Hackathon 2026.
</p>
<div class="wsig-eyebrow" style="margin-top:18px;">How it reads the ground</div>
<ul style="color:{design.TEXT_MUTED};">
<li><b style="color:{design.TEXT};">Model 1</b> — a U-Net (ResNet18 encoder) reads a 6-channel
satellite stack (R, G, B, NIR, NDVI, NDWI) and classifies every 10m patch into one of
7 land-cover types. Trained on 3 real sites (Kadwanchi, Tamhini Ghat, Donimalai) chosen to
cover the classes any single site lacked — see the presets above.</li>
<li><b style="color:{design.TEXT};">Change detection</b> — a rule-based diff of two Model 1
passes, no separate training needed.</li>
<li><b style="color:{design.TEXT};">Recommendation engine</b> — plain if-then rules, no ML —
every alert traces back to a specific, auditable reason.</li>
<li><b style="color:{design.TEXT};">Location picker</b> — presets are the model's actual
trained sites (marked <span style="color:{design.SAGE};">TRAINED SITE</span>); anything else
you search is genuine unseen-location inference, marked
<span style="color:{design.AMBER};">LIVE &middot; UNSEEN LOCATION</span> — worth knowing which
kind of result you're looking at.</li>
</ul>
<div class="wsig-eyebrow" style="margin-top:18px;">Data sources</div>
<p style="color:{design.TEXT_MUTED};">
Sentinel-2 L2A (Earth Search / AWS Open Data) and ESA WorldCover, both free and
automatic for any coordinates — no registration wait. Bhuvan LULC (India-specific,
needs registration) is the planned upgrade once available.
</p>
</div>"""
    )
