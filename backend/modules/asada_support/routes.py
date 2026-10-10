import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException

from core.http import require_entity_module
from .auth import connect, now, require_role
from .monitor import (admin_summary, anomaly_context, answer_question, fetch_monitor,
                      login_monitor, logout_monitor, post_monitor, require_monitor_user)
from .schemas import Login, SupportQuestion
from .schemas import AlertEvent, PushSubscription, WorkOrderClaim, WorkOrderUpdate
from .push import public_config, remove_subscription, save_subscription, send_event


router = APIRouter(prefix="/asadas/{entity_id}/support", tags=["AVI ASADA support"])


def enabled_entity(entity_id):
    return require_entity_module(entity_id, "asada_support")


def authenticated_user(entity_id: str, authorization: str | None):
    entity = enabled_entity(entity_id)
    return entity, require_monitor_user(entity, entity_id, authorization)


@router.get("/status")
def status(entity_id: str, authorization: str | None = Header(default=None)):
    entity = enabled_entity(entity_id)
    try:
        user = require_monitor_user(entity, entity_id, authorization)
    except HTTPException as error:
        if error.status_code not in {401, 403}:
            raise
        user = None
    return {"setup_required": False, "user": user}


@router.post("/login")
def login(entity_id: str, payload: Login):
    entity = enabled_entity(entity_id)
    return login_monitor(entity, entity_id, payload.username, payload.password)


@router.post("/logout", status_code=204)
def logout(entity_id: str, authorization: str | None = Header(default=None)):
    entity = enabled_entity(entity_id)
    logout_monitor(entity, authorization)


@router.get("/push/config")
def push_config(entity_id: str, authorization: str | None = Header(default=None)):
    _, user = authenticated_user(entity_id, authorization)
    require_role(user, "FONTANERO")
    return public_config()


@router.post("/push/subscriptions", status_code=201)
def subscribe_push(entity_id: str, payload: PushSubscription,
                   authorization: str | None = Header(default=None)):
    _, user = authenticated_user(entity_id, authorization)
    require_role(user, "FONTANERO")
    save_subscription(entity_id, user["username"], payload)
    return {"subscribed": True}


@router.delete("/push/subscriptions", status_code=204)
def unsubscribe_push(entity_id: str, payload: PushSubscription,
                     authorization: str | None = Header(default=None)):
    _, user = authenticated_user(entity_id, authorization)
    require_role(user, "FONTANERO")
    remove_subscription(entity_id, user["username"], payload.endpoint)


@router.post("/events", status_code=202)
def receive_event(entity_id: str, payload: AlertEvent,
                  x_event_key: str | None = Header(default=None)):
    entity = enabled_entity(entity_id)
    expected = os.getenv("ASADA_EVENT_SERVICE_KEY", "")
    if not expected or not x_event_key or not hmac.compare_digest(expected, x_event_key):
        raise HTTPException(401, "Credencial de eventos inválida")
    event = payload.model_dump()
    stamp = now().isoformat()
    with connect() as db:
        existing = db.execute("SELECT * FROM avi_alert_events WHERE entity_id=? AND source_order_id=?",
                              (entity_id, payload.source_order_id)).fetchone()
        if existing and existing["status"] == "DELIVERED":
            return {"accepted": True, "duplicate": True,
                    "delivered": existing["delivered_count"]}
        if existing:
            db.execute("UPDATE avi_alert_events SET payload_json=?,status='PROCESSING',updated_at=? WHERE id=?",
                       (json.dumps(event, ensure_ascii=False), stamp, existing["id"]))
        else:
            db.execute("""INSERT INTO avi_alert_events(entity_id,source_order_id,payload_json,status,created_at,updated_at)
                          VALUES(?,?,?,'PROCESSING',?,?)""",
                       (entity_id, payload.source_order_id, json.dumps(event, ensure_ascii=False), stamp, stamp))
    result = send_event(entity["id"], event)
    status = "DELIVERED" if result["delivered"] else "FAILED"
    with connect() as db:
        db.execute("""UPDATE avi_alert_events SET status=?,delivered_count=?,failed_count=?,updated_at=?
                      WHERE entity_id=? AND source_order_id=?""",
                   (status, result["delivered"], result["failed"], now().isoformat(),
                    entity_id, payload.source_order_id))
    if not result["delivered"]:
        raise HTTPException(503, "No hay dispositivos disponibles para recibir la alerta")
    return {"accepted": True, **result}


def monitor_data(entity, user):
    nodes = fetch_monitor(entity, "/api/integrations/avi/nodes")
    orders_payload = fetch_monitor(entity, "/api/integrations/avi/work-orders")
    orders = orders_payload.get("items", orders_payload) if isinstance(orders_payload, dict) else orders_payload
    return nodes, orders


@router.get("/context")
def context(entity_id: str, authorization: str | None = Header(default=None)):
    entity, user = authenticated_user(entity_id, authorization)
    require_role(user, "ADMIN", "OPERADOR", "FONTANERO")
    nodes, orders = monitor_data(entity, user)
    return anomaly_context(nodes, orders, user)


@router.post("/work-orders/{order_id}/claim")
def claim_order(entity_id: str, order_id: int, payload: WorkOrderClaim,
                authorization: str | None = Header(default=None)):
    entity, user = authenticated_user(entity_id, authorization)
    require_role(user, "FONTANERO")
    return post_monitor(entity, f"/api/integrations/avi/work-orders/{order_id}/claim", {
        "username": user["username"],
        "expected_updated_at": payload.expected_updated_at,
        "note": "Orden aceptada por el fontanero desde AVI.",
    })


@router.post("/work-orders/{order_id}/updates")
def update_order(entity_id: str, order_id: int, payload: WorkOrderUpdate,
                 authorization: str | None = Header(default=None)):
    entity, user = authenticated_user(entity_id, authorization)
    require_role(user, "FONTANERO")
    return post_monitor(entity, f"/api/integrations/avi/work-orders/{order_id}/updates", {
        "username": user["username"],
        **payload.model_dump(),
    })


@router.get("/summary")
def summary(entity_id: str, period_days: int = 30, authorization: str | None = Header(default=None)):
    entity, user = authenticated_user(entity_id, authorization)
    require_role(user, "ADMIN", "OPERADOR")
    nodes, orders = monitor_data(entity, user)
    if not 1 <= period_days <= 365:
        raise HTTPException(422, "El período debe estar entre 1 y 365 días")
    return admin_summary(nodes, orders, period_days)


@router.post("/ask")
def ask(entity_id: str, payload: SupportQuestion, authorization: str | None = Header(default=None)):
    entity, user = authenticated_user(entity_id, authorization)
    require_role(user, "ADMIN", "OPERADOR", "FONTANERO")
    nodes, orders = monitor_data(entity, user)
    return answer_question(payload.question, user, nodes, orders, payload.period_days)
