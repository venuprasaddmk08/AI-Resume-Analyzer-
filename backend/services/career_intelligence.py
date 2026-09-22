"""Compares one resume against a fixed set of common role profiles (not
a real job description) to show broad multi-role fit, and derives a
career trajectory straight from the resume's own experience entries.

Reuses the exact same matching/scoring engine as a real JD comparison
(Phase 5/6) — role profiles are just synthetic JDAnalysis objects — so
this never introduces a second, inconsistent way of judging fit.
"""

from schemas import CareerTrajectoryEntry, JDAnalysis, NextRoleSuggestion, RequirementMatch, ResumeAnalysis, RoleFitResult
from services.evidence_engine import build_requirement_matches
from services.resume_intelligence import detect_tone_seniority
from services.scoring_engine import compute_score

# A small, fixed set of common tech role profiles. Not exhaustive — this is
# a broad-strokes "how do I compare across roles" view, not a replacement
# for comparing against a real job description.
ROLE_PROFILES: list[dict] = [
    {
        "role_title": "Backend Developer",
        "required_skills": ["Python", "SQL", "REST API", "Git"],
        "preferred_skills": ["Docker", "AWS", "FastAPI"],
        "nice_to_have_skills": ["Kubernetes"],
    },
    {
        "role_title": "Frontend Developer",
        "required_skills": ["JavaScript", "React", "HTML", "CSS"],
        "preferred_skills": ["TypeScript", "Redux"],
        "nice_to_have_skills": ["Next.js"],
    },
    {
        "role_title": "Data Analyst",
        "required_skills": ["SQL", "Excel", "Data Visualization"],
        "preferred_skills": ["Python", "Tableau", "Statistics"],
        "nice_to_have_skills": ["Power BI"],
    },
    {
        "role_title": "DevOps Engineer",
        "required_skills": ["Linux", "CI/CD", "Docker"],
        "preferred_skills": ["Kubernetes", "AWS", "Terraform"],
        "nice_to_have_skills": ["Prometheus"],
    },
    {
        "role_title": "ML Engineer",
        "required_skills": ["Python", "Machine Learning", "SQL"],
        "preferred_skills": ["Pandas", "scikit-learn", "TensorFlow"],
        "nice_to_have_skills": ["Spark"],
    },
    {
        "role_title": "Data Engineer",
        "required_skills": ["Python", "SQL", "ETL"],
        "preferred_skills": ["Spark", "Airflow", "AWS"],
        "nice_to_have_skills": ["Kafka"],
    },
]

_MAX_EVIDENCE_HIGHLIGHTS = 3


def compute_role_fit(
    resume_analysis: ResumeAnalysis,
    resume_blocks: list[dict],
    resume_sections: list[dict],
) -> list[RoleFitResult]:
    results = []
    for profile in ROLE_PROFILES:
        jd = JDAnalysis(
            role_title=profile["role_title"],
            required_skills=profile["required_skills"],
            preferred_skills=profile["preferred_skills"],
            nice_to_have_skills=profile["nice_to_have_skills"],
        )
        # use_ai_refinement=False: this runs against every role profile at
        # once, so it stays fast/free and deterministic rather than firing
        # one AI call per role on every page load.
        matches, _, _ = build_requirement_matches(jd, resume_analysis, resume_blocks, resume_sections, use_ai_refinement=False)
        score = compute_score(jd, resume_analysis, matches)

        results.append(
            RoleFitResult(
                role_title=profile["role_title"],
                fit_score=score.overall_score,
                matched_skills=[m.canonical_skill for m in matches if m.status == "MATCH"],
                gap_skills=[m.canonical_skill for m in matches if m.status == "GAP"],
                evidence_highlights=_evidence_highlights(matches),
            )
        )

    results.sort(key=lambda r: (r.fit_score is None, -(r.fit_score or 0)))
    return results


def _evidence_highlights(matches: list[RequirementMatch]) -> list[str]:
    matched = [m for m in matches if m.status == "MATCH"]
    matched.sort(key=lambda m: m.confidence, reverse=True)
    return [m.reason for m in matched[:_MAX_EVIDENCE_HIGHLIGHTS]]


