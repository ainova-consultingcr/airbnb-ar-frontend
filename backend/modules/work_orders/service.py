from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .integrations import IntegrationUnavailable, book_inspection, integration_configured, sync_inspection, sync_order


REQUEST_STATUSES = {"received", "contacted", "scheduled", "converted", "cancelled"}
ORDER_TRANSITIONS = {
    "diagnosis": {"awaiting_approval", "cancelled"},
    "awaiting_approval": {"approved", "rejected", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"quality_check", "cancelled"},
    "quality_check": {"in_progress", "ready"},
    "ready": {"delivered"},
    "rejected": {"diagnosis", "cancelled"},
    "delivered": set(), "cancelled": set(),
}


def _now(): return datetime.now(timezone.utc).isoformat()
def _db_path(): return os.getenv("AVI_WORKSHOP_DB", os.path.join(os.path.dirname(__file__), "..", "..", "data", "avi_workshop.db"))


@contextmanager
def _connect():
    path = os.path.abspath(_db_path())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    _init(connection)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _init(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS workshops(id TEXT PRIMARY KEY, slug TEXT UNIQUE, name TEXT, active INTEGER);
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, workshop_id TEXT, username TEXT, password_hash TEXT, role TEXT, active INTEGER, UNIQUE(workshop_id,username));
    CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT, workshop_id TEXT, role TEXT, expires_at TEXT);
    CREATE TABLE IF NOT EXISTS service_requests(id TEXT PRIMARY KEY, code TEXT UNIQUE, workshop_id TEXT, tracking_token_hash TEXT, customer_name TEXT, phone TEXT, consent INTEGER, vehicle_make TEXT, vehicle_model TEXT, vehicle_year INTEGER, plate TEXT, vin TEXT, mileage INTEGER, problem TEXT, preferred_date TEXT, status TEXT, created_at TEXT, updated_at TEXT, version INTEGER);
    CREATE TABLE IF NOT EXISTS work_orders(id TEXT PRIMARY KEY, code TEXT UNIQUE, request_id TEXT UNIQUE, workshop_id TEXT, technician TEXT, diagnosis TEXT, promised_date TEXT, status TEXT, currency TEXT, subtotal REAL, tax REAL, total REAL, decision_comment TEXT, created_at TEXT, updated_at TEXT, version INTEGER);
    CREATE TABLE IF NOT EXISTS work_order_lines(id TEXT PRIMARY KEY, work_order_id TEXT, kind TEXT, description TEXT, sku TEXT, quantity REAL, unit_price REAL);
    CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT, workshop_id TEXT, entity_type TEXT, entity_id TEXT, actor_type TEXT, actor_id TEXT, event TEXT, from_status TEXT, to_status TEXT, note TEXT, created_at TEXT);
    """)
    columns = {row["name"] for row in db.execute("PRAGMA table_info(workshops)")}
    if "whatsapp_number" not in columns:
        db.execute("ALTER TABLE workshops ADD COLUMN whatsapp_number TEXT")
    request_columns = {row["name"] for row in db.execute("PRAGMA table_info(service_requests)")}
    for name in ("inspection_start", "inspection_end", "calendar_event_id"):
        if name not in request_columns:
            db.execute(f"ALTER TABLE service_requests ADD COLUMN {name} TEXT")
    slug = os.getenv("AVI_WORKSHOP_SLUG", "ruta27")
    workshop_id = "workshop-ruta27"
    whatsapp_number = _configured_whatsapp(slug)
    db.execute(
        "INSERT OR IGNORE INTO workshops(id,slug,name,active,whatsapp_number) VALUES(?,?,?,1,?)",
        (workshop_id, slug, os.getenv("AVI_WORKSHOP_NAME", "Repuestos Ruta 27"), whatsapp_number),
    )
    db.execute(
        "UPDATE workshops SET name=?,whatsapp_number=? WHERE id=?",
        (os.getenv("AVI_WORKSHOP_NAME", "Repuestos Ruta 27"), whatsapp_number, workshop_id),
    )
    username = os.getenv("AVI_WORKSHOP_ADVISOR_USER", "asesor")
    password = os.getenv("AVI_WORKSHOP_ADVISOR_PASSWORD", "AVI-Taller-2026")
    db.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,1)", ("user-advisor-ruta27", workshop_id, username, _hash_password(password), "advisor"))
    mechanic_user = os.getenv("AVI_WORKSHOP_MECHANIC_USER", "mecanico")
    mechanic_password = os.getenv("AVI_WORKSHOP_MECHANIC_PASSWORD", "AVI-Mecanico-2026")
    db.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?,?,1)", ("user-mechanic-ruta27", workshop_id, mechanic_user, _hash_password(mechanic_password), "mechanic"))
    db.commit()


def _hash_password(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 210_000).hex()
    return f"{salt}${digest}"


def _verify_password(value, stored):
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(_hash_password(value, salt), stored)


def _token_hash(token): return hashlib.sha256(token.encode()).hexdigest()
def _code(prefix): return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
def _row(row): return dict(row) if row else None


def _whatsapp_number(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits if 8 <= len(digits) <= 15 else None


def _configured_whatsapp(slug):
    raw = os.getenv("AVI_WORKSHOP_WHATSAPP_BY_SLUG", "")
    if raw:
        try:
            configured = json.loads(raw)
            if isinstance(configured, dict) and slug in configured:
                return _whatsapp_number(configured[slug])
        except (TypeError, ValueError):
            pass
    return _whatsapp_number(os.getenv("AVI_WORKSHOP_WHATSAPP_NUMBER", ""))


def _audit(db, workshop_id, entity_type, entity_id, actor_type, actor_id, event, old=None, new=None, note=None):
    db.execute("INSERT INTO audit_events(workshop_id,entity_type,entity_id,actor_type,actor_id,event,from_status,to_status,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (workshop_id, entity_type, entity_id, actor_type, actor_id, event, old, new, note, _now()))


def workshop_by_slug(slug):
    with _connect() as db: return _row(db.execute("SELECT * FROM workshops WHERE slug=? AND active=1", (slug,)).fetchone())


def create_request(slug, payload):
    if not payload["consent_to_contact"]: raise ValueError("Contact consent is required")
    workshop = workshop_by_slug(slug)
    if not workshop: raise LookupError(slug)
    request_id, token, timestamp = str(uuid.uuid4()), secrets.token_urlsafe(32), _now()
    values = (request_id, _code("SOL"), workshop["id"], _token_hash(token), payload["customer_name"], payload["phone"], 1, payload["vehicle_make"], payload["vehicle_model"], payload["vehicle_year"], payload.get("plate"), payload.get("vin"), payload.get("mileage"), payload["problem"], payload.get("preferred_date"), "received", timestamp, timestamp, 1)
    with _connect() as db:
        db.execute("""INSERT INTO service_requests(
            id,code,workshop_id,tracking_token_hash,customer_name,phone,consent,
            vehicle_make,vehicle_model,vehicle_year,plate,vin,mileage,problem,
            preferred_date,status,created_at,updated_at,version
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
        _audit(db, workshop["id"], "service_request", request_id, "customer", "public", "created", None, "received")
    return {"id": request_id, "code": values[1], "status": "received", "tracking_token": token, "created_at": timestamp}


def customer_tracking(slug, request_id, token):
    workshop = workshop_by_slug(slug)
    if not workshop: raise LookupError(slug)
    with _connect() as db:
        request = _row(db.execute("SELECT * FROM service_requests WHERE id=? AND workshop_id=? AND tracking_token_hash=?", (request_id, workshop["id"], _token_hash(token))).fetchone())
        if not request: raise PermissionError()
        order = _row(db.execute("SELECT * FROM work_orders WHERE request_id=?", (request_id,)).fetchone())
        if order:
            order["lines"] = [_row(x) for x in db.execute("SELECT kind,description,sku,quantity,unit_price FROM work_order_lines WHERE work_order_id=?", (order["id"],))]
        events = [_row(x) for x in db.execute("SELECT event,from_status,to_status,note,created_at FROM audit_events WHERE entity_id IN (?,?) AND actor_type!='staff_private' ORDER BY id", (request_id, order["id"] if order else ""))]
    return {"request": request, "work_order": order, "history": events}


def reserve_inspection(slug, request_id, token, start, end):
    workshop = workshop_by_slug(slug)
    if not workshop: raise LookupError(slug)
    with _connect() as db:
        request = db.execute(
            "SELECT * FROM service_requests WHERE id=? AND workshop_id=? AND tracking_token_hash=?",
            (request_id, workshop["id"], _token_hash(token)),
        ).fetchone()
        if not request: raise PermissionError()
        if request["calendar_event_id"]: raise ValueError("Inspection is already booked")
        public_payload = {
            "request_code": request["code"], "start": start, "end": end,
            "vehicle": f'{request["vehicle_make"]} {request["vehicle_model"]} {request["vehicle_year"]}',
        }
        booked = book_inspection(public_payload)
        if not booked.get("event_id"): raise IntegrationUnavailable("Calendar did not confirm the inspection")
        timestamp = _now()
        db.execute(
            "UPDATE service_requests SET inspection_start=?,inspection_end=?,calendar_event_id=?,status='scheduled',updated_at=?,version=version+1 WHERE id=?",
            (start, end, booked["event_id"], timestamp, request_id),
        )
        _audit(db, workshop["id"], "service_request", request_id, "customer", request_id, "inspection_booked", request["status"], "scheduled", f"Inspección reservada: {start}")
    sync_inspection({"request_code": request["code"], "start": start, "end": end, "status": "scheduled", "event_id": booked["event_id"], "updated_at": timestamp})
    return customer_tracking(slug, request_id, token)


def login(slug, username, password):
    workshop = workshop_by_slug(slug)
    if not workshop: return None
    with _connect() as db:
        user = db.execute("SELECT * FROM users WHERE workshop_id=? AND username=? AND active=1", (workshop["id"], username)).fetchone()
        if not user or not _verify_password(password, user["password_hash"]): return None
        token, expires = secrets.token_urlsafe(32), (datetime.now(timezone.utc)+timedelta(hours=8)).isoformat()
        db.execute("INSERT INTO sessions VALUES(?,?,?,?,?)", (_token_hash(token), user["id"], workshop["id"], user["role"], expires))
        return {"access_token": token, "expires_at": expires, "role": user["role"]}


def authenticate(token, slug):
    workshop = workshop_by_slug(slug)
    if not token or not workshop: return None
    with _connect() as db:
        row = _row(db.execute("SELECT * FROM sessions WHERE token_hash=? AND workshop_id=? AND expires_at>?", (_token_hash(token), workshop["id"], _now())).fetchone())
    return row


def list_requests(slug):
    workshop = workshop_by_slug(slug)
    with _connect() as db:
        return [_row(x) for x in db.execute("SELECT * FROM service_requests WHERE workshop_id=? ORDER BY created_at DESC", (workshop["id"],))]


def list_work_orders(slug):
    workshop = workshop_by_slug(slug)
    with _connect() as db:
        return [_row(x) for x in db.execute("SELECT o.*,r.customer_name,r.phone,r.vehicle_make,r.vehicle_model,r.vehicle_year,r.plate FROM work_orders o JOIN service_requests r ON r.id=o.request_id WHERE o.workshop_id=? ORDER BY o.created_at DESC", (workshop["id"],))]


def convert_request(slug, request_id, actor, payload):
    workshop = workshop_by_slug(slug); timestamp = _now()
    with _connect() as db:
        request = db.execute("SELECT * FROM service_requests WHERE id=? AND workshop_id=?", (request_id, workshop["id"])).fetchone()
        if not request: raise LookupError(request_id)
        existing = db.execute("SELECT * FROM work_orders WHERE request_id=?", (request_id,)).fetchone()
        if existing: return _row(existing)
        order_id, code = str(uuid.uuid4()), _code("OT")
        db.execute("INSERT INTO work_orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (order_id, code, request_id, workshop["id"], payload.get("technician"), None, None, "diagnosis", "CRC", 0, 0, 0, None, timestamp, timestamp, 1))
        db.execute("UPDATE service_requests SET status='converted',updated_at=?,version=version+1 WHERE id=?", (timestamp, request_id))
        _audit(db, workshop["id"], "service_request", request_id, "staff_private", actor["user_id"], "converted", request["status"], "converted", payload.get("advisor_note"))
        _audit(db, workshop["id"], "work_order", order_id, "advisor", actor["user_id"], "created", None, "diagnosis")
        created = _row(db.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone())
    sync_order({"order_code": created["code"], "request_code": request["code"], "status": created["status"], "total": 0, "currency": "CRC", "updated_at": timestamp})
    return created


def save_estimate(slug, order_id, actor, payload):
    workshop = workshop_by_slug(slug); timestamp = _now()
    with _connect() as db:
        order = db.execute("SELECT * FROM work_orders WHERE id=? AND workshop_id=?", (order_id, workshop["id"])).fetchone()
        if not order: raise LookupError(order_id)
        if "awaiting_approval" not in ORDER_TRANSITIONS.get(order["status"], set()): raise ValueError("Invalid status transition")
        subtotal = sum(x["quantity"]*x["unit_price"] for x in payload["lines"]); tax=round(subtotal*payload["tax_rate"],2); total=round(subtotal+tax,2)
        db.execute("DELETE FROM work_order_lines WHERE work_order_id=?", (order_id,))
        for line in payload["lines"]: db.execute("INSERT INTO work_order_lines VALUES(?,?,?,?,?,?,?)", (str(uuid.uuid4()), order_id, line["kind"], line["description"], line.get("sku"), line["quantity"], line["unit_price"]))
        db.execute("UPDATE work_orders SET diagnosis=?,promised_date=?,status='awaiting_approval',currency=?,subtotal=?,tax=?,total=?,updated_at=?,version=version+1 WHERE id=?", (payload["diagnosis"],payload.get("promised_date"),payload["currency"],subtotal,tax,total,timestamp,order_id))
        _audit(db, workshop["id"], "work_order", order_id, "advisor", actor["user_id"], "estimate_created", order["status"], "awaiting_approval", payload["diagnosis"])
    result = get_order(slug, order_id)
    _sync_order_record(slug, result)
    return result


def get_order(slug, order_id):
    workshop=workshop_by_slug(slug)
    with _connect() as db:
        order=_row(db.execute("SELECT * FROM work_orders WHERE id=? AND workshop_id=?",(order_id,workshop["id"])).fetchone())
        if not order: raise LookupError(order_id)
        order["lines"]=[_row(x) for x in db.execute("SELECT kind,description,sku,quantity,unit_price FROM work_order_lines WHERE work_order_id=?",(order_id,))]
        return order


def customer_decide(slug, order_id, token, decision, comment):
    workshop=workshop_by_slug(slug); timestamp=_now()
    with _connect() as db:
        order=db.execute("SELECT o.*,r.tracking_token_hash FROM work_orders o JOIN service_requests r ON r.id=o.request_id WHERE o.id=? AND o.workshop_id=?",(order_id,workshop["id"])).fetchone()
        if not order or not hmac.compare_digest(order["tracking_token_hash"],_token_hash(token)): raise PermissionError()
        target="approved" if decision=="approved" else "rejected"
        if target not in ORDER_TRANSITIONS.get(order["status"],set()): raise ValueError("Invalid status transition")
        db.execute("UPDATE work_orders SET status=?,decision_comment=?,updated_at=?,version=version+1 WHERE id=?",(target,comment,timestamp,order_id))
        _audit(db,workshop["id"],"work_order",order_id,"customer",order["request_id"],"customer_decision",order["status"],target,comment)
    result = get_order(slug,order_id)
    _sync_order_record(slug, result)
    return result


def update_status(slug, order_id, actor, status, note):
    workshop=workshop_by_slug(slug); timestamp=_now()
    with _connect() as db:
        order=db.execute("SELECT * FROM work_orders WHERE id=? AND workshop_id=?",(order_id,workshop["id"])).fetchone()
        if not order: raise LookupError(order_id)
        if status not in ORDER_TRANSITIONS.get(order["status"],set()): raise ValueError("Invalid status transition")
        db.execute("UPDATE work_orders SET status=?,updated_at=?,version=version+1 WHERE id=?",(status,timestamp,order_id))
        _audit(db,workshop["id"],"work_order",order_id,"advisor",actor["user_id"],"status_changed",order["status"],status,note)
    result = get_order(slug,order_id)
    _sync_order_record(slug, result)
    return result


def _sync_order_record(slug, order):
    workshop = workshop_by_slug(slug)
    with _connect() as db:
        request = db.execute("SELECT code FROM service_requests WHERE id=? AND workshop_id=?", (order["request_id"], workshop["id"])).fetchone()
    if request:
        sync_order({"order_code": order["code"], "request_code": request["code"], "status": order["status"], "total": order["total"], "currency": order["currency"], "updated_at": order["updated_at"]})


def audit_history(slug, entity_id):
    workshop=workshop_by_slug(slug)
    with _connect() as db: return [_row(x) for x in db.execute("SELECT * FROM audit_events WHERE workshop_id=? AND entity_id=? ORDER BY id",(workshop["id"],entity_id))]
