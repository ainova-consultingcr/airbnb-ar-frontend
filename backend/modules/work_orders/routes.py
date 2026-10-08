from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from .integrations import IntegrationUnavailable, available_slots, integration_configured
from .schemas import AdvisorLogin, CustomerDecision, EstimateCreate, InspectionBooking, ServiceRequestCreate, StatusUpdate, WorkOrderConvert
from .service import authenticate, audit_history, convert_request, create_request, customer_decide, customer_tracking, list_requests, list_work_orders, login, reserve_inspection, save_estimate, update_status, workshop_by_slug


router = APIRouter(prefix="/workshops", tags=["work-orders"])


def _bearer(authorization: Optional[str]):
    return authorization.removeprefix("Bearer ").strip() if authorization else ""


def _staff(slug, authorization, roles):
    session = authenticate(_bearer(authorization), slug)
    if not session or session["role"] not in roles:
        raise HTTPException(status_code=401, detail="Staff authentication required")
    return session


def _advisor(slug, authorization): return _staff(slug, authorization, {"advisor", "manager"})
def _operator(slug, authorization): return _staff(slug, authorization, {"advisor", "mechanic", "manager"})
def _mechanic(slug, authorization): return _staff(slug, authorization, {"mechanic", "manager"})


@router.get("/{slug}")
def public_workshop(slug: str):
    workshop = workshop_by_slug(slug)
    if not workshop: raise HTTPException(status_code=404, detail="Workshop not found")
    return {
        "slug": workshop["slug"],
        "name": workshop["name"],
        "whatsapp": {
            "enabled": bool(workshop.get("whatsapp_number")),
            "number": workshop.get("whatsapp_number"),
            "mode": "click_to_chat",
        },
        "inspections": {"enabled": integration_configured(), "mode": "google_apps_script" if integration_configured() else "manual"},
    }


@router.get("/{slug}/inspection-slots")
def inspection_slots(slug: str, date_from: Optional[str] = None, days: int = Query(default=7, ge=1, le=14)):
    if not workshop_by_slug(slug): raise HTTPException(status_code=404, detail="Workshop not found")
    if not integration_configured():
        return {"available": False, "slots": [], "fallback": "El taller coordinará la inspección manualmente."}
    try: return {"available": True, "slots": available_slots(date_from, days)}
    except IntegrationUnavailable:
        return {"available": False, "slots": [], "fallback": "No pudimos consultar horarios. El taller coordinará la inspección manualmente."}


@router.post("/{slug}/service-requests", status_code=201)
def submit_request(slug: str, payload: ServiceRequestCreate):
    try: return create_request(slug, payload.dict())
    except LookupError: raise HTTPException(status_code=404, detail="Workshop not found")
    except ValueError as error: raise HTTPException(status_code=400, detail=str(error))


@router.get("/{slug}/service-requests/{request_id}/tracking")
def track_request(slug: str, request_id: str, token: str = Query(min_length=20)):
    try: return customer_tracking(slug, request_id, token)
    except LookupError: raise HTTPException(status_code=404, detail="Request not found")
    except PermissionError: raise HTTPException(status_code=403, detail="Invalid tracking token")


@router.post("/{slug}/service-requests/{request_id}/inspection")
def book_request_inspection(slug: str, request_id: str, payload: InspectionBooking, token: str = Query(min_length=20)):
    try: return reserve_inspection(slug, request_id, token, payload.start, payload.end)
    except PermissionError: raise HTTPException(status_code=403, detail="Invalid tracking token")
    except LookupError: raise HTTPException(status_code=404, detail="Request not found")
    except ValueError as error: raise HTTPException(status_code=409, detail=str(error))
    except IntegrationUnavailable: raise HTTPException(status_code=503, detail="No pudimos reservar el horario. El taller lo coordinará manualmente.")


@router.post("/{slug}/advisor/login")
def advisor_login(slug: str, payload: AdvisorLogin):
    session = login(slug, payload.username, payload.password)
    if not session: raise HTTPException(status_code=401, detail="Invalid credentials")
    return session


@router.get("/{slug}/advisor/service-requests")
def advisor_requests(slug: str, authorization: Optional[str] = Header(default=None)):
    _operator(slug, authorization)
    return list_requests(slug)


@router.get("/{slug}/advisor/work-orders")
def advisor_work_orders(slug: str, authorization: Optional[str] = Header(default=None)):
    _operator(slug, authorization)
    return list_work_orders(slug)


@router.post("/{slug}/advisor/service-requests/{request_id}/convert", status_code=201)
def advisor_convert(slug: str, request_id: str, payload: WorkOrderConvert, authorization: Optional[str] = Header(default=None)):
    actor = _advisor(slug, authorization)
    try: return convert_request(slug, request_id, actor, payload.dict())
    except LookupError: raise HTTPException(status_code=404, detail="Request not found")


@router.post("/{slug}/advisor/work-orders/{order_id}/estimate")
def advisor_estimate(slug: str, order_id: str, payload: EstimateCreate, authorization: Optional[str] = Header(default=None)):
    actor = _mechanic(slug, authorization)
    try: return save_estimate(slug, order_id, actor, payload.dict())
    except LookupError: raise HTTPException(status_code=404, detail="Work order not found")
    except ValueError as error: raise HTTPException(status_code=409, detail=str(error))


@router.post("/{slug}/work-orders/{order_id}/decision")
def decide_estimate(slug: str, order_id: str, payload: CustomerDecision, token: str = Query(min_length=20)):
    try: return customer_decide(slug, order_id, token, payload.decision, payload.comment)
    except PermissionError: raise HTTPException(status_code=403, detail="Invalid tracking token")
    except LookupError: raise HTTPException(status_code=404, detail="Work order not found")
    except ValueError as error: raise HTTPException(status_code=409, detail=str(error))


@router.post("/{slug}/advisor/work-orders/{order_id}/status")
def advisor_status(slug: str, order_id: str, payload: StatusUpdate, authorization: Optional[str] = Header(default=None)):
    actor = _advisor(slug, authorization)
    try: return update_status(slug, order_id, actor, payload.status, payload.public_note)
    except LookupError: raise HTTPException(status_code=404, detail="Work order not found")
    except ValueError as error: raise HTTPException(status_code=409, detail=str(error))


@router.get("/{slug}/advisor/audit/{entity_id}")
def advisor_audit(slug: str, entity_id: str, authorization: Optional[str] = Header(default=None)):
    _advisor(slug, authorization)
    return audit_history(slug, entity_id)
