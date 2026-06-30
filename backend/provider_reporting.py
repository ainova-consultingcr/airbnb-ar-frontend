from __future__ import annotations

import csv, html, json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() == ".json":
        value = json.loads(source.read_text(encoding="utf-8"))
        return value.get("records", []) if isinstance(value, dict) else value
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def build_provider_report(records, property_id=None):
    if property_id:
        records = [row for row in records if prop(row) == property_id]
    events = [row for row in records if row.get("event_type") or row.get("type") == "event"]
    counts, sources, providers, properties = Counter(), Counter(), defaultdict(Counter), defaultdict(Counter)
    sessions = set()
    for row in events:
        kind, data, property_name = event(row), metadata(row), prop(row)
        counts[kind] += 1
        sources[str(data.get("source") or data.get("referrer") or "sin identificar")] += 1
        if data.get("session_id"): sessions.add(str(data["session_id"]))
        properties[property_name][kind] += 1
        if kind in {"provider_impression", "info_click", "whatsapp_click", "reservation_started", "reservation_sent"}:
            providers[str(row.get("item_name") or "Sin nombre")][kind] += 1
    whatsapp_keys = ("whatsapp_click", "reservation_started", "reservation_sent")
    provider_rows = []
    for name, item in providers.items():
        whatsapp = sum(item[key] for key in whatsapp_keys)
        provider_rows.append({"name": name, "impressions": item["provider_impression"], "info": item["info_click"],
                              "whatsapp": whatsapp, "rate": rate(min(item["info_click"] + whatsapp, item["provider_impression"]), item["provider_impression"])})
    provider_rows.sort(key=lambda row: (row["whatsapp"], row["info"], row["impressions"]), reverse=True)
    property_rows = [{"name": name, "views": item["property_view"], "searches": item["search"],
                      "info": item["info_click"], "whatsapp": sum(item[key] for key in whatsapp_keys)}
                     for name, item in properties.items()]
    property_rows.sort(key=lambda row: (row["whatsapp"], row["views"]), reverse=True)
    views, searches, impressions, info = counts["property_view"], counts["search"], counts["provider_impression"], counts["info_click"]
    whatsapp = sum(counts[key] for key in whatsapp_keys)
    return {"generated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
            "property_id": property_id or (prop(records[0]) if records else "AVI"), "visitors": len(sessions),
            "views": views, "searches": searches, "impressions": impressions, "info": info, "whatsapp": whatsapp,
            "search_rate": rate(searches, views), "engagement_rate": rate(min(info + whatsapp, impressions), impressions),
            "whatsapp_rate": rate(whatsapp, impressions), "sources": sources.most_common(8),
            "providers": provider_rows[:20], "properties": property_rows}


def render_provider_report(report):
    cards = "".join(metric(label, report[key], note) for label, key, note in (
        ("Personas alcanzadas", "visitors", "sesiones únicas"), ("Vistas", "views", "aperturas de AVI"),
        ("Búsquedas", "searches", f'{report["search_rate"]}% de vistas'), ("Clics en información", "info", "interés real"),
        ("Clics a WhatsApp", "whatsapp", f'{report["whatsapp_rate"]}% de lo mostrado')))
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Visibilidad AVI</title>
<style>:root{{--ink:#102034;--muted:#65748b;--line:#dfe7ef;--brand:#176b57;--paper:#f5f8f7}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Arial,sans-serif}}main{{max-width:1100px;margin:auto;padding:32px 20px}}header{{padding:32px;border-radius:24px;color:white;background:linear-gradient(125deg,#0d3f38,#23846d)}}h1{{font-size:46px;line-height:1;margin:10px 0}}header p{{color:#dcefe9;max-width:720px}}.grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:18px 0}}.metric,.card{{background:white;border:1px solid var(--line);border-radius:18px;padding:20px}}.metric span,.muted{{color:var(--muted);font-size:13px}}.metric b{{display:block;font-size:29px;margin:7px 0}}.metric small{{color:var(--brand)}}.cols{{display:grid;grid-template-columns:1fr 1.7fr;gap:16px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:11px 8px;text-align:left;border-bottom:1px solid var(--line)}}th{{font-size:11px;color:var(--muted);text-transform:uppercase}}.proof{{margin-top:16px;background:#e5f5ec;border:1px solid #b9dfc9;border-radius:18px;padding:20px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr 1fr}}.cols{{grid-template-columns:1fr}}}}</style></head><body><main>
<header><small>AVI · EVIDENCIA DE VISIBILIDAD</small><h1>Tu negocio sí está siendo visto</h1><p>Resultados atribuibles dentro de AVI para <b>{esc(report["property_id"])}</b>. Cada cifra proviene de una acción real.</p><small>Generado: {esc(report["generated_at"])}</small></header>
<section class="grid">{cards}</section><section class="card"><h2>Rendimiento por proveedor</h2>{provider_table(report["providers"])}</section>
<div class="proof"><b>Lectura comercial:</b> AVI mostró proveedores {report["impressions"]} veces y generó {report["info"] + report["whatsapp"]} acciones de intención. Interacción: <b>{report["engagement_rate"]}%</b>.</div>{property_table(report["properties"])}</main></body></html>'''


def write_provider_report(records, output, property_id=None):
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_provider_report(build_provider_report(records, property_id)), encoding="utf-8")
    return path


def event(row): return str(row.get("event_type") or "").strip().lower()
def prop(row): return str(row.get("property") or row.get("property_id") or "AVI")
def rate(part, total): return round(part * 100 / total, 1) if total else 0.0
def esc(value): return html.escape(str(value))
def metadata(row):
    value = row.get("metadata") or {}
    if isinstance(value, dict): return value
    try: return json.loads(value)
    except (TypeError, ValueError): return {}


def metric(label, value, note): return f'<div class="metric"><span>{esc(label)}</span><b>{esc(value)}</b><small>{esc(note)}</small></div>'
def source_table(rows): return '<p class="muted">Sin datos todavía.</p>' if not rows else '<table><tr><th>Origen</th><th>Interacciones</th></tr>' + ''.join(f'<tr><td>{esc(name)}</td><td>{value}</td></tr>' for name, value in rows) + '</table>'
def provider_table(rows): return '<p class="muted">Las interacciones aparecerán aquí.</p>' if not rows else '<table><tr><th>Proveedor</th><th>Visto</th><th>Info</th><th>WhatsApp</th><th>%</th></tr>' + ''.join(f'<tr><td><b>{esc(row["name"])}</b></td><td>{row["impressions"]}</td><td>{row["info"]}</td><td>{row["whatsapp"]}</td><td>{row["rate"]}%</td></tr>' for row in rows) + '</table>'
def property_table(rows): return "" if len(rows) < 2 else '<section class="card" style="margin-top:16px"><h2>Resultados por hotel o Airbnb</h2><table><tr><th>Alojamiento</th><th>Vistas</th><th>Búsquedas</th><th>Clics</th><th>WhatsApp</th></tr>' + ''.join(f'<tr><td><b>{esc(row["name"])}</b></td><td>{row["views"]}</td><td>{row["searches"]}</td><td>{row["info"]}</td><td>{row["whatsapp"]}</td></tr>' for row in rows) + '</table></section>'
