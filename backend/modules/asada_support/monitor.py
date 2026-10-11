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
ROLE_PERMISSIONS = {
    "ADMIN": ["summary", "anomalies", "orders"],
    "OPERADOR": ["summary", "anomalies", "orders"],
    "FONTANERO": ["anomalies", "orders"],
    "LECTOR": [],
}

OUT_OF_SCOPE_ANSWER = (
    "Esta consulta está fuera del ámbito operativo de ASADA. Puedo ayudarte con presión, "
    "caudal, nivel de tanque, nodos, sectores, anomalías, posibles fugas, órdenes de trabajo, "
    "diagnósticos y notificaciones."
)

STATIC_ANSWERS = {
    "greeting": "Hola. Puedo ayudarte a consultar la operación de la ASADA y sus alertas.",
    "flow": ("El caudal se muestra en litros por minuto. Un aumento fuera del rango del sector, "
             "especialmente junto con presión baja, puede indicar una fuga y debe revisarse."),
    "tank": ("El nivel del tanque indica el porcentaje de agua disponible. Debe analizarse junto "
             "con la demanda, el caudal de entrada y las alertas configuradas."),
    "work_order_help": ("Una orden de trabajo registra la atención de una anomalía. El fontanero "
                        "puede tomarla, actualizar el estado, seleccionar el diagnóstico, agregar "
                        "una nota y guardarla como atendida o resuelta."),
    "notifications": ("AVI muestra alertas de ASADA y puede enviar notificaciones push al celular "
                      "del fontanero cuando existe una orden crítica y el dispositivo está suscrito."),
    "access": ("AVI usa la misma cuenta y el mismo rol de ASADA Monitor. Los permisos se aplican "
               "según el perfil administrador, operador, fontanero o lector."),
}


def normalize_question(question: str):
    return "".join(
        character for character in unicodedata.normalize("NFKD", question.casefold())
        if not unicodedata.combining(character)
    )


def classify_question(question: str, user: dict | None = None):
    normalized = normalize_question(question)
    words = set(normalized.replace("¿", " ").replace("?", " ").replace(",", " ").split())
    if words & {"hola", "buenas", "gracias", "hello", "thanks"} and len(words) <= 6:
        return "greeting"
    if any(term in normalized for term in ("notificacion", "notification", "push", "aviso al celular")):
        return "notifications"
    if any(term in normalized for term in ("usuario", "user", "iniciar sesion", "login", "permiso", "permission", "perfil", "rol", "role")):
        return "access"
    if any(term in normalized for term in ("orden de trabajo", "ordenes de trabajo", "work order", "tomar la orden", "atender la orden", "cerrar la orden", "guardar atencion")):
        if any(term in normalized for term in ("cuantas", "pendiente", "asignada", "estado", "actual")):
            return "work_orders"
        return "work_order_help"
    if "diagnostico" in normalized or "nota de atencion" in normalized:
        return "work_order_help"
    if any(term in normalized for term in ("nivel del tanque", "nivel de tanque", "tanque", "tank level")):
        return "tank"
    if "fuga" in normalized or "leak" in normalized:
        return "leak"
    if "caudal" in normalized or "flow" in normalized or "litros por minuto" in normalized or "lpm" in words:
        return "flow"
    if "presion" in normalized or "pressure" in normalized or "psi" in words:
        return "pressure"
    if any(term in normalized for term in ("offline", "fuera de linea", "sin conexion")):
        return "offline"
    if user and user.get("role") in {"ADMIN", "OPERADOR"} and any(
        term in normalized for term in ("mas averias", "causa principal", "este mes", "ultimos dias", "resumen")
    ):
        return "admin_summary"
    if any(term in normalized for term in ("anomalia", "anomaly", "alerta", "alert", "critica", "critical", "lectura", "reading")):
        return "anomalies"
    if any(term in normalized for term in ("estado de la red", "network status", "estado actual", "current status", "monitoreo", "monitoring", "nodo", "node", "sector", "red de agua", "water network")):
        return "network_status"
    return "out_of_scope"


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


def post_monitor(entity: dict, path: str, payload: dict):
    base_url, service_key = monitor_config(entity)
    suffix = path if path.startswith("/") else f"/{path}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if service_key:
        headers["X-Service-Key"] = service_key
    request = Request(f"{base_url}{suffix}", headers=headers,
                      data=json.dumps(payload).encode("utf-8"), method="POST")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("detail")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            detail = None
        if error.code in {401, 403}:
            raise HTTPException(502, "La integración de datos con ASADA Monitor no está autorizada")
        if error.code in {404, 409, 422}:
            raise HTTPException(error.code, detail or "ASADA Monitor rechazó la operación")
        raise HTTPException(502, detail or "ASADA Monitor rechazó la operación")
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise HTTPException(502, "ASADA Monitor no está disponible temporalmente")


