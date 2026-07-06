from __future__ import annotations

import csv
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)

    if source.suffix.lower() == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("records", [])
        if not isinstance(data, list):
            raise ValueError("JSON report input must be a list or {'records': [...]}.")
        return [dict(item) for item in data if isinstance(item, dict)]

    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as file:
            return [dict(row) for row in csv.DictReader(file)]

    raise ValueError("Supported report input formats: .csv and .json")


def demo_records() -> list[dict[str, Any]]:
    return [
        {
            "property": "hotel_demo",
            "language": "es",
            "question": "¿Cuál es la clave del WiFi?",
            "answer": "La red WiFi es HotelTuHotel.",
            "unknown": False,
        },
        {
            "property": "hotel_demo",
            "language": "en",
            "question": "Which restaurants do you recommend?",
            "answer": "These are the restaurants recommended by the hotel.",
            "unknown": False,
        },
        {
            "property": "hotel_demo",
            "language": "es",
            "question": "¿Qué lugares turísticos puedo visitar?",
            "answer": "Estos son algunos lugares recomendados para visitar en Guanacaste.",
            "unknown": False,
        },
        {
            "property": "hotel_demo",
            "language": "es",
            "question": "¿Hay gimnasio?",
            "answer": "No tengo esa información, por favor consulta con recepción.",
            "unknown": True,
        },
        {
            "type": "event",
            "property": "hotel_demo",
            "event_type": "reservation_started",
            "category": "restaurant",
            "item_name": "La Oveja",
            "lead_id": "AVI-REST-001",
        },
        {
            "type": "event",
            "property": "hotel_demo",
            "event_type": "reservation_started",
            "category": "transport",
            "item_name": "Private transport",
            "lead_id": "AVI-TR-001",
        },
    ]


def build_report(records: list[dict[str, Any]], property_id: str | None = None) -> dict[str, Any]:
    if property_id:
        records = [
            record
            for record in records
            if _pick(record, "property", "property_id") == property_id
        ]

    questions = [record for record in records if record.get("question")]
    events = [record for record in records if record.get("type") == "event" or record.get("event_type")]
    service_requests = [record for record in records if record.get("type") == "service_request" or record.get("request_id")]
    unknown_questions = [record for record in questions if _truthy(record.get("unknown"))]

    total_questions = len(questions)
    unknown_count = len(unknown_questions)
    answered_count = max(total_questions - unknown_count, 0)
    answer_rate = round((answered_count / total_questions) * 100) if total_questions else 0

    lead_events = [
        event
        for event in events
        if event.get("lead_id") or "reservation" in str(event.get("event_type", "")).lower()
    ]

    question_counter = Counter(_clean(record.get("question")) for record in questions)
    language_counter = Counter(_clean(record.get("language") or "sin idioma") for record in questions)
    category_counter = Counter(_clean(event.get("category") or "sin categoría") for event in events)
    request_statuses = Counter(_clean(item.get("status") or "Pendiente") for item in service_requests)
    request_categories = Counter(_clean(item.get("category") or "Sin categoría") for item in service_requests)
    delivered_requests = [item for item in service_requests if _clean(item.get("status")) in {"Entregada", "Confirmada"}]
    confirmed_requests = [item for item in service_requests if _clean(item.get("guest_confirmation")) == "Confirmada"]
    ratings = [float(item["rating"]) for item in service_requests if str(item.get("rating") or "").replace(".", "", 1).isdigit()]

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "property_id": property_id or _infer_property(records),
        "total_questions": total_questions,
        "answered_count": answered_count,
        "unknown_count": unknown_count,
        "answer_rate": answer_rate,
        "total_events": len(events),
        "lead_count": len(lead_events),
        "request_total": len(service_requests),
        "request_pending": request_statuses.get("Pendiente", 0),
        "request_in_progress": request_statuses.get("En proceso", 0),
        "request_delivered": len(delivered_requests),
        "request_confirmed_rate": round(len(confirmed_requests) / len(delivered_requests) * 100) if delivered_requests else 0,
        "request_average_rating": round(sum(ratings) / len(ratings), 1) if ratings else "—",
        "request_categories": request_categories.most_common(8),
        "top_questions": question_counter.most_common(8),
        "languages": language_counter.most_common(),
        "event_categories": category_counter.most_common(),
        "unknown_questions": [_clean(record.get("question")) for record in unknown_questions[:8]],
        "recommendations": _recommendations(
            total_questions=total_questions,
            unknown_count=unknown_count,
            lead_count=len(lead_events),
            event_categories=category_counter,
        ),
    }


