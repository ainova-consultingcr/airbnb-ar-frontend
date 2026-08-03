import unicodedata

def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text

def is_short_followup_reply(question: str) -> bool:
    normalized = normalize_text(question).strip()
    affirmative_replies = {
        "si", "si quiero", "ok", "okay", "dale", "claro", "correcto",
        "quiero", "quiero ayuda", "ayuda", "ayudame", "me interesa",
        "si algo mas", "algo mas", "mas", "mas informacion", "otra opcion", "otra cosa",
        "reservar", "reserva", "quiero reservar", "book", "yes",
        "yes please", "more", "more info", "something else", "yeah", "yep", "sure", "help me"
    }
    return normalized in affirmative_replies

def is_negative_followup_reply(question: str) -> bool:
    normalized = normalize_text(question).strip()
    negative_replies = {
        "no", "no gracias", "gracias no", "por ahora no", "ahora no",
        "not", "no thanks", "not now"
    }
    return normalized in negative_replies

def _label_from_context_item(item: dict, lang_key: str) -> str:
    if not item:
        return ""
    name = item.get("name")
    title = item.get("title")
    category = item.get("category")
    if isinstance(name, dict):
        return name.get(lang_key) or name.get("es") or name.get("en") or ""
    if name:
        return name
    if isinstance(title, dict):
        return title.get(lang_key) or title.get("es") or title.get("en") or ""
    if title:
        return title
    if isinstance(category, dict):
        return category.get(lang_key) or category.get("es") or category.get("en") or ""
    return category or item.get("type") or item.get("id") or ""

def _unique_non_empty(items):
    result = []
    seen = set()
    for item in items:
        if not item:
            continue
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(str(item).strip())
    return result

def get_related_alternatives(conversation_context: dict, lang_key: str) -> list[str]:
    context_type = conversation_context.get("type")
    alternatives = []

    if context_type == "auto_parts_search":
        part = conversation_context.get("part", {})
        alternatives.extend(part.get("related_parts", []))
        for offer in conversation_context.get("offers", []):
            alternatives.append(_label_from_context_item(offer, lang_key))

    elif context_type == "hardware_search":
        item = conversation_context.get("item", {})
        alternatives.extend(item.get("related_parts", []))
        for option in conversation_context.get("options", []):
            alternatives.append(_label_from_context_item(option, lang_key))

    elif context_type == "last_action":
        current = _label_from_context_item(conversation_context.get("item", {}), lang_key)
        for option in conversation_context.get("options", []):
            label = _label_from_context_item(option, lang_key)
            if label != current:
                alternatives.append(label)

    return _unique_non_empty(alternatives)[:5]

def handle_negative_followup(question: str, conversation_context: dict, lang_key: str, suggestions: dict):
    if not conversation_context or not is_negative_followup_reply(question):
        return None

    decline_count = int(conversation_context.get("decline_count") or 0)
    if decline_count >= 1:
        return {
            "answer": (
                "Entendido. Quedo atento por si necesitas otra cosa."
                if lang_key == "es"
                else "Understood. I'll stay ready in case you need anything else."
            ),
            "suggestions": suggestions,
            "reset_context": True
        }

    alternatives = get_related_alternatives(conversation_context, lang_key)
    if alternatives:
        alternatives_text = ", ".join(alternatives)
        answer = (
            f"Entendido. Tambien puedo ayudarte con opciones relacionadas como: {alternatives_text}. "
            "Quieres revisar alguna de estas opciones?"
            if lang_key == "es"
            else f"Understood. I can also help with related options such as: {alternatives_text}. "
                 "Would you like to review any of these?"
        )
    else:
        answer = (
            "Entendido. Puedo mostrarte otras opciones relacionadas o esperar una nueva consulta."
            if lang_key == "es"
            else "Understood. I can show related options or wait for a new question."
        )

    return {
        "answer": answer,
        "suggestions": suggestions
    }

