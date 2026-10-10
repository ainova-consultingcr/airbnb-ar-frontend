import json
import os

from pywebpush import WebPushException, webpush
from py_vapid import VapidException

from .auth import connect, now


def config():
    return {
        "public_key": os.getenv("AVI_PUSH_VAPID_PUBLIC_KEY", "").strip(),
        "private_key": os.getenv("AVI_PUSH_VAPID_PRIVATE_KEY", "").strip(),
        "subject": os.getenv("AVI_PUSH_VAPID_SUBJECT", "mailto:admin@example.com").strip(),
    }


def public_config():
    current = config()
    return {"enabled": bool(current["public_key"] and current["private_key"]
                            and current["subject"].startswith("mailto:")),
            "public_key": current["public_key"]}


def save_subscription(user_id: int, subscription):
    stamp = now().isoformat()
    with connect() as db:
        db.execute("""INSERT INTO avi_push_subscriptions(user_id,endpoint,p256dh,auth,created_at,updated_at)
                      VALUES(?,?,?,?,?,?)
                      ON CONFLICT(endpoint) DO UPDATE SET user_id=excluded.user_id,
                      p256dh=excluded.p256dh,auth=excluded.auth,updated_at=excluded.updated_at""",
                   (user_id, subscription.endpoint, subscription.keys.p256dh,
                    subscription.keys.auth, stamp, stamp))


def remove_subscription(user_id: int, endpoint: str):
    with connect() as db:
        db.execute("DELETE FROM avi_push_subscriptions WHERE user_id=? AND endpoint=?",
                   (user_id, endpoint))


def send_event(entity_id: str, event: dict):
    current = config()
    if not current["public_key"] or not current["private_key"]:
        return {"delivered": 0, "failed": 0, "configured": False}
    with connect() as db:
        subscriptions = db.execute("""SELECT s.* FROM avi_push_subscriptions s
          JOIN avi_users u ON u.id=s.user_id
          WHERE u.entity_id=? AND u.role='FONTANERO' AND u.active=1""", (entity_id,)).fetchall()
    payload = json.dumps({
        "title": f"AVI · {event.get('sector') or event['node_id']}",
        "body": event["message"],
        "tag": f"avi-order-{entity_id}-{event['source_order_id']}",
        "url": f"./?property={entity_id}&order={event['source_order_id']}",
        "event": event,
    }, ensure_ascii=False)
    delivered = failed = 0
    expired = []
    for row in subscriptions:
        try:
            webpush(
                subscription_info={"endpoint": row["endpoint"],
                                   "keys": {"p256dh": row["p256dh"], "auth": row["auth"]}},
                data=payload,
                vapid_private_key=current["private_key"],
                vapid_claims={"sub": current["subject"]},
                ttl=300,
                timeout=10,
            )
            delivered += 1
        except (WebPushException, VapidException, ValueError) as error:
            failed += 1
            status = getattr(getattr(error, "response", None), "status_code", None)
            if status in {404, 410}:
                expired.append(row["endpoint"])
    if expired:
        with connect() as db:
            db.executemany("DELETE FROM avi_push_subscriptions WHERE endpoint=?",
                           [(endpoint,) for endpoint in expired])
    return {"delivered": delivered, "failed": failed, "configured": True,
            "subscriptions": len(subscriptions)}
