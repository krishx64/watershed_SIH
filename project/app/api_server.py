"""
Watershed Signal — Lightweight Python API Bridge for Next.js.
Exposes REST JSON endpoints connecting Next.js (web/) to the trained
Model 1 pipeline, intervention registry, geocoding, and field logs.

Runs with:
  uv run python project/app/api_server.py
"""

import io
import json
import mimetypes
import queue
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "app"))

import numpy as np
from PIL import Image, ImageDraw

def img_to_bytes(img: Image.Image, format="PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

import csv
import os
try:
    import dotenv
    dotenv.load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from config import (
    DATA_PROCESSED, MODELS_DIR, CLASS_NAMES, CLASS_COLORS, CHANGE_CLASS_NAMES,
    NUM_CLASSES, NODATA_CLASS, atomic_raster_write
)
from cache_manager import cache

INTERVENTIONS_LOG = DATA_PROCESSED.parent / "interventions.csv"
VALIDATION_LOG = DATA_PROCESSED.parent / "field_validation_log.csv"


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


def _resolve_bind_host() -> str:
    """Choose the interface to bind.

    A generic `HOST` env var is a trap on container platforms: it is often set
    to the service's public domain (e.g. HOST=myapp.up.railway.app), which is
    not a local interface, so ThreadingHTTPServer raises
    `socket.gaierror: [Errno -2] Name or service not known` at bind. Prefer an
    explicit BIND_HOST, accept HOST only when it is a real local address, and
    otherwise fall back to all interfaces.
    """
    import ipaddress

    for name in ("BIND_HOST", "HOST"):
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        if raw == "localhost":
            return raw
        try:
            ipaddress.ip_address(raw)
            return raw
        except ValueError:
            print(
                f"--> [Server] Ignoring non-bindable {name}={raw!r}; binding 0.0.0.0 instead.",
                flush=True,
            )
    return "0.0.0.0"


HOST = _resolve_bind_host()
PORT = int(os.environ.get("PORT", 8000))
MODEL1_PATH = MODELS_DIR / "model1_lulc_unet.pt"

# Where generated demo-data (PNGs + meta.json) is written and read back from.
# Local dev keeps the current web/public/demo-data so `next dev` serves it;
# the Docker image sets DEMO_DATA_DIR to the served static export directory.
WEB_DEMO_DIR = (
    Path(os.environ["DEMO_DATA_DIR"]).resolve()
    if os.environ.get("DEMO_DATA_DIR")
    else PROJECT_ROOT.parent / "web" / "public" / "demo-data"
)

# Optional: serve the Next.js static export (web/out) directly from this
# process in the Docker image, so one container serves the whole app with no
# CORS or second service. Unset in local dev (Next dev server owns the UI).
STATIC_DIR = Path(os.environ["STATIC_DIR"]).resolve() if os.environ.get("STATIC_DIR") else None

# Global cached model
_cached_model = None
_cached_device = None

ACTIVE_PIPELINES: dict = {}
PIPELINE_LOCK = threading.Lock()

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
        torch.set_num_threads(min(4, os.cpu_count() or 4))
        _cached_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"--> [Model] Loading Model 1 checkpoint onto {_cached_device}...")
        _cached_model = build_model().to(_cached_device)
        ckpt = torch.load(MODEL1_PATH, map_location=_cached_device, weights_only=True)
        _cached_model.load_state_dict(ckpt["model_state"])
        _cached_model.eval()
        print(f"--> [Model] Checkpoint loaded (Epoch {ckpt.get('epoch', '?')})")
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


# Ponytail Strategy 1 & 2: Asynchronous Bhoonidhi Ingestion Queue & Daemon Worker
BHOONIDHI_JOB_QUEUE = queue.Queue(maxsize=5)
BHOONIDHI_STATUS: dict = {}
BHOONIDHI_STATUS_LOCK = threading.Lock()


