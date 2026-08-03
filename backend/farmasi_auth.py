from datetime import datetime, timedelta, timezone
from threading import Lock
import hmac
import secrets
from farmasi_sellers import seller_by_credentials


_sessions = {}
_lock = Lock()
SESSION_HOURS = 8


def authenticate_seller(slug, username, password):
    seller = seller_by_credentials(slug, username)
    if not seller:
        return None
    valid = (
        hmac.compare_digest(username, seller["username"])
        and hmac.compare_digest(password, seller["password"])
    )
    if not valid:
        return None
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    with _lock:
        _sessions[token] = {"expires_at": expires_at, "seller_id": seller["id"]}
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at.isoformat(), "seller_id": seller["id"]}


def validate_seller_token(token):
    if not token:
        return False
    now = datetime.now(timezone.utc)
    with _lock:
        session = _sessions.get(token)
        if not session or session["expires_at"] <= now:
            _sessions.pop(token, None)
            return None
        return {"seller_id": session["seller_id"]}


def revoke_seller_token(token):
    with _lock:
        _sessions.pop(token, None)
