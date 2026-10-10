import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException


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
        CREATE TABLE IF NOT EXISTS avi_asada_push_subscriptions(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entity_id TEXT NOT NULL,
          username TEXT NOT NULL COLLATE NOCASE,
          endpoint TEXT NOT NULL UNIQUE,
          p256dh TEXT NOT NULL,
          auth TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS avi_asada_push_user
          ON avi_asada_push_subscriptions(entity_id,username);
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


def require_role(user: dict, *roles):
    if user["role"] not in roles:
        raise HTTPException(403, "Tu perfil de AVI no tiene permiso para esta consulta")
