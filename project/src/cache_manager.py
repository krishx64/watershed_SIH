"""
Two-tier Cache Manager for Watershed Signal.
Provides fast caching for:
1. Geocoding lookups (OSM Nominatim)
2. STAC catalog search results
3. Calculated AOI metadata (meta.json outputs)

Architecture:
- If `redis` is installed and `REDIS_URL` is set in environment (or default localhost:6379 connects),
  it uses Redis.
- Otherwise, it transparently uses an in-process thread-safe LRU cache with TTL expiration.
"""

import json
import os
import time
from threading import Lock
from typing import Any, Optional

class _CacheEntry:
    def __init__(self, value: Any, expires_at: float):
        self.value = value
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class CacheManager:
    def __init__(self, default_ttl: int = 86400):
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, _CacheEntry] = {}
        self._lock = Lock()
        self._redis_client = None
        self._redis_bytes_client = None
        self._use_redis = False

        # Attempt to initialize Redis if configured
        redis_url = os.environ.get("REDIS_URL")
        try:
            import redis
            if redis_url:
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_bytes_client = redis.from_url(redis_url, decode_responses=False)
                self._redis_client.ping()
                self._use_redis = True
                print("--> [Cache] Connected to Redis backend.")
            else:
                client = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=0.2, decode_responses=True)
                bytes_client = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=0.2, decode_responses=False)
                client.ping()
                self._redis_client = client
                self._redis_bytes_client = bytes_client
                self._use_redis = True
                print("--> [Cache] Connected to local Redis on port 6379 (JSON + Binary bytes).")
        except Exception:
            self._use_redis = False

    @property
    def backend_name(self) -> str:
        return "redis" if self._use_redis else "in-memory"

    def get_json(self, key: str) -> Optional[Any]:
        if self._use_redis and self._redis_client:
            try:
                raw = self._redis_client.get(key)
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                pass

        with self._lock:
            entry = self._memory_cache.get(key)
            if entry is not None:
                if entry.is_expired():
                    del self._memory_cache[key]
                    return None
                return entry.value
        return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        effective_ttl = ttl if ttl is not None else self.default_ttl
        serialized = json.dumps(value)

        if self._use_redis and self._redis_client:
            try:
                self._redis_client.setex(key, effective_ttl, serialized)
                return
            except Exception:
                pass

        with self._lock:
            if len(self._memory_cache) >= 1000:
                now = time.time()
                expired = [k for k, v in self._memory_cache.items() if v.is_expired()]
                for k in expired:
                    del self._memory_cache[k]
                if len(self._memory_cache) >= 1000:
                    for k in list(self._memory_cache.keys())[:200]:
                        del self._memory_cache[k]

            self._memory_cache[key] = _CacheEntry(value, time.time() + effective_ttl)

    def get_bytes(self, key: str) -> Optional[bytes]:
        if self._use_redis and self._redis_bytes_client:
            try:
                raw = self._redis_bytes_client.get(key)
                if raw is not None:
                    return raw
            except Exception:
                pass

        with self._lock:
            entry = self._memory_cache.get(key)
            if entry is not None:
                if entry.is_expired():
                    del self._memory_cache[key]
                    return None
                if isinstance(entry.value, (bytes, bytearray)):
                    return bytes(entry.value)
        return None

    def set_bytes(self, key: str, data: bytes, ttl: Optional[int] = None) -> None:
        effective_ttl = ttl if ttl is not None else self.default_ttl

        if self._use_redis and self._redis_bytes_client:
            try:
                self._redis_bytes_client.setex(key, effective_ttl, data)
                return
            except Exception:
                pass

        with self._lock:
            if len(self._memory_cache) >= 1000:
                now = time.time()
                expired = [k for k, v in self._memory_cache.items() if v.is_expired()]
                for k in expired:
                    del self._memory_cache[k]
                if len(self._memory_cache) >= 1000:
                    for k in list(self._memory_cache.keys())[:200]:
                        del self._memory_cache[k]

            self._memory_cache[key] = _CacheEntry(data, time.time() + effective_ttl)

    def has(self, key: str) -> bool:
        return self.get_json(key) is not None or self.get_bytes(key) is not None


# Global singleton cache instance
cache = CacheManager()
