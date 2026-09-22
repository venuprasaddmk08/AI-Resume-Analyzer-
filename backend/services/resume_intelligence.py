"""Deterministic resume-quality checks (bullet issues, quantification,
tone/seniority, an explainable health checklist) plus one AI-assisted
bullet rewrite with a strict no-fabrication rule and honest fallback.

Nothing here reports a fact about the candidate that wasn't already in
their own resume text — the health/tone signals are heuristics over the
already-extracted structured resume, and the rewrite only rephrases the
bullet the candidate provided.
"""

import json
import re
from pathlib import Path

from pydantic import BaseModel

from schemas import BulletAnalysis, BulletRewrite, ResumeAnalysis, ResumeHealth, ResumeHealthCheck
from services.ai_client import AIUnavailableError, UNTRUSTED_DOCUMENT_NOTICE, generate_structured

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bullet_rewrite.txt"

_SYSTEM_PROMPT = (
    "You are a precise resume writing coach. You rewrite wording only — you never invent "
    "facts, numbers, or outcomes not already in the text given to you. You respond with JSON only."
)

_QUANT_RE = re.compile(r"(\d+(\.\d+)?\s?%|\$\s?\d|\b\d+[kKmMbB]?\+?\b)")

_WEAK_PREFIXES = [
    "responsible for",
    "worked on",
    "helped with",
    "helped to",
    "involved in",
    "assisted with",
    "in charge of",
    "tasked with",
]

_LEADERSHIP_WORDS = ["led", "managed", "mentored", "owned", "directed", "supervised", "founded", "spearheaded"]
_SENIOR_TITLE_WORDS = ["senior", "lead", "principal", "staff", "manager", "head of", "director", "vp", "chief"]


class _AIRewrite(BaseModel):
    rewritten: str


def analyze_bullet(source: str, text: str) -> BulletAnalysis:
    issues = []
    has_quant = bool(_QUANT_RE.search(text))
    lowered = text.strip().lower()

    if any(lowered.startswith(prefix) for prefix in _WEAK_PREFIXES):
        issues.append("Starts with a passive/weak phrase — lead with a specific action verb instead.")
    if not has_quant:
        issues.append("No measurable outcome (a number, percentage, or scale) — consider adding one.")
    word_count = len(text.split())
    if word_count < 5:
        issues.append("Very short — may be missing context about scope or impact.")
    elif word_count > 40:
        issues.append("Quite long — consider splitting into two bullets or tightening the wording.")

    return BulletAnalysis(source=source, text=text, has_quantification=has_quant, issues=issues)


def collect_bullets(resume_analysis: ResumeAnalysis) -> list[BulletAnalysis]:
    bullets = []
    for exp in resume_analysis.experience:
        if exp.description:
            bullets.append(analyze_bullet("experience", exp.description))
    for proj in resume_analysis.projects:
        if proj.description:
            bullets.append(analyze_bullet("project", proj.description))
    for achievement in resume_analysis.achievements:
        bullets.append(analyze_bullet("achievement", achievement))
    return bullets


def detect_tone_seniority(resume_analysis: ResumeAnalysis) -> str:
    experience_count = len(resume_analysis.experience)
    text_blob = " ".join(
        [exp.description or "" for exp in resume_analysis.experience]
        + [exp.title or "" for exp in resume_analysis.experience]
    ).lower()

    has_senior_title = any(word in text_blob for word in _SENIOR_TITLE_WORDS)
    has_leadership_language = any(word in text_blob for word in _LEADERSHIP_WORDS)

    if has_senior_title or (experience_count >= 3 and has_leadership_language):
        return "Senior / Leadership-leaning"
    if experience_count == 0:
        return "Entry-level / Student"
    if experience_count <= 2:
        return "Early-career"
    return "Mid-level"


def compute_resume_health(resume_analysis: ResumeAnalysis, bullets: list[BulletAnalysis]) -> ResumeHealth:
    checks = []

    has_contact = bool(resume_analysis.contact.email or resume_analysis.contact.phone)
    checks.append(
        ResumeHealthCheck(
            label="Contact information",
            passed=has_contact,
            detail="Email or phone found." if has_contact else "No email or phone number was found.",
        )
    )

    has_skills = len(resume_analysis.skills) > 0
    checks.append(
        ResumeHealthCheck(
            label="Skills listed",
            passed=has_skills,
            detail=f"{len(resume_analysis.skills)} skill(s) found." if has_skills else "No skills were detected.",
        )
    )

    quantified = sum(1 for b in bullets if b.has_quantification)
    quant_ratio = (quantified / len(bullets)) if bullets else 0.0
    quant_passed = quant_ratio >= 0.3
    checks.append(
        ResumeHealthCheck(
            label="Quantified bullets",
            passed=quant_passed,
            detail=(
                f"{quantified} of {len(bullets)} bullets include a measurable outcome."
                if bullets
                else "No experience/project bullets were found to check."
            ),
        )
    )

    has_education_or_experience = bool(resume_analysis.education or resume_analysis.experience)
    checks.append(
        ResumeHealthCheck(
            label="Education or experience present",
            passed=has_education_or_experience,
            detail="Found." if has_education_or_experience else "No education or experience entries were found.",
        )
    )

    weak_opening_count = sum(1 for b in bullets if any("weak phrase" in issue for issue in b.issues))
    weak_passed = weak_opening_count == 0
    checks.append(
        ResumeHealthCheck(
            label="Strong bullet openings",
            passed=weak_passed,
            detail=(
                "All bullets start with a specific action."
                if weak_passed
                else f"{weak_opening_count} bullet(s) start with a passive/weak phrase."
            ),
        )
    )

    score = 100.0 * sum(1 for c in checks if c.passed) / len(checks)
    return ResumeHealth(score=round(score, 1), checks=checks)


def rewrite_bullet(bullet_text: str) -> BulletRewrite:
    """Never raises — always returns a usable (AI or fallback) rewrite."""
    try:
        ai_result = _rewrite_with_ai(bullet_text)
        return BulletRewrite(original=bullet_text, rewritten=ai_result.rewritten, ai_generated=True)
    except AIUnavailableError as exc:
        return _fallback_rewrite(bullet_text, reason=str(exc))


def _rewrite_with_ai(bullet_text: str) -> "_AIRewrite":
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    schema_json = json.dumps(_AIRewrite.model_json_schema())
    user_prompt = template.format(
        untrusted_notice=UNTRUSTED_DOCUMENT_NOTICE,
        bullet_text=bullet_text,
        schema_json=schema_json,
    )
    return generate_structured(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt, schema=_AIRewrite)


def _fallback_rewrite(bullet_text: str, reason: str) -> BulletRewrite:
    lowered = bullet_text.strip().lower()
    tips = []
    for prefix in _WEAK_PREFIXES:
        if lowered.startswith(prefix):
            tips.append(f"Replace the opening \"{bullet_text.strip()[:len(prefix)]}\" with a specific action verb (e.g., \"Built\", \"Led\", \"Designed\").")
            break
    if not _QUANT_RE.search(bullet_text):
        tips.append("Add a measurable outcome if you can (a number, percentage, or scale).")
    if not tips:
        tips.append("Consider tightening the wording and leading with the outcome.")

    return BulletRewrite(
        original=bullet_text,
        rewritten=bullet_text,
        ai_generated=False,
        warnings=[
            "AI-personalized rewrite was unavailable, so no rewritten text is shown — only generic tips: "
            + " ".join(tips)
            + f" Reason: {reason}",
        ],
    )
