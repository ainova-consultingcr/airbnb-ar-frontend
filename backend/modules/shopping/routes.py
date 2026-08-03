from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from core.http import require_entity_module
from farmasi_auth import authenticate_seller, revoke_seller_token, validate_seller_token
from farmasi_sellers import public_seller, seller_by_id
from .schemas import SellerLogin, ShoppingRequest, ShoppingStatus
from .service import create_order, list_orders, update_order


router = APIRouter()


def require_farmasi_seller(authorization: Optional[str]):
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    session = validate_seller_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Seller authentication required")
    return token, session["seller_id"]


@router.post("/farmasi/order-requests")
def create_farmasi_order_request(payload: ShoppingRequest):
    require_entity_module(payload.property_id, "shopping")
    if payload.property_id != "farmasi" or not payload.items or not seller_by_id(payload.seller_id):
        raise HTTPException(status_code=400, detail="Invalid Farmasi demo order")
    return create_order(payload.dict())


@router.get("/farmasi/sellers/{seller_slug}")
def get_farmasi_seller(seller_slug: str):
    seller = public_seller(seller_slug)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    return seller


@router.post("/farmasi/seller/login")
def farmasi_seller_login(payload: SellerLogin):
    session = authenticate_seller(payload.seller_slug, payload.username, payload.password)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return session


@router.post("/farmasi/seller/logout")
def farmasi_seller_logout(authorization: Optional[str] = Header(default=None)):
    token, _ = require_farmasi_seller(authorization)
    revoke_seller_token(token)
    return {"ok": True}


@router.get("/farmasi/order-requests")
def get_farmasi_order_requests(
    property_id: str,
    seller_id: str,
    authorization: Optional[str] = Header(default=None),
):
    require_entity_module(property_id, "shopping")
    _, authenticated_seller_id = require_farmasi_seller(authorization)
    if authenticated_seller_id != seller_id:
        raise HTTPException(status_code=403, detail="Seller access denied")
    return list_orders(property_id, seller_id)


@router.patch("/farmasi/order-requests/{order_id}")
def patch_farmasi_order_request(
    order_id: str,
    payload: ShoppingStatus,
    authorization: Optional[str] = Header(default=None),
):
    _, authenticated_seller_id = require_farmasi_seller(authorization)
    current = next(
        (row for row in list_orders("farmasi", authenticated_seller_id) if row["id"] == order_id),
        None,
    )
    if not current:
        raise HTTPException(status_code=404, detail="Order not found")
    if payload.status not in {"confirmed", "cancelled", "delivered"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    order = update_order(order_id, payload.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
