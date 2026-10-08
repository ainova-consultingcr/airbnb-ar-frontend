import hashlib
import hmac
import os
import sqlite3

from fastapi import APIRouter, Header, HTTPException

from core.http import require_entity_module
from .auth import (connect, create_session, hash_password, now, public_user,
                   require_role, require_user, verify_password)
from .monitor import admin_summary, anomaly_context, answer_question, fetch_monitor
from .schemas import Login, Setup, SupportQuestion, UserCreate


router = APIRouter(prefix="/asadas/{entity_id}/support", tags=["AVI ASADA support"])
DUMMY_HASH = hash_password("contraseña-de-comparacion")


def enabled_entity(entity_id):
    return require_entity_module(entity_id, "asada_support")


@router.get("/status")
def status(entity_id: str, authorization: str | None = Header(default=None)):
    enabled_entity(entity_id)
    with connect() as db:
        setup_required = not db.execute("SELECT 1 FROM avi_users WHERE entity_id=? LIMIT 1", (entity_id,)).fetchone()
    if setup_required:
        return {"setup_required": True, "user": None}
    try:
        user = require_user(entity_id, authorization)
    except HTTPException:
        user = None
    return {"setup_required": False, "user": user}


@router.post("/setup", status_code=201)
def setup(entity_id: str, payload: Setup, x_setup_key: str | None = Header(default=None)):
    enabled_entity(entity_id)
    expected = os.getenv("AVI_SETUP_KEY", "")
    if not expected or not x_setup_key or not hmac.compare_digest(expected, x_setup_key):
        raise HTTPException(401, "Clave de configuración de AVI inválida")
    if payload.role != "ADMIN":
        raise HTTPException(422, "La primera cuenta de AVI debe ser administradora")
    try:
        with connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM avi_users WHERE entity_id=? LIMIT 1", (entity_id,)).fetchone():
                raise HTTPException(409, "AVI ya fue configurado para esta ASADA")
            cursor = db.execute("""INSERT INTO avi_users(entity_id,username,full_name,role,password_hash,created_at)
                                   VALUES(?,?,?,?,?,?)""", (entity_id, payload.username.lower(), payload.full_name,
                                   "ADMIN", hash_password(payload.password), now().isoformat()))
            token = create_session(db, cursor.lastrowid)
            row = db.execute("SELECT * FROM avi_users WHERE id=?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "El usuario ya existe")
    return {**public_user(row), "access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(entity_id: str, payload: Login):
    enabled_entity(entity_id)
    with connect() as db:
        row = db.execute("SELECT * FROM avi_users WHERE entity_id=? AND username=? COLLATE NOCASE",
                         (entity_id, payload.username)).fetchone()
        valid = verify_password(payload.password, row["password_hash"] if row else DUMMY_HASH)
        if not row or not valid or not row["active"]:
            raise HTTPException(401, "Usuario o contraseña de AVI incorrectos")
        token = create_session(db, row["id"])
    return {**public_user(row), "access_token": token, "token_type": "bearer"}


@router.get("/users")
def users(entity_id: str, authorization: str | None = Header(default=None)):
    actor = require_user(entity_id, authorization)
    require_role(actor, "ADMIN")
    with connect() as db:
        return [public_user(row) for row in db.execute(
            "SELECT * FROM avi_users WHERE entity_id=? ORDER BY full_name", (entity_id,)
        )]


@router.post("/users", status_code=201)
def create_user(entity_id: str, payload: UserCreate, authorization: str | None = Header(default=None)):
    actor = require_user(entity_id, authorization)
    require_role(actor, "ADMIN")
    try:
        with connect() as db:
            cursor = db.execute("""INSERT INTO avi_users(entity_id,username,full_name,role,password_hash,created_at)
                                   VALUES(?,?,?,?,?,?)""", (entity_id, payload.username.lower(), payload.full_name,
                                   payload.role, hash_password(payload.password), now().isoformat()))
            row = db.execute("SELECT * FROM avi_users WHERE id=?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "El usuario ya existe en esta ASADA")
    return public_user(row)


def monitor_data(entity, user):
    nodes = fetch_monitor(entity, "/api/integrations/avi/nodes")
    orders_payload = fetch_monitor(entity, "/api/integrations/avi/work-orders")
    orders = orders_payload.get("items", orders_payload) if isinstance(orders_payload, dict) else orders_payload
    return nodes, orders


@router.get("/context")
def context(entity_id: str, authorization: str | None = Header(default=None)):
    user = require_user(entity_id, authorization)
    entity = enabled_entity(entity_id)
    nodes, orders = monitor_data(entity, user)
    return anomaly_context(nodes, orders, user)


@router.get("/summary")
def summary(entity_id: str, period_days: int = 30, authorization: str | None = Header(default=None)):
    user = require_user(entity_id, authorization)
    require_role(user, "ADMIN", "OPERADOR")
    entity = enabled_entity(entity_id)
    nodes, orders = monitor_data(entity, user)
    if not 1 <= period_days <= 365:
        raise HTTPException(422, "El período debe estar entre 1 y 365 días")
    return admin_summary(nodes, orders, period_days)


@router.post("/ask")
def ask(entity_id: str, payload: SupportQuestion, authorization: str | None = Header(default=None)):
    user = require_user(entity_id, authorization)
    entity = enabled_entity(entity_id)
    nodes, orders = monitor_data(entity, user)
    return answer_question(payload.question, user, nodes, orders, payload.period_days)
