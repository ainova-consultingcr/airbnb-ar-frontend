from __future__ import annotations

from collections.abc import Callable, Mapping


def handle_transport_information(
    *,
    entity: Mapping,
    effective_question: str,
    lang_key: str,
    no_info_message: Callable[[Mapping, str], str],
) -> dict | None:
    question_lower = effective_question.lower()
    signals = ["transporte", "aeropuerto", "airport", "ride", "taxi"]
    if not any(word in question_lower for word in signals):
        return None

    transport_config = entity.get("ui", {}).get("services", {}).get("transport")
    if not transport_config:
        return {
            "answer": no_info_message(entity, lang_key),
            "suggestions": entity.get("ui", {}).get("suggestions", {}),
        }

    options = transport_config if isinstance(transport_config, list) else [transport_config]
    options = [option for option in options if isinstance(option, dict)]
    if not options:
        return {
            "answer": no_info_message(entity, lang_key),
            "suggestions": entity.get("ui", {}).get("suggestions", {}),
        }

    prices = [option.get("price") for option in options if option.get("price") is not None]
    price_text = f"${min(prices)}" if prices else None
    if lang_key == "en":
        message = "We can help you book transportation to or from the airport."
        if price_text:
            message += f" Price from: {price_text}."
        message += " Choose one of these options:"
    else:
        message = "Podemos ayudarte a reservar transporte hacia o desde el aeropuerto."
        if price_text:
            message += f" Precio desde: {price_text}."
        message += " Elige una de estas opciones:"

    cta_options = []
    for option in options:
        option_name = option.get("name") or option.get("title") or (
            "Airport transportation" if lang_key == "en" else "Transporte aeropuerto"
        )
        option_price = option.get("price")
        price_suffix = f" - ${option_price}" if option_price is not None else ""
        cta_options.append({
            "type": "transport",
            "text": {
                "es": option.get("button_es") or f"{option_name}{price_suffix}",
                "en": option.get("button_en") or f"{option_name}{price_suffix}",
            },
            "data": option,
        })

    return {"answer": message, "cta_options": cta_options}


def handle_hospitality_information(
    *,
    entity: Mapping,
    question: str,
    effective_question: str,
    lang_key: str,
    intent: str,
    messages: Mapping,
    lead_id_factory: Callable[[str], str],
    normalize: Callable[[str], str],
    no_info_message: Callable[[Mapping, str], str],
) -> dict | None:
    entity_type = entity.get("type", "")
    if entity_type not in {"hotel", "airbnb", "tourism", "tourism_assistant"}:
        return None

    services = entity.get("ui", {}).get("services", {})
    suggestions = entity.get("ui", {}).get("suggestions", {})
    restaurants = services.get("restaurants", [])

    if question.lower() == "otros restaurantes":
        options = [
            {**restaurant, "lead_id": lead_id_factory("AVI-REST")}
            for restaurant in restaurants
            if not restaurant.get("has_own_restaurant")
        ]
        return {
            "answer": messages["other_restaurants"][lang_key],
            "restaurant_options": options,
        }

    if intent == "food":
        if not restaurants:
            return {
                "answer": "No hay restaurantes disponibles en este momento.",
                "suggestions": suggestions,
            }
        options = [
            {**restaurant, "lead_id": lead_id_factory("AVI-REST")}
            for restaurant in restaurants
        ]
        return {
            "answer": (
                "These are the restaurants recommended by the hotel:"
                if lang_key == "en"
                else "Estos son los restaurantes recomendados por el hotel:"
            ),
            "restaurant_options": options,
            "suggestions": suggestions,
        }

    if intent == "tours":
        tours = services.get("tours", [])
        if not tours:
            return {
                "answer": "No hay tours disponibles en este momento.",
                "suggestions": suggestions,
            }
        options = [
            {
                "type": "tour",
                "text": {"es": tour.get("name", "Tour"), "en": tour.get("name", "Tour")},
                "data": {**tour, "lead_id": lead_id_factory("AVI-TOUR")},
            }
            for tour in tours
        ]
        return {
            "answer": messages["tours_available"][lang_key],
            "cta_options": options,
        }

    if intent == "tourist_places":
        places = services.get("tourist_places", [])
        if not places:
            return {"answer": no_info_message(entity, lang_key), "suggestions": suggestions}
        return {
            "answer": (
                "These are some recommended places to visit in Guanacaste. "
                "Check the official link before traveling because access conditions may change."
                if lang_key == "en"
                else "Estos son algunos lugares recomendados para visitar en Guanacaste. "
                     "Consulta el enlace oficial antes de viajar porque las condiciones de acceso pueden cambiar."
            ),
            "place_options": places,
            "suggestions": suggestions,
        }

    if intent == "nearby_businesses":
        businesses = services.get("nearby_businesses", [])
        normalized_question = normalize(effective_question)
        type_keywords = {
            "pharmacy": ["farmacia", "farmacias", "pharmacy", "pharmacies"],
            "supermarket": ["supermercado", "supermercados", "supermarket", "supermarkets"],
            "clinic": ["clinica", "clinicas", "centro medico", "medical center", "clinic", "clinics"],
            "clothing": [
                "tienda de ropa", "tiendas de ropa", "ropa", "comprar ropa",
                "clothing", "clothes", "clothing store", "clothing stores",
            ],
        }
        requested_types = {
            business_type
            for business_type, keywords in type_keywords.items()
            if any(keyword in normalized_question for keyword in keywords)
        }
        if requested_types:
            businesses = [
                business for business in businesses
                if business.get("type") in requested_types
            ]
        if not businesses:
            return {
                "answer": no_info_message(entity, lang_key),
                "suggestions": suggestions,
            }

        return {
            "answer": (
                "These nearby service categories may be useful during your stay. "
                "Check the map for current locations and opening hours."
                if lang_key == "en"
                else "Estas categorías de servicios cercanos pueden ser útiles durante tu estadía. "
                     "Consulta el mapa para verificar ubicaciones y horarios actuales."
            ),
            "business_options": businesses,
            "suggestions": suggestions,
        }

    return None
