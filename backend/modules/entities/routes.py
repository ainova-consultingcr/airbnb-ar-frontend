import json

from fastapi import APIRouter, HTTPException

from modules.requests import is_accommodation_entity
from rag import load_property_data

router = APIRouter()

@router.get("/property")
def get_property(property_id: str = "hotel_demo"):
    try:
        data = load_property_data(property_id)

        response = {
            "id": data["id"],
            "name": data["name"],
            "type": data.get("type"),
            "color": data["branding"]["primary_color"],
            "welcome": data["branding"]["welcome"],
            "suggestions": data.get("ui", {}).get(
                "suggestions", data.get("suggestions", {})
            ),
            "messages": data.get("messages", {}),
            "theme": data.get("theme", {}),
            "ui": data.get("ui", {}),
            #"services": data.get("services", {}),
            "contact": data.get("contact", {})
        }

        if is_accommodation_entity(data):
            response["service_requests"] = {
                "enabled": data.get("service_requests", {}).get("enabled", True),
                "room_label": data.get("service_requests", {}).get("room_label", "Habitaci?n"),
                "poll_seconds": 15,
            }

        if data.get("type") == "auto_parts_store":
            services = data.get("ui", {}).get("services", {})
            response["auto_parts"] = {
                "sales_flow": services.get("sales_flow", {}),
                "supported_vehicles": services.get("supported_vehicles", []),
                "catalog": data.get("catalog", []),
                "offers": data.get("offers", []),
                "wear_suggestions": data.get("wear_suggestions", [])
            }

        if data.get("type") == "hardware_store":
            services = data.get("ui", {}).get("services", {})
            response["hardware"] = {
                "sales_flow": services.get("sales_flow", {}),
                "store_sections": services.get("store_sections", []),
                "catalog": data.get("catalog", []),
                "offers": data.get("offers", []),
                "diy_guides": data.get("diy_guides", []),
                "workshops": data.get("workshops", [])
            }

        if data.get("type") == "wellness_sales_assistant":
            services = data.get("ui", {}).get("services", {})
            response["wellness"] = {
                "recommendation_flow": services.get("recommendation_flow", {}),
                "catalog": data.get("catalog", []),
                "recommendations": data.get("recommendations", {})
            }

        return response

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Property not found")
    except (OSError, json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=str(e))
