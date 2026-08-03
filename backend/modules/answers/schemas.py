from typing import Optional

from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    property_id: Optional[str] = "demo_property"
    question: str
    language: Optional[str] = "es"
    conversation_context: dict = Field(default_factory=dict)
    room_id: Optional[str] = None
    guest_session_id: Optional[str] = None
