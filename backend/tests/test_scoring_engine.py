"""Tests for scoring_engine.py. The local semantic model is mocked where
relevant — no live network/model download happens in this test file."""

import services.scoring_engine as scoring_engine
from schemas import (
    CertificationEntry,
    EducationEntry,
    EvidenceItem,
    JDAnalysis,
    RequirementMatch,
    ResumeAnalysis,
)


def _match(requirement, priority, status, evidence_type=None, origin="ai_extracted", reason="test reason"):
    evidence = []
    if evidence_type is not None:
        evidence = [
            EvidenceItem(text=f"evidence for {requirement}", evidence_type=evidence_type, origin=origin)
        ]
    return RequirementMatch(
        requirement=requirement,
        canonical_skill=requirement,
        priority=priority,
        status=status,
        evidence=evidence,
        confidence=0.8,
        reason=reason,
        signal="exact" if evidence_type else "none",
    )


# ---------------------------------------------------------------------------
# Skills component
# ---------------------------------------------------------------------------


def test_skills_component_all_mandatory_matched_is_100():
    matches = [_match("Python", "MANDATORY", "MATCH", "WORK"), _match("SQL", "MANDATORY", "MATCH", "WORK")]
    component = scoring_engine._skills_component(matches)
    assert component.score == 100.0
    assert component.insufficient_evidence is False


def test_skills_component_priority_weighted_calculation():
    matches = [
        _match("Python", "MANDATORY", "MATCH", "WORK"),  # weight 3, earned 3
        _match("AWS", "PREFERRED", "GAP"),  # weight 2, earned 0
        _match("Kubernetes", "NICE_TO_HAVE", "PARTIAL", "OTHER", origin="raw_text"),  # weight 1, earned 0.5
    ]
    component = scoring_engine._skills_component(matches)
    # (3*1 + 2*0 + 1*0.5) / (3+2+1) * 100 = 3.5/6*100 = 58.333...
    assert component.score == 58.3
    assert component.insufficient_evidence is False


def test_skills_component_no_requirements_is_insufficient_evidence():
    component = scoring_engine._skills_component([])
    assert component.score is None
    assert component.insufficient_evidence is True


# ---------------------------------------------------------------------------
# Evidence-backed components (experience / projects)
# ---------------------------------------------------------------------------


def test_experience_component_counts_work_and_internship_evidence():
    matches = [
        _match("Python", "MANDATORY", "MATCH", "WORK"),
        _match("FastAPI", "MANDATORY", "MATCH", "PROJECT"),
        _match("SQL", "MANDATORY", "MATCH", "INTERNSHIP"),
    ]
    component = scoring_engine._evidence_backed_component(matches, scoring_engine.EXPERIENCE_EVIDENCE_TYPES, "work/internship")
    # 2 of 3 covered matches (WORK + INTERNSHIP) count as experience-backed
    assert component.score == round(2 / 3 * 100, 1)
    assert component.insufficient_evidence is False


def test_projects_component_counts_project_evidence():
    matches = [
        _match("Python", "MANDATORY", "MATCH", "WORK"),
        _match("FastAPI", "MANDATORY", "MATCH", "PROJECT"),
        _match("SQL", "MANDATORY", "MATCH", "INTERNSHIP"),
    ]
    component = scoring_engine._evidence_backed_component(matches, scoring_engine.PROJECT_EVIDENCE_TYPES, "project")
    assert component.score == round(1 / 3 * 100, 1)
    assert component.insufficient_evidence is False


def test_evidence_backed_component_insufficient_when_all_untyped():
    # Simulates AI-unavailable fallback mode: matches exist (via raw_text)
    # but none carry a specific evidence_type classification.
    matches = [
        _match("Docker", "MANDATORY", "MATCH", "OTHER", origin="raw_text"),
        _match("SQL", "MANDATORY", "MATCH", "OTHER", origin="raw_text"),
    ]
    component = scoring_engine._evidence_backed_component(matches, scoring_engine.EXPERIENCE_EVIDENCE_TYPES, "work/internship")
    assert component.score is None
    assert component.insufficient_evidence is True


def test_evidence_backed_component_insufficient_when_nothing_matched():
    matches = [_match("Docker", "MANDATORY", "GAP")]
    component = scoring_engine._evidence_backed_component(matches, scoring_engine.EXPERIENCE_EVIDENCE_TYPES, "work/internship")
    assert component.score is None
    assert component.insufficient_evidence is True


# ---------------------------------------------------------------------------
# Certifications component
# ---------------------------------------------------------------------------


