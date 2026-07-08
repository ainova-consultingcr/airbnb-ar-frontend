"""Service requests for AVI accommodation entities."""

from __future__ import annotations

import json
import unicodedata
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

ACCOMMODATION_TYPES = {"hotel", "airbnb", "lodging", "hostel", "vacation_rental", "vacation rental"}

CATEGORY_KEYWORDS = {
    "Mantenimiento": ("no funciona", "no sirve", "danado", "fuga", "agua caliente",
                      "aire acondicionado", "televisor", "electricidad", "cerradura",
                      "inodoro", "ducha", "maintenance", "broken", "not working",
                      "leak", "hot water", "air conditioning"),
    "Amenidades": ("toalla", "jabon", "shampoo", "papel higienico", "amenidad",
                   "plancha", "secadora", "almohada", "cobija", "towel", "soap",
                   "toilet paper", "iron", "pillow", "blanket", "amenity"),
    "Ropa de cama": ("sabana", "ropa de cama", "funda", "linen", "bedsheet"),
    "Bebidas": ("agua", "botella", "hielo", "bebida", "water", "bottle", "ice", "drink"),
    "Limpieza": ("limpieza", "limpiar", "aseo", "basura", "housekeeping", "clean", "trash"),
    "Recepción": ("recepcion", "llave", "tarjeta", "equipaje", "front desk", "key", "luggage"),
}

NON_OPERATIONAL_SIGNALS = ("transporte", "taxi", "aeropuerto", "airport", "reservar", "reserva", "book")

REQUEST_SIGNALS = (
    "necesito", "necesitamos", "quiero pedir", "quisiera pedir", "pueden traer",
    "puede traer", "me trae", "envien", "hace falta", "falta", "solicito", "requiero",
    "no funciona", "no sirve", "esta danado", "hay una fuga", "i need", "we need",
    "please bring", "can you bring", "send", "request", "not working", "is broken",
    "there is a leak",
)


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(char for char in text if unicodedata.category(char) != "Mn").strip()


def is_accommodation_entity(entity: dict[str, Any]) -> bool:
    return _normalize(entity.get("type")).replace("-", "_") in ACCOMMODATION_TYPES


def classify_service_request(question: str) -> dict[str, str] | None:
    """Conservatively identify an operational request in Spanish or English."""
    normalized = _normalize(question)
    if any(signal in normalized for signal in NON_OPERATIONAL_SIGNALS):
        return None
    if not normalized or not any(signal in normalized for signal in REQUEST_SIGNALS):
        return None

    category = "Recepción"
    for candidate, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            category = candidate
            break

    urgent_terms = ("humo", "fuego", "gas", "inundacion", "emergencia",
                    "no puedo salir", "smoke", "fire", "gas leak", "flood",
                    "emergency", "locked in")
    priority = "Urgente" if any(term in normalized for term in urgent_terms) else "Normal"
    return {"category": category, "priority": priority}


def sheet_command(webhook_url: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    if not webhook_url:
        raise RuntimeError("GOOGLE_SHEET_WEBHOOK is not configured")
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    result = json.loads(body or "{}")
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or "Google Sheets rejected the request")
    return result


def create_service_request(webhook_url: str, **data: Any) -> dict[str, Any]:
    request_id = f"AVI-SOL-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    result = sheet_command(webhook_url, {
        "type": "service_request", "action": "create", "request_id": request_id,
        "property": data["property_id"], "room_id": data["room_id"],
        "guest_session_id": data["guest_session_id"],
        "description": data["description"].strip(), "category": data["category"],
        "priority": data.get("priority", "Normal"), "status": "Pendiente",
        "timestamp": timestamp,
    })
    return result.get("request") or {
        "id": request_id, "property_id": data["property_id"], "room_id": data["room_id"],
        "description": data["description"].strip(), "category": data["category"],
        "priority": data.get("priority", "Normal"), "status": "Pendiente",
        "created_at": timestamp,
    }


def get_service_request(webhook_url: str, **data: Any) -> dict[str, Any]:
    result = sheet_command(webhook_url, {
        "type": "service_request", "action": "get", "property": data["property_id"],
        "request_id": data["request_id"], "guest_session_id": data["guest_session_id"],
    })
    if not result.get("request"):
        raise LookupError(data["request_id"])
    return result["request"]


def confirm_service_request(webhook_url: str, **data: Any) -> dict[str, Any]:
    result = sheet_command(webhook_url, {
        "type": "service_request", "action": "confirm", "property": data["property_id"],
        "request_id": data["request_id"], "guest_session_id": data["guest_session_id"],
        "received": data["received"], "rating": data.get("rating"),
    })
    if not result.get("request"):
        raise LookupError(data["request_id"])
    return result["request"]

