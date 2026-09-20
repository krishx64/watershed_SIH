"""
Watershed Signal — Hugging Face Gradio + FastAPI Bridge (PS-26015).
Runs on Hugging Face Spaces (CPU Basic: 16 GB RAM + 2 vCPUs, 100% Free).
Serves both an interactive Gradio UI and REST API endpoints for Next.js web client.
"""

import csv
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "app"))

import numpy as np
from PIL import Image, ImageDraw
import gradio as gr
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import (
    DATA_PROCESSED, MODELS_DIR, CLASS_NAMES, CLASS_COLORS, CHANGE_CLASS_NAMES,
    NUM_CLASSES, NODATA_CLASS
)
from cache_manager import cache

MODEL1_PATH = MODELS_DIR / "model1_lulc_unet.pt"
WEB_DEMO_DIR = PROJECT_ROOT / "outputs" / "demo-data"
WEB_DEMO_DIR.mkdir(parents=True, exist_ok=True)

INTERVENTIONS_LOG = DATA_PROCESSED.parent / "interventions.csv"
VALIDATION_LOG = DATA_PROCESSED.parent / "field_validation_log.csv"

# Global cached model
_cached_model = None
_cached_device = None

CHANGE_CLASS_COLORS = {
    0: (230, 230, 230),
    1: (43, 110, 130),
    2: (162, 59, 46),
    3: (166, 106, 22),
    4: (78, 122, 61),
    255: (225, 225, 225),
}


def get_model():
    global _cached_model, _cached_device
    if _cached_model is None:
        import torch
        from model1_unet import build_model
        _cached_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"--> [Model] Loading Model 1 checkpoint onto {_cached_device}...", flush=True)
        _cached_model = build_model().to(_cached_device)
        if MODEL1_PATH.exists():
            ckpt = torch.load(MODEL1_PATH, map_location=_cached_device, weights_only=True)
            _cached_model.load_state_dict(ckpt["model_state"])
            _cached_model.eval()
            print(f"--> [Model] Checkpoint loaded (Epoch {ckpt.get('epoch', '?')})", flush=True)
    return _cached_model, _cached_device


def colorize(class_map: np.ndarray, color_map: dict) -> np.ndarray:
    h, w = class_map.shape
    rgb = np.zeros((h, w, 3), dtype="uint8")
    for cls, color in color_map.items():
        rgb[class_map == cls] = color
    return rgb


def class_hectares(class_map: np.ndarray, pixel_area_m2: float = 100.0) -> dict:
    out = {}
    for cls in range(NUM_CLASSES):
        count = int(np.sum(class_map == cls))
        out[str(cls)] = {
            "name": CLASS_NAMES[cls],
            "pixels": count,
            "hectares": round(count * pixel_area_m2 / 10000, 2),
        }
    n_nodata = int(np.sum(class_map == NODATA_CLASS))
    if n_nodata:
        out[str(NODATA_CLASS)] = {
            "name": CLASS_NAMES[NODATA_CLASS],
            "pixels": n_nodata,
            "hectares": round(n_nodata * pixel_area_m2 / 10000, 2),
        }
    return out


