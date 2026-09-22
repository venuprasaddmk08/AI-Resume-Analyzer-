"""Computes the application-generated Job-Fit Score from Phase 5's
requirement matches plus the resume/JD structured analyses.

This is NOT an official ATS score — it is a configurable, explainable
heuristic. Weights and priority multipliers live in one place
(SCORE_WEIGHTS, PRIORITY_WEIGHTS below) so they're easy to see and tune.
Any component we genuinely can't determine from the evidence available
is marked insufficient_evidence rather than assigned a guessed number,
and the overall score is renormalized over only the components that
could be computed.
"""

from schemas import (
    ComponentName,
    ComponentScore,
    EvidenceSummary,
    JDAnalysis,
    RequirementMatch,
    ResumeAnalysis,
    ScoreBreakdown,
)
from services.semantic_matcher import cosine_similarity_matrix, embed_texts
from services.semantic_matcher import is_available as semantic_model_available
from services.skill_normalizer import normalize_skill

# Prototype starting weights — not a universal hiring standard. Tune here;
# nowhere else in the codebase should hardcode a component weight.
SCORE_WEIGHTS: dict[ComponentName, float] = {
    "skills": 0.35,
    "experience": 0.25,
    "projects": 0.20,
    "education": 0.10,
    "certifications": 0.10,
}

PRIORITY_WEIGHTS: dict[str, float] = {"MANDATORY": 3.0, "PREFERRED": 2.0, "NICE_TO_HAVE": 1.0}
STATUS_POINTS: dict[str, float] = {"MATCH": 1.0, "PARTIAL": 0.5, "GAP": 0.0}

EXPERIENCE_EVIDENCE_TYPES = {"WORK", "INTERNSHIP"}
PROJECT_EVIDENCE_TYPES = {"PROJECT"}

SCORE_METHOD_DESCRIPTION = (
    "Application-generated estimate (not an official ATS score). Weighted average of "
    "Skills (35%), Experience (25%), Projects (20%), Education (10%), and Certifications (10%). "
    "Mandatory requirements count more than preferred, which count more than nice-to-have. "
    "Any component with insufficient evidence is excluded and the remaining weights are "
    "renormalized rather than guessed."
)


def _skills_component(matches: list[RequirementMatch]) -> ComponentScore:
    if not matches:
        return ComponentScore(
            score=None,
            insufficient_evidence=True,
            detail="No job requirements could be extracted to score against.",
        )

    weighted_total = 0.0
    weighted_earned = 0.0
    for match in matches:
        weight = PRIORITY_WEIGHTS[match.priority]
        weighted_total += weight
        weighted_earned += weight * STATUS_POINTS[match.status]

    score = round(weighted_earned / weighted_total * 100, 1) if weighted_total else None
    matched_count = sum(1 for m in matches if m.status == "MATCH")
    return ComponentScore(
        score=score,
        insufficient_evidence=score is None,
        detail=f"{matched_count} of {len(matches)} requirements matched (priority-weighted).",
    )


def _evidence_backed_component(matches: list[RequirementMatch], relevant_types: set[str], label: str) -> ComponentScore:
    covered = [m for m in matches if m.status in ("MATCH", "PARTIAL")]
    if not covered:
        return ComponentScore(
            score=None,
            insufficient_evidence=True,
            detail=f"No matched or partial requirements to evaluate {label} coverage against.",
        )

    has_typed_evidence = any(m.evidence and m.evidence[0].evidence_type != "OTHER" for m in covered)
    if not has_typed_evidence:
        return ComponentScore(
            score=None,
            insufficient_evidence=True,
            detail=(
                f"Matched evidence is not classified by type (AI structured extraction was "
                f"unavailable), so {label} coverage can't be determined."
            ),
        )

    backed = sum(1 for m in covered if m.evidence and m.evidence[0].evidence_type in relevant_types)
    score = round(backed / len(covered) * 100, 1)
    return ComponentScore(
        score=score,
        insufficient_evidence=False,
        detail=f"{backed} of {len(covered)} matched/partial requirements are backed by {label} evidence.",
    )


