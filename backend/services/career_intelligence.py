"""Compares one resume against a fixed set of common role profiles (not
a real job description) to show broad multi-role fit, and derives a
career trajectory straight from the resume's own experience entries.

Reuses the exact same matching/scoring engine as a real JD comparison
(Phase 5/6) — role profiles are just synthetic JDAnalysis objects — so
this never introduces a second, inconsistent way of judging fit.
"""

from schemas import CareerTrajectoryEntry, JDAnalysis, RequirementMatch, ResumeAnalysis, RoleFitResult
from services.evidence_engine import build_requirement_matches
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
        "role_title": "Full-Stack Developer",
        "required_skills": ["JavaScript", "SQL", "REST API"],
        "preferred_skills": ["React", "Python", "Docker"],
        "nice_to_have_skills": ["GraphQL"],
    },
    {
        "role_title": "Data Scientist",
        "required_skills": ["Python", "SQL", "Machine Learning"],
        "preferred_skills": ["Pandas", "scikit-learn", "TensorFlow"],
        "nice_to_have_skills": ["Spark"],
    },
    {
        "role_title": "DevOps Engineer",
        "required_skills": ["Linux", "CI/CD", "Docker"],
        "preferred_skills": ["Kubernetes", "AWS", "Terraform"],
        "nice_to_have_skills": ["Prometheus"],
    },
    {
        "role_title": "Product Manager",
        "required_skills": ["Agile", "Stakeholder Management", "Roadmapping"],
        "preferred_skills": ["SQL", "Analytics"],
        "nice_to_have_skills": ["Figma"],
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
