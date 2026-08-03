from fastapi import APIRouter

from .schemas import LeadEventRequest
from .service import log_event

router = APIRouter()

@router.post("/track-lead")
def track_lead(req: LeadEventRequest):
    print("TRACK LEAD RECEIVED")
    print(req)
    log_event(
        property_id=req.property_id,
        event_type=req.event_type,
        category=req.category,
        item_name=req.item_name,
        lead_id=req.lead_id,
        metadata=req.metadata
    )

    return {
        "success": True
    }
