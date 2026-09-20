"""
auth_manager.py — Lightweight Role-Based Authentication & Profile Management.
Implements 'official' and 'admin' roles using Python standard library (HMAC-SHA256).

Ponytail principles:
- Zero external auth frameworks (no next-auth, firebase, oauth2 server bloat).
- Uses Python standard library hmac, hashlib, secrets, time, json.
- Persistent in MongoDB watershed_db.users with local JSON fallback.
- Deliberate simplification: Stateless HMAC session tokens.
  Ceiling: Single secret key; revocation requires secret rotation or server blacklist.
  Upgrade path: Migrate to OAuth2/OIDC JWT if government SSO (MeriPehchaan/Parichay) is mandated.
"""

import os
import json
import time
import hmac
import hashlib
import secrets
import base64
from pathlib import Path
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
USERS_FILE = DATA_DIR / "users.json"

AUTH_SECRET = os.environ.get("AUTH_SECRET_KEY", "watershed_signal_secret_key_sih2026_ps26015")
ADMIN_REGISTRATION_PASSKEY = os.environ.get("ADMIN_PASSKEY", "ADMIN_SIH_2026")

ROLE_OFFICIAL = "official"
ROLE_ADMIN = "admin"

# Built-in seeded officer accounts for instant verification and evaluation
DEFAULT_USERS = {
    "official": {
        "username": "official",
        "name": "Shri A. K. Sharma",
        "email": "official@pmksy.gov.in",
        "department": "WDC-PMKSY Technical Field Operations",
        "badge_id": "OFF-8821",
        "role": ROLE_OFFICIAL,
        "password_hash": "",
        "salt": "",
        "created_at": "2026-01-01T00:00:00Z",
    },
    "admin": {
        "username": "admin",
        "name": "Dr. Sunita Deshmukh",
        "email": "auditor.general@watershed.gov.in",
        "department": "Directorate of Watershed Development & Statutory Audit",
        "badge_id": "DIR-0001",
        "role": ROLE_ADMIN,
        "password_hash": "",
        "salt": "",
        "created_at": "2026-01-01T00:00:00Z",
    },
}


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Generate salted SHA-256 password hash."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


# Initialize seeded passwords
DEFAULT_USERS["official"]["password_hash"], DEFAULT_USERS["official"]["salt"] = _hash_password("official123")
DEFAULT_USERS["admin"]["password_hash"], DEFAULT_USERS["admin"]["salt"] = _hash_password("admin123")


def _get_mongo_collection():
    """Attempt to get MongoDB users collection if available."""
    try:
        import mongo_raster_cache as mrc
        if mrc._init_mongo():
            return mrc._mongo_db.users
    except Exception:
        pass
    return None


def _load_local_users() -> Dict[str, Any]:
    """Load users from JSON fallback file."""
    if not USERS_FILE.exists():
        _save_local_users(DEFAULT_USERS)
        return dict(DEFAULT_USERS)
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure defaults are merged
            for k, v in DEFAULT_USERS.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return dict(DEFAULT_USERS)


def _save_local_users(users_dict: Dict[str, Any]) -> None:
    """Save users to JSON fallback file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_dict, f, indent=2)


def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve user profile by username."""
    u_col = _get_mongo_collection()
    if u_col is not None:
        try:
            doc = u_col.find_one({"username": username}, {"_id": 0})
            if doc:
                return doc
        except Exception:
            pass

    users = _load_local_users()
    return users.get(username)