def _certifications_component(jd: JDAnalysis, resume: ResumeAnalysis) -> ComponentScore:
    if not jd.certifications:
        return ComponentScore(
            score=100.0,
            insufficient_evidence=False,
            detail="Job description does not specify required certifications.",
        )

    required = {normalize_skill(c) for c in jd.certifications}
    have = {normalize_skill(c.name) for c in resume.certifications}
    matched = required & have
    score = round(len(matched) / len(required) * 100, 1)
    return ComponentScore(
        score=score,
        insufficient_evidence=False,
        detail=f"{len(matched)} of {len(required)} required certifications found in resume.",
    )


def _education_component(jd: JDAnalysis, resume: ResumeAnalysis) -> ComponentScore:
    if not jd.education_requirements:
        return ComponentScore(
            score=100.0,
            insufficient_evidence=False,
            detail="Job description does not specify education requirements.",
        )

    if not resume.education:
        return ComponentScore(
            score=0.0,
            insufficient_evidence=False,
            detail="Job description specifies education requirements, but no education was found in the resume.",
        )

    if semantic_model_available():
        entry_texts = [f"{e.degree or ''} {e.field_of_study or ''}".strip() for e in resume.education]
        entry_texts = [text for text in entry_texts if text]
        if entry_texts:
            requirement_embedding = embed_texts([jd.education_requirements])
            entry_embeddings = embed_texts(entry_texts)
            if requirement_embedding is not None and entry_embeddings is not None:
                similarities = cosine_similarity_matrix(requirement_embedding, entry_embeddings)[0]
                best = float(max(similarities.max(), 0.0))
                score = round(min(best, 1.0) * 100, 1)
                return ComponentScore(
                    score=score,
                    insufficient_evidence=False,
                    detail=f"Semantic similarity between resume education and the stated requirement: {best:.2f}.",
                )

    return ComponentScore(
        score=None,
        insufficient_evidence=True,
        detail="Could not automatically verify whether the resume's education satisfies the stated requirement.",
    )


def _build_evidence_summary(matches: list[RequirementMatch]) -> EvidenceSummary:
    def _count(priority: str, status: str) -> int:
        return sum(1 for m in matches if m.priority == priority and m.status == status)

    def _total(priority: str) -> int:
        return sum(1 for m in matches if m.priority == priority)

    return EvidenceSummary(
        total_requirements=len(matches),
        matched=sum(1 for m in matches if m.status == "MATCH"),
        partial=sum(1 for m in matches if m.status == "PARTIAL"),
        gaps=sum(1 for m in matches if m.status == "GAP"),
        mandatory_matched=_count("MANDATORY", "MATCH"),
        mandatory_total=_total("MANDATORY"),
        preferred_matched=_count("PREFERRED", "MATCH"),
        preferred_total=_total("PREFERRED"),
        nice_to_have_matched=_count("NICE_TO_HAVE", "MATCH"),
        nice_to_have_total=_total("NICE_TO_HAVE"),
    )


def compute_score(jd_analysis: JDAnalysis, resume_analysis: ResumeAnalysis, matches: list[RequirementMatch]) -> ScoreBreakdown:
    components: dict[ComponentName, ComponentScore] = {
        "skills": _skills_component(matches),
        "experience": _evidence_backed_component(matches, EXPERIENCE_EVIDENCE_TYPES, "work/internship"),
        "projects": _evidence_backed_component(matches, PROJECT_EVIDENCE_TYPES, "project"),
        "education": _education_component(jd_analysis, resume_analysis),
        "certifications": _certifications_component(jd_analysis, resume_analysis),
    }

    weighted_sum = 0.0
    weight_used = 0.0
    for name, component in components.items():
        if component.score is not None:
            weighted_sum += component.score * SCORE_WEIGHTS[name]
            weight_used += SCORE_WEIGHTS[name]
    overall_score = round(weighted_sum / weight_used, 1) if weight_used > 0 else None

    def _factor(match: RequirementMatch) -> str:
        return f"{match.canonical_skill} ({match.priority.replace('_', ' ').lower()}): {match.reason}"

    positive_factors = [_factor(m) for m in matches if m.status == "MATCH"]
    partial_factors = [_factor(m) for m in matches if m.status == "PARTIAL"]
    negative_factors = [_factor(m) for m in matches if m.status == "GAP"]

    return ScoreBreakdown(
        component_scores=components,
        overall_score=overall_score,
        positive_factors=positive_factors,
        partial_factors=partial_factors,
        negative_factors=negative_factors,
        evidence_summary=_build_evidence_summary(matches),
        score_method=SCORE_METHOD_DESCRIPTION,
    )
