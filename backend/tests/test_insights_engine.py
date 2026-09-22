"""Tests for the career insights engine. Never calls the real AI provider —
generate_structured is monkeypatched, matching the project's testing rules."""

import pytest

import services.insights_engine as insights_engine
from schemas import EvidenceItem, JDAnalysis, RequirementMatch
from services.ai_client import AIUnavailableError
from services.insights_engine import _AIInsights, generate_career_insights


def _match(skill, status, priority="MANDATORY", evidence_type="WORK", evidence_text="did the thing"):
    evidence = (
        [EvidenceItem(text=evidence_text, evidence_type=evidence_type, origin="ai_extracted")]
        if status == "MATCH"
        else []
    )
    return RequirementMatch(
        requirement=skill,
        canonical_skill=skill,
        priority=priority,
        status=status,
        evidence=evidence,
        confidence=0.9 if status == "MATCH" else 0.0,
        reason="reason text",
        signal="exact" if status == "MATCH" else "none",
    )


def test_returns_empty_when_no_matches():
    result = generate_career_insights([], JDAnalysis())
    assert result.learning_roadmap == []
    assert result.interview_questions == []
    assert result.ai_generated is False
    assert result.warnings


def test_ai_success_path(monkeypatch):
    matches = [_match("Python", "MATCH"), _match("Docker", "GAP", priority="PREFERRED")]

    ai_result = _AIInsights(
        learning_roadmap=[
            {
                "skill": "Docker",
                "priority": "PREFERRED",
                "steps": ["Learn containers", "Build an image", "Deploy it"],
                "resources": ["docker tutorial", "docker crash course"],
                "practice_project": "Containerize a small API.",
            }
        ],
        interview_questions=[
            {"category": "Technical", "question": "Tell me about your Python usage.", "based_on": "Python"},
        ],
    )
    monkeypatch.setattr(insights_engine, "generate_structured", lambda **kwargs: ai_result)

    result = generate_career_insights(matches, JDAnalysis(role_title="Backend Developer"))

    assert result.ai_generated is True
    assert result.warnings == []
    assert result.learning_roadmap[0].skill == "Docker"
    assert result.interview_questions[0].based_on == "Python"


def test_ai_path_caps_technical_and_project_questions(monkeypatch):
    matches = [_match(f"Skill{i}", "MATCH") for i in range(8)]

    ai_result = _AIInsights(
        learning_roadmap=[],
        interview_questions=(
            [{"category": "Technical", "question": f"Q{i}", "based_on": f"Skill{i}"} for i in range(8)]
            + [{"category": "Project", "question": f"P{i}", "based_on": f"Skill{i}"} for i in range(4)]
            + [{"category": "Behavioral", "question": "B", "based_on": None}]
        ),
    )
    monkeypatch.setattr(insights_engine, "generate_structured", lambda **kwargs: ai_result)

    result = generate_career_insights(matches, JDAnalysis())

    categories = [q.category for q in result.interview_questions]
    assert categories.count("Technical") == 5
    assert categories.count("Project") == 2
    assert categories.count("Behavioral") == 1


def test_falls_back_when_ai_unavailable(monkeypatch):
    matches = [
        _match("Python", "MATCH", evidence_type="PROJECT"),
        _match("Docker", "GAP", priority="PREFERRED"),
        _match("Kubernetes", "GAP", priority="NICE_TO_HAVE"),
    ]

    def raise_unavailable(**kwargs):
        raise AIUnavailableError("simulated outage")

    monkeypatch.setattr(insights_engine, "generate_structured", raise_unavailable)

    result = generate_career_insights(matches, JDAnalysis(role_title="Backend Developer"))

    assert result.ai_generated is False
    assert "unavailable" in result.warnings[0]
    assert len(result.learning_roadmap) == 2
    assert result.learning_roadmap[0].skill == "Docker"  # PREFERRED sorts before NICE_TO_HAVE
    assert result.learning_roadmap[1].skill == "Kubernetes"

    categories = [q.category for q in result.interview_questions]
    assert "Technical" in categories
    assert "Project" in categories
    assert categories.count("Behavioral") == 2
    assert "Gap-focused" in categories

    gap_focused = next(q for q in result.interview_questions if q.category == "Gap-focused")
    assert gap_focused.based_on == "Docker"  # highest priority gap


def test_fallback_never_raises_on_unexpected_provider_error(monkeypatch):
    matches = [_match("Python", "MATCH")]

    def raise_unavailable(**kwargs):
        raise AIUnavailableError("boom")

    monkeypatch.setattr(insights_engine, "generate_structured", raise_unavailable)

    result = generate_career_insights(matches, JDAnalysis())
    assert result.ai_generated is False
