import services.resume_intelligence as resume_intelligence
from schemas import ExperienceEntry, ProjectEntry, ResumeAnalysis
from services.ai_client import AIUnavailableError
from services.resume_intelligence import (
    _AIRewrite,
    analyze_bullet,
    collect_bullets,
    compute_resume_health,
    detect_tone_seniority,
    rewrite_bullet,
)


def test_analyze_bullet_flags_weak_opening_and_missing_metric():
    result = analyze_bullet("experience", "Responsible for maintaining the database.")
    assert result.has_quantification is False
    assert any("weak phrase" in issue for issue in result.issues)
    assert any("measurable outcome" in issue for issue in result.issues)


def test_analyze_bullet_recognizes_quantification():
    result = analyze_bullet("experience", "Reduced page load time by 40% for 10k daily users.")
    assert result.has_quantification is True
    assert not any("weak phrase" in issue for issue in result.issues)


def test_collect_bullets_gathers_all_sources():
    resume = ResumeAnalysis(
        experience=[ExperienceEntry(description="Built APIs.")],
        projects=[ProjectEntry(description="Built a churn model.")],
        achievements=["Won a hackathon."],
    )
    bullets = collect_bullets(resume)
    assert {b.source for b in bullets} == {"experience", "project", "achievement"}


def test_detect_tone_seniority_entry_level_with_no_experience():
    assert detect_tone_seniority(ResumeAnalysis()) == "Entry-level / Student"


def test_detect_tone_seniority_senior_from_title():
    resume = ResumeAnalysis(experience=[ExperienceEntry(title="Senior Backend Engineer")])
    assert "Senior" in detect_tone_seniority(resume)


def test_resume_health_scores_perfect_resume_higher():
    good = ResumeAnalysis(
        contact={"email": "a@b.com"},
        skills=[{"skill": "Python", "evidence_text": "Python", "evidence_type": "OTHER"}],
        experience=[ExperienceEntry(description="Reduced latency by 30% for 5k users.")],
    )
    bad = ResumeAnalysis()

    good_bullets = collect_bullets(good)
    bad_bullets = collect_bullets(bad)

    good_health = compute_resume_health(good, good_bullets)
    bad_health = compute_resume_health(bad, bad_bullets)

    assert good_health.score > bad_health.score


def test_rewrite_ai_success_path(monkeypatch):
    monkeypatch.setattr(resume_intelligence, "generate_structured", lambda **kwargs: _AIRewrite(rewritten="Built X, improving Y."))

    result = rewrite_bullet("Worked on the backend.")

    assert result.ai_generated is True
    assert result.rewritten == "Built X, improving Y."
    assert result.warnings == []


def test_rewrite_falls_back_when_ai_unavailable(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("simulated outage")

    monkeypatch.setattr(resume_intelligence, "generate_structured", raise_unavailable)

    result = rewrite_bullet("Worked on the backend.")

    assert result.ai_generated is False
    assert result.rewritten == "Worked on the backend."  # unchanged, never fabricated
    assert "unavailable" in result.warnings[0]
