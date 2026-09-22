"""Tests for jd_analyzer.py. Mocks the AI client entirely — no live
network calls happen in this test file."""

import services.jd_analyzer as jd_analyzer
from schemas import JDAnalysis
from services.ai_client import AIUnavailableError


def test_analyze_jd_uses_ai_result_when_available(monkeypatch):
    canned = JDAnalysis(
        role_title="Backend Developer",
        seniority="Mid",
        required_skills=["Python", "SQL", "FastAPI"],
        preferred_skills=["Docker", "AWS"],
    )
    monkeypatch.setattr(jd_analyzer, "generate_structured", lambda **kwargs: canned)

    result = jd_analyzer.analyze_job_description("Backend Developer\nRequirements\nPython, SQL, FastAPI")

    assert result.role_title == "Backend Developer"
    assert result.ai_used is True
    assert "Python" in result.required_skills
    assert "Docker" in result.preferred_skills


def test_analyze_jd_falls_back_when_ai_unavailable(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("no key configured")

    monkeypatch.setattr(jd_analyzer, "generate_structured", raise_unavailable)

    result = jd_analyzer.analyze_job_description("Backend Developer\nRequirements\nPython, SQL, FastAPI, AWS")

    assert result.ai_used is False
    assert result.required_skills == []
    assert result.preferred_skills == []
    assert result.role_title is None
    assert any("unavailable" in w.lower() for w in result.warnings)