def test_certifications_component_not_required_is_full_score():
    jd = JDAnalysis(certifications=[])
    resume = ResumeAnalysis(certifications=[])
    component = scoring_engine._certifications_component(jd, resume)
    assert component.score == 100.0
    assert component.insufficient_evidence is False


def test_certifications_component_required_but_missing_is_zero():
    jd = JDAnalysis(certifications=["AWS Certified Developer"])
    resume = ResumeAnalysis(certifications=[])
    component = scoring_engine._certifications_component(jd, resume)
    assert component.score == 0.0


def test_certifications_component_partial_match_regardless_of_casing():
    jd = JDAnalysis(certifications=["AWS Certified Developer", "Scrum Master"])
    resume = ResumeAnalysis(certifications=[CertificationEntry(name="aws certified developer")])
    component = scoring_engine._certifications_component(jd, resume)
    assert component.score == 50.0


def test_certifications_component_insufficient_when_jd_analysis_failed():
    # An empty certifications list means "the JD doesn't ask for this"
    # ONLY when AI analysis actually ran. When it failed entirely, an
    # empty list just means nothing was ever extracted — it must not be
    # read as "vacuously satisfied" (100%), which is a different claim.
    jd = JDAnalysis(certifications=[], ai_used=False)
    resume = ResumeAnalysis(certifications=[])
    component = scoring_engine._certifications_component(jd, resume)
    assert component.score is None
    assert component.insufficient_evidence is True


# ---------------------------------------------------------------------------
# Education component
# ---------------------------------------------------------------------------


def test_education_component_not_required_is_full_score():
    jd = JDAnalysis(education_requirements=None)
    resume = ResumeAnalysis(education=[])
    component = scoring_engine._education_component(jd, resume)
    assert component.score == 100.0
    assert component.insufficient_evidence is False


def test_education_component_required_but_none_listed_is_zero():
    jd = JDAnalysis(education_requirements="Bachelor's degree in Computer Science")
    resume = ResumeAnalysis(education=[])
    component = scoring_engine._education_component(jd, resume)
    assert component.score == 0.0


def test_education_component_insufficient_when_jd_analysis_failed():
    jd = JDAnalysis(education_requirements=None, ai_used=False)
    resume = ResumeAnalysis(education=[])
    component = scoring_engine._education_component(jd, resume)
    assert component.score is None
    assert component.insufficient_evidence is True


def test_education_component_insufficient_when_semantic_model_unavailable(monkeypatch):
    monkeypatch.setattr(scoring_engine, "semantic_model_available", lambda: False)
    jd = JDAnalysis(education_requirements="Bachelor's degree in Computer Science")
    resume = ResumeAnalysis(education=[EducationEntry(degree="B.Tech", field_of_study="Computer Science")])
    component = scoring_engine._education_component(jd, resume)
    assert component.score is None
    assert component.insufficient_evidence is True


def test_education_component_uses_semantic_similarity_when_available(monkeypatch):
    import numpy as np

    monkeypatch.setattr(scoring_engine, "semantic_model_available", lambda: True)

    def fake_embed_texts(texts):
        vectors = {
            "Bachelor's degree in Computer Science": [1.0, 0.0],
            "B.Tech Computer Science": [0.8, 0.6],
        }
        return np.array([vectors[t] for t in texts])

    monkeypatch.setattr(scoring_engine, "embed_texts", fake_embed_texts)

    jd = JDAnalysis(education_requirements="Bachelor's degree in Computer Science")
    resume = ResumeAnalysis(education=[EducationEntry(degree="B.Tech", field_of_study="Computer Science")])
    component = scoring_engine._education_component(jd, resume)

    assert component.insufficient_evidence is False
    assert component.score == 80.0  # dot product of the two unit vectors above


# ---------------------------------------------------------------------------
# Full compute_score: overall renormalization + explainability
# ---------------------------------------------------------------------------


def test_compute_score_renormalizes_over_available_components(monkeypatch):
    monkeypatch.setattr(scoring_engine, "semantic_model_available", lambda: False)

    matches = [
        _match("Python", "MANDATORY", "MATCH", "OTHER", origin="raw_text"),  # skills=100, experience/projects insufficient
    ]
    jd = JDAnalysis(required_skills=["Python"], certifications=[], education_requirements=None)
    resume = ResumeAnalysis(certifications=[], education=[])

    breakdown = scoring_engine.compute_score(jd, resume, matches)

    assert breakdown.component_scores["skills"].score == 100.0
    assert breakdown.component_scores["experience"].insufficient_evidence is True
    assert breakdown.component_scores["projects"].insufficient_evidence is True
    assert breakdown.component_scores["certifications"].score == 100.0
    assert breakdown.component_scores["education"].score == 100.0

    # Only skills(0.35) + certifications(0.10) + education(0.10) had scores;
    # experience/projects were excluded and weights renormalized.
    used_weight = 0.35 + 0.10 + 0.10
    expected = round((100.0 * 0.35 + 100.0 * 0.10 + 100.0 * 0.10) / used_weight, 1)
    assert breakdown.overall_score == expected == 100.0


