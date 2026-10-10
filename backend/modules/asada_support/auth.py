import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Header, HTTPException


ROLES = ("ADMIN", "OPERADOR", "FONTANERO")
PERMISSIONS = {
    "ADMIN": ("summary", "anomalies", "users"),
    "OPERADOR": ("summary", "anomalies"),
    "FONTANERO": ("anomalies", "orders"),
}
PBKDF2_ITERATIONS = 600_000
DATABASE_PATH = Path(os.getenv(
    "AVI_ACCESS_DATABASE",
    Path(__file__).resolve().parents[2] / "data" / "avi_access.sqlite3",
))


@contextmanager
def connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS avi_users(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entity_id TEXT NOT NULL,
          username TEXT NOT NULL COLLATE NOCASE,
          full_name TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('ADMIN','OPERADOR','FONTANERO')),
          password_hash TEXT NOT NULL,
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL,
          UNIQUE(entity_id,username));
        CREATE TABLE IF NOT EXISTS avi_sessions(
          token_hash TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES avi_users(id) ON DELETE CASCADE,
          expires_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS avi_session_expiry ON avi_sessions(expires_at);
        CREATE TABLE IF NOT EXISTS avi_push_subscriptions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL REFERENCES avi_users(id) ON DELETE CASCADE,
          endpoint TEXT NOT NULL UNIQUE,
          p256dh TEXT NOT NULL,
          auth TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS avi_push_user ON avi_push_subscriptions(user_id);
        CREATE TABLE IF NOT EXISTS avi_alert_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entity_id TEXT NOT NULL,
          source_order_id INTEGER NOT NULL,
          payload_json TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'PENDING',
          delivered_count INTEGER NOT NULL DEFAULT 0,
          failed_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          UNIQUE(entity_id,source_order_id));
        """)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def now():
    return datetime.now(timezone.utc)


def hash_password(password: str):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str):
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return algorithm == "pbkdf2_sha256" and hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def public_user(row):
    return {
        "id": row["id"], "entity_id": row["entity_id"], "username": row["username"],
        "full_name": row["full_name"], "role": row["role"], "active": bool(row["active"]),
        "permissions": list(PERMISSIONS[row["role"]]),
    }


def create_session(db, user_id: int):
    token = secrets.token_urlsafe(32)
    expiry = now() + timedelta(hours=12)
    db.execute("DELETE FROM avi_sessions WHERE expires_at<=?", (now().isoformat(),))
    db.execute("INSERT INTO avi_sessions VALUES(?,?,?)", (
        hashlib.sha256(token.encode()).hexdigest(), user_id, expiry.isoformat(),
    ))
    return token


def require_user(entity_id: str, authorization: str | None = Header(default=None)):
    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Inicia sesión en AVI para continuar")
    with connect() as db:
        row = db.execute("""SELECT u.* FROM avi_sessions s JOIN avi_users u ON u.id=s.user_id
                            WHERE s.token_hash=? AND s.expires_at>? AND u.entity_id=? AND u.active=1""",
                         (hashlib.sha256(token.encode()).hexdigest(), now().isoformat(), entity_id)).fetchone()
    if not row:
        raise HTTPException(401, "La sesión de AVI venció")
    return public_user(row)


def require_role(user: dict, *roles):
    if user["role"] not in roles:
        raise HTTPException(403, "Tu perfil de AVI no tiene permiso para esta consulta")
