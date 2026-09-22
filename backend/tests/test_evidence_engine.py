"""Tests for evidence_engine.py. The local semantic model and the AI
client are both mocked at the module level — no live network/model
download happens in this test file."""

import numpy as np

import services.evidence_engine as evidence_engine
from schemas import AIRefinementDecision, JDAnalysis, ResumeAnalysis, SkillEvidence
from services.ai_client import AIUnavailableError


def _disable_semantic(monkeypatch):
    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)


def test_exact_match_uses_ai_extracted_skill(monkeypatch):
    _disable_semantic(monkeypatch)
    jd = JDAnalysis(required_skills=["Python"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Python",
                evidence_text="Built REST APIs in Python.",
                evidence_type="WORK",
                confidence=0.9,
            )
        ]
    )

    matches, semantic_ok, ai_used = evidence_engine.build_requirement_matches(jd, resume, [], [])

    assert len(matches) == 1
    match = matches[0]
    assert match.status == "MATCH"
    assert match.signal == "exact"
    assert match.canonical_skill == "Python"
    assert match.priority == "MANDATORY"
    assert match.evidence[0].origin == "ai_extracted"
    assert match.evidence[0].text == "Built REST APIs in Python."
    assert semantic_ok is False
    assert ai_used is False


def test_exact_match_respects_skill_aliases(monkeypatch):
    _disable_semantic(monkeypatch)
    jd = JDAnalysis(required_skills=["ML"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Machine Learning",
                evidence_text="Trained a churn prediction model.",
                evidence_type="PROJECT",
                confidence=0.8,
            )
        ]
    )

    matches, _, _ = evidence_engine.build_requirement_matches(jd, resume, [], [])

    assert matches[0].status == "MATCH"
    assert matches[0].signal == "exact"


def test_raw_text_fallback_works_without_any_ai_extracted_skills(monkeypatch):
    _disable_semantic(monkeypatch)
    jd = JDAnalysis(required_skills=["Docker"])
    resume = ResumeAnalysis(skills=[])  # simulates AI-unavailable fallback mode
    blocks = [{"text": "Used Docker to containerize the deployment.", "page_number": 2, "bbox": None, "font_size": None, "is_heading": False}]

    matches, _, _ = evidence_engine.build_requirement_matches(jd, resume, blocks, [])

    match = matches[0]
    assert match.status == "MATCH"
    assert match.signal == "raw_text"
    assert match.evidence[0].origin == "raw_text"
    assert match.evidence[0].source_page == 2


def test_raw_text_match_does_not_fire_on_partial_word(monkeypatch):
    _disable_semantic(monkeypatch)
    jd = JDAnalysis(required_skills=["Go"])
    resume = ResumeAnalysis(skills=[])
    blocks = [{"text": "Worked on Google Cloud infrastructure.", "page_number": 1, "bbox": None, "font_size": None, "is_heading": False}]

    matches, _, _ = evidence_engine.build_requirement_matches(jd, resume, blocks, [])

    # "Go" must not match inside "Google" — word-boundary matching required.
    assert matches[0].status == "GAP"


def test_gap_when_nothing_found_and_no_semantic_signal(monkeypatch):
    _disable_semantic(monkeypatch)
    jd = JDAnalysis(required_skills=["Kubernetes"])
    resume = ResumeAnalysis(skills=[])

    matches, _, _ = evidence_engine.build_requirement_matches(jd, resume, [], [])

    match = matches[0]
    assert match.status == "GAP"
    assert match.signal == "none"
    assert match.evidence == []
    assert match.confidence == 0.0


def _unit_vector(cos_angle: float) -> list[float]:
    return [cos_angle, (1 - cos_angle**2) ** 0.5]


def _mock_semantic(monkeypatch, vectors: dict[str, list[float]]):
    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: True)

    def fake_embed_texts(texts):
        return np.array([vectors[t] for t in texts])

    monkeypatch.setattr(evidence_engine, "embed_texts", fake_embed_texts)
    # Use the real cosine_similarity_matrix (plain dot product) since our
    # hand-built vectors above are already unit length.


