"""
mongo_raster_cache.py — Lightweight MongoDB Clipped Raster Store & Ingestion Audit.
Stores pre-clipped, 6-channel normalized watershed tensors (~4 MB) in MongoDB GridFS
for <50ms repeat reads, eliminating the need to download or store 1 GB raw scene ZIPs.

Ponytail principles:
- Minimal code, zero boilerplate, no heavy ORM layers.
- Uses GridFS for chunked binary storage; standard BSON for metadata and audit logging.
- Gracefully degrades to a no-op if MongoDB is not running or unreachable.
"""

import os
import io
import time
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
import numpy as np

_mongo_client = None
_mongo_db = None
_grid_fs = None
_connected = False
_connection_attempted = False


def _init_mongo():
    """Lazy initialize MongoDB client with quick timeout so offline dev doesn't hang."""
    global _mongo_client, _mongo_db, _grid_fs, _connected, _connection_attempted
    if _connection_attempted:
        return _connected

    _connection_attempted = True
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
    db_name = os.environ.get("MONGO_DB_NAME", "watershed_db")

    try:
        import pymongo
        import gridfs
        # Try primary URI first (e.g. 127.0.0.1 on host, or host.docker.internal in Docker)
        candidates = [mongo_uri]
        if "127.0.0.1" in mongo_uri or "localhost" in mongo_uri:
            candidates.append(mongo_uri.replace("127.0.0.1", "host.docker.internal").replace("localhost", "host.docker.internal"))

        for uri in candidates:
            try:
                client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=1000)
                client.admin.command("ping")
                _mongo_client = client
                _mongo_db = _mongo_client[db_name]
                _grid_fs = gridfs.GridFS(_mongo_db, collection="raster_cache")
                _connected = True
                print(f"--> [MongoCache] Connected to MongoDB Compass/Local ({db_name}) at {uri}", flush=True)
                return _connected
            except Exception:
                continue

        # If loop completed without connection
        raise RuntimeError(f"Could not connect to MongoDB at {candidates}")
    except Exception as e:
        # ponytail: graceful no-op on Mongo connection failure to keep pipeline running offline
        _connected = False
        print(f"--> [MongoCache] MongoDB not reachable ({e}). Gracefully running without Mongo cache.", flush=True)

    return _connected


def bbox_to_key(bbox: tuple) -> str:
    """Canonical string key for bounding box rounded to 4 decimal places (~11m)."""
    return f"{bbox[0]:.4f}_{bbox[1]:.4f}_{bbox[2]:.4f}_{bbox[3]:.4f}"


def get_cached_raster(bbox: tuple, date_tag: str) -> Optional[Tuple[np.ndarray, str, Dict[str, Any]]]:
    """
    Fetch pre-clipped 6-channel array from MongoDB GridFS (<50ms).
    Returns (stack, source_label, metadata_dict) or None on cache miss.
    """
    if not _init_mongo():
        return None

    key = bbox_to_key(bbox)
    try:
        doc = _mongo_db.raster_meta.find_one({"bbox_key": key, "date_tag": date_tag})
        if not doc:
            return None

        # Fetch bytes from GridFS
        file_id = doc["gridfs_id"]
        raw_bytes = _grid_fs.get(file_id).read()

        # ponytail: direct numpy buffer deserialization via io.BytesIO without custom codecs
        buf = io.BytesIO(raw_bytes)
        stack = np.load(buf)
        source = doc.get("source", "MongoDB Cached Raster")
        metadata = doc.get("metadata", {})
        print(f"--> [MongoCache] Cache HIT for {date_tag} [{key}] (Source: {source})", flush=True)
        return stack, source, metadata
    except Exception as e:
        print(f"--> [MongoCache] Error reading from Mongo: {e}", flush=True)
        return None


def save_cached_raster(
    bbox: tuple,
    date_tag: str,
    stack: np.ndarray,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Save clipped 6-channel array into MongoDB GridFS.
    Compresses to ~4MB and stores alongside spatial query metadata.
    """
    if not _init_mongo():
        return False

    key = bbox_to_key(bbox)
    try:
        # Check if old entry exists and delete its GridFS file to prevent orphaned chunks
        old = _mongo_db.raster_meta.find_one({"bbox_key": key, "date_tag": date_tag})
        if old and "gridfs_id" in old:
            try:
                _grid_fs.delete(old["gridfs_id"])
            except Exception:
                pass

        # ponytail: serialize numpy array to in-memory buffer in float32
        buf = io.BytesIO()
        np.save(buf, stack.astype(np.float32))
        buf.seek(0)
        data = buf.read()

        gridfs_id = _grid_fs.put(
            data,
            filename=f"{key}_{date_tag}.npy",
            content_type="application/x-numpy",
        )

        _mongo_db.raster_meta.update_one(
            {"bbox_key": key, "date_tag": date_tag},
            {"$set": {
                "bbox_key": key,
                "bbox": list(bbox),
                "date_tag": date_tag,
                "source": source,
                "gridfs_id": gridfs_id,
                "shape": list(stack.shape),
                "size_bytes": len(data),
                "metadata": metadata or {},
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        print(f"--> [MongoCache] Stored {date_tag} raster in GridFS ({len(data)/1e6:.2f} MB, source: {source})", flush=True)
        return True
    except Exception as e:
        print(f"--> [MongoCache] Error writing to Mongo: {e}", flush=True)
        return False


def log_ingestion_audit(
    action: str,
    aoi_name: str,
    bbox: tuple,
    date_tag: str,
    source: str,
    tier: int,
    latency_s: float,
    fallback_reason: Optional[str] = None,
    product_id: Optional[str] = None,
) -> None:
    """
    Log satellite ingestion event directly to unified audit trail and MongoDB collection.
    """
    try:
        import audit_logger
        audit_logger.record_audit(
            category="ingestion",
            action=action,
            user="pipeline_worker",
            role="system",
            details={
                "aoi_name": aoi_name,
                "bbox": list(bbox),
                "date_tag": date_tag,
                "source": source,
                "tier": tier,
                "product_id": product_id,
                "latency_s": round(latency_s, 3),
                "fallback_reason": fallback_reason,
            },
            status="fallback" if fallback_reason else "success",
        )
        print(f"--> [MongoAudit] Logged ingestion audit (Tier {tier}, {source})", flush=True)
    except Exception as e:
        print(f"--> [MongoAudit] Failed to log audit: {e}", flush=True)