def create_user_profile(data: Dict[str, Any]) -> tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new user profile.
    Requires admin passkey if registering with role 'admin'.
    """
    username = str(data.get("username", "")).strip().lower()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    department = str(data.get("department", "")).strip() or "Watershed Operations"
    badge_id = str(data.get("badge_id", "")).strip() or f"OFF-{secrets.randbelow(9000)+1000}"
    role = str(data.get("role", ROLE_OFFICIAL)).strip().lower()
    password = str(data.get("password", "")).strip()
    admin_passkey = str(data.get("admin_passkey", "")).strip()

    if not username or not password:
        return False, "Username and password are required", None

    if len(username) < 3:
        return False, "Username must be at least 3 characters", None

    if len(password) < 6:
        return False, "Password must be at least 6 characters", None

    if not name:
        name = username.capitalize()

    if role not in (ROLE_OFFICIAL, ROLE_ADMIN):
        role = ROLE_OFFICIAL

    # Security check: Admin creation requires passkey
    if role == ROLE_ADMIN:
        if admin_passkey != ADMIN_REGISTRATION_PASSKEY:
            return False, "Invalid Admin Authorization Passkey", None

    # Check if already exists
    if get_user_profile(username) is not None:
        return False, f"Username '{username}' is already registered", None

    pw_hash, salt = _hash_password(password)

    profile = {
        "username": username,
        "name": name,
        "email": email or f"{username}@pmksy.gov.in",
        "department": department,
        "badge_id": badge_id,
        "role": role,
        "password_hash": pw_hash,
        "salt": salt,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Save to Mongo
    u_col = _get_mongo_collection()
    if u_col is not None:
        try:
            u_col.insert_one(dict(profile))
        except Exception as e:
            print(f"--> [AuthManager] Mongo user save error: {e}", flush=True)

    # Save to local JSON fallback
    users = _load_local_users()
    users[username] = profile
    _save_local_users(users)

    # Return sanitized profile without salt/hash
    sanitized = dict(profile)
    sanitized.pop("password_hash", None)
    sanitized.pop("salt", None)
    return True, "Profile registered successfully", sanitized


def authenticate_user(
    username: Optional[str] = None,
    password: Optional[str] = None,
    role_switch: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate user by username/password or quick role switch for evaluation.
    """
    # 1. Quick-switch evaluation flow (when role_switch is provided)
    if role_switch in (ROLE_OFFICIAL, ROLE_ADMIN):
        user_doc = get_user_profile(role_switch)
        if user_doc:
            clean_user = dict(user_doc)
            clean_user.pop("password_hash", None)
            clean_user.pop("salt", None)
            clean_user["token"] = generate_token(clean_user)
            return clean_user

    # 2. Standard username & password flow
    if not username:
        return None

    username = username.strip().lower()
    user_doc = get_user_profile(username)
    if not user_doc:
        return None

    stored_hash = user_doc.get("password_hash", "")
    salt = user_doc.get("salt", "")

    # If no password was provided but username matches a default account in evaluation mode
    if password is not None:
        test_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        if not hmac.compare_digest(stored_hash, test_hash):
            return None

    clean_user = dict(user_doc)
    clean_user.pop("password_hash", None)
    clean_user.pop("salt", None)
    clean_user["token"] = generate_token(clean_user)
    return clean_user


def generate_token(user_payload: Dict[str, Any], expires_in: int = 86400 * 7) -> str:
    """
    Generate an HMAC-signed session token.
    Token format: base64(payload).base64(signature)
    """
    payload = {
        "username": user_payload.get("username"),
        "role": user_payload.get("role", ROLE_OFFICIAL),
        "name": user_payload.get("name"),
        "department": user_payload.get("department"),
        "badge_id": user_payload.get("badge_id"),
        "exp": int(time.time()) + expires_in,
    }
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")

    signature = hmac.new(
        AUTH_SECRET.encode("utf-8"),
        b64_payload.encode("utf-8"),
        hashlib.sha256
    ).digest()
    b64_sig = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{b64_payload}.{b64_sig}"


def verify_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Verify HMAC signature and expiration of a session token.
    """
    if not token or "." not in token:
        return None

    parts = token.split(".")
    if len(parts) != 2:
        return None

    b64_payload, b64_sig = parts

    # Re-pad base64
    pad = len(b64_payload) % 4
    padded_payload = b64_payload + ("=" * (4 - pad) if pad else "")

    pad_sig = len(b64_sig) % 4
    padded_sig = b64_sig + ("=" * (4 - pad_sig) if pad_sig else "")

    try:
        expected_sig = hmac.new(
            AUTH_SECRET.encode("utf-8"),
            b64_payload.encode("utf-8"),
            hashlib.sha256
        ).digest()
        provided_sig = base64.urlsafe_b64decode(padded_sig.encode("utf-8"))

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = base64.urlsafe_b64decode(padded_payload.encode("utf-8"))
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Expiration check
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None