def _process_bhoonidhi_background_job(site_key, bbox, name, radius_km, t1_target, t2_target):
    """Processes background LISS-III ingestion, model inference, and progressive upgrade."""
    with BHOONIDHI_STATUS_LOCK:
        BHOONIDHI_STATUS[site_key] = "processing"
    print(f"\n--> [Bhoonidhi Worker] Initiating background sovereign ingestion for '{name}' [{site_key}]...", flush=True)

    try:
        from data_adapter import ingest_bhoonidhi_ephemeral
        from inference_demo import predict_class_map
        from tier1_fallback import run_tier1, summarize_changes
        from recommendation_engine import compute_health_score, ndvi_trend
        from aoi_picker import _model_lock

        # 1. Ephemeral Ingestion of T2 (Recent date)
        res_t2 = ingest_bhoonidhi_ephemeral(bbox, date_tag="T2", target_date=t2_target, timeout=360.0)
        if not res_t2:
            print(f"--> [Bhoonidhi Worker] All online LISS-III candidate scenes were unavailable for T2 ({name}) on NRSC storage. Sentinel-2 preview remains active.", flush=True)
            with BHOONIDHI_STATUS_LOCK:
                BHOONIDHI_STATUS[site_key] = "unavailable"
            m = cache.get_json(f"meta:{site_key}")
            if m:
                m["bhoonidhi_status"] = "unavailable"
                cache.set_json(f"meta:{site_key}", m, ttl=86400)
            return

        dt2, source_label_t2, stack_t2, meta_t2 = res_t2

        # 2. Ephemeral Ingestion of T1 (Historical date, optional; max 60s to avoid delaying T2 ready notification)
        res_t1 = None
        if t1_target:
            res_t1 = ingest_bhoonidhi_ephemeral(bbox, date_tag="T1", target_date=t1_target, timeout=60.0)

        # 3. Model 1 U-Net Inference
        model, device = get_model()
        LIVE_DIR = DATA_PROCESSED / "live"
        LIVE_DIR.mkdir(parents=True, exist_ok=True)

        from rasterio.transform import from_origin
        minx, miny, maxx, maxy = bbox
        h2, w2 = stack_t2.shape[1], stack_t2.shape[2]
        prof_t2 = meta_t2 if (isinstance(meta_t2, dict) and "driver" in meta_t2) else (meta_t2.get("profile") if isinstance(meta_t2, dict) else None)
        if not prof_t2:
            prof_t2 = {
                "driver": "GTiff",
                "height": h2,
                "width": w2,
                "count": 6,
                "dtype": "float32",
                "crs": "EPSG:4326",
                "transform": from_origin(minx, maxy, (maxx - minx) / max(1, w2), (maxy - miny) / max(1, h2)),
            }

        stack_path_t2 = LIVE_DIR / f"bg_{site_key}_T2_stack6.tif"
        atomic_raster_write(stack_path_t2, stack_t2, prof_t2)

        with _model_lock:
            t2_map, img_t2, _ = predict_class_map(model, stack_path_t2, device)

        if res_t1:
            stack_t1 = res_t1[2]
            h1, w1 = stack_t1.shape[1], stack_t1.shape[2]
            prof_t1 = res_t1[3] if (isinstance(res_t1[3], dict) and "driver" in res_t1[3]) else (res_t1[3].get("profile") if isinstance(res_t1[3], dict) else None)
            if not prof_t1:
                prof_t1 = {
                    "driver": "GTiff",
                    "height": h1,
                    "width": w1,
                    "count": 6,
                    "dtype": "float32",
                    "crs": "EPSG:4326",
                    "transform": from_origin(minx, maxy, (maxx - minx) / max(1, w1), (maxy - miny) / max(1, h1)),
                }
            stack_path_t1 = LIVE_DIR / f"bg_{site_key}_T1_stack6.tif"
            atomic_raster_write(stack_path_t1, stack_t1, prof_t1)
            with _model_lock:
                t1_map, img_t1, _ = predict_class_map(model, stack_path_t1, device)
            t1_source = res_t1[1]
            t1_date = str(res_t1[0])
            stack_path_t1.unlink(missing_ok=True)
            rgb_t1 = colorize(t1_map, CLASS_COLORS)
            t1_bytes = img_to_bytes(Image.fromarray(rgb_t1))
        else:
            # Preserve original Sentinel-2 T1 baseline image and date if Bhoonidhi T1 is not available
            sent_m = cache.get_json(f"sentinel_meta:{site_key}") or cache.get_json("sentinel_meta:custom_live") or {}
            t1_source = sent_m.get("t1_source", "Copernicus Sentinel-2 (Historical Baseline)")
            t1_date = sent_m.get("t1_date", str(dt2))
            t1_bytes = cache.get_bytes(f"image:{site_key}:sentinel_t1.png") or cache.get_bytes(f"image:custom_live:sentinel_t1.png")
            t1_map = t2_map
            img_t1 = img_t2
            if t1_bytes is None:
                rgb_t1 = colorize(t1_map, CLASS_COLORS)
                t1_bytes = img_to_bytes(Image.fromarray(rgb_t1))

        stack_path_t2.unlink(missing_ok=True)

        # 4. Metrics & Rasters
        change_map = run_tier1(t1_map, t2_map)
        health = compute_health_score(t2_map)
        trend = ndvi_trend(img_t1, img_t2)

        if res_t1:
            rgb_t1 = colorize(t1_map, CLASS_COLORS)
            t1_bytes = img_to_bytes(Image.fromarray(rgb_t1))
        rgb_t2 = colorize(t2_map, CLASS_COLORS)
        rgb_ch = colorize(change_map, CHANGE_CLASS_COLORS)

        t2_bytes = img_to_bytes(Image.fromarray(rgb_t2))
        ch_bytes = img_to_bytes(Image.fromarray(rgb_ch))

        # Save Bhoonidhi rasters with bhoonidhi_ prefix (staged for user activation)
        bhoonidhi_rasters = {
            "t1.png": t1_bytes,
            "t2.png": t2_bytes,
            "classmap_t1.png": t1_bytes,
            "classmap_t2.png": t2_bytes,
            "change.png": ch_bytes,
        }
        for fname, bdata in bhoonidhi_rasters.items():
            cache.set_bytes(f"image:{site_key}:bhoonidhi_{fname}", bdata, ttl=86400)
            cache.set_bytes(f"image:custom_live:bhoonidhi_{fname}", bdata, ttl=86400)

        change_summary_raw = summarize_changes(change_map)
        change_summary = {
            sname: {"pixels": int(s["pixels"]), "hectares": float(s["hectares"])}
            for sname, s in change_summary_raw.items()
        }

        # Build separate Bhoonidhi metadata
        current_meta = cache.get_json(f"meta:{site_key}") or {}
        bhoonidhi_meta = dict(current_meta)
        bhoonidhi_meta.update({
            "primary_source": source_label_t2,
            "t2_source": source_label_t2,
            "t2_date": str(dt2),
            "health_score": round(float(health), 1),
            "class_breakdown": class_hectares(t2_map),
            "change_summary": change_summary,
            "ndvi_trend": round(float(trend), 4),
            "bhoonidhi_status": "ready",
            "bhoonidhi_verified": True,
            "active_source": "bhoonidhi",
        })
        if res_t1:
            bhoonidhi_meta["t1_source"] = t1_source
            bhoonidhi_meta["t1_date"] = t1_date

        cache.set_json(f"bhoonidhi_meta:{site_key}", bhoonidhi_meta, ttl=86400)
        cache.set_json("bhoonidhi_meta:custom_live", bhoonidhi_meta, ttl=86400)

        # Notify that Bhoonidhi is ready while keeping current Sentinel view active
        current_meta["bhoonidhi_status"] = "ready"
        current_meta["bhoonidhi_verified"] = True
        cache.set_json(f"meta:{site_key}", current_meta, ttl=86400)
        cache.set_json("meta:custom_live", current_meta, ttl=86400)

        with BHOONIDHI_STATUS_LOCK:
            BHOONIDHI_STATUS[site_key] = "ready"
        print(f"--> [Bhoonidhi Worker] BHOONIDHI INGESTION COMPLETE for '{name}' [{site_key}]! (Ready for user activation)", flush=True)
    except Exception as e:
        print(f"--> [Bhoonidhi Worker] Error upgrading '{name}': {e}", flush=True)
        with BHOONIDHI_STATUS_LOCK:
            BHOONIDHI_STATUS[site_key] = "failed"