def build_conversation_context_text(conversation_context: dict, lang_key: str) -> str:
    if not conversation_context:
        return ""

    context_type = conversation_context.get("type")
    if context_type == "last_action":
        item = conversation_context.get("item", {})
        options = conversation_context.get("options", [])
        item_name = (
            (item.get("name", {}).get(lang_key) if isinstance(item.get("name"), dict) else item.get("name"))
            or (item.get("title", {}).get(lang_key) if isinstance(item.get("title"), dict) else item.get("title"))
            or "not specified"
        )
        lines = [
            "ACTIVE CONVERSATION CONTEXT:",
            "The customer is continuing from the last action or recommendation shown by AVI.",
            f"Action type: {conversation_context.get('action_type') or 'not specified'}",
            f"Topic: {conversation_context.get('topic') or 'not specified'}",
            f"Item: {item_name}",
        ]

        summary = item.get("summary", {})
        if isinstance(summary, dict):
            summary = summary.get(lang_key) or summary.get("es") or summary.get("en") or ""
        if summary:
            lines.append(f"Item summary: {summary}")
        if item.get("price"):
            lines.append(f"Price: {item.get('price')}")
        if item.get("whatsapp"):
            lines.append("A WhatsApp booking/contact option is available.")
        if item.get("map_url"):
            lines.append("A map link is available.")
        if item.get("info_url"):
            lines.append("An information link is available.")
        if options:
            option_names = []
            for option in options[:5]:
                option_names.append(
                    (
                        option.get("name", {}).get(lang_key)
                        if isinstance(option.get("name"), dict)
                        else None
                    )
                    or option.get("name")
                    or (
                        option.get("category", {}).get(lang_key)
                        if isinstance(option.get("category"), dict)
                        else None
                    )
                    or option.get("type")
                    or "option"
                )
            lines.append("Recently shown options: " + ", ".join(option_names))

        lines.append(
            "If the customer's new message is short, affirmative or ambiguous, "
            "interpret it as a continuation of this last AVI action."
        )
        return "\n".join(lines)

    if context_type == "hardware_search":
        item = conversation_context.get("item", {})
        options = conversation_context.get("options", [])
        lines = [
            "ACTIVE CONVERSATION CONTEXT:",
            "The customer is continuing a guided hardware-store sales flow.",
            f"Topic: {conversation_context.get('topic') or 'not specified'}",
            f"Selected product/project: {item.get('name') or item.get('category') or 'not specified'}",
        ]

        if item.get("sku"):
            lines.append(f"SKU: {item.get('sku')}")
        if item.get("category"):
            lines.append(f"Category: {item.get('category')}")
        if item.get("aisle"):
            lines.append(f"Aisle: {item.get('aisle')}")
        if item.get("bay"):
            lines.append(f"Bay/section: {item.get('bay')}")
        if item.get("related_parts"):
            lines.append("Useful add-ons: " + ", ".join(item.get("related_parts")))
        if options:
            option_names = []
            for option in options[:5]:
                title = option.get("title", {})
                option_names.append(
                    option.get("name")
                    or (title.get(lang_key) if isinstance(title, dict) else title)
                    or option.get("id")
                    or "option"
                )
            lines.append("Relevant products/offers/workshops: " + ", ".join(option_names))

        lines.append(
            "If the customer's new message is short, affirmative or ambiguous, "
            "interpret it as a continuation of this selected hardware-store product or project."
        )
        return "\n".join(lines)

    if context_type == "wellness_profile":
        profile = conversation_context.get("profile", {})
        options = conversation_context.get("options", [])
        lines = [
            "ACTIVE CONVERSATION CONTEXT:",
            "The customer is continuing a Farmasi personalized wellness recommendation flow.",
            f"Goal: {profile.get('goal') or 'not specified'}",
            f"Age range: {profile.get('age_range') or 'not specified'}",
            f"Current weight: {profile.get('current_weight') or 'not specified'}",
            f"Target: {profile.get('target') or 'not specified'}",
            f"Activity level: {profile.get('activity_level') or 'not specified'}",
            f"Diet style: {profile.get('diet_style') or 'not specified'}",
            f"Exercise willingness: {profile.get('exercise_willingness') or 'not specified'}",
            f"Budget: {profile.get('budget') or 'not specified'}",
            f"Safety notes: {profile.get('safety_notes') or 'not specified'}",
        ]
        if options:
            option_names = [
                option.get("name") or option.get("sku") or "option"
                for option in options[:5]
            ]
            lines.append("Relevant Farmasi products: " + ", ".join(option_names))
        lines.append(
            "If the customer's new message is short, affirmative or ambiguous, "
            "interpret it as a continuation of this Farmasi profile. Do not diagnose. "
            "Recommend only using official catalog information. Do not show prices or product URLs. "
            "Include simple usage guidance from the catalog when available."
        )
        return "\n".join(lines)

    if context_type != "auto_parts_search":
        return ""

    vehicle = conversation_context.get("vehicle", {})
    part = conversation_context.get("part", {})
    offers = conversation_context.get("offers", [])
    related_parts = part.get("related_parts", [])
    vehicle_label = " ".join(
        str(value)
        for value in [
            vehicle.get("make"),
            vehicle.get("model"),
            vehicle.get("year"),
        ]
        if value
    )

    lines = [
        "ACTIVE CONVERSATION CONTEXT:",
        "The customer is continuing a guided auto-parts sales flow.",
        f"Vehicle: {vehicle_label or 'not specified'}",
        f"Selected part/category: {part.get('name') or part.get('category') or 'not specified'}",
    ]

    if part.get("sku"):
        lines.append(f"SKU: {part.get('sku')}")
    if part.get("category"):
        lines.append(f"Category: {part.get('category')}")
    if related_parts:
        lines.append("Related preventive parts: " + ", ".join(related_parts))
    if offers:
        offer_titles = []
        for offer in offers:
            title = offer.get("title", {})
            offer_titles.append(title.get(lang_key) or title.get("es") or title.get("en") or offer.get("id", "offer"))
        lines.append("Relevant active offers: " + ", ".join(offer_titles))

    lines.append(
        "If the customer's new message is short, affirmative or ambiguous, "
        "interpret it as a continuation of this selected vehicle and part."
    )
    return "\n".join(lines)