def auth_monitor(entity: dict, path: str, method="GET", payload=None, authorization=None):
    base_url, _ = monitor_config(entity)
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if authorization:
        headers["Authorization"] = authorization
    request = Request(f"{base_url}{path}", headers=headers, data=data, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else None
    except HTTPError as error:
        try:
            detail = json.loads(error.read().decode("utf-8")).get("detail")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            detail = None
        if error.code in {401, 403}:
            raise HTTPException(error.code, detail or "Usuario o contraseña de ASADA incorrectos")
        raise HTTPException(502, detail or "ASADA Monitor rechazó la autenticación")
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise HTTPException(502, "ASADA Monitor no está disponible temporalmente")


def avi_user(remote_user: dict, entity_id: str):
    role = str(remote_user.get("role") or "").upper()
    if role not in ROLE_PERMISSIONS or not remote_user.get("active", True):
        raise HTTPException(403, "La cuenta de ASADA no tiene acceso activo")
    return {
        "id": remote_user.get("id"),
        "entity_id": entity_id,
        "username": remote_user.get("username"),
        "full_name": remote_user.get("full_name"),
        "role": role,
        "active": True,
        "permissions": ROLE_PERMISSIONS[role],
    }


def login_monitor(entity: dict, entity_id: str, username: str, password: str):
    result = auth_monitor(entity, "/api/auth/login", method="POST", payload={
        "username": username, "password": password,
    })
    return {**avi_user(result, entity_id), "access_token": result["access_token"],
            "token_type": "bearer"}


def require_monitor_user(entity: dict, entity_id: str, authorization: str | None):
    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Inicia sesión con tu cuenta de ASADA para continuar")
    remote = auth_monitor(entity, "/api/auth/me", authorization=f"Bearer {token}")
    return avi_user(remote, entity_id)


def logout_monitor(entity: dict, authorization: str | None):
    if authorization:
        auth_monitor(entity, "/api/auth/logout", method="POST", authorization=authorization)


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
                "timestamp": node.get("timestamp"),
                "explanation": _explanation(node, severity),
            })
    anomalies.sort(key=lambda item: _timestamp_sort_key(item.get("timestamp")), reverse=True)
    visible_orders = orders
    if user["role"] == "FONTANERO":
        visible_orders = [item for item in orders if not item.get("assignee")
                          or str(item.get("assignee")).lower() == user["username"].lower()]
    visible_orders = sorted(
        visible_orders,
        key=lambda item: _timestamp_sort_key(item.get("created_at") or item.get("updated_at")),
        reverse=True,
    )
    return {"user": user, "anomalies": anomalies, "orders": visible_orders}


def _timestamp_sort_key(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return float("-inf")


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
    intent = classify_question(question, user)
    if intent == "out_of_scope":
        return {"answer": OUT_OF_SCOPE_ANSWER, "scope": "out_of_scope", "ai_used": False}
    if intent in STATIC_ANSWERS:
        return {"answer": STATIC_ANSWERS[intent], "scope": "asada", "ai_used": False}
    if intent == "admin_summary":
        summary = admin_summary(nodes, orders, period_days)
        if not summary["total_failures"]:
            answer = f"No hay averías registradas en los últimos {period_days} días."
        else:
            answer = (f"En los últimos {period_days} días, {summary['top_sector']} fue el sector con más averías "
                      f"({summary['top_sector_failures']}). La causa principal fue {summary['main_cause']} "
                      f"({summary['main_cause_count']} casos).")
        return {"answer": answer, "summary": summary, "scope": "asada", "ai_used": False}
    context = anomaly_context(nodes, orders, user)
    if intent == "pressure":
        measured = [item for item in nodes if item.get("pressure_psi") is not None]
        if measured:
            lowest = min(measured, key=lambda item: item["pressure_psi"])
            sector = lowest.get("sector_name") or lowest.get("sector_id") or "Sin sector"
            answer = ("La presión se interpreta con el límite configurado para cada sector y junto con el caudal. "
                      f"La lectura más baja disponible es {lowest['pressure_psi']} psi en {sector}, nodo {lowest.get('node_id')}.")
        else:
            answer = "La presión se muestra en psi. Debe compararse con el límite del sector y con el caudal; todavía no hay lecturas disponibles."
        return {"answer": answer, "anomalies": context["anomalies"], "scope": "asada", "ai_used": False}
    if intent == "leak":
        possible_leaks = [item for item in context["anomalies"] if item["severity"] in {"CRITICA", "POSSIBLE_LEAK", "POSIBLE FUGA"}]
        answer = ("Una posible fuga es una alerta inicial cuando coinciden presión baja y caudal alto; requiere inspección para confirmarla. "
                  f"En este momento hay {len(possible_leaks)} alerta(s) de posible fuga visible(s) para tu perfil.")
        return {"answer": answer, "anomalies": possible_leaks, "scope": "asada", "ai_used": False}
    if intent == "offline":
        offline = [item for item in context["anomalies"] if item["severity"] == "OFFLINE"]
        answer = ("Un nodo aparece offline cuando no reporta dentro del tiempo configurado. "
                  f"Actualmente hay {len(offline)} nodo(s) offline visible(s) para tu perfil; revisa alimentación, enlace y gateway.")
        return {"answer": answer, "anomalies": offline, "scope": "asada", "ai_used": False}
    if intent == "work_orders":
        return {"answer": f"Tienes {len(context['orders'])} orden(es) de trabajo visible(s) para tu perfil.",
                "orders": context["orders"], "scope": "asada", "ai_used": False}
    if intent == "network_status":
        normal_count = sum(1 for item in nodes if str(item.get("severity") or item.get("status")).upper() == "NORMAL")
        answer = (f"Estado actual: {len(nodes)} nodo(s), {normal_count} normal(es), "
                  f"{len(context['anomalies'])} con anomalía u offline y {len(context['orders'])} orden(es) visible(s) para tu perfil.")
        return {"answer": answer, "anomalies": context["anomalies"], "orders": context["orders"],
                "scope": "asada", "ai_used": False}
    if context["anomalies"]:
        first = context["anomalies"][0]
        answer = f"Hay {len(context['anomalies'])} anomalías activas. En {first['sector']}, nodo {first['node_id']}: {first['explanation']}"
    else:
        answer = "No hay anomalías activas en los datos disponibles de la ASADA."
    return {"answer": answer, "anomalies": context["anomalies"], "orders": context["orders"],
            "scope": "asada", "ai_used": False}
