# Watershed Signal — Production Backend Container
# Target: Google Cloud Run / Docker Container
# Exposes the REST API Bridge (app/api_server.py) on $PORT (default 8080)

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies:
# - libgomp1: OpenMP runtime required by scipy, scikit-image, and PyTorch
# - libexpat1: XML/parser library required by rasterio / GDAL binary extensions
# - ca-certificates: Required for secure SSL/TLS connections to satellite data providers
# - curl: Required for container healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    libgomp1 \
    libexpat1 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pinned PyTorch CPU wheels and project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 \
        --extra-index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Create runtime directories for pipeline caching and raster buffers
RUN mkdir -p data/raw data/processed data/labels outputs models

# Copy application source code, models, and configurations
COPY src/ ./src/
COPY app/ ./app/
COPY models/ ./models/
COPY .streamlit/ ./.streamlit/
COPY app.py ./

# Environment defaults for Cloud Run & Python imports
ENV HOST=0.0.0.0 \
    PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app/app \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8080

# Health check verifies the API responds with 200 OK
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Default entrypoint starts embedded Redis daemon then runs the REST API server for Next.js
CMD ["sh", "-c", "redis-server --daemonize yes && python app/api_server.py"]
