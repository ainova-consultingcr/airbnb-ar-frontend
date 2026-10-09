from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


Role = Literal["ADMIN", "OPERADOR", "FONTANERO"]


class Login(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserCreate(Login):
    full_name: str = Field(min_length=2, max_length=120)
    role: Role


class Setup(UserCreate):
    role: Role = "ADMIN"


class SupportQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=500)
    period_days: int = Field(default=30, ge=1, le=365)


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=20, max_length=512)
    auth: str = Field(min_length=8, max_length=256)


class PushSubscription(BaseModel):
    endpoint: str = Field(min_length=20, max_length=4096)
    keys: PushKeys

    @field_validator("endpoint")
    @classmethod
    def secure_push_endpoint(cls, value: str):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("El endpoint push debe usar HTTPS")
        return value


class AlertEvent(BaseModel):
    source_order_id: int = Field(gt=0)
    node_id: str = Field(min_length=1, max_length=128)
    sector: str = Field(default="Sin sector", max_length=160)
    severity: str = Field(default="CRITICA", max_length=40)
    pressure_psi: float
    flow_lpm: float
    timestamp: str = Field(min_length=10, max_length=80)
    message: str = Field(min_length=3, max_length=1000)
