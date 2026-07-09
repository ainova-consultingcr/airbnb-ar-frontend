from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
from rag import load_property_data, build_context
from prompts import SYSTEM_PROMPT_TEMPLATE
import urllib.request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import uuid
from service_requests import (
    classify_service_request, confirm_service_request, create_service_request,
    get_service_request, is_accommodation_entity,
)

load_dotenv()
GOOGLE_SHEET_WEBHOOK = os.getenv("GOOGLE_SHEET_WEBHOOK", "https://script.google.com/macros/s/AKfycbzm1z2UQV0j8ySZr4N7LoeQuqAdHyRKNOJgpnIjGj4D3n1Krph198v0O30mACG-Wu3qpA/exec")

app = FastAPI()

class LeadEventRequest(BaseModel):
    property_id: str
    category: str
    item_name: Optional[str] = None
    lead_id: Optional[str] = None
    event_type: str
    metadata: dict = Field(default_factory=dict)

class ServiceRequestConfirmation(BaseModel):
    property_id: str
    guest_session_id: str
    received: bool
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    
def generate_lead_id(prefix="AVI"):
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"

def log_event(property_id, event_type, category, item_name=None, lead_id=None, metadata=None):

    try:
        print("entro a log event")
        payload = json.dumps({
            "type": "event",
            "property": property_id,
            "event_type": event_type,
            "category": category,
            "item_name": item_name,
            "lead_id": lead_id,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).encode("utf-8")

        req = urllib.request.Request(
            GOOGLE_SHEET_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        response = urllib.request.urlopen(req, timeout=3)
        print("EVENT LOG RESPONSE:", response.status)

    except Exception as e:
        print("EVENT LOG ERROR:", str(e))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
         "https://ainova-consultingcr.github.io",
        "http://127.0.0.1:5500",
         "http://localhost:5500"],  # solo desarrollo
    #allow_credentials=False,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.options("/{full_path:path}")
def options_handler(full_path: str):
    return JSONResponse(content={})

@app.get("/property")
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
    
def decorate_answer(text: str):
    icons = {
        "wifi": "📶",
        "restaurante": "",
        "pool": "🏊",
        "checkin": "🕒",
    }

    for key, icon in icons.items():
        text = text.replace(key, f"{icon} {key}")

    return text

def log_question(property_id, language, question, answer, unknown):

    try:

        payload = json.dumps({
            "property": property_id,
            "language": language,
            "question": question,
            "answer": answer,
            "unknown": unknown
        }).encode("utf-8")

        req = urllib.request.Request(
            GOOGLE_SHEET_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        #urllib.request.urlopen(req)
        response = urllib.request.urlopen(req, timeout=3)
        print("LOG RESPONSE:", response.status)

    except Exception as e:
        #print("Error logging question:", e)
        print("LOG ERROR:", str(e))
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


RECOMMENDATIONS = {
    "food": [
        "Restaurante La Oveja – cocina local muy popular",
        "Surf & Turf – mariscos y carnes"
    ],
    "tours": [
        "Tamarindo Adventures – tours de canopy y rafting",
        "Pacific Sun Tours – excursiones de un día"
    ],
    "transport": [
        "Rent a Car Guanacaste – entrega en el alojamiento",
        "Eco Rent – opciones económicas"
    ],
    "shopping": [
        "Souvenir Market Tamarindo – artesanías locales",
        "Playa Shops – ropa y recuerdos"
    ]
}

OPENAI_MODEL = "gpt-4.1-mini"

load_dotenv()
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





class AskRequest(BaseModel):
    property_id: Optional[str] = "demo_property"
    #category: str
    #item_name: Optional[str] = None
    #lead_id: Optional[str] = None
    #event_type: str
    #metadata: Optional[dict] = {}
    question: str
    language: Optional[str] = "es"
    conversation_context: dict = Field(default_factory=dict)
    room_id: Optional[str] = None
    guest_session_id: Optional[str] = None

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

def find_faq(question: str, entity: dict):
   # normalized_question = normalize_text(question)
    #faqs = entity.get("faqs", [])

    #for faq in faqs:
    #    normalized_faq_q = normalize_text(faq.get("question", ""))

    #    if normalized_faq_q in normalized_question:
    #       return faq.get("answer")
    normalized_question = normalize_text(question)

    for faq in entity.get("faqs", []):
        faq_question = normalize_text(faq.get("question", ""))

        # coincidencia simple por inclusión
        if faq_question in normalized_question or normalized_question in faq_question:
            return faq.get("answer")

        # coincidencia por palabras clave
        keywords = [w for w in faq_question.split() if len(w) > 3]

        matches = sum(1 for word in keywords if word in normalized_question)

        if matches >= 2:
            return faq.get("answer")

    return None

@app.post("/ask")
def ask(req: AskRequest):
 lang = (req.language or "es").lower()
 lang_key = "en" if lang.startswith("en") else "es"
 use_conversation_context = (
     req.conversation_context.get("type") in ["auto_parts_search", "hardware_search", "wellness_profile"]
     or is_short_followup_reply(req.question)
 )
 conversation_context_text = (
     build_conversation_context_text(req.conversation_context, lang_key)
     if use_conversation_context
     else ""
 )
 effective_question = expand_followup_question(req.question, req.conversation_context, lang_key)
    #print("ENTITY:", json.dumps(entity, indent=2))
    #print("DEBUG FAQs:", entity.get("faqs"))
 try:
    # 1) Cargar entidad
    entity = load_property_data(req.property_id)
    request_classification = classify_service_request(req.question) if is_accommodation_entity(entity) else None
    if request_classification:
        if not req.room_id or not req.guest_session_id:
            return {
                "answer": ("Please scan the QR in your room before making a service request."
                           if lang_key == "en" else
                           "Escanea el QR de tu habitaci?n para registrar la solicitud correctamente."),
                "requires_room": True,
            }
        try:
            service_request = create_service_request(
                GOOGLE_SHEET_WEBHOOK, property_id=req.property_id, room_id=req.room_id,
                guest_session_id=req.guest_session_id, description=req.question,
                category=request_classification["category"],
                priority=request_classification["priority"],
            )
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"No se pudo registrar la solicitud: {error}")
        answer = (
            f"Request {service_request['id']} registered for room {req.room_id}. "
            "We will notify you when it is delivered."
            if lang_key == "en" else
            f"Listo. Registr? la solicitud {service_request['id']} para la habitaci?n "
            f"{req.room_id}. Te avisar? cuando sea atendida."
        )
        return {"answer": answer, "service_request": service_request}
    services = entity.get("ui", {}).get("services", {})
    restaurants = services.get("restaurants", [])
    suggestions = entity.get("ui", {}).get("suggestions", {})

    negative_followup = handle_negative_followup(
        req.question,
        req.conversation_context,
        lang_key,
        suggestions
    )
    if negative_followup:
        return negative_followup

        # 2) Contexto desde entidad
    context_text = build_context(entity)

        # 3) Prompt universal
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            entity_name=entity.get("name", req.property_id),
            entity_type=entity.get("type", "generic"),
            language=req.language or "es",
           
            context=context_text
        )

        # 4) Recomendaciones dinámicas (opcional)
    intent = detect_intent(req.question)
    
    #services = entity.get("ui", {}).get("services", {})
    #restaurants = services.get("restaurants", [])
    entity_type = entity.get("type", "")
    hotel_like_entity = entity_type in ["hotel", "airbnb", "tourism", "tourism_assistant"]
    if entity_type == "wellness_sales_assistant":
        intent = "general"

    if hotel_like_entity and req.question.lower() == "otros restaurantes":
     external_restaurants = [
        r for r in restaurants
        if not r.get("has_own_restaurant")
     ]

     restaurant_options = [
        {**restaurant, "lead_id": generate_lead_id("AVI-REST")}
        for restaurant in external_restaurants
     ]

     return {
        "answer": MESSAGES["other_restaurants"][lang_key],
        "restaurant_options": restaurant_options
     }    
    if hotel_like_entity and intent == "food":
     if not restaurants:
        return {
            "answer": "No hay restaurantes disponibles en este momento.",
            "suggestions": entity.get("ui", {}).get("suggestions", {})
        }

     restaurant_options = [
        {**restaurant, "lead_id": generate_lead_id("AVI-REST")}
        for restaurant in restaurants
     ]

     return {
         "answer": (
         "These are the restaurants recommended by the hotel:"
            if lang_key == "en"
            else "Estos son los restaurantes recomendados por el hotel:"
         ),
        "restaurant_options": restaurant_options,
        "suggestions": entity.get("ui", {}).get("suggestions", {})
    }
    if hotel_like_entity and intent == "tours":

     services = entity.get("ui", {}).get("services", {})
     tours = services.get("tours", [])

     if not tours:
        return {
            "answer": "No hay tours disponibles en este momento.",
            "suggestions": entity.get("ui", {}).get("suggestions", {})
        }

     options = []

     for t in tours:

        lead_id = generate_lead_id("AVI-TOUR")

        options.append({
            "type": "tour",
            "text": {
                "es": t.get("name", "Tour"),
                "en": t.get("name", "Tour")
            },
            "data": {
                **t,
                "lead_id": lead_id
            }
        })

     return {
        #"answer": "Estas actividades están disponibles:"
        "answer": MESSAGES["tours_available"][lang_key],
        "cta_options": options
     }

    if hotel_like_entity and intent == "tourist_places":
     tourist_places = services.get("tourist_places", [])

     if not tourist_places:
        return {
            "answer": get_no_info_message(entity, lang_key),
            "suggestions": entity.get("ui", {}).get("suggestions", {})
        }

     return {
        "answer": (
            "These are some recommended places to visit in Guanacaste. "
            "Check the official link before traveling because access conditions may change."
            if lang_key == "en"
            else "Estos son algunos lugares recomendados para visitar en Guanacaste. "
                 "Consulta el enlace oficial antes de viajar porque las condiciones de acceso pueden cambiar."
        ),
        "place_options": tourist_places,
        "suggestions": entity.get("ui", {}).get("suggestions", {})
     }

    if hotel_like_entity and intent == "nearby_businesses":
     nearby_businesses = services.get("nearby_businesses", [])
     normalized_question = normalize_text(effective_question)
     type_keywords = {
        "pharmacy": ["farmacia", "farmacias", "pharmacy", "pharmacies"],
        "supermarket": ["supermercado", "supermercados", "supermarket", "supermarkets"],
        "clinic": ["clinica", "clinicas", "centro medico", "medical center", "clinic", "clinics"],
        "clothing": ["tienda de ropa", "tiendas de ropa", "ropa", "comprar ropa", "clothing", "clothes", "clothing store", "clothing stores"]
      }
     requested_types = {
        business_type
        for business_type, keywords in type_keywords.items()
        if any(keyword in normalized_question for keyword in keywords)
     }
     if requested_types:
        nearby_businesses = [
            business
            for business in nearby_businesses
            if business.get("type") in requested_types
        ]

     if not nearby_businesses:
        return {
            "answer": get_no_info_message(entity, lang_key),
            "suggestions": entity.get("ui", {}).get("suggestions", {})
        }

     return {
        "answer": (
            "These nearby service categories may be useful during your stay. "
            "Check the map for current locations and opening hours."
            if lang_key == "en"
            else "Estas categorías de servicios cercanos pueden ser útiles durante tu estadía. "
                 "Consulta el mapa para verificar ubicaciones y horarios actuales."
        ),
        "business_options": nearby_businesses,
        "suggestions": entity.get("ui", {}).get("suggestions", {})
     }
        
        
        #suggestions = RECOMMENDATIONS.get(intent, [])
    suggestions = entity.get("ui", {}).get("suggestions", {})
    recommendation_text = ""
    if suggestions:
            recommendation_text = (
                "\nYou may suggest up to 2 local options from the list below, "
                "only if relevant and naturally:\n"
                + "\n".join(suggestions)
            )
        
    # 1️⃣ Buscar FAQ directo
    faq_answer = find_faq(effective_question, entity)

    if faq_answer:
            return {
         "answer": faq_answer,
         "action": "none",
         "poi": None,
        
         "suggestions": entity.get("ui", {}).get("suggestions", {})
        
        }
        # 🚀 DETECCIÓN DE TRANSPORTE (NUEVO)
    question_lower = effective_question.lower()

    if any(word in question_lower for word in ["transporte", "aeropuerto", "airport", "ride", "taxi"]):
         transport_config = entity.get("ui", {}).get("services", {}).get("transport")
         if not transport_config:
             return {
                 "answer": get_no_info_message(entity, lang_key),
                 "suggestions": entity.get("ui", {}).get("suggestions", {})
             }

         transport_options = transport_config if isinstance(transport_config, list) else [transport_config]
         transport_options = [option for option in transport_options if isinstance(option, dict)]
         if not transport_options:
             return {
                 "answer": get_no_info_message(entity, lang_key),
                 "suggestions": entity.get("ui", {}).get("suggestions", {})
             }

         prices = [option.get("price") for option in transport_options if option.get("price") is not None]
         price_text = f"${min(prices)}" if prices else None
         if lang_key == "en":
             transport_message = "We can help you book transportation to or from the airport."
             if price_text:
                 transport_message += f" Price from: {price_text}."
             transport_message += " Choose one of these options:"
         else:
             transport_message = "Podemos ayudarte a reservar transporte hacia o desde el aeropuerto."
             if price_text:
                 transport_message += f" Precio desde: {price_text}."
             transport_message += " Elige una de estas opciones:"

         cta_options = []
         for option in transport_options:
             option_name = option.get("name") or option.get("title") or (
                 "Airport transportation" if lang_key == "en" else "Transporte aeropuerto"
             )
             option_price = option.get("price")
             price_suffix = f" - ${option_price}" if option_price is not None else ""
             cta_options.append({
                 "type": "transport",
                 "text": {
                     "es": option.get("button_es") or f"{option_name}{price_suffix}",
                     "en": option.get("button_en") or f"{option_name}{price_suffix}"
                 },
                 "data": option
             })

         return {
          "answer": transport_message,
          "cta_options": cta_options
        }

    if False and any(word in question_lower for word in ["transporte", "aeropuerto", "airport", "ride", "taxi"]):

         transport = entity.get("ui", {}).get("services", {}).get("transport")
         if not transport:
             return {
                 "answer": get_no_info_message(entity, lang_key),
                 "suggestions": entity.get("ui", {}).get("suggestions", {})
             }

         price = transport.get("price")
         price_text = f"${price}" if price is not None else None
         if lang_key == "en":
             transport_message = "We can help you book private transportation."
             if price_text:
                 transport_message += f" Price from: {price_text}."
             transport_message += " Would you like to book now?"
         else:
             transport_message = "Podemos ayudarte a reservar transporte privado."
             if price_text:
                 transport_message += f" Precio desde: {price_text}."
             transport_message += " ¿Deseas reservar ahora?"

         return {
         "answer": transport_message,
         "cta_options": [{
             "type": "transport",
             "text": {
                 "es": "Reservar ahora",
                 "en": "Book now"
             },
             "data": transport
         }]
        }

        # 5) Llamada OpenAI
        
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *(
                    [{"role": "system", "content": conversation_context_text}]
                    if conversation_context_text
                    else []
                ),
                # si quieres meter recomendaciones, puedes activar esto:
                # {"role": "system", "content": recommendation_text},
                {"role": "user", "content": effective_question}
            ],
           # temperature=0.3
        )

        # ✅ Respuesta segura (evita null/None)
    answer = None

    if response.choices and response.choices[0].message:
            answer = response.choices[0].message.content
          
    LOW_QUALITY_PATTERNS = [
        "no tengo esa información",
        "no dispongo de esa información",
        "no cuento con esa información",
        "i don't have that information",
        "i do not have that information"
        ]
    answer_text = (answer or "").lower()

    is_generic = any(p in answer_text for p in LOW_QUALITY_PATTERNS)
    if not answer or is_generic:
            answer = get_no_info_message(entity, lang_key)
           
    log_question(req.property_id, req.language, req.question, answer,is_generic)
    print("LOGGING QUESTION:", req.question)
    return {"answer": answer,  
               
              # "suggestions": entity.get("suggestions", {}).get("suggestions", {})
              "suggestions": suggestions
        }
        
    
 except FileNotFoundError:
    raise HTTPException(status_code=404, detail="Property not found")
 except HTTPException:
    raise
 except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.get("/service-requests/{request_id}")
def service_request_status(request_id: str, property_id: str, guest_session_id: str):
    try:
        return get_service_request(
            GOOGLE_SHEET_WEBHOOK, property_id=property_id, request_id=request_id,
            guest_session_id=guest_session_id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar la solicitud: {error}")


@app.post("/service-requests/{request_id}/confirm")
def service_request_confirmation(request_id: str, req: ServiceRequestConfirmation):
    try:
        return confirm_service_request(
            GOOGLE_SHEET_WEBHOOK, property_id=req.property_id, request_id=request_id,
            guest_session_id=req.guest_session_id, received=req.received, rating=req.rating,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"No se pudo actualizar la solicitud: {error}")


@app.post("/track-lead")
def track_lead(req: LeadEventRequest):
    print("TRACK LEAD RECEIVED")
    print(req)
    log_event(
        property_id=req.property_id,
        event_type=req.event_type,
        category=req.category,
        item_name=req.item_name,
        lead_id=req.lead_id,
        metadata=req.metadata
    )

    return {
        "success": True
    }