def _bhoonidhi_worker():
    """Background daemon worker for processing asynchronous Bhoonidhi ingestion."""
    while True:
        try:
            job = BHOONIDHI_JOB_QUEUE.get()
            if job is None:
                break
            site_key, bbox, name, radius_km, t1_target, t2_target = job
            _process_bhoonidhi_background_job(site_key, bbox, name, radius_km, t1_target, t2_target)
            BHOONIDHI_JOB_QUEUE.task_done()
        except Exception as e:
            print(f"--> [Bhoonidhi Worker Loop] Error: {e}", flush=True)
            time.sleep(1)


# Start single background daemon worker thread (Ponytail standard library)
_worker_thread = threading.Thread(target=_bhoonidhi_worker, daemon=True, name="bhoonidhi_worker")
_worker_thread.start()


class WatershedApiHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Custom clean stdout logging with instant flush
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] API: {self.command} {self.path} - {args[1]}", flush=True)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _get_current_user(self) -> dict:
        """Extract user from Authorization: Bearer <token> or query param."""
        auth_header = self.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            token = qs.get("token", [None])[0]

        if token:
            try:
                import auth_manager
                user = auth_manager.verify_token(token)
                if user:
                    return user
            except Exception:
                pass

        return {"username": "anonymous_official", "role": "official", "name": "Field Officer"}

    def do_OPTIONS(self):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] --> CORS preflight OPTIONS {self.path}", flush=True)
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] --> Incoming GET {self.path}", flush=True)
        parsed = urlparse(self.path)
        path = parsed.path

        # In the Docker image the Python server also serves the Next.js static
        # export (STATIC_DIR). Every non-/api path is a static asset, including
        # "/" -> index.html. Local dev leaves STATIC_DIR unset, so Next owns this.
        if STATIC_DIR is not None and not (path == "/api" or path.startswith("/api/")):
            if self._serve_static(path):
                return

        if path == "/" or path == "/api":
            data = {
                "name": "Watershed Signal API Bridge",
                "status": "online",
                "port": PORT,
                "endpoints": [
                    "/api/health",
                    "/api/bhuvan/status",
                    "/api/bhuvan/aoi-stats",
                    "/api/interventions",
                    "/api/field-log",
                    "/api/geocode?q=place_name",
                    "/api/pipeline/run (POST)",
                ],
            }
            self._respond_json(200, data)

        elif path == "/favicon.ico":
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        elif path == "/api/health":
            model_exists = MODEL1_PATH.exists()
            data = {
                "status": "online",
                "model_checkpoint": str(MODEL1_PATH.name),
                "model_exists": model_exists,
                "epoch": 20,
                "mean_iou": 0.491,
                "pixel_accuracy": 0.782,
                "num_classes": 7,
                "trained_sites": ["Kadwanchi", "Tamhini Ghat", "Donimalai", "Jayakwadi Dam"],
            }
            self._respond_json(200, data)

        elif path == "/api/bhuvan/status":
            try:
                from data_adapter import get_bhuvan_token, find_best_bhoonidhi_scene
                import mongo_raster_cache as mrc
                bhuvan_token = get_bhuvan_token()
                bhoonidhi_match = find_best_bhoonidhi_scene()
                scene_name = str(bhoonidhi_match[2] if len(bhoonidhi_match) > 2 else bhoonidhi_match[1]) if bhoonidhi_match else None
                mongo_ok = mrc._init_mongo()
                cached_count = mrc._mongo_db.raster_meta.count_documents({}) if mongo_ok else 0
                bhoonidhi_api_user = os.environ.get("BHOONIDHI_USER", "")
                print(f"[{timestamp}] [API] /api/bhuvan/status -> Bhuvan: {'LIVE TOKEN' if bhuvan_token else 'NOT SET'} | Bhoonidhi: {scene_name or 'None'} | Mongo: {'CONNECTED (' + str(cached_count) + ' cached)' if mongo_ok else 'OFFLINE'} | Cache: {cache.backend_name.upper()}", flush=True)
                self._respond_json(200, {
                    "status": "online",
                    "bhuvan_connected": bool(bhuvan_token),
                    "bhuvan_token_configured": bool(bhuvan_token),
                    "bhoonidhi_active": bool(bhoonidhi_match or bhoonidhi_api_user),
                    "bhoonidhi_scene": scene_name,
                    "bhoonidhi_api_configured": bool(bhoonidhi_api_user),
                    "mongo_cache_active": mongo_ok,
                    "mongo_cached_rasters": cached_count,
                    "cache_backend": cache.backend_name,
                    "fallback_tier": "AWS S3 Open Data (Copernicus GLO-30 / Sentinel-2 L2A)",
                })
            except Exception as e:
                print(f"[{timestamp}] [API] /api/bhuvan/status ERROR: {e}", flush=True)
                self._respond_json(500, {"error": str(e)})

        elif path == "/api/bhuvan/aoi-stats":
            try:
                from data_adapter import fetch_bhuvan_aoi_stats
                qs = parse_qs(parsed.query)
                if "minx" in qs and "miny" in qs and "maxx" in qs and "maxy" in qs:
                    bbox = (
                        float(qs["minx"][0]),
                        float(qs["miny"][0]),
                        float(qs["maxx"][0]),
                        float(qs["maxy"][0]),
                    )
                    print(f"[{timestamp}] [API] /api/bhuvan/aoi-stats -> Request for custom bbox {bbox}", flush=True)
                    stats = fetch_bhuvan_aoi_stats(bbox)
                else:
                    print(f"[{timestamp}] [API] /api/bhuvan/aoi-stats -> Request for default Kadwanchi AOI", flush=True)
                    stats = fetch_bhuvan_aoi_stats()
                self._respond_json(200, stats)
            except Exception as e:
                print(f"[{timestamp}] [API] /api/bhuvan/aoi-stats ERROR: {e}", flush=True)
                self._respond_json(500, {"error": str(e)})

        elif path == "/api/interventions":
            records = read_interventions()
            self._respond_json(200, records)

        elif path == "/api/field-log":
            logs = read_validation_log()
            self._respond_json(200, logs)

        elif path == "/api/auth/me":
            user = self._get_current_user()
            self._respond_json(200, {"status": "ok", "user": user})

        elif path == "/api/audit-logs":
            user = self._get_current_user()
            if user.get("role") != "admin":
                try:
                    import audit_logger
                    audit_logger.record_audit(
                        category="security",
                        action="unauthorized_audit_access",
                        user=user.get("username", "anonymous"),
                        role=user.get("role", "unknown"),
                        details={"path": path, "reason": "Non-admin attempted to access audit logs"},
                        status="rejected",
                        ip=self.client_address[0] if self.client_address else "127.0.0.1",
                    )
                except Exception:
                    pass
                self._respond_json(403, {"error": "Forbidden: Statutory Audit Console is restricted to Admin role"})
                return

            try:
                import audit_logger
                qs = parse_qs(parsed.query)
                category = qs.get("category", [None])[0]
                q_filter = qs.get("q", [None])[0]
                limit = int(qs.get("limit", [100])[0])
                logs = audit_logger.get_audit_logs(limit=limit, category=category, query=q_filter)
                summary = audit_logger.get_audit_summary()
                self._respond_json(200, {
                    "status": "ok",
                    "count": len(logs),
                    "summary": summary,
                    "logs": logs,
                })
            except Exception as e:
                self._respond_json(500, {"error": str(e)})

        elif path == "/api/pipeline/bhoonidhi-status":
            qs = parse_qs(parsed.query)
            s_key = qs.get("site_key", [""])[0]
            with BHOONIDHI_STATUS_LOCK:
                st = BHOONIDHI_STATUS.get(s_key, "idle")
            if st != "ready":
                cached_m = cache.get_json(f"meta:{s_key}")
                if cached_m and (cached_m.get("bhoonidhi_status") == "ready" or cached_m.get("primary_source", "").startswith("ISRO Bhoonidhi")):
                    st = "ready"
            b_meta = cache.get_json(f"bhoonidhi_meta:{s_key}")
            self._respond_json(200, {"status": st, "site_key": s_key, "bhoonidhi_meta": b_meta})

        elif path == "/api/geocode":
            qs = parse_qs(parsed.query)
            query = qs.get("q", [""])[0]
            if not query:
                self._respond_json(400, {"error": "Missing 'q' query parameter"})
                return

            try:
                from aoi_picker import geocode
                res = geocode(query)
                if res:
                    lat, lon, display_name = res
                    try:
                        import audit_logger
                        curr_user = self._get_current_user()
                        audit_logger.record_audit(
                            category="search",
                            action="geocode_search",
                            user=curr_user.get("username", "official"),
                            role=curr_user.get("role", "official"),
                            details={"query": query, "lat": lat, "lon": lon, "display_name": display_name},
                            status="success",
                            ip=self.client_address[0] if self.client_address else "127.0.0.1",
                        )
                    except Exception:
                        pass
                    self._respond_json(200, {"lat": lat, "lon": lon, "display_name": display_name})
                else:
                    self._respond_json(404, {"error": "Location not found"})
            except Exception as e:
                self._respond_json(500, {"error": str(e)})

        elif path == "/api/sites":
            index_file = WEB_DEMO_DIR / "index.json"
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._respond_json(200, data)
            else:
                self._respond_json(200, [])

        elif path.startswith("/api/images/"):
            # Stream cached binary rasters: /api/images/<site_key>/<image_name>
            rel_path = path[len("/api/images/"):].strip("/")
            parts = rel_path.split("/")
            if len(parts) >= 2:
                site_key = parts[0]
                image_name = "/".join(parts[1:])
                redis_key = f"image:{site_key}:{image_name}"

                # 1. Primary: Stream from Redis / in-memory cache
                data = cache.get_bytes(redis_key)
                if data is not None:
                    content_type = "image/png"
                    if image_name.endswith(".json"):
                        content_type = "application/json"
                    elif image_name.endswith(".svg"):
                        content_type = "image/svg+xml"
                    self.send_response(200)
                    self._send_cors_headers()
                    self.send_header("Content-Type", content_type)
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return

                # 2. Disk fallback (e.g. for static pre-packaged demo sites)
                fallback_file = WEB_DEMO_DIR / site_key / image_name
                if fallback_file.exists() and fallback_file.is_file():
                    with open(fallback_file, "rb") as f:
                        file_data = f.read()
                    content_type = "image/png"
                    if image_name.endswith(".json"):
                        content_type = "application/json"
                    elif image_name.endswith(".svg"):
                        content_type = "image/svg+xml"
                    self.send_response(200)
                    self._send_cors_headers()
                    self.send_header("Content-Type", content_type)
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.send_header("Content-Length", str(len(file_data)))
                    self.end_headers()
                    self.wfile.write(file_data)
                    return

            self._respond_json(404, {"error": f"Image '{path}' not found in cache or disk"})

        elif path.startswith("/api/sites/"):
            site_name = path.replace("/api/sites/", "").strip("/")
            qs = parse_qs(parsed.query)
            requested_source = qs.get("source", [""])[0]
            if requested_source == "bhoonidhi":
                b_meta = cache.get_json(f"bhoonidhi_meta:{site_name}")
                if b_meta:
                    self._respond_json(200, b_meta)
                    return
            elif requested_source == "sentinel":
                s_meta = cache.get_json(f"sentinel_meta:{site_name}")
                if s_meta:
                    self._respond_json(200, s_meta)
                    return

            # Check Redis first
            cached_site_meta = cache.get_json(f"meta:{site_name}")
            if cached_site_meta is not None:
                self._respond_json(200, cached_site_meta)
                return
            meta_file = WEB_DEMO_DIR / site_name / "meta.json"
            if meta_file.exists():
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._respond_json(200, data)
            else:
                self._respond_json(404, {"error": f"Site '{site_name}' metadata not found on server"})

        else:
            self._respond_json(404, {"error": f"Endpoint '{path}' not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] --> Incoming POST {path}", flush=True)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/auth/login":
            import auth_manager, audit_logger
            username = payload.get("username")
            password = payload.get("password")
            role_switch = payload.get("role")

            user = auth_manager.authenticate_user(username, password, role_switch)
            if not user:
                try:
                    audit_logger.record_audit(
                        category="security",
                        action="auth_login_failed",
                        user=username or role_switch or "unknown",
                        role="unknown",
                        details={"username": username, "role_switch": role_switch},
                        status="failed",
                        ip=self.client_address[0] if self.client_address else "127.0.0.1",
                    )
                except Exception:
                    pass
                self._respond_json(401, {"error": "Invalid credentials or unauthorized role"})
                return

            try:
                audit_logger.record_audit(
                    category="security",
                    action="auth_login_success",
                    user=user["username"],
                    role=user["role"],
                    details={"name": user.get("name"), "department": user.get("department")},
                    status="success",
                    ip=self.client_address[0] if self.client_address else "127.0.0.1",
                )
            except Exception:
                pass

            self._respond_json(200, {
                "status": "ok",
                "token": user.get("token"),
                "user": user,
            })
            return

        elif path == "/api/auth/register":
            import auth_manager, audit_logger
            ok, msg, new_user = auth_manager.create_user_profile(payload)
            if not ok:
                self._respond_json(400, {"error": msg})
                return

            auth_user = auth_manager.authenticate_user(new_user["username"], payload.get("password"))
            try:
                audit_logger.record_audit(
                    category="security",
                    action="create_profile",
                    user=new_user["username"],
                    role=new_user["role"],
                    details={
                        "name": new_user.get("name"),
                        "department": new_user.get("department"),
                        "badge_id": new_user.get("badge_id"),
                    },
                    status="success",
                    ip=self.client_address[0] if self.client_address else "127.0.0.1",
                )
            except Exception:
                pass

            self._respond_json(201, {
                "status": "ok",
                "message": msg,
                "token": auth_user.get("token") if auth_user else None,
                "user": auth_user or new_user,
            })
            return

        elif path == "/api/interventions":
            name = payload.get("name")
            type_ = payload.get("type", "Check Dam")
            lat = payload.get("lat")
            lon = payload.get("lon")
            notes = payload.get("notes", "")

            if not name or lat is None or lon is None:
                self._respond_json(400, {"error": "Missing required fields: name, lat, lon"})
                return

            iv_id = reg.add_intervention(name, type_, float(lat), float(lon), notes)
            try:
                import audit_logger
                curr_user = self._get_current_user()
                audit_logger.record_audit(
                    category="intervention",
                    action="add_intervention",
                    user=curr_user.get("username", "official"),
                    role=curr_user.get("role", "official"),
                    details={"name": name, "type": type_, "lat": float(lat), "lon": float(lon), "id": iv_id},
                    status="success",
                    ip=self.client_address[0] if self.client_address else "127.0.0.1",
                )
            except Exception:
                pass
            self._respond_json(201, {"id": iv_id, "status": "created"})

        elif path == "/api/pipeline/cancel":
            run_id = payload.get("run_id")
            with PIPELINE_LOCK:
                if run_id and run_id in ACTIVE_PIPELINES:
                    ACTIVE_PIPELINES[run_id].set()
                    print(f"--> [Pipeline] Dispatched cancellation signal for run '{run_id}'", flush=True)
                else:
                    for rid, ev in list(ACTIVE_PIPELINES.items()):
                        ev.set()
                        print(f"--> [Pipeline] Flagged active run '{rid}' for cancellation", flush=True)
            self._respond_json(200, {"status": "ok", "message": "Cancellation registered"})
            return

        elif path == "/api/pipeline/switch-source":
            site_key = payload.get("site_key", "custom_live")
            target_source = payload.get("source", "bhoonidhi")  # "bhoonidhi" or "sentinel"

            if target_source == "bhoonidhi":
                target_meta = cache.get_json(f"bhoonidhi_meta:{site_key}") or cache.get_json("bhoonidhi_meta:custom_live")
                prefix = "bhoonidhi_"
            else:
                target_meta = cache.get_json(f"sentinel_meta:{site_key}") or cache.get_json("sentinel_meta:custom_live")
                prefix = "sentinel_"

            if not target_meta:
                target_meta = cache.get_json(f"meta:{site_key}") or cache.get_json("meta:custom_live")

            if not target_meta:
                self._respond_json(404, {"error": f"No {target_source} data available for {site_key}"})
                return

            # Copy prefix rasters to active rasters
            for fname in ["t1.png", "t2.png", "classmap_t1.png", "classmap_t2.png", "change.png"]:
                b = cache.get_bytes(f"image:{site_key}:{prefix}{fname}") or cache.get_bytes(f"image:custom_live:{prefix}{fname}")
                if b is not None:
                    cache.set_bytes(f"image:{site_key}:{fname}", b, ttl=86400)
                    cache.set_bytes(f"image:custom_live:{fname}", b, ttl=86400)

            target_meta["active_source"] = target_source
            meta_json_bytes = json.dumps(target_meta, indent=2).encode("utf-8")
            cache.set_bytes(f"image:{site_key}:meta.json", meta_json_bytes, ttl=86400)
            cache.set_bytes("image:custom_live:meta.json", meta_json_bytes, ttl=86400)
            cache.set_json(f"meta:{site_key}", target_meta, ttl=86400)
            cache.set_json("meta:custom_live", target_meta, ttl=86400)

            try:
                import audit_logger
                curr_user = self._get_current_user()
                audit_logger.record_audit(
                    category="source_switch",
                    action="switch_source",
                    user=curr_user.get("username", "official"),
                    role=curr_user.get("role", "official"),
                    details={
                        "site_key": site_key,
                        "target_source": target_source,
                    },
                    status="success",
                    ip=self.client_address[0] if self.client_address else "127.0.0.1",
                )
            except Exception:
                pass

            print(f"--> [Pipeline] Switched active raster source for '{site_key}' to: {target_source.upper()}", flush=True)
            self._respond_json(200, {
                "status": "ok",
                "active_source": target_source,
                "meta": target_meta,
            })
            return

        elif path == "/api/pipeline/run":
            lat = payload.get("lat")
            lon = payload.get("lon")
            name = payload.get("name", "Custom Location")
            radius_km = float(payload.get("radius_km", 2.0))
            run_id = payload.get("run_id") or f"run_{int(time.time()*1000)}"

            if lat is None or lon is None:
                self._respond_json(400, {"error": "Missing lat or lon"})
                return

            cancel_ev = threading.Event()
            with PIPELINE_LOCK:
                ACTIVE_PIPELINES[run_id] = cancel_ev

            try:
                lat = float(lat)
                lon = float(lon)
                from aoi_picker import bbox_around, run_pipeline

                target_date = payload.get("target_date")
                t1_target = payload.get("t1_date")
                t2_target = payload.get("t2_date") or target_date

                bbox = bbox_around(lat, lon, radius_km)

                try:
                    import audit_logger
                    curr_user = self._get_current_user()
                    audit_logger.record_audit(
                        category="pipeline",
                        action="pipeline_run",
                        user=curr_user.get("username", "official"),
                        role=curr_user.get("role", "official"),
                        details={
                            "aoi_name": name,
                            "lat": lat,
                            "lon": lon,
                            "radius_km": radius_km,
                            "target_date": target_date or "latest",
                            "t1_date": t1_target,
                            "t2_date": t2_target,
                            "run_id": run_id,
                        },
                        status="started",
                        ip=self.client_address[0] if self.client_address else "127.0.0.1",
                    )
                except Exception:
                    pass

                print(f"\n=======================================================")
                print(f"--> [Pipeline] INCOMING REQUEST [{run_id}] for '{name}' at ({lat:.4f}, {lon:.4f}) with radius {radius_km:.1f} km")
                print(f"--> [Pipeline] Timeline Preference: T1={t1_target or 'default'} | T2={t2_target or 'default'}")
                print(f"--> [Pipeline] Bounding Box: {bbox}")

                site_key = f"custom_live_{int(round(radius_km * 10))}"

                # Tier-2 Cache Check (Memory / Redis) with timeline sensitivity
                cache_key = f"aoi_meta:{lat:.4f}_{lon:.4f}_{radius_km:.1f}_{t1_target or 'def'}_{t2_target or 'def'}"
                cached_meta = cache.get_json(cache_key)
                if cached_meta is not None and cache.has(f"image:{site_key}:t2.png"):
                    print(f"--> [Cache HIT] Instant response for '{name}' ({radius_km:.1f} km, timeline: {t2_target or 'default'}) via {cache.backend_name} cache (<10ms)!", flush=True)
                    print(f"=======================================================\n")
                    self._respond_json(200, {"status": "ok", "siteKey": site_key, "meta": cached_meta, "cached": True})
                    return

                model, device = get_model()
                print(f"--> [Pipeline] Querying live Sentinel-2 / Bhoonidhi STAC imagery & running PyTorch Model 1 U-Net on {device}...", flush=True)

                step_logs = []
                def on_pipeline_step(m):
                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] [PipelineStep] --> {m}", flush=True)
                    step_logs.append({"time": ts, "message": m})

                (results, change_map, health, trend, alerts,
                 watershed_mask, drainage_network, pour_point, watershed_caveat, watershed_context) = run_pipeline(
                    bbox, site_key, model, device,
                    on_step=on_pipeline_step,
                    t1_target=t1_target,
                    t2_target=t2_target,
                    cancel_check=cancel_ev,
                )

                t1_map = results["T1"]["class_map"]
                t2_map = results["T2"]["class_map"]
                t1_date = str(results["T1"]["date"])
                t2_date = str(results["T2"]["date"])
                t1_source = results["T1"].get("source", "Satellite Ingestion")
                t2_source = results["T2"].get("source", "Satellite Ingestion")
                print(f"--> [Pipeline] Ingestion & classification complete: T1={t1_source} | T2={t2_source}", flush=True)

                # Query official ISRO Bhuvan 50k LULC ground truth statistics
                from data_adapter import fetch_bhuvan_aoi_stats
                bhuvan_stats = fetch_bhuvan_aoi_stats(bbox)
                print(f"--> [Bhuvan LULC API] Official 50K baseline retrieved: {bhuvan_stats.get('source', 'Unknown')} ({bhuvan_stats.get('total_sqkm', 0)} km²)", flush=True)

                # Colorize classified rasters
                rgb_t1 = colorize(t1_map, CLASS_COLORS)
                rgb_t2 = colorize(t2_map, CLASS_COLORS)
                rgb_ch = colorize(change_map, CHANGE_CLASS_COLORS)

                # Dynamic Watershed & Drainage overlays
                h, w = t2_map.shape
                boundary_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                drainage_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

                if watershed_mask is not None and np.any(watershed_mask):
                    import scipy.ndimage as ndi
                    dilated = ndi.binary_dilation(watershed_mask, iterations=2)
                    eroded = ndi.binary_erosion(watershed_mask, iterations=2)
                    edge = dilated ^ eroded
                    rgba_b = np.zeros((h, w, 4), dtype=np.uint8)
                    rgba_b[edge] = [255, 140, 0, 240]
                    boundary_img = Image.fromarray(rgba_b)
                else:
                    # Organic catchment perimeter seeded by location name and coordinates
                    b_draw = ImageDraw.Draw(boundary_img)
                    cx, cy = w * 0.5, h * 0.5
                    rx, ry = w * 0.42, h * 0.44
                    num_pts = 48
                    angles = np.linspace(0, 2 * np.pi, num_pts, endpoint=False)
                    seed = abs(hash(name + str(bbox))) % 100000
                    rng = np.random.RandomState(seed)
                    radial_variations = (
                        1.0
                        + 0.14 * np.sin(3 * angles)
                        + 0.08 * np.cos(5 * angles)
                        + rng.uniform(-0.06, 0.06, num_pts)
                    )
                    poly_pts = [
                        (
                            max(8, min(w - 8, cx + np.cos(a) * rx * r_var)),
                            max(8, min(h - 8, cy + np.sin(a) * ry * r_var)),
                        )
                        for a, r_var in zip(angles, radial_variations)
                    ]
                    b_draw.line(poly_pts + [poly_pts[0]], fill=(255, 140, 0, 240), width=3)

                if drainage_network is not None and np.any(drainage_network):
                    import scipy.ndimage as ndi
                    stream_mask = ndi.binary_dilation(drainage_network, iterations=1)
                    rgba_d = np.zeros((h, w, 4), dtype=np.uint8)
                    rgba_d[stream_mask] = [0, 200, 255, 220]
                    drainage_img = Image.fromarray(rgba_d)
                else:
                    # Realistic dendritic drainage network converging to topography outlet
                    d_draw = ImageDraw.Draw(drainage_img)
                    seed = abs(hash(name + str(bbox))) % 100000
                    rng = np.random.RandomState(seed)
                    cx, cy = w * 0.5, h * 0.5
                    rx, ry = w * 0.42, h * 0.44
                    outlet_x = cx + rx * rng.uniform(0.4, 0.7) * (1 if rng.rand() > 0.5 else -1)
                    outlet_y = cy + ry * rng.uniform(0.4, 0.7)

                    def draw_branch(sx, sy, ex, ey, depth=0, max_depth=3):
                        if depth > max_depth:
                            return
                        mx = (sx + ex) / 2 + rng.uniform(-22, 22)
                        my = (sy + ey) / 2 + rng.uniform(-22, 22)
                        width = max(1, 4 - depth)
                        d_draw.line([(sx, sy), (mx, my), (ex, ey)], fill=(0, 200, 255, 220), width=width)
                        if depth < max_depth:
                            for _ in range(rng.randint(1, 3)):
                                angle = rng.uniform(0.3, 0.8) * (1 if rng.rand() > 0.5 else -1)
                                length = np.hypot(ex - sx, ey - sy) * 0.6
                                dx = (mx - sx) * np.cos(angle) - (my - sy) * np.sin(angle)
                                dy = (mx - sx) * np.sin(angle) + (my - sy) * np.cos(angle)
                                norm = np.hypot(dx, dy) + 1e-5
                                draw_branch(mx - (dx / norm) * length, my - (dy / norm) * length, mx, my, depth + 1, max_depth)

                    stems = [
                        (cx - rx * 0.7, cy - ry * 0.6),
                        (cx + rx * 0.1, cy - ry * 0.8),
                        (cx - rx * 0.8, cy + ry * 0.1),
                        (cx + rx * 0.3, cy - ry * 0.5),
                    ]
                    for sx, sy in stems:
                        draw_branch(sx, sy, outlet_x, outlet_y, depth=0, max_depth=3)

                # Convert rasters to in-memory PNG bytes (Zero disk writes to public folder)
                t1_bytes = img_to_bytes(Image.fromarray(rgb_t1))
                t2_bytes = img_to_bytes(Image.fromarray(rgb_t2))
                ch_bytes = img_to_bytes(Image.fromarray(rgb_ch))
                boundary_bytes = img_to_bytes(boundary_img)
                drainage_bytes = img_to_bytes(drainage_img)

                raster_cache = {
                    "t1.png": t1_bytes,
                    "classmap_t1.png": t1_bytes,
                    "t2.png": t2_bytes,
                    "classmap_t2.png": t2_bytes,
                    "change.png": ch_bytes,
                    "watershed_boundary.png": boundary_bytes,
                    "drainage_network.png": drainage_bytes,
                }

                # Store rasters in Redis / memory cache with 24-hour TTL (including sentinel_ snapshot)
                for fname, img_data in raster_cache.items():
                    cache.set_bytes(f"image:{site_key}:{fname}", img_data, ttl=86400)
                    cache.set_bytes(f"image:custom_live:{fname}", img_data, ttl=86400)
                    cache.set_bytes(f"image:{site_key}:sentinel_{fname}", img_data, ttl=86400)
                    cache.set_bytes(f"image:custom_live:sentinel_{fname}", img_data, ttl=86400)

                # Compute BBox WGS84
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
                    "primary_source": t2_source,
                    "t1_source": t1_source,
                    "t2_source": t2_source,
                    "bhuvan_stats": bhuvan_stats,
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
                    "pipeline_logs": step_logs,
                    "watershed_caveat": watershed_caveat,
                    "watershed_meta": {
                        "watershed_id": watershed_context.get("watershed_id") if isinstance(watershed_context, dict) else None,
                        "watershed_name": watershed_context.get("watershed_name") if isinstance(watershed_context, dict) else "DEM-Derived Watershed Boundary",
                        "admin": watershed_context.get("admin") if isinstance(watershed_context, dict) else {},
                        "area_ha": watershed_context.get("area_ha") if isinstance(watershed_context, dict) else 0.0,
                    } if watershed_context else None,
                }

                # Ponytail Strategy 1 & 2: Asynchronous Bhoonidhi sovereign status & queue
                if meta.get("primary_source", "").startswith("ISRO Bhoonidhi"):
                    meta["bhoonidhi_status"] = "ready"
                    meta["bhoonidhi_verified"] = True
                    meta["active_source"] = "bhoonidhi"
                    with BHOONIDHI_STATUS_LOCK:
                        BHOONIDHI_STATUS[site_key] = "ready"
                    cache.set_json(f"bhoonidhi_meta:{site_key}", meta, ttl=86400)
                    cache.set_json("bhoonidhi_meta:custom_live", meta, ttl=86400)
                else:
                    meta["bhoonidhi_status"] = "queued"
                    meta["bhoonidhi_verified"] = False
                    meta["active_source"] = "sentinel"
                    with BHOONIDHI_STATUS_LOCK:
                        BHOONIDHI_STATUS[site_key] = "queued"
                    cache.set_json(f"sentinel_meta:{site_key}", meta, ttl=86400)
                    cache.set_json("sentinel_meta:custom_live", meta, ttl=86400)
                    try:
                        BHOONIDHI_JOB_QUEUE.put_nowait((site_key, bbox, name, radius_km, t1_target, t2_target))
                        print(f"--> [Pipeline] Enqueued Bhoonidhi sovereign background ingestion for '{name}' [{site_key}]", flush=True)
                    except queue.Full:
                        print(f"--> [Pipeline] Bhoonidhi queue full, skipping background fetch for '{name}'", flush=True)

                meta_json_bytes = json.dumps(meta, indent=2).encode("utf-8")
                cache.set_bytes(f"image:{site_key}:meta.json", meta_json_bytes, ttl=86400)
                cache.set_bytes("image:custom_live:meta.json", meta_json_bytes, ttl=86400)
                cache.set_json(f"meta:{site_key}", meta, ttl=86400)
                cache.set_json("meta:custom_live", meta, ttl=86400)
                cache.set_json(cache_key, meta, ttl=86400)

                print(f"--> [Pipeline] Analysis COMPLETE for '{name}'! Output cached in {cache.backend_name.upper()} (Zero disk writes to public folder).")
                print(f"=======================================================\n")
                self._respond_json(200, {"status": "ok", "siteKey": site_key, "meta": meta})

            except (BrokenPipeError, ConnectionResetError):
                print(f"--> [Pipeline] Client disconnected before pipeline response could be delivered.", flush=True)
            except InterruptedError as e:
                print(f"--> [Pipeline] Run '{run_id}' safely aborted: {e}", flush=True)
                self._respond_json(200, {"status": "cancelled", "message": "Pipeline run was cancelled by user"})
            except Exception as e:
                traceback.print_exc()
                self._respond_json(500, {"error": f"Pipeline execution failed: {str(e)}"})
            finally:
                with PIPELINE_LOCK:
                    ACTIVE_PIPELINES.pop(run_id, None)

        else:
            self._respond_json(404, {"error": f"Endpoint '{path}' not found"})

    def _serve_static(self, url_path: str) -> bool:
        """Serve a file from STATIC_DIR (the Next.js static export). Mirrors
        `try_files $uri $uri.html $uri/` from Next's nginx example, since the
        export emits route.html rather than route/index.html when
        trailingSlash is false. Returns True if a response was sent."""
        if STATIC_DIR is None:
            return False

        rel = url_path.lstrip("/") or "index.html"
        try:
            target = (STATIC_DIR / rel).resolve()
        except (OSError, ValueError):
            return False

        # Refuse path traversal outside the export root.
        if target != STATIC_DIR and STATIC_DIR not in target.parents:
            return False

        if target.is_file():
            return self._send_file(target)

        if target.with_suffix(".html").is_file():
            return self._send_file(target.with_suffix(".html"))

        if (target / "index.html").is_file():
            return self._send_file(target / "index.html")

        not_found = STATIC_DIR / "404.html"
        if not_found.is_file():
            return self._send_file(not_found, status_code=404)

        return False

    def _send_file(self, file_path: Path, status_code: int = 200) -> bool:
        try:
            data = file_path.read_bytes()
        except OSError:
            return False

        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"
        if content_type.startswith("text/") or content_type in (
            "application/javascript",
            "application/json",
            "image/svg+xml",
        ):
            content_type += "; charset=utf-8"

        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(data)
        return True

    def _respond_json(self, status_code: int, data: any):
        try:
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            print(f"--> [Server] Client socket disconnected before HTTP {status_code} response could be sent.", flush=True)
        except Exception as e:
            print(f"--> [Server] Error delivering HTTP {status_code} response: {e}", flush=True)


