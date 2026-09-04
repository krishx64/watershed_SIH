"""
Unified AOI picker: pick one of the 3 trained sites (Kadwanchi, Tamhini Ghat,
Donimalai) or search/enter coordinates for anywhere else. Whichever AOI is
active drives every main tab (Land Cover, Change, Health & Alerts, Map) via
st.session_state["active_aoi"] -- there's no separate "explore" panel; picking
a location IS the main flow.

Presets and custom searches both run the same live pipeline (fetch a fresh
Sentinel-2 T1/T2 pair, run the trained model, Tier-1 change detection) --
the only difference is presets are pre-filled coordinates for known-good
sites the model was actually trained on, which the header marks with a
"TRAINED SITE" badge so that distinction stays visible without needing
separate UI real estate for it.

Reuses the same tested pipeline functions as the rest of the project
(search_scene/clip_scene_to_stack from data_download.py, build_6channel_stack
from preprocessing.py, predict_class_map from inference_demo.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import requests
import streamlit as st

from config import AOI_CENTER_LAT, AOI_CENTER_LON, AOI_NAME, DATA_PROCESSED
from data_download import search_scene, clip_scene_to_stack
from preprocessing import build_6channel_stack
from inference_demo import predict_class_map
from tier1_fallback import run_tier1
from recommendation_engine import compute_health_score, generate_alerts, ndvi_trend

LIVE_DIR = DATA_PROCESSED / "live"
LIVE_DIR.mkdir(parents=True, exist_ok=True)

HALF_KM = 4.5  # ~9km x 9km box, consistent with the rest of the project's AOIs

# The 3 sites Model 1 was actually trained on (see config.AOI_JOBS / AUX_AOIS).
# Kadwanchi is the primary (has a real T1/T2 change-detection story); the
# other two were auxiliary/training-only, but their coordinates are real and
# make perfectly good presets to explore here too.
PRESET_AOIS = [
    {"key": AOI_NAME, "display_name": "Kadwanchi Watershed", "lat": AOI_CENTER_LAT, "lon": AOI_CENTER_LON},
    {"key": "tamhini_ghat_forest", "display_name": "Tamhini Ghat", "lat": 18.4493, "lon": 73.4227},
    {"key": "donimalai_barren", "display_name": "Donimalai Mine", "lat": 15.0589, "lon": 76.5937},
]


def geocode(place_name: str):
    """Free-text place name -> (lat, lon, display_name), via OpenStreetMap Nominatim. None if not found."""
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place_name, "format": "json", "limit": 1, "countrycodes": "in"},
        headers={"User-Agent": "watershed-signal-sih2026-demo/1.0 (hackathon prototype)"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"]), results[0].get("display_name", place_name)


def bbox_around(lat: float, lon: float, half_km: float = HALF_KM):
    dlat = half_km / 111.0
    dlon = half_km / (111.0 * np.cos(np.radians(lat)))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def run_pipeline(bbox, label: str, model, device, on_step=None):
    """Fetch T1+T2, build stacks, run Model 1 + Tier-1 change detection. Returns a result dict.

    on_step(msg), if given, is called before each named stage so a caller can
    surface live progress -- this pipeline takes 20-60s (two live satellite
    fetches + two model passes), long enough that a single static spinner
    leaves the user guessing whether it's stuck.
    """
    def step(msg):
        if on_step:
            on_step(msg)

    results = {}
    for date_tag in ("T1", "T2"):
        step(f"Searching Sentinel-2 catalog for {date_tag} imagery...")
        item = search_scene(bbox, date_tag)
        raw_path = LIVE_DIR / f"{label}_{date_tag}_rgbnir.tif"
        step(f"Downloading & clipping {date_tag} scene ({item.datetime.date()})...")
        clip_scene_to_stack(item, bbox, raw_path)
        stack_path = LIVE_DIR / f"{label}_{date_tag}_stack6.tif"
        step(f"Computing NDVI / NDWI for {date_tag}...")
        build_6channel_stack(raw_path, stack_path)
        step(f"Running land-cover model on {date_tag}...")
        class_map, img, profile = predict_class_map(model, stack_path, device)
        results[date_tag] = {"class_map": class_map, "img": img, "profile": profile, "date": item.datetime.date()}

    step("Comparing T1 vs T2 for changes...")
    change_map = run_tier1(results["T1"]["class_map"], results["T2"]["class_map"])
    step("Computing health score & NDVI trend...")
    health = compute_health_score(results["T2"]["class_map"])
    trend = ndvi_trend(results["T1"]["img"][4], results["T2"]["img"][4])
    step("Generating alerts & recommendations...")
    alerts = generate_alerts(results["T2"]["class_map"], change_map, health, trend)
    return results, change_map, health, trend, alerts


def _set_active_aoi(key, display_name, lat, lon, trained, model, device):
    bbox = bbox_around(lat, lon)
    with st.status(f"Analyzing {display_name}...", expanded=True) as status:
        def on_step(msg):
            status.update(label=msg)
            st.write(f":gray[{msg}]")

        results, change_map, health, trend, alerts = run_pipeline(bbox, key, model, device, on_step=on_step)
        status.update(label=f"Done — {display_name} ready", state="complete", expanded=False)
    st.session_state["active_aoi"] = {
        "key": key, "display_name": display_name, "lat": lat, "lon": lon, "trained": trained,
        "class_t1": results["T1"]["class_map"], "class_t2": results["T2"]["class_map"],
        "img_t1": results["T1"]["img"], "img_t2": results["T2"]["img"], "profile": results["T2"]["profile"],
        "t1_date": results["T1"]["date"], "t2_date": results["T2"]["date"],
        "change_map": change_map, "health": health, "trend": trend, "alerts": alerts,
    }


def render_picker(model1, device):
    st.html('<div class="wsig-eyebrow">Location</div>')

    current = st.session_state.get("active_aoi")  # None until a location has been picked
    preset_cols = st.columns(len(PRESET_AOIS) + 2)
    for col, preset in zip(preset_cols, PRESET_AOIS):
        if col.button(preset["display_name"], use_container_width=True,
                      disabled=(current is not None and current["key"] == preset["key"])):
            try:
                _set_active_aoi(preset["key"], preset["display_name"], preset["lat"], preset["lon"],
                                 True, model1, device)
                st.rerun()
            except RuntimeError as e:
                st.error(f"Couldn't load {preset['display_name']}: {e}")

    with preset_cols[-2]:
        with st.popover("Search a place", use_container_width=True):
            place_query = st.text_input("Place name", placeholder="e.g. Ralegan Siddhi, Maharashtra")
            if st.button("Locate & analyze") and place_query:
                try:
                    found = geocode(place_query)
                except requests.RequestException as e:
                    found = None
                    st.error(f"Geocoding failed: {e}")
                if found is None:
                    st.warning(f'No match for "{place_query}".')
                else:
                    lat, lon, name = found
                    try:
                        _set_active_aoi(f"search_{lat:.3f}_{lon:.3f}", name.split(",")[0], lat, lon,
                                         False, model1, device)
                        st.rerun()
                    except RuntimeError as e:
                        st.error(f"Couldn't complete this location: {e}")

    with preset_cols[-1]:
        with st.popover("Enter coordinates", use_container_width=True):
            lat = st.number_input("Latitude", value=AOI_CENTER_LAT, format="%.4f")
            lon = st.number_input("Longitude", value=AOI_CENTER_LON, format="%.4f")
            if st.button("Analyze coordinates"):
                try:
                    _set_active_aoi(f"coord_{lat:.3f}_{lon:.3f}", f"{lat:.3f}, {lon:.3f}", lat, lon,
                                     False, model1, device)
                    st.rerun()
                except RuntimeError as e:
                    st.error(f"Couldn't complete this location: {e}")
