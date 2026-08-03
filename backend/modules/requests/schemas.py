from typing import Optional

from pydantic import BaseModel, Field


class ServiceRequestConfirmation(BaseModel):
    property_id: str
    guest_session_id: str
    received: bool
    rating: Optional[int] = Field(default=None, ge=1, le=5)