def read_interventions() -> list[dict]:
    if not INTERVENTIONS_LOG.exists():
        return []
    with open(INTERVENTIONS_LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_validation_log() -> list[dict]:
    if not VALIDATION_LOG.exists():
        return []
    with open(VALIDATION_LOG, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---- FastAPI REST Server ----
app = FastAPI(title="Watershed Signal API Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def api_health():
    model_exists = MODEL1_PATH.exists()
    return {
        "status": "online",
        "platform": "Hugging Face Spaces (Gradio + FastAPI)",
        "model_checkpoint": str(MODEL1_PATH.name),
        "model_exists": model_exists,
        "epoch": 20,
        "mean_iou": 0.491,
        "pixel_accuracy": 0.782,
        "num_classes": 7,
        "trained_sites": ["Kadwanchi", "Tamhini Ghat", "Donimalai", "Jayakwadi Dam"],
    }


@app.get("/api/interventions")
def api_get_interventions():
    return read_interventions()


@app.get("/api/field-log")
def api_get_field_log():
    return read_validation_log()


@app.get("/api/geocode")
def api_geocode(q: str = ""):
    if not q:
        raise HTTPException(status_code=400, detail="Missing query parameter 'q'")
    try:
        from aoi_picker import geocode
        res = geocode(q)
        if res:
            lat, lon, display_name = res
            return {"lat": lat, "lon": lon, "display_name": display_name}
        raise HTTPException(status_code=404, detail="Location not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/run")
async def api_pipeline_run(request: Request):
    payload = await request.json()
    lat = payload.get("lat")
    lon = payload.get("lon")
    name = payload.get("name", "Custom Location")
    radius_km = float(payload.get("radius_km", 2.0))

    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Missing lat or lon")

    try:
        lat = float(lat)
        lon = float(lon)
        from aoi_picker import bbox_around, run_pipeline

        bbox = bbox_around(lat, lon, radius_km)
        site_key = f"custom_live_{int(round(radius_km * 10))}"
        out_dir = WEB_DEMO_DIR / site_key
        out_dir.mkdir(parents=True, exist_ok=True)

        cache_key = f"aoi_meta:{lat:.4f}_{lon:.4f}_{radius_km:.1f}"
        cached_meta = cache.get_json(cache_key)
        if cached_meta is not None:
            return {"status": "ok", "siteKey": site_key, "meta": cached_meta, "cached": True}

        model, device = get_model()
        (results, change_map, health, trend, alerts,
         watershed_mask, drainage_network, pour_point, watershed_caveat, watershed_context) = run_pipeline(
            bbox, site_key, model, device,
            on_step=lambda m: print(f"    --> {m}", flush=True)
        )

        t1_map = results["T1"]["class_map"]
        t2_map = results["T2"]["class_map"]
        t1_date = str(results["T1"]["date"])
        t2_date = str(results["T2"]["date"])

        left, bottom, right, top = bbox
        bbox_wgs84 = {"west": float(left), "south": float(bottom), "east": float(right), "north": float(top)}

        from tier1_fallback import summarize_changes
        change_summary_raw = summarize_changes(change_map)
        change_summary = {
            sname: {"pixels": int(s["pixels"]), "hectares": float(s["hectares"])}
            for sname, s in change_summary_raw.items()
        }

        meta = {
            "key": site_key,
            "display_name": name,
            "bbox_wgs84": bbox_wgs84,
            "class_names": {str(k): v for k, v in CLASS_NAMES.items()},
            "class_colors": {str(k): list(v) for k, v in CLASS_COLORS.items()},
            "has_change_pair": True,
            "t1_date": t1_date,
            "t2_date": t2_date,
            "health_score": round(float(health), 1),
            "class_breakdown": class_hectares(t2_map),
            "change_class_names": {str(k): v for k, v in CHANGE_CLASS_NAMES.items()},
            "change_class_colors": {str(k): list(v) for k, v in CHANGE_CLASS_COLORS.items()},
            "change_summary": change_summary,
            "ndvi_trend": round(float(trend), 4),
            "alerts": alerts,
            "radius_km": radius_km,
            "watershed_caveat": watershed_caveat,
            "watershed_meta": {
                "watershed_id": watershed_context.get("watershed_id") if isinstance(watershed_context, dict) else None,
                "watershed_name": watershed_context.get("watershed_name") if isinstance(watershed_context, dict) else "DEM-Derived Watershed Boundary",
                "admin": watershed_context.get("admin") if isinstance(watershed_context, dict) else {},
                "area_ha": watershed_context.get("area_ha") if isinstance(watershed_context, dict) else 0.0,
            } if watershed_context else None,
        }

        cache.set_json(cache_key, meta)
        return {"status": "ok", "siteKey": site_key, "meta": meta}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


# ---- Interactive Gradio Dashboard ----
def gradio_run_demo(lat: float, lon: float, radius_km: float):
    try:
        from aoi_picker import bbox_around, run_pipeline
        model, device = get_model()
        bbox = bbox_around(lat, lon, radius_km)
        site_key = f"hf_demo_{int(round(radius_km * 10))}"
        
        (results, change_map, health, trend, alerts,
         watershed_mask, drainage_network, pour_point, watershed_caveat, watershed_context) = run_pipeline(
            bbox, site_key, model, device
        )
        t2_map = results["T2"]["class_map"]
        rgb_t2 = colorize(t2_map, CLASS_COLORS)
        rgb_ch = colorize(change_map, CHANGE_CLASS_COLORS)
        
        summary_text = (
            f"### Watershed Health Score: {health:.1f}/100\n"
            f"- **NDVI Trend**: {trend:+.4f}\n"
            f"- **Alerts Generated**: {len(alerts)}\n"
            f"- **Topography Pour Point**: {pour_point or 'Computed'}\n"
        )
        return rgb_t2, rgb_ch, summary_text
    except Exception as e:
        return None, None, f"**Error**: {str(e)}"


with gr.Blocks(title="Watershed Signal API Bridge") as demo:
    gr.Markdown(
        """
        # 🌊 Watershed Signal — API Bridge & Pipeline
        ### Smart India Hackathon 2026 (PS-26015)
        This Hugging Face Space powers the live AI backend for the **Watershed Signal** Next.js application with 16 GB RAM and 2 vCPUs.
        
        - **REST API URL**: `https://<your-space>.hf.space/api/pipeline/run`
        - **Health Check**: `https://<your-space>.hf.space/api/health`
        """
    )
    with gr.Row():
        with gr.Column():
            lat_input = gr.Number(value=19.9248, label="Latitude (°N)")
            lon_input = gr.Number(value=75.8943, label="Longitude (°E)")
            radius_input = gr.Slider(minimum=0.5, maximum=5.0, value=2.0, step=0.5, label="Catchment Radius (km)")
            run_btn = gr.Button("🚀 Run Live Pipeline", variant="primary")
        with gr.Column():
            out_lulc = gr.Image(label="Segmented LULC (Model 1 U-Net)")
            out_change = gr.Image(label="Change Detection Matrix")
            out_summary = gr.Markdown()

    run_btn.click(
        fn=gradio_run_demo,
        inputs=[lat_input, lon_input, radius_input],
        outputs=[out_lulc, out_change, out_summary]
    )

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
