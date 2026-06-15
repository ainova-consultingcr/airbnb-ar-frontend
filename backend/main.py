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

GOOGLE_SHEET_WEBHOOK = "https://script.google.com/macros/s/AKfycbzm1z2UQV0j8ySZr4N7LoeQuqAdHyRKNOJgpnIjGj4D3n1Krph198v0O30mACG-Wu3qpA/exec"

app = FastAPI()

class LeadEventRequest(BaseModel):
    property_id: str
    category: str
    item_name: Optional[str] = None
    lead_id: Optional[str] = None
    event_type: str
    metadata: dict = Field(default_factory=dict)
    
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

        return {
            "id": data["id"],
            "name": data["name"],
            "color": data["branding"]["primary_color"],
            "welcome": data["branding"]["welcome"],
            "suggestions": data.get("suggestions", {}),
            "messages": data.get("messages", {}),
            "theme": data.get("theme", {}),
            "ui": data.get("ui", {}),
            #"services": data.get("services", {}),
            "contact": data.get("contact", {})
        }

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
    q = question.lower()

    if any(word in q for word in ["comer", "restaurante", "cenar", "almorzar", "food"]):
        return "food"
    if any(word in q for word in ["tour", "excursion", "actividad", "paseo"]):
        return "tours"
    if any(word in q for word in ["carro", "auto", "rentar", "rent", "transport"]):
        return "transport"
    if any(word in q for word in ["tienda", "comprar", "shop"]):
        return "shopping"

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

NO_INFO_MESSAGES = {
    "es": "No tengo esa información, por favor consulta con el encargado de recepción.",
    "en": "I don't have that information. Please contact the host."
}


import unicodedata

def normalize_text(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text

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
    #print("ENTITY:", json.dumps(entity, indent=2))
    #print("DEBUG FAQs:", entity.get("faqs"))
 try:
    # 1) Cargar entidad
    entity = load_property_data(req.property_id)
    services = entity.get("ui", {}).get("services", {})
    restaurants = services.get("restaurants", [])

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
    if req.question.lower() == "otros restaurantes":
     external_restaurants = [
        r for r in restaurants
        if not r.get("has_own_restaurant")
     ]

     options = []

     for r in external_restaurants:

        lead_id = generate_lead_id("AVI-REST")

        options.append({
            "type": "restaurant",
            "text": {
                "es": r.get("name"),
                "en": r.get("name")
            },
            "data": {
                **r,
                "lead_id": lead_id
            }
        })

     return {
        #"answer": "Estos son otros restaurantes cercanos:"
        "answer": MESSAGES["other_restaurants"][lang_key],
        "cta_options": options
     }    
    if intent == "food":
     #own_restaurant = entity.get("restaurant", {})
    # services = entity.get("ui", {}).get("services", {})
     #restaurants = services.get("restaurants", [])
     own_restaurant = next(
    (r for r in restaurants if r.get("has_own_restaurant")),
    None
    )
     #if own_restaurant.get("has_own_restaurant"):
     if own_restaurant:
       return {
           # "answer": f"Te recomendamos primero nuestro restaurante {own_restaurant['name']}. ¿Deseas reservar o prefieres ver otras opciones cercanas?",
            "answer": MESSAGES["own_restaurant"][lang_key].format(
             name=own_restaurant["name"]),
            "cta_options": [
                {
                    "type": "own_restaurant",
                    "text": {
                        "es": "Reservar restaurante",
                        "en": "Book restaurant"
                    },
                    "data": own_restaurant
                },
                {
                    "type": "external_restaurants",
                    "text": {
                        "es": "Ver otros restaurantes",
                        "en": "See other restaurants"
                    }
                }
            ]
        }

        
     if not restaurants:
        return {
            "answer": "No hay restaurantes disponibles en este momento.",
            "suggestions": entity.get("ui", {}).get("suggestions", {})
        }

     options = []

     for r in restaurants:

        lead_id = generate_lead_id("AVI-REST")

        options.append({
            "type": "restaurant",
            "text": {
                "es": r.get("name", "Restaurante"),
                "en": r.get("name", "Restaurant")
            },
            "data": {
                **r,
                "lead_id": lead_id
            }
        })

     return {
         "answer": (
         "You can book at these restaurants:"
            if lang_key == "en"
            else "Puedes reservar en estos restaurantes:"
         ),
        "cta_options": options
    }
    if intent == "tours":

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
    faq_answer = find_faq(req.question, entity)

    if faq_answer:
            return {
         "answer": faq_answer,
         "action": "none",
         "poi": None,
        
         "suggestions": entity.get("ui", {}).get("suggestions", {})
        
        }
        # 🚀 DETECCIÓN DE TRANSPORTE (NUEVO)
    question_lower = req.question.lower()

    if any(word in question_lower for word in ["transporte", "aeropuerto", "airport", "ride", "taxi"]):

         transport = entity.get("ui", {}).get("services", {}).get("transport")
         if not transport:
             return {
                 "answer": NO_INFO_MESSAGES.get(lang_key, NO_INFO_MESSAGES["es"]),
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
                # si quieres meter recomendaciones, puedes activar esto:
                # {"role": "system", "content": recommendation_text},
                {"role": "user", "content": req.question}
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
            answer = NO_INFO_MESSAGES.get(lang_key, NO_INFO_MESSAGES["es"])
           
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
