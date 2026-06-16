import json
import os
import re

BASE_DIR = os.path.dirname(__file__)
ENTITIES_DIR = os.path.join(BASE_DIR, "data", "entities")

ENTITY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def get_entity_dir(entity_id: str) -> str:
    if not entity_id or not ENTITY_ID_PATTERN.fullmatch(entity_id):
        raise FileNotFoundError(f"Entidad no existe: {entity_id}")

    entity_path = os.path.join(ENTITIES_DIR, entity_id)
    if not os.path.isdir(entity_path):
        raise FileNotFoundError(f"Entidad no existe: {entity_id}")

    return entity_path

def build_context(entity: dict) -> str:
    #sections = []
    lines = []
# --- Básico ---
    lines.append(f"Place name: {entity.get('name', '')}")
    lines.append(f"Place type: {entity.get('type', '')}")
   #  lines.append(f"Location: {entity.get('location', {}).get('address')}")
   
   
    # --- Location ---
    loc = entity.get("location", {})
    if loc:
        lines.append("Location:")
        for k in ["country", "province", "city", "address"]:
            if loc.get(k):
                lines.append(f"- {k}: {loc.get(k)}")

    # --- Contact ---
    contact = entity.get("contact", {})
    if contact:
        lines.append("Contact:")
        if contact.get("host_name"):
            lines.append(f"- host_name: {contact.get('host_name')}")
        if contact.get("whatsapp"):
            lines.append(f"- whatsapp: {contact.get('whatsapp')}")

    # --- Schedules ---
    schedules = entity.get("schedules", {})
    if schedules:
        lines.append("Schedules:")
        for k, v in schedules.items():
            if v:
                lines.append(f"- {k}: {v}")

    # --- Rules ---
    rules = entity.get("rules", [])
    if rules:
        lines.append("General rules:")
        for r in rules:
            lines.append(f"- {r}")

    # --- Spaces ---
    spaces = entity.get("spaces", [])
    if spaces:
        lines.append("Spaces:")
        for s in spaces:
            name = s.get("name", "Space")
            desc = s.get("description", "")
            lines.append(f"- {name}: {desc}")

            if s.get("rules"):
                lines.append(f"  Rules: {', '.join(s.get('rules'))}")

            avail = s.get("availability", {})
            if avail.get("from") or avail.get("to"):
                lines.append(f"  Availability: {avail.get('from','')} - {avail.get('to','')}")

    # --- Services ---
    services = entity.get("services", [])
    if services:
        lines.append("Services:")
        for srv in services:
            lines.append(f"- {srv.get('name','Service')}")
            if srv.get("how_to_use"):
                lines.append(f"  How to use: {srv.get('how_to_use')}")
            if srv.get("how_to_request"):
                lines.append(f"  How to request: {srv.get('how_to_request')}")
            if srv.get("details"):
                lines.append(f"  Details: {srv.get('details')}")

    catalog = entity.get("catalog", [])
    if catalog:
        lines.append("Catalog:")
        for item in catalog:
            lines.append(f"- {item.get('name', 'Item')} (SKU: {item.get('sku', 'N/A')})")
            if item.get("category"):
                lines.append(f"  Category: {item.get('category')}")
            fitment = item.get("vehicle_fitment", [])
            if fitment:
                fitment_text = []
                for vehicle in fitment:
                    fitment_text.append(
                        f"{vehicle.get('make')} {vehicle.get('model')} "
                        f"{vehicle.get('year_from')}-{vehicle.get('year_to')}"
                    )
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

    diy_guides = entity.get("diy_guides", [])
    if diy_guides:
        lines.append("DIY guides:")
        for guide in diy_guides:
            title = guide.get("title", {})
            lines.append(f"- {title.get('es') or title.get('en') or guide.get('id')}")
            if guide.get("category"):
                lines.append(f"  Category: {guide.get('category')}")
            difficulty = guide.get("difficulty", {})
            if difficulty:
                lines.append(f"  Difficulty: {difficulty.get('es') or difficulty.get('en')}")
            if guide.get("estimated_time"):
                estimated = guide.get("estimated_time", {})
                lines.append(f"  Estimated time: {estimated.get('es') or estimated.get('en')}")
            if guide.get("required_products"):
                lines.append(f"  Required products: {', '.join(guide.get('required_products'))}")
            if guide.get("safety_notes"):
                lines.append(f"  Safety notes: {', '.join(guide.get('safety_notes'))}")

    workshops = entity.get("workshops", [])
    if workshops:
        lines.append("Workshops and talks:")
        for workshop in workshops:
            title = workshop.get("title", {})
            lines.append(f"- {title.get('es') or title.get('en') or workshop.get('id')}")
            if workshop.get("category"):
                lines.append(f"  Category: {workshop.get('category')}")
            if workshop.get("date") or workshop.get("time"):
                lines.append(f"  Date/time: {workshop.get('date', '')} {workshop.get('time', '')}".strip())
            if workshop.get("location"):
                lines.append(f"  Location: {workshop.get('location')}")
            summary = workshop.get("summary", {})
            if summary:
                lines.append(f"  Summary: {summary.get('es') or summary.get('en')}")

    wear_suggestions = entity.get("wear_suggestions", [])
    if wear_suggestions:
        lines.append("Preventive wear suggestions:")
        for group in wear_suggestions:
            label = group.get("label", {})
            lines.append(f"- {label.get('es') or label.get('en') or group.get('condition')}")
            for suggestion in group.get("suggestions", []):
                reason = suggestion.get("reason", {})
                lines.append(
                    f"  {suggestion.get('part')}: {reason.get('es') or reason.get('en')}"
                )

    # --- FAQs ---
    faqs = entity.get("faqs", [])
    if faqs:
        lines.append("FAQs:")
        for f in faqs:
            q = f.get("question", "")
            a = f.get("answer", "")
            if q and a:
                lines.append(f"- Q: {q}")
                lines.append(f"  A: {a}")

    # --- Recommendations ---
    recs = entity.get("recommendations", {})
    if recs:
        lines.append("External recommendations (use only if relevant):")
        for cat, items in recs.items():
            if items:
                lines.append(f"- {cat}: {', '.join(items)}")
   

  #  if "spaces" in entity:
   #     lines.append("\nSpaces:")
  #      for s in entity["spaces"]:
  #          lines.append(
  #              f"- {s['name']}: {s.get('description', '')}. "
  #              f"Rules: {', '.join(s.get('rules', []))}. "
  #              f"Availability: {s.get('availability', {}).get('from', '')} - {s.get('availability', {}).get('to', '')}"
  #          )

   # if "services" in entity:
   #     lines.append("\nServices:")
   #     for srv in entity["services"]:
   #         lines.append(f"- {srv['name']}: {srv.get('details', '') or srv.get('how_to_request', '')}")

    #if "rules" in entity:
    #    lines.append("\nGeneral rules:")
    #    for rule in entity["rules"]:
    
    #        lines.append(f"- {rule}")

    #if "schedules" in entity:
    #    lines.append("\nSchedules:")
    #    for k, v in entity["schedules"].items():
    #        lines.append(f"- {k}: {v}")

    #if "faqs" in entity:
    #    lines.append("\nFAQs:")
    #    for f in entity["faqs"]:
    #        lines.append(f"- Q: {f['question']} A: {f['answer']}")

    #if "recommendations" in entity:
    #    lines.append("\nExternal recommendations:")
    #    for k, items in entity["recommendations"].items():
    #        lines.append(f"- {k}: {', '.join(items)}")

    return "\n".join(lines)

