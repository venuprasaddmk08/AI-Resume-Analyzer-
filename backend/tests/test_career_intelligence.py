from schemas import ExperienceEntry, ResumeAnalysis, SkillEvidence
from services.career_intelligence import ROLE_PROFILES, build_career_trajectory, compute_role_fit, suggest_next_role


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


def test_next_role_uses_title_keyword_for_role_family():
    resume = ResumeAnalysis(
        experience=[ExperienceEntry(title="Backend Engineer", organization="Acme")],
        skills=[SkillEvidence(skill="Python", evidence_text="Python", evidence_type="OTHER")],
    )
    role_fit = compute_role_fit(resume, resume_blocks=[], resume_sections=[])

    result = suggest_next_role(resume, role_fit)

    assert result.current_role_family == "Backend Developer"
    assert result.suggested_next_role is not None
    assert "Suggested next-role analysis" in result.rationale
    assert "guaranteed" in result.rationale.lower()
    assert any("Backend Engineer" in e for e in result.supporting_evidence)


def test_next_role_falls_back_to_top_role_fit_without_title_keyword():
    resume = ResumeAnalysis(
        experience=[ExperienceEntry(title="Software Engineer", organization="Acme")],
        skills=[
            SkillEvidence(skill="Python", evidence_text="Python", evidence_type="OTHER"),
            SkillEvidence(skill="SQL", evidence_text="SQL", evidence_type="OTHER"),
            SkillEvidence(skill="REST API", evidence_text="REST API", evidence_type="OTHER"),
            SkillEvidence(skill="Git", evidence_text="Git", evidence_type="OTHER"),
        ],
    )
    role_fit = compute_role_fit(resume, resume_blocks=[], resume_sections=[])

    result = suggest_next_role(resume, role_fit)

    assert result.current_role_family == "Backend Developer"


def test_next_role_returns_honest_no_evidence_message_when_nothing_to_go_on():
    result = suggest_next_role(ResumeAnalysis(), [])

    assert result.current_role_family is None
    assert result.suggested_next_role is None
    assert "Not enough" in result.rationale
    assert result.supporting_evidence == []


def test_next_role_suggests_lead_from_senior_title():
    resume = ResumeAnalysis(
        experience=[
            ExperienceEntry(title="Senior Backend Engineer", organization="Acme"),
            ExperienceEntry(title="Backend Engineer", organization="Beta"),
            ExperienceEntry(title="Junior Backend Engineer", organization="Gamma"),
        ],
    )
    role_fit = compute_role_fit(resume, resume_blocks=[], resume_sections=[])

    result = suggest_next_role(resume, role_fit)

    assert result.current_level == "Senior Backend Developer"
    assert result.suggested_next_role == "Lead Backend Developer"


def test_next_role_already_at_top_of_ladder(monkeypatch):
    # detect_tone_seniority's coarsest bucket ("Senior / Leadership-leaning")
    # maps to rung 3, one below the ladder's top rung — this exercises the
    # defensive "already at the top" branch directly, in case a future
    # tone bucket maps to the top rung.
    import services.career_intelligence as career_intelligence

    monkeypatch.setitem(career_intelligence._TONE_TO_RUNG, "Top Rung Test", career_intelligence._TOP_RUNG)
    monkeypatch.setattr(career_intelligence, "detect_tone_seniority", lambda resume_analysis: "Top Rung Test")

    resume = ResumeAnalysis(experience=[ExperienceEntry(title="Lead Backend Engineer", organization="Acme")])
    role_fit = compute_role_fit(resume, resume_blocks=[], resume_sections=[])

    result = suggest_next_role(resume, role_fit)

    assert result.suggested_next_role is None
    assert "already reads at the top" in result.rationale
