from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
