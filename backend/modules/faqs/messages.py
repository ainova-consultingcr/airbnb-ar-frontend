MESSAGES = {
    "restaurants_available": {
        "es": " Puedes reservar en estos restaurantes:",
        "en": " You can book at these restaurants:"
    },

    "other_restaurants": {
        "es": " Estos son otros restaurantes cercanos:",
        "en": " These are other nearby restaurants:"
    },

    "own_restaurant": {
        "es": "Te recomendamos primero nuestro restaurante {name}. ¿Deseas reservar o prefieres ver otras opciones cercanas?",
        "en": "We recommend our restaurant {name} first. Would you like to book a table or see other nearby options?"
    },

    "tours_available": {
        "es": "Estas actividades están disponibles:",
        "en": "These activities are available:"
    },

    "no_restaurants": {
        "es": "No hay restaurantes disponibles en este momento.",
        "en": "There are no restaurants available at the moment."
    },

    "no_tours": {
        "es": "No hay tours disponobles en este momento.",
        "en": "No tours are available at the moment."
    }
}

NO_INFO_MESSAGES = {
    "es": "No tengo esa información, por favor consulta con el encargado de recepción.",
    "en": "I don't have that information. Please contact the host."
}

ENTITY_NO_INFO_MESSAGES = {
    "wellness_sales_assistant": {
        "es": (
            "No tengo esa informacion en el catalogo Farmasi. "
            "Puedo ayudarte con productos disponibles, forma de uso general "
            "o conectar tu consulta con un asesor Farmasi."
        ),
        "en": (
            "I don't have that information in the Farmasi catalog. "
            "I can help with available products, general usage guidance, "
            "or connect your question with a Farmasi advisor."
        )
    }
}


def get_no_info_message(entity: dict, lang_key: str) -> str:
    entity_type = entity.get("type", "")
    entity_messages = ENTITY_NO_INFO_MESSAGES.get(entity_type, {})
    return entity_messages.get(lang_key) or NO_INFO_MESSAGES.get(lang_key, NO_INFO_MESSAGES["es"])
