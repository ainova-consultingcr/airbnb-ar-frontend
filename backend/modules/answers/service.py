from collections.abc import Callable
from typing import Any


LOW_QUALITY_PATTERNS = (
    "no tengo esa información",
    "no dispongo de esa información",
    "no cuento con esa información",
    "i don't have that information",
    "i do not have that information",
)


def build_system_prompt(
    *,
    entity: dict,
    property_id: str,
    language: str,
    context_builder: Callable[[dict], str],
    prompt_template: str,
) -> str:
    return prompt_template.format(
        entity_name=entity.get("name", property_id),
        entity_type=entity.get("type", "generic"),
        language=language,
        context=context_builder(entity),
    )


def generate_answer(
    *,
    client_factory: Callable[..., Any],
    api_key: str | None,
    model: str,
    system_prompt: str,
    conversation_context: str,
    question: str,
    fallback_factory: Callable[[], str],
) -> tuple[str, bool]:
    """Generate the final conversational answer and apply AVI's safe fallback."""
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_context:
        messages.append({"role": "system", "content": conversation_context})
    messages.append({"role": "user", "content": question})

    client = client_factory(api_key=api_key)
    response = client.chat.completions.create(model=model, messages=messages)

    answer = None
    if response.choices and response.choices[0].message:
        answer = response.choices[0].message.content

    answer_text = (answer or "").lower()
    is_generic = any(pattern in answer_text for pattern in LOW_QUALITY_PATTERNS)
    if not answer or is_generic:
        answer = fallback_factory()

    return answer, is_generic
