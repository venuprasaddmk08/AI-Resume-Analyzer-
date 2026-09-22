"""AI-assisted structured job description analysis, built on top of the
raw parsed text from jd_parser.py (Phase 3).

When AI is unavailable, this falls back to a minimal, clearly-flagged
deterministic result rather than inventing requirements that were never
stated in the job description.
"""

import json
from pathlib import Path

from schemas import JDAnalysis
from services.ai_client import AIUnavailableError, UNTRUSTED_DOCUMENT_NOTICE, generate_structured

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "jd_analysis.txt"

_SYSTEM_PROMPT = (
    "You are a precise job description information extractor. You only report "
    "requirements explicitly present in the provided text. You never invent "
    "skills, seniority, or requirements. You respond with JSON only."
)


def analyze_job_description(normalized_text: str) -> JDAnalysis:
    """Returns a structured JDAnalysis. Uses AI when available; falls back
    to an empty, clearly-flagged result when it is not."""
    try:
        return _analyze_with_ai(normalized_text)
    except AIUnavailableError as exc:
        return _fallback_analysis(reason=str(exc))


def _analyze_with_ai(normalized_text: str) -> JDAnalysis:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    schema_json = json.dumps(JDAnalysis.model_json_schema())
    user_prompt = template.format(
        untrusted_notice=UNTRUSTED_DOCUMENT_NOTICE,
        schema_json=schema_json,
        jd_text=normalized_text,
    )
    analysis = generate_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=JDAnalysis,
    )
    analysis.ai_used = True
    return analysis


def _fallback_analysis(reason: str) -> JDAnalysis:
    return JDAnalysis(
        role_title=None,
        seniority=None,
        required_skills=[],
        preferred_skills=[],
        nice_to_have_skills=[],
        experience_requirements=None,
        education_requirements=None,
        certifications=[],
        responsibilities=[],
        tools=[],
        domain_knowledge=[],
        ai_used=False,
        warnings=[
            "AI structured analysis was unavailable, so requirements could not be "
            f"automatically extracted from this job description. Reason: {reason}",
        ],
    )