def test_semantic_signal_produces_match_above_threshold(monkeypatch):
    requirement_text = "Container Orchestration"
    candidate_text = "Kubernetes: Deployed services using Kubernetes for orchestration."
    _mock_semantic(
        monkeypatch,
        {
            requirement_text: [1.0, 0.0],
            candidate_text: _unit_vector(0.7),  # above SEMANTIC_MATCH_THRESHOLD (0.62)
        },
    )
    jd = JDAnalysis(preferred_skills=["Container Orchestration"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Kubernetes",
                evidence_text="Deployed services using Kubernetes for orchestration.",
                evidence_type="PROJECT",
                confidence=0.7,
            )
        ]
    )

    matches, semantic_ok, ai_used = evidence_engine.build_requirement_matches(
        jd, resume, [], [], use_ai_refinement=False
    )

    match = matches[0]
    assert match.status == "MATCH"
    assert match.signal == "semantic"
    assert match.priority == "PREFERRED"
    assert semantic_ok is True
    assert ai_used is False


def test_semantic_signal_produces_partial_in_middle_band(monkeypatch):
    requirement_text = "Container Orchestration"
    candidate_text = "Kubernetes: Deployed services using Kubernetes for orchestration."
    _mock_semantic(
        monkeypatch,
        {
            requirement_text: [1.0, 0.0],
            candidate_text: _unit_vector(0.5),  # between PARTIAL (0.45) and MATCH (0.62)
        },
    )
    jd = JDAnalysis(preferred_skills=["Container Orchestration"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Kubernetes",
                evidence_text="Deployed services using Kubernetes for orchestration.",
                evidence_type="PROJECT",
                confidence=0.7,
            )
        ]
    )

    matches, _, ai_used = evidence_engine.build_requirement_matches(jd, resume, [], [], use_ai_refinement=False)

    assert matches[0].status == "PARTIAL"
    assert matches[0].signal == "semantic"
    assert ai_used is False


def test_low_semantic_similarity_falls_through_to_gap(monkeypatch):
    requirement_text = "Container Orchestration"
    candidate_text = "Testing: Wrote unit tests for the billing module."
    _mock_semantic(
        monkeypatch,
        {
            requirement_text: [1.0, 0.0],
            candidate_text: _unit_vector(0.1),  # below PARTIAL threshold
        },
    )
    jd = JDAnalysis(preferred_skills=["Container Orchestration"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Testing",
                evidence_text="Wrote unit tests for the billing module.",
                evidence_type="WORK",
                confidence=0.7,
            )
        ]
    )

    matches, _, _ = evidence_engine.build_requirement_matches(jd, resume, [], [], use_ai_refinement=False)

    assert matches[0].status == "GAP"


def test_ai_refinement_can_promote_partial_to_match(monkeypatch):
    requirement_text = "Container Orchestration"
    candidate_text = "Kubernetes: Deployed services using Kubernetes for orchestration."
    _mock_semantic(monkeypatch, {requirement_text: [1.0, 0.0], candidate_text: _unit_vector(0.5)})
    monkeypatch.setattr(evidence_engine, "is_ai_available", lambda: True)
    monkeypatch.setattr(
        evidence_engine,
        "generate_structured",
        lambda **kwargs: AIRefinementDecision(status="MATCH", reason="Kubernetes usage directly demonstrates this."),
    )

    jd = JDAnalysis(preferred_skills=["Container Orchestration"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Kubernetes",
                evidence_text="Deployed services using Kubernetes for orchestration.",
                evidence_type="PROJECT",
                confidence=0.7,
            )
        ]
    )

    matches, _, ai_used = evidence_engine.build_requirement_matches(jd, resume, [], [], use_ai_refinement=True)

    assert matches[0].status == "MATCH"
    assert matches[0].signal == "ai_reasoning"
    assert ai_used is True


def test_ai_refinement_unavailable_keeps_semantic_result(monkeypatch):
    requirement_text = "Container Orchestration"
    candidate_text = "Kubernetes: Deployed services using Kubernetes for orchestration."
    _mock_semantic(monkeypatch, {requirement_text: [1.0, 0.0], candidate_text: _unit_vector(0.5)})
    monkeypatch.setattr(evidence_engine, "is_ai_available", lambda: True)

    def raise_unavailable(**kwargs):
        raise AIUnavailableError("no key configured")

    monkeypatch.setattr(evidence_engine, "generate_structured", raise_unavailable)

    jd = JDAnalysis(preferred_skills=["Container Orchestration"])
    resume = ResumeAnalysis(
        skills=[
            SkillEvidence(
                skill="Kubernetes",
                evidence_text="Deployed services using Kubernetes for orchestration.",
                evidence_type="PROJECT",
                confidence=0.7,
            )
        ]
    )

    matches, _, ai_used = evidence_engine.build_requirement_matches(jd, resume, [], [], use_ai_refinement=True)

    assert matches[0].status == "PARTIAL"
    assert matches[0].signal == "semantic"
    assert ai_used is False
