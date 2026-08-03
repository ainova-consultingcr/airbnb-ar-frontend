"""Public catalog queries."""

from __future__ import annotations

from collections.abc import Mapping

from core.modules import MODULE_REGISTRY


def catalog_for_entity(entity: Mapping) -> list:
    MODULE_REGISTRY.require_enabled(entity, "catalog")
    return list(entity.get("catalog", []))


def build_catalog_context(entity: Mapping) -> list[str]:
    lines = []
    catalog = entity.get("catalog", [])
    hide_commercial_fields = entity.get("type") == "wellness_sales_assistant"
    if catalog:
        lines.append("Catalog:")
        for item in catalog:
            lines.append(f"- {item.get('name', 'Item')} (SKU: {item.get('sku', 'N/A')})")
            if item.get("brand"):
                lines.append(f"  Brand: {item.get('brand')}")
            if item.get("category"):
                lines.append(f"  Category: {item.get('category')}")
            if item.get("price") and not hide_commercial_fields:
                lines.append(f"  Price: {item.get('price')}")
            if item.get("availability"):
                lines.append(f"  Availability: {item.get('availability')}")
            if item.get("official_summary"):
                lines.append(f"  Official summary: {item.get('official_summary')}")
            if item.get("how_to_use"):
                lines.append(f"  How to use: {item.get('how_to_use')}")
            if item.get("goal_tags"):
                lines.append(f"  Goal tags: {', '.join(item.get('goal_tags'))}")
            if item.get("source_url") and not hide_commercial_fields:
                lines.append(f"  Official URL: {item.get('source_url')}")
            fitment = item.get("vehicle_fitment", [])
            if fitment:
                fitment_text = [
                    f"{vehicle.get('make')} {vehicle.get('model')} "
                    f"{vehicle.get('year_from')}-{vehicle.get('year_to')}"
                    for vehicle in fitment
                ]
                lines.append(f"  Compatible vehicles: {', '.join(fitment_text)}")
            if item.get("quality_options"):
                options = [
                    f"{option.get('type')}: {option.get('details')}"
                    for option in item.get("quality_options", [])
                ]
                lines.append(f"  Quality options: {'; '.join(options)}")
            if item.get("notes"):
                lines.append(f"  Notes: {item.get('notes')}")
            if item.get("related_parts"):
                lines.append(f"  Related parts: {', '.join(item.get('related_parts'))}")

    offers = entity.get("offers", [])
    if offers:
        lines.append("Active offers:")
        for offer in offers:
            if offer.get("active") is False:
                continue
            title = offer.get("title", {})
            details = offer.get("details", {})
            lines.append(f"- {title.get('es') or title.get('en') or offer.get('id')}")
            if details:
                lines.append(f"  Details: {details.get('es') or details.get('en')}")
            if offer.get("categories"):
                lines.append(f"  Categories: {', '.join(offer.get('categories'))}")
            if offer.get("valid_until"):
                lines.append(f"  Valid until: {offer.get('valid_until')}")
    return lines
