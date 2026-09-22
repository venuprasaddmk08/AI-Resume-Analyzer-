"""AI-assisted structured resume analysis, built on top of the raw parsed
text from resume_parser.py (Phase 2).

All facts must be grounded in the actual resume text. The model is
explicitly instructed never to invent skills, dates, employers, or
metrics, and every reported skill must carry a real supporting quote.

When AI is unavailable (no key configured, DEMO_MODE, or a provider
failure), this falls back to a minimal, clearly-flagged deterministic
extraction (regex-based contact info only) rather than fabricating
structured skills/education/experience without AI grounding.
"""

import json
import re
from pathlib import Path

from schemas import ContactInfo, ResumeAnalysis
from services.ai_client import AIUnavailableError, UNTRUSTED_DOCUMENT_NOTICE, generate_structured

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "resume_analysis.txt"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(\(?\+?\d[\d \-().]{7,}\d)")
_LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/\S+", re.IGNORECASE)
_GITHUB_RE = re.compile(r"(https?://)?(www\.)?github\.com/\S+", re.IGNORECASE)

_SYSTEM_PROMPT = (
    "You are a precise resume information extractor. You only report facts "
    "explicitly present in the provided text. You never invent skills, dates, "
    "employers, metrics, or achievements. You respond with JSON only."
)


def analyze_resume(normalized_text: str) -> ResumeAnalysis:
    """Returns a structured ResumeAnalysis. Uses AI when available; falls
    back to a minimal, clearly-flagged deterministic extraction when it
    is not."""
    try:
        return _analyze_with_ai(normalized_text)
    except AIUnavailableError as exc:
        return _fallback_analysis(normalized_text, reason=str(exc))


def _analyze_with_ai(normalized_text: str) -> ResumeAnalysis:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    schema_json = json.dumps(ResumeAnalysis.model_json_schema())
    user_prompt = template.format(
        untrusted_notice=UNTRUSTED_DOCUMENT_NOTICE,
        schema_json=schema_json,
        resume_text=normalized_text,
    )
    analysis = generate_structured(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        schema=ResumeAnalysis,
    )
    analysis.ai_used = True
    return analysis


def _fallback_analysis(normalized_text: str, reason: str) -> ResumeAnalysis:
    email_match = _EMAIL_RE.search(normalized_text)
    phone_match = _PHONE_RE.search(normalized_text)
    linkedin_match = _LINKEDIN_RE.search(normalized_text)
    github_match = _GITHUB_RE.search(normalized_text)

    return ResumeAnalysis(
        candidate_name=None,
        contact=ContactInfo(
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(0).strip() if phone_match else None,
            linkedin_url=linkedin_match.group(0) if linkedin_match else None,
            github_url=github_match.group(0) if github_match else None,
        ),
        skills=[],
        education=[],
        experience=[],
        projects=[],
        certifications=[],
        achievements=[],
        languages=[],
        sections_detected=[],
        ai_used=False,
        warnings=[
            "AI structured analysis was unavailable, so skills, education, experience, "
            "projects, and certifications could not be automatically extracted. Only "
            f"contact details found via pattern matching are shown. Reason: {reason}",
        ],
    )
