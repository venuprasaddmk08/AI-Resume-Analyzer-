from schemas import ExperienceEntry, ResumeAnalysis, SkillEvidence
from services.career_intelligence import ROLE_PROFILES, build_career_trajectory, compute_role_fit


def _resume_with_skills(*skills):
    return ResumeAnalysis(
        skills=[SkillEvidence(skill=s, evidence_text=s, evidence_type="OTHER", confidence=0.7) for s in skills]
    )


def test_role_fit_covers_every_profile():
    resume = _resume_with_skills("Python", "SQL")
    results = compute_role_fit(resume, resume_blocks=[], resume_sections=[])
    assert len(results) == len(ROLE_PROFILES)
    assert {r.role_title for r in results} == {p["role_title"] for p in ROLE_PROFILES}


def test_role_fit_sorted_descending_by_score():
    resume = _resume_with_skills("Python", "SQL", "REST API", "Git", "Docker", "AWS", "FastAPI")
    results = compute_role_fit(resume, resume_blocks=[], resume_sections=[])
    scores = [r.fit_score for r in results if r.fit_score is not None]
    assert scores == sorted(scores, reverse=True)
    assert results[0].role_title == "Backend Developer"


def test_role_fit_evidence_highlights_grounded_in_matches():
    resume = _resume_with_skills("Python", "SQL", "REST API", "Git")
    results = compute_role_fit(resume, resume_blocks=[], resume_sections=[])
    backend = next(r for r in results if r.role_title == "Backend Developer")
    assert "Python" in backend.matched_skills
    assert backend.evidence_highlights
    assert len(backend.evidence_highlights) <= 3


def test_role_fit_reports_gaps_for_unmatched_role():
    resume = _resume_with_skills("Photoshop")
    results = compute_role_fit(resume, resume_blocks=[], resume_sections=[])
    devops = next(r for r in results if r.role_title == "DevOps Engineer")
    assert "Linux" in devops.gap_skills


def test_career_trajectory_passes_through_experience_order():
    resume = ResumeAnalysis(
        experience=[
            ExperienceEntry(title="Senior Engineer", organization="Acme", start_date="2023", end_date="2025"),
            ExperienceEntry(title="Junior Engineer", organization="Beta", start_date="2021", end_date="2023"),
        ]
    )
    trajectory = build_career_trajectory(resume)
    assert len(trajectory) == 2
    assert trajectory[0].title == "Senior Engineer"
    assert trajectory[1].organization == "Beta"


def test_career_trajectory_empty_when_no_experience():
    assert build_career_trajectory(ResumeAnalysis()) == []
