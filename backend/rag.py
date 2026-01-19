import json
import os
def build_context(entity: dict) -> str:
    #sections = []
    lines = []

    lines.append(f"Place name: {entity.get('name')}")
    lines.append(f"Place type: {entity.get('entity_type')}")
    lines.append(f"Location: {entity.get('location', {}).get('address')}")

    if "spaces" in entity:
        lines.append("\nSpaces:")
        for s in entity["spaces"]:
            lines.append(
                f"- {s['name']}: {s.get('description', '')}. "
                f"Rules: {', '.join(s.get('rules', []))}. "
                f"Availability: {s.get('availability', {}).get('from', '')} - {s.get('availability', {}).get('to', '')}"
            )

    if "services" in entity:
        lines.append("\nServices:")
        for srv in entity["services"]:
            lines.append(f"- {srv['name']}: {srv.get('details', '') or srv.get('how_to_request', '')}")

    if "rules" in entity:
        lines.append("\nGeneral rules:")
        for rule in entity["rules"]:
            lines.append(f"- {rule}")

    if "schedules" in entity:
        lines.append("\nSchedules:")
        for k, v in entity["schedules"].items():
            lines.append(f"- {k}: {v}")

    if "faqs" in entity:
        lines.append("\nFAQs:")
        for f in entity["faqs"]:
            lines.append(f"- Q: {f['question']} A: {f['answer']}")

    if "recommendations" in entity:
        lines.append("\nExternal recommendations:")
        for k, items in entity["recommendations"].items():
            lines.append(f"- {k}: {', '.join(items)}")

    return "\n".join(lines)


def load_property_data(property_id : str):
    #with open(f"data/entities/{property_id}.json", "r", encoding="utf-8") as f:
    #  return json.load(f)
    path = f"data/entities/{property_id}.json"
    if not os.path.exists(path):
       raise FileNotFoundError(
            f"No existe el archivo de datos para la entidad: {property_id} -> {path}"
       )

    with open(path, "r", encoding="utf-8") as f:
       return json.load(f)

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
