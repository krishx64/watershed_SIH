"""
bhoonidhi_client.py — Official ISRO Bhoonidhi STAC & Download Client.
Connects to https://bhoonidhi-api.nrsc.gov.in for Indian satellite imagery.

Ponytail principles:
- Standard library only (urllib.request + ssl + json), zero third-party OAuth bloat.
- In-memory token caching with 60s safety buffer to respect the 20 auth/hr limit.
- Abortable chunked streaming with time-budget circuit breaker to prevent hanging on large ZIPs.
- Automatic error classification for HTTP 412 (concurrency) and 429 (rate limiting).
"""

import os
import json
import ssl
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import urllib.request
import urllib.error

# Load environment variables if not already loaded
try:
    import dotenv
    dotenv.load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

BASE_URL = "https://bhoonidhi-api.nrsc.gov.in"

# ponytail: Single global download semaphore ensures at most ONE active Bhoonidhi download
# across the entire server, protecting against HTTP 412 (concurrency > 3) and bandwidth saturation.
BHOONIDHI_SEMAPHORE = threading.BoundedSemaphore(value=1)
_circuit_breaker_until: float = 0.0

def is_circuit_broken() -> bool:
    """Check if Bhoonidhi circuit breaker is active."""
    return time.time() < _circuit_breaker_until

def trip_circuit_breaker(duration_sec: float = 900.0, reason: str = "Rate limit"):
    """Trip Bhoonidhi circuit breaker to protect NRSC servers."""
    global _circuit_breaker_until
    _circuit_breaker_until = time.time() + duration_sec
    print(f"--> [Bhoonidhi] Circuit breaker TRIPPED for {duration_sec:.0f}s ({reason}). Diverting to AWS S3 fallback.", flush=True)