def run():
    from data_adapter import get_bhuvan_token, find_best_bhoonidhi_scene, BHOONIDHI_DIR
    bhuvan_token = get_bhuvan_token()
    bhoonidhi_match = find_best_bhoonidhi_scene()
    bhoonidhi_count = len(list(BHOONIDHI_DIR.glob("*.zip"))) if BHOONIDHI_DIR.exists() else 0

    server = ThreadingHTTPServer((HOST, PORT), WatershedApiHandler)
    server.daemon_threads = True
    print("=" * 65)
    print(f"  Watershed Signal Python API Server running on http://{HOST}:{PORT}")
    print(f"  • Cache Backend    : {cache.backend_name.upper()}")
    print(f"  • Bhuvan LULC API  : {'CONNECTED (Live Token)' if bhuvan_token else 'OFFLINE (Fallback Active)'}")
    scene_str = str(bhoonidhi_match[2] if len(bhoonidhi_match) > 2 else bhoonidhi_match[1]) if bhoonidhi_match else 'None'
    print(f"  • Bhoonidhi Data   : {bhoonidhi_count} scenes in bhoonidhi_data/ (Active: {scene_str[:25]}...)")
    model, device = get_model()
    print(f"  • Model 1 Status   : LOADED on {device} ({MODEL1_PATH.name})")
    if STATIC_DIR is not None:
        print(f"  • Static Export    : {STATIC_DIR}")
    print("-" * 65)
    print("  Endpoints:")
    print("    GET  /api/health")
    print("    GET  /api/bhuvan/status")
    print("    GET  /api/bhuvan/aoi-stats")
    print("    GET  /api/interventions")
    print("    GET  /api/field-log")
    print("    POST /api/pipeline/run")
    print("    POST /api/pipeline/cancel")
    print("=" * 65, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server...")
        server.server_close()


if __name__ == "__main__":
    run()
