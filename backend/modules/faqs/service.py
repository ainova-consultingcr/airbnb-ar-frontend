"""FAQ matching behavior extracted from the application entry point."""

from __future__ import annotations

from collections.abc import Callable, Mapping


def find_faq(
    question: str,
    entity: Mapping,
    normalize: Callable[[str], str],
):
    normalized_question = normalize(question)
    for faq in entity.get("faqs", []):
        faq_question = normalize(faq.get("question", ""))
        if faq_question in normalized_question or normalized_question in faq_question:
            return faq.get("answer")

        keywords = [word for word in faq_question.split() if len(word) > 3]
        matches = sum(1 for word in keywords if word in normalized_question)
        if matches >= 2:
            return faq.get("answer")
    return None


def build_faq_context(entity: Mapping) -> list[str]:
    lines = []
    faqs = entity.get("faqs", [])
    if faqs:
        lines.append("FAQs:")
        for faq in faqs:
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            if question and answer:
                lines.append(f"- Q: {question}")
                lines.append(f"  A: {answer}")
    return lines


def build_faq_response(
    question: str,
    entity: Mapping,
    suggestions,
    normalize: Callable[[str], str],
) -> dict | None:
    answer = find_faq(question, entity, normalize)
    if not answer:
        return None
    return {
        "answer": answer,
        "action": "none",
        "poi": None,
        "suggestions": suggestions,
    }
