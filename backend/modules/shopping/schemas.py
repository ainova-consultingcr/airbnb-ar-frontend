from typing import Optional

from pydantic import BaseModel, Field


class ShoppingItem(BaseModel):
    sku: str
    name: str
    price: float = Field(ge=0)
    quantity: int = Field(ge=1, le=99)


class ShoppingRequest(BaseModel):
    property_id: str
    seller_id: str
    customer_session_id: str
    customer_name: Optional[str] = None
    items: list[ShoppingItem]


class ShoppingStatus(BaseModel):
    status: str


class SellerLogin(BaseModel):
    seller_slug: str
    username: str
    password: str
