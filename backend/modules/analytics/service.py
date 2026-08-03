import json
import urllib.request
from datetime import datetime, timezone

from core.config import GOOGLE_SHEET_WEBHOOK

def log_event(property_id, event_type, category, item_name=None, lead_id=None, metadata=None):

    try:
        print("entro a log event")
        payload = json.dumps({
            "type": "event",
            "property": property_id,
            "event_type": event_type,
            "category": category,
            "item_name": item_name,
            "lead_id": lead_id,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).encode("utf-8")

        req = urllib.request.Request(
            GOOGLE_SHEET_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        response = urllib.request.urlopen(req, timeout=3)
        print("EVENT LOG RESPONSE:", response.status)

    except Exception as e:
        print("EVENT LOG ERROR:", str(e))

def log_question(property_id, language, question, answer, unknown):

    try:

        payload = json.dumps({
            "property": property_id,
            "language": language,
            "question": question,
            "answer": answer,
            "unknown": unknown
        }).encode("utf-8")

        req = urllib.request.Request(
            GOOGLE_SHEET_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        #urllib.request.urlopen(req)
        response = urllib.request.urlopen(req, timeout=3)
        print("LOG RESPONSE:", response.status)

    except Exception as e:
        #print("Error logging question:", e)
        print("LOG ERROR:", str(e))