_ROLE_FAMILY_KEYWORDS = {
    "Backend Developer": ["backend", "back-end", "back end"],
    "Frontend Developer": ["frontend", "front-end", "front end"],
    "Data Analyst": ["data analyst", "business analyst", "analytics"],
    "DevOps Engineer": ["devops", "site reliability", "sre", "platform engineer"],
    "ML Engineer": ["machine learning", "ml engineer", "ai engineer"],
    "Data Engineer": ["data engineer", "etl"],
}

# Index into this list = a "rung" on the ladder for any role family.
_TONE_TO_RUNG = {
    "Entry-level / Student": 0,
    "Early-career": 1,
    "Mid-level": 2,
    "Senior / Leadership-leaning": 3,
}
_TOP_RUNG = 4  # "Lead {role}"


def _rung_title(role_family: str, rung: int) -> str:
    if rung == 0:
        return "Intern"
    if rung == 1:
        return f"Junior {role_family}"
    if rung == 2:
        return role_family
    if rung == 3:
        return f"Senior {role_family}"
    return f"Lead {role_family}"


def suggest_next_role(resume_analysis: ResumeAnalysis, role_fit_results: list[RoleFitResult]) -> NextRoleSuggestion:
    """Evidence-grounded, directional next-role suggestion — never a
    guaranteed outcome, and never invented beyond the resume's own latest
    title and the already-computed role-fit results."""
    latest = resume_analysis.experience[0] if resume_analysis.experience else None
    latest_title_lower = (latest.title or "").lower() if latest else ""

    role_family = next(
        (family for family, keywords in _ROLE_FAMILY_KEYWORDS.items() if any(kw in latest_title_lower for kw in keywords)),
        None,
    )

    # Only fall back to the top role-fit result when it's backed by an
    # actual score — with zero skill/experience evidence, every profile
    # scores None and picking one anyway would be an arbitrary guess, not
    # an evidence-grounded suggestion.
    top_fit = role_fit_results[0] if role_fit_results else None
    if role_family is None and top_fit is not None and top_fit.fit_score is not None:
        role_family = top_fit.role_title

    if role_family is None:
        return NextRoleSuggestion(
            rationale="Not enough resume experience or skill evidence to suggest a next role.",
        )

    supporting_evidence = []
    if latest:
        where = f" at {latest.organization}" if latest.organization else ""
        supporting_evidence.append(f'Latest resume entry: "{latest.title or "Unknown title"}"{where}.')

    matching_fit = next((r for r in role_fit_results if r.role_title == role_family), top_fit)
    if matching_fit is not None and matching_fit.fit_score is not None:
        supporting_evidence.append(
            f"{role_family} track shows {round(matching_fit.fit_score)}/100 fit with "
            f"{len(matching_fit.matched_skills)} matched skill(s)."
        )

    current_rung = _TONE_TO_RUNG.get(detect_tone_seniority(resume_analysis), 2)
    current_level = _rung_title(role_family, current_rung)

    if current_rung >= _TOP_RUNG:
        return NextRoleSuggestion(
            current_role_family=role_family,
            current_level=current_level,
            suggested_next_role=None,
            rationale=(
                "Suggested next-role analysis based on demonstrated experience: this resume already reads at "
                f"the top of the {role_family} track shown here. Not a guaranteed outcome — a real promotion "
                "depends on factors this app has no visibility into."
            ),
            supporting_evidence=supporting_evidence,
        )

    next_level = _rung_title(role_family, current_rung + 1)
    return NextRoleSuggestion(
        current_role_family=role_family,
        current_level=current_level,
        suggested_next_role=next_level,
        rationale=(
            f"Suggested next-role analysis based on demonstrated experience: {current_level} → {next_level}. "
            "This is a directional suggestion, not a guaranteed career outcome."
        ),
        supporting_evidence=supporting_evidence,
    )


def build_career_trajectory(resume_analysis: ResumeAnalysis) -> list[CareerTrajectoryEntry]:
    """Passes through the resume's own experience entries, in the order
    they were extracted (typically most-recent-first, as most resumes are
    written) — never re-sorted by parsing free-text dates, which would
    risk misordering on inconsistent formats."""
    return [
        CareerTrajectoryEntry(
            title=entry.title,
            organization=entry.organization,
            start_date=entry.start_date,
            end_date=entry.end_date,
            description=entry.description,
        )
        for entry in resume_analysis.experience
    ]
