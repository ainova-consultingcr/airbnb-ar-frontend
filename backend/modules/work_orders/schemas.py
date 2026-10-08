from typing import Literal, Optional

from pydantic import BaseModel, Field


class ServiceRequestCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    consent_to_contact: bool
    vehicle_make: str = Field(min_length=2, max_length=60)
    vehicle_model: str = Field(min_length=1, max_length=60)
    vehicle_year: int = Field(ge=1950, le=2100)
    plate: Optional[str] = Field(default=None, max_length=20)
    vin: Optional[str] = Field(default=None, max_length=40)
    mileage: Optional[int] = Field(default=None, ge=0, le=5_000_000)
    problem: str = Field(min_length=5, max_length=2000)
    preferred_date: Optional[str] = Field(default=None, max_length=40)


class AdvisorLogin(BaseModel):
    username: str
    password: str


class WorkOrderConvert(BaseModel):
    advisor_note: Optional[str] = Field(default=None, max_length=1000)
    technician: Optional[str] = Field(default=None, max_length=120)


class EstimateLine(BaseModel):
    kind: Literal["labor", "part"]
    description: str = Field(min_length=2, max_length=300)
    sku: Optional[str] = Field(default=None, max_length=80)
    quantity: float = Field(gt=0, le=999)
    unit_price: float = Field(ge=0, le=100_000_000)


class EstimateCreate(BaseModel):
    diagnosis: str = Field(min_length=5, max_length=3000)
    currency: str = Field(default="CRC", pattern="^[A-Z]{3}$")
    tax_rate: float = Field(default=0.13, ge=0, le=1)
    promised_date: Optional[str] = Field(default=None, max_length=40)
    lines: list[EstimateLine] = Field(min_length=1, max_length=100)


class CustomerDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    comment: Optional[str] = Field(default=None, max_length=1000)


class InspectionBooking(BaseModel):
    start: str = Field(min_length=16, max_length=40)
    end: str = Field(min_length=16, max_length=40)


class StatusUpdate(BaseModel):
    status: Literal["diagnosis", "in_progress", "quality_check", "ready", "delivered", "cancelled"]
    public_note: Optional[str] = Field(default=None, max_length=1000)
