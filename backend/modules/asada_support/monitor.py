import json
import os
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from fastapi import HTTPException


TIMEOUT_SECONDS = max(5, min(60, int(os.getenv("ASADA_MONITOR_TIMEOUT_SECONDS", "60"))))


def monitor_config(entity: dict):
    config = entity.get("asada_support") or {}
    base_url_env = str(config.get("api_base_url_env") or "")
    base_url = str((os.getenv(base_url_env, "") if base_url_env else "") or config.get("api_base_url") or "").rstrip("/")
    parsed = urlparse(base_url)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    if not base_url or (parsed.scheme != "https" and not local_http) or not parsed.netloc:
        raise HTTPException(503, "La API de datos de la ASADA no está configurada")
    key_name = str(config.get("service_key_env") or "")
    service_key = os.getenv(key_name, "") if key_name else ""
    return base_url, service_key


def fetch_monitor(entity: dict, path: str, query=None):
    base_url, service_key = monitor_config(entity)
    suffix = path if path.startswith("/") else f"/{path}"
    if query:
        suffix += f"?{urlencode(query)}"
    headers = {"Accept": "application/json"}
    if service_key:
        headers["X-Service-Key"] = service_key
    request = Request(f"{base_url}{suffix}", headers=headers)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in {401, 403}:
            raise HTTPException(502, "La integración de datos con ASADA Monitor no está autorizada")
        raise HTTPException(502, "ASADA Monitor rechazó la consulta de datos")
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise HTTPException(502, "ASADA Monitor no está disponible temporalmente")


def anomaly_context(nodes, orders, user):
    anomalies = []
    for node in nodes:
        severity = str(node.get("severity") or node.get("status") or "OFFLINE").upper()
        if severity not in {"NORMAL"}:
            anomalies.append({
                "node_id": node.get("node_id"),
                "sector": node.get("sector_name") or node.get("sector_id") or "Sin sector",
                "pressure_psi": node.get("pressure_psi"),
                "flow_lpm": node.get("flow_lpm"),
                "severity": severity,
                "explanation": _explanation(node, severity),
            })
    visible_orders = orders
    if user["role"] == "FONTANERO":
        visible_orders = [item for item in orders if item.get("assignee") == user["username"]]
    return {"user": user, "anomalies": anomalies, "orders": visible_orders}


def _explanation(node, severity):
    pressure = node.get("pressure_psi")
    flow = node.get("flow_lpm")
    if severity in {"CRITICA", "POSSIBLE_LEAK", "POSIBLE FUGA"}:
        return (f"La presión bajó a {pressure} psi y el caudal subió a {flow} L/min. "
                "Puede existir una fuga; realiza una inspección visual del tramo asociado al nodo.")
    if severity == "OFFLINE":
        return "El nodo no reporta datos recientes. Revisa alimentación, enlace y gateway antes de diagnosticar la red."
    return "Hay una condición fuera del rango esperado. Compara con nodos cercanos y revisa el sector."


def orders_in_period(orders, days):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    selected = []
    for item in orders:
        try:
            created = datetime.fromisoformat(str(item.get("created_at") or "").replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if created >= start:
            selected.append(item)
    return selected, start


def admin_summary(nodes, orders, period_days=30):
    dated_orders = [item for item in orders if item.get("created_at")]
    selected, period_start = orders_in_period(orders, period_days) if dated_orders else (orders, datetime.now(timezone.utc) - timedelta(days=period_days))
    sector_by_node = {item.get("node_id"): item.get("sector_name") or item.get("sector_id") or "Sin sector" for item in nodes}
    sector_counts = Counter(sector_by_node.get(item.get("node_id"), "Sin sector") for item in selected)
    causes = Counter(
        str(item.get("diagnosis") or item.get("cause") or "Pendiente de diagnóstico").strip()
        for item in selected
    )
    return {
        "period_days": period_days,
        "period_start": period_start.isoformat(),
        "total_failures": len(selected),
        "top_sector": sector_counts.most_common(1)[0][0] if sector_counts else None,
        "top_sector_failures": sector_counts.most_common(1)[0][1] if sector_counts else 0,
        "main_cause": causes.most_common(1)[0][0] if causes else None,
        "main_cause_count": causes.most_common(1)[0][1] if causes else 0,
    }


def answer_question(question, user, nodes, orders, period_days=30):
    normalized = "".join(
        character for character in unicodedata.normalize("NFKD", question.casefold())
        if not unicodedata.combining(character)
    )
    if user["role"] == "ADMIN" and any(term in normalized for term in ("sector", "avería", "averia", "causa", "mes")):
        summary = admin_summary(nodes, orders, period_days)
        if not summary["total_failures"]:
            answer = f"No hay averías registradas en los últimos {period_days} días."
        else:
            answer = (f"En los últimos {period_days} días, {summary['top_sector']} fue el sector con más averías "
                      f"({summary['top_sector_failures']}). La causa principal fue {summary['main_cause']} "
                      f"({summary['main_cause_count']} casos).")
        return {"answer": answer, "summary": summary}
    context = anomaly_context(nodes, orders, user)
    if "presion" in normalized:
        measured = [item for item in nodes if item.get("pressure_psi") is not None]
        if measured:
            lowest = min(measured, key=lambda item: item["pressure_psi"])
            sector = lowest.get("sector_name") or lowest.get("sector_id") or "Sin sector"
            answer = ("La presión se interpreta con el límite configurado para cada sector y junto con el caudal. "
                      f"La lectura más baja disponible es {lowest['pressure_psi']} psi en {sector}, nodo {lowest.get('node_id')}.")
        else:
            answer = "La presión se muestra en psi. Debe compararse con el límite del sector y con el caudal; todavía no hay lecturas disponibles."
        return {"answer": answer, "anomalies": context["anomalies"]}
    if "fuga" in normalized:
        possible_leaks = [item for item in context["anomalies"] if item["severity"] in {"CRITICA", "POSSIBLE_LEAK", "POSIBLE FUGA"}]
        answer = ("Una posible fuga es una alerta inicial cuando coinciden presión baja y caudal alto; requiere inspección para confirmarla. "
                  f"En este momento hay {len(possible_leaks)} alerta(s) de posible fuga visible(s) para tu perfil.")
        return {"answer": answer, "anomalies": possible_leaks}
    if "offline" in normalized or "fuera de linea" in normalized or "sin conexion" in normalized:
        offline = [item for item in context["anomalies"] if item["severity"] == "OFFLINE"]
        answer = ("Un nodo aparece offline cuando no reporta dentro del tiempo configurado. "
                  f"Actualmente hay {len(offline)} nodo(s) offline visible(s) para tu perfil; revisa alimentación, enlace y gateway.")
        return {"answer": answer, "anomalies": offline}
    if any(term in normalized for term in ("estado", "red", "monitoreo")):
        normal_count = sum(1 for item in nodes if str(item.get("severity") or item.get("status")).upper() == "NORMAL")
        answer = (f"Estado actual: {len(nodes)} nodo(s), {normal_count} normal(es), "
                  f"{len(context['anomalies'])} con anomalía u offline y {len(context['orders'])} orden(es) visible(s) para tu perfil.")
        return {"answer": answer, "anomalies": context["anomalies"], "orders": context["orders"]}
    if context["anomalies"]:
        first = context["anomalies"][0]
        answer = f"Hay {len(context['anomalies'])} anomalías activas. En {first['sector']}, nodo {first['node_id']}: {first['explanation']}"
    else:
        answer = "No hay anomalías activas en los datos disponibles de la ASADA."
    return {"answer": answer, "anomalies": context["anomalies"], "orders": context["orders"]}
