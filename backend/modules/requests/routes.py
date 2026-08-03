from fastapi import APIRouter, HTTPException

from core.config import GOOGLE_SHEET_WEBHOOK
from core.http import require_entity_module
from .schemas import ServiceRequestConfirmation
from .service import confirm_service_request, get_service_request


router = APIRouter()


@router.get("/service-requests/{request_id}")
def service_request_status(request_id: str, property_id: str, guest_session_id: str):
    require_entity_module(property_id, "requests")
    try:
        return get_service_request(
            GOOGLE_SHEET_WEBHOOK,
            property_id=property_id,
            request_id=request_id,
            guest_session_id=guest_session_id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar la solicitud: {error}")


@router.post("/service-requests/{request_id}/confirm")
def service_request_confirmation(request_id: str, req: ServiceRequestConfirmation):
    require_entity_module(req.property_id, "requests")
    try:
        return confirm_service_request(
            GOOGLE_SHEET_WEBHOOK,
            property_id=req.property_id,
            request_id=request_id,
            guest_session_id=req.guest_session_id,
            received=req.received,
            rating=req.rating,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar la solicitud: {error}")
