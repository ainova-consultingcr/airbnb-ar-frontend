import os

from fastapi import HTTPException

from core.config import GOOGLE_SHEET_WEBHOOK
from core.ids import generate_lead_id
from modules.conversation import (
    build_conversation_context_text,
    expand_followup_question,
    handle_negative_followup,
    is_short_followup_reply,
    normalize_text,
)
from modules.faqs.configured_responses import (
    handle_hospitality_information,
    handle_transport_information,
)
from modules.faqs.messages import MESSAGES, get_no_info_message
from modules.faqs.service import build_faq_response
from modules.intents import detect_intent
from modules.requests.flow import ServiceRequestCreationError, handle_service_request
from prompts import SYSTEM_PROMPT_TEMPLATE
from rag import build_context, load_property_data

from .schemas import AskRequest
from .service import build_system_prompt, generate_answer

OPENAI_MODEL = "gpt-4.1-mini"

def handle_ask(req: AskRequest, *, client_factory, question_logger):
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
    try:
        request_response = handle_service_request(
            entity=entity,
            property_id=req.property_id,
            question=req.question,
            room_id=req.room_id,
            guest_session_id=req.guest_session_id,
            lang_key=lang_key,
            webhook_url=GOOGLE_SHEET_WEBHOOK,
        )
    except ServiceRequestCreationError as error:
        raise HTTPException(status_code=502, detail=f"No se pudo registrar la solicitud: {error}")
    if request_response:
        return request_response
    suggestions = entity.get("ui", {}).get("suggestions", {})

    negative_followup = handle_negative_followup(
        req.question,
        req.conversation_context,
        lang_key,
        suggestions
    )
    if negative_followup:
        return negative_followup

    system_prompt = build_system_prompt(
        entity=entity,
        property_id=req.property_id,
        language=req.language or "es",
        context_builder=build_context,
        prompt_template=SYSTEM_PROMPT_TEMPLATE,
    )

        # 4) Recomendaciones dinámicas (opcional)
    intent = detect_intent(req.question)

    #services = entity.get("ui", {}).get("services", {})
    #restaurants = services.get("restaurants", [])
    entity_type = entity.get("type", "")
    if entity_type == "wellness_sales_assistant":
        intent = "general"

    hospitality_response = handle_hospitality_information(
        entity=entity,
        question=req.question,
        effective_question=effective_question,
        lang_key=lang_key,
        intent=intent,
        messages=MESSAGES,
        lead_id_factory=generate_lead_id,
        normalize=normalize_text,
        no_info_message=get_no_info_message,
    )
    if hospitality_response:
        return hospitality_response

    faq_response = build_faq_response(effective_question, entity, suggestions, normalize_text)
    if faq_response:
        return faq_response

    transport_response = handle_transport_information(
        entity=entity,
        effective_question=effective_question,
        lang_key=lang_key,
        no_info_message=get_no_info_message,
    )
    if transport_response:
        return transport_response

    answer, is_generic = generate_answer(
        client_factory=client_factory,
        api_key=os.getenv("OPENAI_API_KEY"),
        model=OPENAI_MODEL,
        system_prompt=system_prompt,
        conversation_context=conversation_context_text,
        question=effective_question,
        fallback_factory=lambda: get_no_info_message(entity, lang_key),
    )

    question_logger(req.property_id, req.language, req.question, answer, is_generic)
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
