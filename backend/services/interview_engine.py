"""Evaluates one free-text practice-interview answer and suggests a
follow-up question (Phase 8). The candidate's answer is their own live
input, not a resume claim — evaluated on its own merits, never used to
assert new facts about the candidate.

Falls back to generic, honest feedback when AI is unavailable.
"""

import json
from pathlib import Path

from pydantic import BaseModel

from schemas import InterviewEvaluation
from services.ai_client import AIUnavailableError, UNTRUSTED_DOCUMENT_NOTICE, generate_structured

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "interview_evaluation.txt"

_SYSTEM_PROMPT = (
    "You are an encouraging, precise interview coach. You evaluate only the answer text "
    "given to you. You never invent facts about the candidate. You respond with JSON only."
)


class _AIEvaluation(BaseModel):
    strengths: list[str]
    improvements: list[str]
    follow_up_question: str | None = None


def evaluate_answer(
    question: str,
    answer: str,
    based_on: str | None,
    role_title: str | None,
) -> InterviewEvaluation:
    """Never raises — always returns a usable (AI or fallback) evaluation."""
    try:
        ai_result = _evaluate_with_ai(question, answer, based_on, role_title)
        return InterviewEvaluation(
            strengths=ai_result.strengths,
            improvements=ai_result.improvements,
            follow_up_question=ai_result.follow_up_question,
            ai_generated=True,
        )
    except AIUnavailableError as exc:
        return _fallback_evaluation(answer, reason=str(exc))


def _evaluate_with_ai(
    question: str,
    answer: str,
    based_on: str | None,
    role_title: str | None,
) -> "_AIEvaluation":
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    schema_json = json.dumps(_AIEvaluation.model_json_schema())
    user_prompt = template.format(
        untrusted_notice=UNTRUSTED_DOCUMENT_NOTICE,
        role_title=role_title or "this role",
        question=question,
        based_on=based_on or "N/A",
        answer=answer,
        schema_json=schema_json,
    )
    return generate_structured(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt, schema=_AIEvaluation)


def _fallback_evaluation(answer: str, reason: str) -> InterviewEvaluation:
    word_count = len(answer.split())
    has_number = any(ch.isdigit() for ch in answer)

    improvements = []
    if word_count < 25:
        improvements.append("Add more detail — walk through the situation, your specific action, and the outcome.")
    if not has_number:
        improvements.append("Add a measurable outcome if you can (a number, percentage, or time saved).")
    if not improvements:
        improvements.append("Make sure you clearly state the outcome and what you'd do differently, if anything.")

    strengths = ["You provided a written answer to practice with."] if word_count > 0 else []

    return InterviewEvaluation(
        strengths=strengths,
        improvements=improvements,
        follow_up_question="Can you walk through the specific outcome of that in more detail?",
        ai_generated=False,
        warnings=[
            "AI-personalized feedback was unavailable, so generic writing tips are shown instead. "
            f"Reason: {reason}",
        ],
    )