def test_compute_score_positive_partial_negative_factors_categorized(monkeypatch):
    monkeypatch.setattr(scoring_engine, "semantic_model_available", lambda: False)

    matches = [
        _match("Python", "MANDATORY", "MATCH", "WORK", reason="Resume lists Python."),
        _match("Docker", "PREFERRED", "PARTIAL", "OTHER", origin="raw_text", reason="Possibly related text found."),
        _match("Kubernetes", "NICE_TO_HAVE", "GAP", reason="No evidence found in the submitted resume."),
    ]
    jd = JDAnalysis(certifications=[], education_requirements=None)
    resume = ResumeAnalysis()

    breakdown = scoring_engine.compute_score(jd, resume, matches)

    assert len(breakdown.positive_factors) == 1
    assert "Python" in breakdown.positive_factors[0]
    assert len(breakdown.partial_factors) == 1
    assert "Docker" in breakdown.partial_factors[0]
    assert len(breakdown.negative_factors) == 1
    assert "Kubernetes" in breakdown.negative_factors[0]

    summary = breakdown.evidence_summary
    assert summary.total_requirements == 3
    assert summary.matched == 1
    assert summary.partial == 1
    assert summary.gaps == 1
    assert summary.mandatory_matched == 1
    assert summary.mandatory_total == 1
    assert summary.preferred_total == 1
    assert summary.nice_to_have_total == 1

    assert "not an official ats score" in breakdown.score_method.lower()


def test_compute_score_renormalizes_to_the_only_determinate_components():
    # No matches at all -> skills/experience/projects are all insufficient
    # evidence. Certifications is required-but-missing (a real 0.0, not
    # insufficient). Education is not required (a real 100.0).
    jd = JDAnalysis(certifications=["Scrum Master"], education_requirements=None)
    resume = ResumeAnalysis(certifications=[])

    breakdown = scoring_engine.compute_score(jd, resume, [])

    assert breakdown.component_scores["skills"].insufficient_evidence is True
    assert breakdown.component_scores["experience"].insufficient_evidence is True
    assert breakdown.component_scores["projects"].insufficient_evidence is True
    assert breakdown.component_scores["education"].score == 100.0
    assert breakdown.component_scores["certifications"].score == 0.0

    used_weight = 0.10 + 0.10  # only certifications + education contributed
    expected = round((0.0 * 0.10 + 100.0 * 0.10) / used_weight, 1)
    assert breakdown.overall_score == expected == 50.0


def test_compute_score_overall_is_none_when_jd_analysis_entirely_failed():
    # When JD structured analysis fails outright, every field on the
    # fallback JDAnalysis is empty (not because the JD genuinely requires
    # nothing, but because nothing was ever extracted) and there are zero
    # requirement matches. The overall score must reflect "we don't know"
    # (None), never a fabricated 100 from certifications/education wrongly
    # reading "empty" as "vacuously satisfied."
    jd = JDAnalysis(ai_used=False)
    resume = ResumeAnalysis()

    breakdown = scoring_engine.compute_score(jd, resume, [])

    assert breakdown.overall_score is None
    for component in breakdown.component_scores.values():
        assert component.score is None
        assert component.insufficient_evidence is True


def test_compute_score_overall_is_none_when_nothing_at_all_is_determinate(monkeypatch):
    # Force education to be insufficient too (required, but no semantic
    # model to verify it) and certifications to have nothing required to
    # check against... but certifications is only ever indeterminate when
    # required, so require one and leave it genuinely unresolved is not
    # possible by design — instead confirm the renormalization guard
    # itself: with zero weight used, overall_score must be None.
    monkeypatch.setattr(scoring_engine, "semantic_model_available", lambda: False)
    jd = JDAnalysis(certifications=[], education_requirements="Bachelor's degree")
    resume = ResumeAnalysis(certifications=[], education=[EducationEntry(degree="B.Tech")])

    breakdown = scoring_engine.compute_score(jd, resume, [])

    # certifications not required -> 100 (always determinate); everything
    # else insufficient. This demonstrates renormalization lands exactly on
    # the one scorable component rather than guessing at the rest.
    assert breakdown.overall_score == 100.0
    assert breakdown.component_scores["education"].insufficient_evidence is True
