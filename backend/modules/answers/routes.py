from fastapi import APIRouter

from .flow import handle_ask
from .schemas import AskRequest


def create_router(client_factory_resolver, question_logger_resolver):
    router = APIRouter()

    @router.post("/ask")
    def ask(req: AskRequest):
        return handle_ask(
            req,
            client_factory=client_factory_resolver(),
            question_logger=question_logger_resolver(),
        )

    return router, ask
