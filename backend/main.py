from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
from dotenv import load_dotenv
from openai import OpenAI

from rag import load_property_data, build_context
from prompts import SYSTEM_PROMPT_TEMPLATE


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

OPENAI_MODEL = "gpt-4o-mini"

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # solo desarrollo
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    property_id: Optional[str] = "demo_property"
    question: str
    language: Optional[str] = "es"


@app.post("/ask")
def ask(req: AskRequest):
    try:
        # 1) Cargar entidad (1 sola vez)
        entity = load_property_data(req.property_id)
        place_type = entity.get("type", "generic")
        # 2) Contexto desde entidad
        context_text = build_context(entity)

        # 3) Prompt universal
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            entity_name=entity.get("name", req.property_id),
            entity_type=entity.get("entity_type", "entity"),
            place_type=place_type,
            language=req.language or "es",
            context=context_text
        )

        # 4) Recomendaciones dinámicas
        intent = detect_intent(req.question)
        suggestions = RECOMMENDATIONS.get(intent, [])

        recommendation_text = ""
        if suggestions:
            recommendation_text = (
                "\nYou may suggest up to 2 local options from the list below, "
                "only if relevant and naturally:\n"
                + "\n".join(suggestions)
            )

        # 5) Llamada OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": recommendation_text},
                {"role": "user", "content": req.question}
            ],
            temperature=0.3
        )

        return {"answer": response.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
