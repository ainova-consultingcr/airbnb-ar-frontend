from datetime import datetime, timezone
from threading import Lock
import uuid
from farmasi_sheets import sync_order_to_sheet


_lock = Lock()
_orders = {}


def create_order(payload):
    now = datetime.now(timezone.utc).isoformat()
    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "code": f"AVI-FAR-{uuid.uuid4().hex[:6].upper()}",
        "property_id": payload["property_id"],
        "seller_id": payload["seller_id"],
        "customer_session_id": payload["customer_session_id"],
        "customer_name": payload.get("customer_name") or "Cliente",
        "items": payload["items"],
        "estimated_total": round(sum(item["price"] * item["quantity"] for item in payload["items"]), 2),
        "status": "requested",
        "created_at": now,
        "updated_at": now,
    }
    with _lock:
        _orders[order_id] = order
    sync_order_to_sheet(order, "created")
    return order.copy()


def list_orders(property_id, seller_id):
    with _lock:
        rows = [
            order.copy() for order in _orders.values()
            if order["property_id"] == property_id and order["seller_id"] == seller_id
        ]
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)


def update_order(order_id, status):
    with _lock:
        order = _orders.get(order_id)
        if not order:
            return None
        order["status"] = status
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = order.copy()
    sync_order_to_sheet(updated, "status_updated")
    return updated