def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def load_property_data(entity_id : str) -> dict:
     entity_path = get_entity_dir(entity_id)
    #with open(f"data/entities/{property_id}.json", "r", encoding="utf-8") as f:
    #  return json.load(f)
    # entity_path = os.path.join(ENTITIES_DIR, entity_id)    
    #path = f"data/entities/{property_id}.json"
    
   # if not os.path.exists(path):
    #   raise FileNotFoundError(
     #       f"No existe el archivo de datos para la entidad: {property_id} -> {path}"
     #  )
     entity = _load_json(os.path.join(entity_path, "entity.json"), {})
     spaces = _load_json(os.path.join(entity_path, "spaces.json"), [])
     services = _load_json(os.path.join(entity_path, "services.json"), [])
     rules = _load_json(os.path.join(entity_path, "rules.json"), [])
     faqs = _load_json(os.path.join(entity_path, "faqs.json"), [])
     schedules = _load_json(os.path.join(entity_path, "schedules.json"), {})
     recommendations = _load_json(os.path.join(entity_path, "recommendations.json"), {})
     catalog = _load_json(os.path.join(entity_path, "catalog.json"), [])
     offers = _load_json(os.path.join(entity_path, "offers.json"), [])
     diy_guides = _load_json(os.path.join(entity_path, "diy_guides.json"), [])
     workshops = _load_json(os.path.join(entity_path, "workshops.json"), [])
     wear_suggestions = _load_json(
         os.path.join(entity_path, "wear_suggestions.json"), []
     )

     entity["spaces"] = spaces
     entity["services"] = services
     entity["rules"] = rules
     entity["faqs"] = faqs
     entity["schedules"] = schedules
     entity["recommendations"] = recommendations
     entity["catalog"] = catalog
     entity["offers"] = offers
     entity["diy_guides"] = diy_guides
     entity["workshops"] = workshops
     entity["wear_suggestions"] = wear_suggestions
    #with open(path, "r", encoding="utf-8") as f:
       #return json.load(f)
     return entity
#def build_context(data):
#    return f"""
#Nombre: {data['name']}
#Reglas: {data['rules']}
#Check-in: {data['checkin']}
#Check-out: {data['checkout']}
#WiFi: {data['wifi']}
#Aire acondicionado: {data['air_conditioning']}
#Contacto: {data['contact']}
#"""
#print(dir())
