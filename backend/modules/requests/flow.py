from __future__ import annotations

from typing import Any

from core.modules import MODULE_REGISTRY
from .service import classify_service_request, create_service_request, is_accommodation_entity


class ServiceRequestCreationError(RuntimeError):
    pass


def handle_service_request(
    *,
    entity: dict[str, Any],
    property_id: str,
    question: str,
    room_id: str | None,
    guest_session_id: str | None,
    lang_key: str,
    webhook_url: str,
) -> dict[str, Any] | None:
    if not is_accommodation_entity(entity):
        return None
    if not MODULE_REGISTRY.is_enabled(entity, "requests"):
        return None
    classification = classify_service_request(question)
    if not classification:
        return None
    if not room_id or not guest_session_id:
        return {
            "answer": (
                "Please scan the QR in your room before making a service request."
                if lang_key == "en"
                else "Escanea el QR de tu habitaci?n para registrar la solicitud correctamente."
            ),
            "requires_room": True,
        }
    try:
        service_request = create_service_request(
            webhook_url,
            property_id=property_id,
            room_id=room_id,
            guest_session_id=guest_session_id,
            description=question,
            category=classification["category"],
            priority=classification["priority"],
        )
    except Exception as error:
        raise ServiceRequestCreationError(str(error)) from error
    answer = (
        f"Request {service_request['id']} registered for room {room_id}. "
        "We will notify you when it is delivered."
        if lang_key == "en"
        else f"Listo. Registr? la solicitud {service_request['id']} para la habitaci?n "
             f"{room_id}. Te avisar? cuando sea atendida."
    )
    return {"answer": answer, "service_request": service_request}