def render_html_report(report: dict[str, Any]) -> str:
    title = f"Reporte AVI - {_escape(report.get('property_id') or 'Propiedad')}"
    generated_at = _escape(report["generated_at"])

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #07111f;
      --panel: #0f1b2d;
      --panel-soft: #132238;
      --text: #f8fafc;
      --muted: #a8b3c7;
      --accent: #86c45c;
      --accent-2: #5cc8ff;
      --danger: #f97373;
      --border: rgba(255,255,255,.11);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(134,196,92,.26), transparent 28rem),
        radial-gradient(circle at bottom right, rgba(92,200,255,.15), transparent 28rem),
        var(--bg);
    }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 36px 22px 56px; }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr .8fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }}
    .card {{
      border: 1px solid var(--border);
      border-radius: 26px;
      background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025));
      box-shadow: 0 20px 60px rgba(0,0,0,.24);
      backdrop-filter: blur(18px);
    }}
    .intro {{ padding: 28px; }}
    .eyebrow {{ color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }}
    h1 {{ margin: 10px 0 10px; font-size: clamp(32px, 5vw, 56px); line-height: .96; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .date {{ display: inline-flex; margin-top: 14px; padding: 9px 13px; border-radius: 999px; color: #dbeafe; background: rgba(92,200,255,.12); }}
    .score {{ display: grid; place-items: center; padding: 28px; text-align: center; }}
    .score strong {{ font-size: 70px; line-height: 1; color: var(--accent); }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0; }}
    .metric {{ padding: 18px; border-radius: 22px; background: var(--panel); border: 1px solid var(--border); }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 30px; }}
    .section-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }}
    section {{ padding: 22px; }}
    h2 {{ margin: 0 0 14px; font-size: 19px; }}
    ol, ul {{ margin: 0; padding-left: 20px; }}
    li {{ margin: 10px 0; color: #dbe4f0; }}
    .bar-row {{ display: grid; grid-template-columns: 110px 1fr 38px; gap: 10px; align-items: center; margin: 11px 0; color: #dbe4f0; }}
    .bar {{ height: 10px; overflow: hidden; border-radius: 999px; background: rgba(255,255,255,.08); }}
    .bar > i {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }}
    .empty {{ color: var(--muted); font-style: italic; }}
    .danger li::marker {{ color: var(--danger); }}
    .actions li::marker {{ color: var(--accent); }}
    footer {{ margin-top: 22px; color: var(--muted); font-size: 12px; text-align: center; }}
    @media (max-width: 820px) {{
      .hero, .section-grid, .grid {{ grid-template-columns: 1fr; }}
    }}
    @media print {{
      body {{ background: #fff; color: #172033; }}
      main {{ padding: 18px; }}
      .card, .metric {{ box-shadow: none; background: #fff; border-color: #d7dce5; }}
      p, li, .empty, .metric span, footer {{ color: #4b5563; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="hero">
      <div class="intro card">
        <div class="eyebrow">AVI Intelligence Report</div>
        <h1>Reporte ejecutivo del asistente</h1>
        <p>Una lectura rápida del comportamiento de los huéspedes: qué preguntan, dónde AVI resuelve bien y qué oportunidades comerciales se están generando.</p>
        <div class="date">Generado: {generated_at}</div>
      </div>
      <div class="score card">
        <span class="eyebrow">Tasa de respuesta</span>
        <strong>{report["answer_rate"]}%</strong>
        <p>{_escape(report["answered_count"])} de {_escape(report["total_questions"])} consultas fueron respondidas sin marcarse como información faltante.</p>
      </div>
    </div>

    <div class="grid">
      {_metric("Consultas", report["total_questions"])}
      {_metric("Sin información", report["unknown_count"])}
      {_metric("Eventos", report["total_events"])}
      {_metric("Leads", report["lead_count"])}
    </div>

    <div class="section-grid">
      <section class="card">
        <h2>Preguntas más frecuentes</h2>
        {_ordered_list(report["top_questions"])}
      </section>
      <section class="card">
        <h2>Idiomas usados</h2>
        {_bars(report["languages"])}
      </section>
      <section class="card">
        <h2>Oportunidades por categoría</h2>
        {_bars(report["event_categories"])}
      </section>
      <section class="card">
        <h2>Información faltante</h2>
        {_unordered_list(report["unknown_questions"], css_class="danger")}
      </section>
    </div>

    <section class="card" style="margin-top:16px">
      <h2>Recomendaciones accionables</h2>
      {_unordered_list(report["recommendations"], css_class="actions")}
    </section>
    <footer>AVI convierte conversaciones de huéspedes en información operativa para mejorar servicio, ventas y contenido.</footer>
  </main>
</body>
</html>"""


def write_html_report(
    records: list[dict[str, Any]],
    output_path: str | Path,
    property_id: str | None = None,
) -> Path:
    report = build_report(records, property_id=property_id)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html_report(report), encoding="utf-8")
    return output


def _recommendations(
    total_questions: int,
    unknown_count: int,
    lead_count: int,
    event_categories: Counter[str],
) -> list[str]:
    recommendations = []
    if unknown_count:
        recommendations.append(
            "Agregar o mejorar respuestas para las preguntas sin información; son el contenido que más rápido mejora la experiencia del huésped."
        )
    if lead_count:
        recommendations.append(
            "Dar seguimiento diario a los leads generados por AVI, especialmente reservas de restaurantes, transporte y tours."
        )
    if event_categories:
        top_category = event_categories.most_common(1)[0][0]
        recommendations.append(
            f"Revisar la categoría con más interacción: {top_category}. Puede indicar una oportunidad comercial o una necesidad frecuente."
        )
    if total_questions == 0:
        recommendations.append(
            "Aún no hay suficientes consultas para analizar; mantener el QR visible y explicar brevemente a los huéspedes para qué sirve AVI."
        )
    recommendations.append(
        "Revisar este reporte semanalmente durante el piloto para ajustar contenido, servicios recomendados y alianzas locales."
    )
    return recommendations


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>'


def _ordered_list(items: list[tuple[str, int]]) -> str:
    if not items:
        return '<p class="empty">Sin datos todavía.</p>'
    return "<ol>" + "".join(
        f"<li>{_escape(text)} <strong>({count})</strong></li>" for text, count in items
    ) + "</ol>"


def _unordered_list(items: list[str], css_class: str = "") -> str:
    if not items:
        return '<p class="empty">Sin datos todavía.</p>'
    class_attr = f' class="{css_class}"' if css_class else ""
    return f"<ul{class_attr}>" + "".join(f"<li>{_escape(item)}</li>" for item in items) + "</ul>"


def _bars(items: list[tuple[str, int]]) -> str:
    if not items:
        return '<p class="empty">Sin datos todavía.</p>'

    max_count = max(count for _, count in items) or 1
    rows = []
    for label, count in items:
        width = round((count / max_count) * 100)
        rows.append(
            f'<div class="bar-row"><span>{_escape(label)}</span>'
            f'<div class="bar"><i style="width:{width}%"></i></div>'
            f'<strong>{count}</strong></div>'
        )
    return "".join(rows)


def _pick(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if record.get(key):
            return record[key]
    return None


def _infer_property(records: list[dict[str, Any]]) -> str:
    for record in records:
        value = _pick(record, "property", "property_id")
        if value:
            return str(value)
    return "AVI"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _escape(value: Any) -> str:
    return html.escape(str(value))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "si", "sí"}
