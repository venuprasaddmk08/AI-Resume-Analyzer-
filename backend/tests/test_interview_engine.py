"""Tests for the interview answer evaluator. Never calls the real AI
provider — generate_structured is monkeypatched."""

import services.interview_engine as interview_engine
from services.ai_client import AIUnavailableError
from services.interview_engine import _AIEvaluation, evaluate_answer


def test_ai_success_path(monkeypatch):
    ai_result = _AIEvaluation(
        strengths=["Gave a concrete example."],
        improvements=["Add a measurable outcome."],
        follow_up_question="What was the measurable impact?",
    )
    monkeypatch.setattr(interview_engine, "generate_structured", lambda **kwargs: ai_result)

    result = evaluate_answer(
        question="Tell me about a project.",
        answer="I built a churn predictor using scikit-learn.",
        based_on="Python",
        role_title="Data Scientist",
    )

    assert result.ai_generated is True
    assert result.warnings == []
    assert result.strengths == ["Gave a concrete example."]
    assert result.follow_up_question == "What was the measurable impact?"


def test_falls_back_when_ai_unavailable(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("simulated outage")

    monkeypatch.setattr(interview_engine, "generate_structured", raise_unavailable)

    result = evaluate_answer(
        question="Tell me about a project.",
        answer="I built something.",
        based_on=None,
        role_title=None,
    )

    assert result.ai_generated is False
    assert "unavailable" in result.warnings[0]
    assert result.improvements
    assert result.follow_up_question


def test_fallback_flags_missing_quantification_and_short_answer(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("boom")

    monkeypatch.setattr(interview_engine, "generate_structured", raise_unavailable)

    result = evaluate_answer(question="Q", answer="Short.", based_on=None, role_title=None)

    assert any("more detail" in tip for tip in result.improvements)
    assert any("measurable outcome" in tip for tip in result.improvements)
