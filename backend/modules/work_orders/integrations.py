"""Optional Google Apps Script bridge for the workshop pilot."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class IntegrationUnavailable(RuntimeError):
    pass


def integration_configured() -> bool:
    return bool(os.getenv("AVI_WORKSHOP_APPS_SCRIPT_URL", "").strip() and os.getenv("AVI_WORKSHOP_INTEGRATION_SECRET", "").strip())


def command(action: str, data: dict | None = None, timeout: int = 8) -> dict:
    url = os.getenv("AVI_WORKSHOP_APPS_SCRIPT_URL", "").strip()
    secret = os.getenv("AVI_WORKSHOP_INTEGRATION_SECRET", "").strip()
    if not url or not secret:
        raise IntegrationUnavailable("Workshop integration is not configured")
    payload = json.dumps({"secret": secret, "action": action, "data": data or {}}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8") or "{}")
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise IntegrationUnavailable("Workshop integration did not respond") from error
    if not result.get("ok"):
        raise IntegrationUnavailable(result.get("error") or "Workshop integration rejected the request")
    return result


def available_slots(date_from: str | None = None, days: int = 7) -> list[dict]:
    return command("availability", {"date_from": date_from, "days": max(1, min(days, 14))}).get("slots", [])


def book_inspection(payload: dict) -> dict:
    return command("book_inspection", payload).get("inspection") or {}


def sync_inspection(payload: dict) -> bool:
    try:
        command("sync_inspection", payload)
        return True
    except IntegrationUnavailable:
        return False


def sync_order(payload: dict) -> bool:
    try:
        command("sync_order", payload)
        return True
    except IntegrationUnavailable:
        return False