def expand_followup_question(question: str, conversation_context: dict, lang_key: str) -> str:
    normalized = normalize_text(question).strip()
    affirmative_replies = {
        "si", "sí", "si quiero", "sí quiero", "ok", "okay", "dale", "claro",
        "correcto", "quiero", "quiero ayuda", "ayuda", "ayudame", "me interesa",
        "si algo mas", "algo mas", "mas", "mas informacion", "otra opcion", "otra cosa",
        "reservar", "reserva", "quiero reservar",
        "yes", "yes please", "more", "more info", "something else", "yeah", "yep", "sure", "help me"
    }

    if normalized not in affirmative_replies:
        return question
    if conversation_context.get("type") == "last_action":
        item = conversation_context.get("item", {})
        topic = conversation_context.get("topic") or conversation_context.get("action_type") or "la opcion anterior"
        item_name = (
            (item.get("name", {}).get(lang_key) if isinstance(item.get("name"), dict) else item.get("name"))
            or (item.get("title", {}).get(lang_key) if isinstance(item.get("title"), dict) else item.get("title"))
            or topic
        )

        if lang_key == "en":
            return (
                f"Yes, I want help with {item_name}. Continue from AVI's previous {topic} "
                "recommendation, explain the next step and available action without starting over."
            )

        return (
            f"Si, quiero ayuda con {item_name}. Continua desde la recomendacion anterior de {topic}, "
            "explica el siguiente paso y la accion disponible sin empezar desde cero."
        )

    if conversation_context.get("type") == "hardware_search":
        item = conversation_context.get("item", {})
        item_name = item.get("name") or conversation_context.get("topic") or "la busqueda de ferreteria"
        aisle = f" en {item.get('aisle')}" if item.get("aisle") else ""

        if lang_key == "en":
            return (
                f"Yes, I want help with {item_name}{aisle}. Continue from the previous hardware-store "
                "recommendation, include aisle guidance, useful add-ons, active offers and workshops if relevant."
            )

        return (
            f"Si, quiero ayuda con {item_name}{aisle}. Continua desde la recomendacion anterior de ferreteria, "
            "incluye guia de pasillo, complementos utiles, ofertas activas y charlas si son relevantes."
        )

    if conversation_context.get("type") != "auto_parts_search":
        return question

    vehicle = conversation_context.get("vehicle", {})
    part = conversation_context.get("part", {})
    vehicle_label = " ".join(
        str(value)
        for value in [
            vehicle.get("make"),
            vehicle.get("model"),
            vehicle.get("year"),
        ]
        if value
    )
    part_label = part.get("name") or part.get("category") or "el repuesto seleccionado"

    if lang_key == "en":
        return (
            f"Yes, I want help with {part_label} for {vehicle_label}. "
            "Continue from the previous recommendation, explain next steps, compatibility checks, "
            "active offers and useful related parts without starting over."
        )

    return (
        f"Sí, quiero ayuda con {part_label} para {vehicle_label}. "
        "Continúa desde la recomendación anterior, explica el siguiente paso, compatibilidad, "
        "ofertas activas y repuestos relacionados útiles sin empezar desde cero."
    )
