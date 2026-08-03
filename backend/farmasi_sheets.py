import json
import os
import urllib.request

from farmasi_sellers import seller_by_id


def sync_order_to_sheet(order, event_type):
    webhook = os.getenv("FARMASI_SHEETS_WEBHOOK", "").strip()
    if not webhook:
        return False
    seller = seller_by_id(order["seller_id"])
    if not seller:
        return False
    payload = json.dumps({
        "type": "farmasi_order",
        "event_type": event_type,
        "sheet_key": seller["sheet_key"],
        "seller_id": seller["id"],
        "seller_slug": seller["slug"],
        "order": order,
    }).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return 200 <= response.status < 300
    except Exception as error:
        print("FARMASI SHEET SYNC ERROR:", str(error))
        return False
