from fastapi import FastAPI
from dotenv import load_dotenv
from openai import OpenAI

from core.application import configure_http
from core.config import GOOGLE_SHEET_WEBHOOK
from core.ids import generate_lead_id
from modules.analytics import log_event, log_question
from modules.analytics.routes import router as analytics_router, track_lead
from modules.analytics.schemas import LeadEventRequest
from modules.answers.routes import create_router as create_answers_router
from modules.answers.schemas import AskRequest
from modules.conversation import normalize_text
from modules.entities.routes import get_property, router as entities_router
from modules.faqs import find_faq as find_module_faq
from modules.faqs.messages import (
    ENTITY_NO_INFO_MESSAGES,
    MESSAGES,
    NO_INFO_MESSAGES,
    get_no_info_message,
)
from modules.intents import detect_intent
from modules.requests.routes import (
    router as requests_router,
    service_request_confirmation,
    service_request_status,
)
from modules.requests.schemas import ServiceRequestConfirmation
from modules.shopping.routes import (
    create_farmasi_order_request,
    farmasi_seller_login,
    farmasi_seller_logout,
    get_farmasi_order_requests,
    get_farmasi_seller,
    patch_farmasi_order_request,
    require_farmasi_seller,
    router as shopping_router,
)
from modules.shopping.schemas import (
    SellerLogin as FarmasiSellerLogin,
    ShoppingItem as FarmasiOrderItem,
    ShoppingRequest as FarmasiOrderRequest,
    ShoppingStatus as FarmasiOrderStatus,
)


OPENAI_MODEL = "gpt-4.1-mini"

load_dotenv()

app = FastAPI()
options_handler = configure_http(app)
app.include_router(requests_router)
app.include_router(shopping_router)
app.include_router(analytics_router)
app.include_router(entities_router)


def find_faq(question: str, entity: dict):
    """Backward-compatible entry point for FAQ matching."""
    return find_module_faq(question, entity, normalize_text)


answers_router, ask = create_answers_router(
    lambda: OpenAI,
    lambda: log_question,
)
app.include_router(answers_router)