class BhoonidhiClient:
    def __init__(self, user: Optional[str] = None, password: Optional[str] = None):
        self.user = user or os.environ.get("BHOONIDHI_USER")
        self.password = password or os.environ.get("BHOONIDHI_PASSWORD")
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._refresh_token: Optional[str] = None

        # SSL context for government portal
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def get_token(self) -> str:
        """
        Authenticate or refresh JWT token. Bhoonidhi allows 20 token requests/hr.
        Reuses cached access_token if still valid (>60s remaining).
        """
        now = time.time()
        # ponytail: reuse cached token until 60s before expiry to protect 20 auth/hr quota
        if self._access_token and (self._token_expiry - now) > 60:
            return self._access_token

        if not self.user or not self.password:
            raise ValueError("BHOONIDHI_USER and BHOONIDHI_PASSWORD must be configured in .env")

        # Try refresh token grant if available
        if self._refresh_token and (self._token_expiry - now) <= 60:
            try:
                return self._refresh_access_token()
            except Exception:
                pass  # Fall back to password grant

        # Password grant authentication
        url = f"{BASE_URL}/auth/token"
        payload = json.dumps({
            "userId": self.user,
            "password": self.password,
            "grant_type": "password",
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "WatershedSignal/1.0"}
        )
        with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self._access_token = data["access_token"]
            self._refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 1200)
            self._token_expiry = now + expires_in
            print(f"--> [Bhoonidhi] New token acquired for user '{self.user}' (valid for {expires_in}s)", flush=True)
            return self._access_token

    def _refresh_access_token(self) -> str:
        url = f"{BASE_URL}/auth/token"
        payload = json.dumps({
            "userId": self.user,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "WatershedSignal/1.0"}
        )
        with urllib.request.urlopen(req, context=self.ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self._access_token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 1200)
            return self._access_token

    def search_scenes(
        self,
        bbox: tuple,
        datetime_str: str,
        collection: str = "ResourceSat-2A_LISS3_BOA",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search Bhoonidhi STAC catalog for Online products covering bbox.
        CRITICAL: filter 'Online' == 'Y' ensures the product can be downloaded via API.
        """
        token = self.get_token()
        url = f"{BASE_URL}/data/search"

        payload = {
            "collections": [collection],
            "bbox": list(bbox),
            "datetime": datetime_str,
            "filter": {
                "args": [{"property": "Online"}, "Y"],
                "op": "eq",
            },
            "filter-lang": "cql2-json",
            "limit": limit,
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "WatershedSignal/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                features = data.get("features", [])
                print(f"--> [Bhoonidhi] Search '{collection}' returned {len(features)} online scenes", flush=True)
                return features
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"--> [Bhoonidhi] Search '{collection}' returned 0 scenes (HTTP 404: no data in catalog for this date/aoi)", flush=True)
                return []
            raise

    def download_scene_zip(
        self,
        product_id: str,
        collection: str,
        out_zip_path: Path,
        timeout: float = 15.0,
    ) -> Path:
        """
        Download product archive from Bhoonidhi with a strict time budget.
        Guarded by BHOONIDHI_SEMAPHORE (max 1 concurrent download) and circuit breaker.
        """
        if is_circuit_broken():
            raise RuntimeError("Bhoonidhi circuit breaker active due to rate limits. Using fallback.")

        # Non-blocking acquisition to avoid thread pool starvation
        acquired = BHOONIDHI_SEMAPHORE.acquire(blocking=True, timeout=5.0)
        if not acquired:
            raise RuntimeError("Bhoonidhi download in progress by another worker. Using fast fallback.")

        try:
            token = self.get_token()
            url = f"{BASE_URL}/download?id={product_id}&collection={collection}"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "WatershedSignal/1.0",
                },
            )

            out_zip_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = out_zip_path.with_suffix(".tmp")
            start_time = time.time()

            try:
                with urllib.request.urlopen(req, context=self.ctx, timeout=timeout) as resp:
                    cl_header = resp.headers.get("Content-Length")
                    cl = int(cl_header) if cl_header and cl_header.isdigit() else 0
                    total_mb_str = f"{cl / (1024 * 1024):.1f} MB" if cl > 0 else "unknown size"
                    print(f"--> [Bhoonidhi Download] Connected! Total Archive Size: {total_mb_str}. Streaming...", flush=True)

                    downloaded = 0
                    last_log_time = start_time
                    with open(temp_path, "wb") as f:
                        while True:
                            # ponytail: abort download if exceeding time budget to trigger graceful fallback
                            elapsed = time.time() - start_time
                            if elapsed > timeout:
                                d_mb = downloaded / (1024 * 1024)
                                raise TimeoutError(
                                    f"Bhoonidhi download exceeded time budget ({timeout:.0f}s) after downloading {d_mb:.1f} MB of {total_mb_str}"
                                )

                            chunk = resp.read(1024 * 1024)  # 1MB chunk
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            if now - last_log_time >= 5.0:
                                last_log_time = now
                                speed = (downloaded / (1024 * 1024)) / max(0.01, elapsed)
                                pct_str = f"({(downloaded / cl * 100):.0f}%)" if cl > 0 else ""
                                print(
                                    f"--> [Bhoonidhi Download] {downloaded / (1024 * 1024):.1f} MB / {total_mb_str} {pct_str} at {speed:.2f} MB/s (elapsed: {elapsed:.0f}s)...",
                                    flush=True,
                                )

                if cl > 0 and downloaded < int(cl * 0.95):
                    if temp_path.exists():
                        temp_path.unlink()
                    raise IOError(
                        f"Premature stream EOF: Received only {downloaded / (1024 * 1024):.1f} MB of expected {total_mb_str}."
                    )

                import zipfile
                if not zipfile.is_zipfile(temp_path):
                    if temp_path.exists():
                        temp_path.unlink()
                    raise IOError(
                        f"Corrupted archive: Received file ({downloaded / (1024 * 1024):.1f} MB) is not a valid ZIP archive."
                    )

                temp_path.replace(out_zip_path)
                total_time = time.time() - start_time
                file_size_mb = out_zip_path.stat().st_size / (1024 * 1024)
                print(f"--> [Bhoonidhi] Successfully downloaded and verified {product_id} ({file_size_mb:.1f} MB in {total_time:.2f}s)", flush=True)
                return out_zip_path
            except urllib.error.HTTPError as e:
                if temp_path.exists():
                    temp_path.unlink()
                if e.code == 412:
                    trip_circuit_breaker(900.0, "Concurrency limit exceeded (HTTP 412)")
                    raise RuntimeError("Bhoonidhi concurrent download limit (3) exceeded (HTTP 412)")
                elif e.code == 429:
                    trip_circuit_breaker(1200.0, "Rate limit reached (HTTP 429)")
                    raise RuntimeError("Bhoonidhi rate limit reached (HTTP 429)")
                raise
            except Exception:
                if temp_path.exists():
                    temp_path.unlink()
                raise
        finally:
            BHOONIDHI_SEMAPHORE.release()
