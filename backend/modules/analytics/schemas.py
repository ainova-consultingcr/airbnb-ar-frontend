from typing import Optional

from pydantic import BaseModel, Field

class LeadEventRequest(BaseModel):
    property_id: str
    category: str
    item_name: Optional[str] = None
    lead_id: Optional[str] = None
    event_type: str
    metadata: dict = Field(default_factory=dict)
