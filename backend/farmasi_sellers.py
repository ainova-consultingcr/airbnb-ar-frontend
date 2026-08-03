import os


SELLERS = {
    "ana": {
        "id": "seller-ana-001",
        "slug": "ana",
        "display_name": "Ana · Asesora Farmasi",
        "whatsapp": "86380783",
        "username": os.getenv("FARMASI_ANA_USER", "ana"),
        "password": os.getenv("FARMASI_ANA_PASSWORD", "AVI-Ana-2026"),
        "sheet_key": "farmasi_ana",
        "active": True,
    },
    "maria": {
        "id": "seller-maria-002",
        "slug": "maria",
        "display_name": "María · Asesora Farmasi",
        "whatsapp": "88880000",
        "username": os.getenv("FARMASI_MARIA_USER", "maria"),
        "password": os.getenv("FARMASI_MARIA_PASSWORD", "AVI-Maria-2026"),
        "sheet_key": "farmasi_maria",
        "active": True,
    },
}


def public_seller(slug):
    seller = SELLERS.get((slug or "").lower())
    if not seller or not seller["active"]:
        return None
    return {
        "id": seller["id"],
        "slug": seller["slug"],
        "display_name": seller["display_name"],
        "whatsapp": seller["whatsapp"],
    }


def seller_by_credentials(slug, username):
    seller = SELLERS.get((slug or "").lower())
    if seller and seller["active"] and seller["username"] == username:
        return seller
    return None


def seller_by_id(seller_id):
    return next((seller for seller in SELLERS.values() if seller["id"] == seller_id), None)
