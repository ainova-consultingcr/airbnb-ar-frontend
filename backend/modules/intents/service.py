from modules.conversation import normalize_text

def detect_intent(question: str) -> str:
    q = normalize_text(question)

    if any(phrase in q for phrase in [
        "farmacia",
        "farmacias",
        "pharmacy",
        "pharmacies",
        "supermercado",
        "supermercados",
        "supermarket",
        "supermarkets",
        "clinica",
        "clinicas",
        "centro medico",
        "medical center",
        "clinic",
        "clinics",
        "tienda de ropa",
        "tiendas de ropa",
        "ropa",
        "comprar ropa",
        "clothing",
        "clothes",
        "clothing store",
        "clothing stores",
        "servicios y tiendas",
        "services and shops",
        "negocios cercanos",
        "nearby businesses"
    ]):
        return "nearby_businesses"

    if any(word in q for word in [
        "comer",
        "restaurante",
        "restaurantes",
        "cenar",
        "almorzar",
        "food",
        "restaurant",
        "restaurants",
        "where to eat",
        "dining"
    ]):
        return "food"
    if any(phrase in q for phrase in [
        "lugar turistico",
        "lugares turisticos",
        "que visitar",
        "donde ir",
        "atracciones",
        "sitios turisticos",
        "playas",
        "parques nacionales",
        "cataratas",
        "tourist attraction",
        "tourist attractions",
        "places to visit",
        "what to visit",
        "beaches",
        "national parks",
        "waterfalls"
    ]):
        return "tourist_places"
    if any(word in q for word in ["tour", "excursion", "actividad", "paseo"]):
        return "tours"
    if any(word in q for word in ["carro", "auto", "rentar", "rent", "transport"]):
        return "transport"
    if any(word in q for word in ["tienda", "comprar", "shop"]):
        return "nearby_businesses"

    return "general"
