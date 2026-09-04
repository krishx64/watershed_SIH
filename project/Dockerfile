# Watershed Signal -- deploy image for Hugging Face Spaces (Docker SDK).
#
# Build context is this `project/` folder (COPY paths below are relative to
# it): `docker build -t watershed-signal .` from inside project/, or
# `docker build -t watershed-signal -f project/Dockerfile project/` from the
# repo root. See documentation.md "Deployment" section for the full guide.
#
# CPU-only torch, pinned to the exact same versions (2.6.0 / 0.21.0) already
# validated to work together locally against segmentation-models-pytorch --
# see requirements.txt's header for why an unpinned pair breaks at import
# time with `RuntimeError: operator torchvision::nms does not exist`. Same
# pin, just the cpu wheel index instead of cu124.

FROM python:3.12-slim

WORKDIR /app

# libgomp1: scipy/scikit-image pull in OpenMP at runtime; not always present
# on the slim base. rasterio/geopandas/shapely/pyproj wheels on PyPI bundle
# their own GDAL/GEOS/PROJ builds (manylinux), so no system GDAL needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 \
        --extra-index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY app/ ./app/
COPY models/ ./models/
COPY .streamlit/ ./.streamlit/

# Spaces' Docker SDK expects the app on 7860 and reachable from outside the container.
EXPOSE 7860
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "app/streamlit_app.py"]
