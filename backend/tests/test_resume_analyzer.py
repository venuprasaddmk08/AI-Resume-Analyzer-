"""Tests for resume_analyzer.py. Mocks the AI client entirely — no live
network calls happen in this test file."""

import services.resume_analyzer as resume_analyzer
from schemas import ContactInfo, ResumeAnalysis, SkillEvidence
from services.ai_client import AIUnavailableError


def test_analyze_resume_uses_ai_result_when_available(monkeypatch):
    canned = ResumeAnalysis(
        candidate_name="Jane Doe",
        contact=ContactInfo(email="jane@example.com"),
        skills=[
            SkillEvidence(
                skill="Python",
                evidence_text="Built REST APIs using Python and FastAPI.",
                evidence_type="WORK",
                confidence=0.9,
            )
        ],
    )
    monkeypatch.setattr(resume_analyzer, "generate_structured", lambda **kwargs: canned)

    result = resume_analyzer.analyze_resume("Jane Doe\nBuilt REST APIs using Python and FastAPI.")

    assert result.candidate_name == "Jane Doe"
    assert result.ai_used is True
    assert result.skills[0].skill == "Python"
    assert result.skills[0].evidence_text == "Built REST APIs using Python and FastAPI."


def test_analyze_resume_falls_back_when_ai_unavailable(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("no key configured")

    monkeypatch.setattr(resume_analyzer, "generate_structured", raise_unavailable)

    text = "Jane Doe\nEmail: jane.doe@example.com\nPhone: (555) 123-4567\nSkills\nPython, SQL"
    result = resume_analyzer.analyze_resume(text)

    assert result.ai_used is False
    assert result.contact.email == "jane.doe@example.com"
    assert result.contact.phone is not None
    assert result.skills == []
    assert result.education == []
    assert any("unavailable" in w.lower() for w in result.warnings)


def test_fallback_never_fabricates_skills_or_experience(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("no key configured")

    monkeypatch.setattr(resume_analyzer, "generate_structured", raise_unavailable)

    result = resume_analyzer.analyze_resume("Some resume text with Python and AWS mentioned.")

    # Even though "Python" and "AWS" appear in the text, the deterministic
    # fallback must never guess skills without AI grounding + evidence.
    assert result.skills == []
    assert result.experience == []
    assert result.projects == []
    assert result.certifications == []
