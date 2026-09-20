# Watershed Signal -- single-image deployment of the WHOLE project.
#
# Stage 1 builds the Next.js app as a static export (web/out). Stage 2 installs
# the Python pipeline and serves both that export and the /api/* endpoints from
# one process, so there is one container, one port, and no CORS or second
# service to run.
#
# Build from the repository root (this Dockerfile expects the repo root as its
# context, because it needs both web/ and project/):
#   docker build -t watershed-signal .
# Run:
#   docker run --rm -p 8000:8000 watershed-signal

# ---------- Stage 1: Next.js static export ----------
FROM node:22-slim AS web-builder
WORKDIR /web

# Install deps first so this layer caches independently of source edits.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./

# Static export mode disables the /api rewrite (static exports don't support
# rewrites); the Python server handles /api/* directly at runtime. Setting the
# API base to "/" makes the client's API_BASE_URL resolve to a same-origin
# relative path ("/api/...") inside the single container.
RUN NEXT_STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=/ npm run build

# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim
WORKDIR /app

# libgomp1 is needed by scipy/scikit-image at runtime. libexpat1 is required
# by rasterio's manylinux wheel (it links libexpat.so.1 at import time even
# though GDAL itself is bundled). rasterio/geopandas/shapely/pyproj wheels
# otherwise bundle their own GDAL/GEOS/PROJ.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch, pinned to the exact pair validated with
# segmentation-models-pytorch (see project/requirements.txt for why the pins
# matter). Installed first so it caches separately from the rest.
#
# The API image serves the Next.js export as its UI and never runs the
# Streamlit dashboard or the Hugging Face Gradio/FastAPI bridge (project/app.py),
# and aoi_picker/geo_photo import streamlit optionally, so those UI-only stacks
# are filtered out. Deriving from requirements.txt keeps it the single source of
# truth (no second list to drift).
COPY project/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 \
        --extra-index-url https://download.pytorch.org/whl/cpu \
    && grep -vE '^(streamlit|streamlit-folium|gradio|fastapi|uvicorn)[=<>]' requirements.txt > requirements-api.txt \
    && pip install --no-cache-dir -r requirements-api.txt

# Backend code + trained checkpoint, preserving project/src and project/app
# layout that config.py and api_server.py resolve paths from. Only Model 1 is
# loaded by the API; model2_change_siamese.pt (55 MB) is used solely by
# src/model2_change.py's training script and is not needed at runtime.
COPY project/src/ ./src/
COPY project/app/ ./app/
COPY project/models/model1_lulc_unet.pt ./models/

# The built frontend (index.html, try.html, _next/, demo-data/, ...).
COPY --from=web-builder /web/out ./static/

# STATIC_DIR turns on static serving; DEMO_DATA_DIR is where the pipeline
# writes generated PNG/JSON and reads it back (mount a volume here to persist).
ENV STATIC_DIR=/app/static \
    DEMO_DATA_DIR=/app/static/demo-data \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000
CMD ["python", "app/api_server.py"]
