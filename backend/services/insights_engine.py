"""Generates a learning roadmap and mock-interview questions grounded in
the already-computed requirement matches (Phase 5) for one analysis.

Tries one AI call for a role-aware, personalized version. When AI is
unavailable (no key, DEMO_MODE, or a provider failure), falls back to a
deterministic generic template — the same shape of content, honestly
labeled as non-personalized, never fabricated.
"""

import json
from pathlib import Path

from pydantic import BaseModel

from schemas import CareerInsights, InterviewQuestion, JDAnalysis, LearningStep, RequirementMatch
from services.ai_client import AIUnavailableError, UNTRUSTED_DOCUMENT_NOTICE, generate_structured
from services.external_evidence import youtube_search_url

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "career_insights.txt"

_SYSTEM_PROMPT = (
    "You are a precise, encouraging career coach. You only use the skill names and "
    "evidence given to you. You never invent facts about the candidate. You respond "
    "with JSON only."
)

_PRIORITY_ORDER = {"MANDATORY": 0, "PREFERRED": 1, "NICE_TO_HAVE": 2}

_GENERIC_STEPS = ["Learn the fundamentals", "Follow a guided tutorial or course", "Apply it in a small practice project"]
_BEHAVIORAL_QUESTIONS = [
    "Tell me about a time you had to learn a new technology quickly for a project. How did you approach it?",
    "Describe a challenging bug or technical problem you solved recently. What was your process?",
]


class _AIInsights(BaseModel):
    learning_roadmap: list[LearningStep]
    interview_questions: list[InterviewQuestion]


def _sort_by_priority(matches: list[RequirementMatch]) -> list[RequirementMatch]:
    return sorted(matches, key=lambda m: _PRIORITY_ORDER.get(m.priority, 9))


def _with_youtube_link(step: LearningStep) -> LearningStep:
    step.youtube_search_url = youtube_search_url(f"{step.skill} tutorial")
    return step


def generate_career_insights(matches: list[RequirementMatch], jd_analysis: JDAnalysis) -> CareerInsights:
    """Returns CareerInsights for this set of matches. Never raises —
    always returns a usable (AI or fallback) result."""
    gap_matches = _sort_by_priority([m for m in matches if m.status == "GAP"])
    matched_matches = _sort_by_priority([m for m in matches if m.status == "MATCH"])

    if not gap_matches and not matched_matches:
        return CareerInsights(
            ai_generated=False,
            warnings=["No matched or gap requirements were available to build insights from."],
        )

    try:
        ai_insights = _generate_with_ai(gap_matches, matched_matches, jd_analysis)
        roadmap = [_with_youtube_link(step) for step in ai_insights.learning_roadmap]
        return CareerInsights(
            learning_roadmap=roadmap,
            interview_questions=ai_insights.interview_questions,
            ai_generated=True,
        )
    except AIUnavailableError as exc:
        return CareerInsights(
            learning_roadmap=_fallback_roadmap(gap_matches),
            interview_questions=_fallback_questions(matched_matches, gap_matches, jd_analysis.role_title),
            ai_generated=False,
            warnings=[
                "AI-personalized roadmap and interview questions were unavailable, so a generic "
                f"template is shown instead. Reason: {exc}",
            ],
        )


def _generate_with_ai(
    gap_matches: list[RequirementMatch],
    matched_matches: list[RequirementMatch],
    jd_analysis: JDAnalysis,
) -> _AIInsights:
    match_data = {
        "role_title": jd_analysis.role_title,
        "gap_skills": [{"skill": m.canonical_skill, "priority": m.priority} for m in gap_matches],
        "matched_skills": [
            {
                "skill": m.canonical_skill,
                "priority": m.priority,
                "evidence_type": m.evidence[0].evidence_type if m.evidence else None,
                "evidence_text": m.evidence[0].text if m.evidence else None,
            }
            for m in matched_matches
        ],
    }

    template = _PROMPT_PATH.read_text(encoding="utf-8")
    schema_json = json.dumps(_AIInsights.model_json_schema())
    user_prompt = template.format(
        untrusted_notice=UNTRUSTED_DOCUMENT_NOTICE,
        schema_json=schema_json,
        match_data_json=json.dumps(match_data),
    )
    return generate_structured(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt, schema=_AIInsights)


def _fallback_roadmap(gap_matches: list[RequirementMatch]) -> list[LearningStep]:
    return [
        LearningStep(
            skill=m.canonical_skill,
            priority=m.priority,
            steps=list(_GENERIC_STEPS),
            resources=[
                f"beginner {m.canonical_skill} tutorial",
                f"{m.canonical_skill} crash course",
                f"{m.canonical_skill} practice project ideas",
            ],
            practice_project=(
                f"Build a small project that specifically applies {m.canonical_skill}, "
                "then describe it with a concrete outcome."
            ),
            youtube_search_url=youtube_search_url(f"{m.canonical_skill} tutorial"),
        )
        for m in gap_matches
    ]


def _fallback_questions(
    matched_matches: list[RequirementMatch],
    gap_matches: list[RequirementMatch],
    role_title: str | None,
) -> list[InterviewQuestion]:
    role_text = f"the {role_title} role" if role_title else "this role"

    questions = [
        InterviewQuestion(
            category="Technical",
            question=(
                f"The job description asks for {m.canonical_skill}, and the resume shows evidence "
                f"of it. Walk through a specific example of how {m.canonical_skill} was used."
            ),
            based_on=m.canonical_skill,
        )
        for m in matched_matches[:5]
    ]

    questions += [
        InterviewQuestion(
            category="Project",
            question=(
                f"Tell me more about the project that used {m.canonical_skill}. "
                "What was the specific contribution to it?"
            ),
            based_on=m.canonical_skill,
        )
        for m in matched_matches
        if m.evidence and m.evidence[0].evidence_type == "PROJECT"
    ][:2]

    questions += [InterviewQuestion(category="Behavioral", question=q, based_on=None) for q in _BEHAVIORAL_QUESTIONS]

    if gap_matches:
        top_gap = gap_matches[0]
        role_text_capitalized = role_text[0].upper() + role_text[1:]
        questions.append(
            InterviewQuestion(
                category="Gap-focused",
                question=(
                    f"{role_text_capitalized} also asks for {top_gap.canonical_skill}, which isn't "
                    "clearly shown in the resume. Is there any experience with it, even informally?"
                ),
                based_on=top_gap.canonical_skill,
            )
        )

    return questions
