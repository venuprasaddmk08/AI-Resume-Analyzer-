"""Integration tests for the /api/analysis/* endpoints. Mocks the
analyzer functions and the evidence engine's AI/semantic dependencies so
no live network calls happen here."""

from fastapi.testclient import TestClient

import api.analysis as analysis_api
from main import app
from schemas import JDAnalysis, RequirementMatch, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def _upload_resume(text: bytes = b"Jane Doe\nSkills\nPython, SQL") -> int:
    response = client.post("/api/resume/upload", files={"file": ("resume.txt", text, "text/plain")})
    return response.json()["resume_id"]


def _create_job(text: str = "Backend Developer\nRequirements\nPython, SQL") -> int:
    response = client.post("/api/jobs/create", json={"text": text})
    return response.json()["job_id"]


def test_run_returns_404_for_unknown_resume():
    job_id = _create_job()
    response = client.post("/api/analysis/run", json={"resume_id": 999999, "job_id": job_id})
    assert response.status_code == 404


def test_run_returns_404_for_unknown_job():
    resume_id = _upload_resume()
    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": 999999})
    assert response.status_code == 404


def test_run_analyzes_and_matches(monkeypatch):
    resume_id = _upload_resume()
    job_id = _create_job()

    monkeypatch.setattr(
        analysis_api,
        "analyze_resume",
        lambda text: ResumeAnalysis(
            skills=[
                SkillEvidence(skill="Python", evidence_text="Python, SQL", evidence_type="OTHER", confidence=0.6)
            ]
        ),
    )
    monkeypatch.setattr(
        analysis_api,
        "analyze_job_description",
        lambda text: JDAnalysis(required_skills=["Python"], preferred_skills=["AWS"]),
    )
    # Keep semantic matching out of this test — it's covered separately.
    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["job_id"] == job_id
    assert len(body["matches"]) == 2

    python_match = next(m for m in body["matches"] if m["requirement"] == "Python")
    assert python_match["status"] == "MATCH"
    assert python_match["priority"] == "MANDATORY"

    aws_match = next(m for m in body["matches"] if m["requirement"] == "AWS")
    assert aws_match["status"] == "GAP"
    assert aws_match["priority"] == "PREFERRED"
    assert aws_match["evidence"] == []

    analysis_id = body["analysis_id"]

    get_response = client.get(f"/api/analysis/{analysis_id}")
    assert get_response.status_code == 200
    assert get_response.json()["analysis_id"] == analysis_id

    skills_response = client.get(f"/api/analysis/{analysis_id}/skills")
    assert skills_response.status_code == 200
    skills_body = skills_response.json()
    assert len(skills_body["matching"]) == 1
    assert len(skills_body["gaps"]) == 1
    assert skills_body["partial"] == []

    evidence_response = client.get(f"/api/analysis/{analysis_id}/evidence")
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()["evidence_graph"]) == 2

    score_response = client.get(f"/api/analysis/{analysis_id}/score")
    assert score_response.status_code == 200
    score_body = score_response.json()["score"]
    assert score_body["overall_score"] is not None
    assert score_body["component_scores"]["skills"]["score"] is not None
    assert "not an official ATS score" in score_body["score_method"]

    # The full analysis response also carries the score inline.
    assert body["score"]["overall_score"] == score_body["overall_score"]


def test_score_endpoint_returns_404_for_unknown_analysis():
    response = client.get("/api/analysis/999999/score")
    assert response.status_code == 404


def test_get_analysis_returns_404_for_unknown_id():
    response = client.get("/api/analysis/999999")
    assert response.status_code == 404


def test_run_analyzes_resume_and_job_sequentially_when_both_uncached(monkeypatch):
    """The resume and JD AI structured-analysis calls used to run
    concurrently, but low-RPM free-tier providers (e.g. Gemini) reliably
    429/503 the second concurrent call, so they now run one after the
    other. Asserts the job call only starts after the resume call has
    fully returned."""
    call_order = []

    def sequential_analyze_resume(text):
        call_order.append("resume_start")
        call_order.append("resume_end")
        return ResumeAnalysis(skills=[])

    def sequential_analyze_job(text):
        call_order.append("job_start")
        call_order.append("job_end")
        return JDAnalysis(required_skills=["Python"])

    resume_id = _upload_resume()
    job_id = _create_job()

    monkeypatch.setattr(analysis_api, "analyze_resume", sequential_analyze_resume)
    monkeypatch.setattr(analysis_api, "analyze_job_description", sequential_analyze_job)

    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})

    assert response.status_code == 200
    assert call_order == ["resume_start", "resume_end", "job_start", "job_end"]


def test_run_calls_evidence_engine_with_ai_refinement_disabled(monkeypatch):
    """The /run endpoint must return a fast baseline: it should never pay for
    the per-PARTIAL-match AI adjudication call inside the request that the
    frontend's loading screen is waiting on."""
    resume_id = _upload_resume()
    job_id = _create_job()

    monkeypatch.setattr(analysis_api, "analyze_resume", lambda text: ResumeAnalysis(skills=[]))
    monkeypatch.setattr(analysis_api, "analyze_job_description", lambda text: JDAnalysis(required_skills=["Python"]))

    captured = {}
    real_build_requirement_matches = analysis_api.build_requirement_matches

    def _capturing_build_requirement_matches(*args, **kwargs):
        captured["use_ai_refinement"] = kwargs.get("use_ai_refinement")
        return real_build_requirement_matches(*args, **kwargs)

    monkeypatch.setattr(analysis_api, "build_requirement_matches", _capturing_build_requirement_matches)

    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})

    assert response.status_code == 200
    assert captured["use_ai_refinement"] is False


def test_refine_endpoint_calls_evidence_engine_with_ai_refinement_enabled_and_persists(monkeypatch):
    resume_id = _upload_resume()
    job_id = _create_job()

    monkeypatch.setattr(analysis_api, "analyze_resume", lambda text: ResumeAnalysis(skills=[]))
    monkeypatch.setattr(analysis_api, "analyze_job_description", lambda text: JDAnalysis(required_skills=["Python"]))

    run_response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})
    analysis_id = run_response.json()["analysis_id"]

    captured = {}
    real_build_requirement_matches = analysis_api.build_requirement_matches

    def _capturing_build_requirement_matches(*args, **kwargs):
        captured["use_ai_refinement"] = kwargs.get("use_ai_refinement")
        return [
            RequirementMatch(
                requirement="Python",
                canonical_skill="python",
                priority="MANDATORY",
                status="MATCH",
                evidence=[],
                confidence=0.8,
                reason="AI confirmed it.",
                signal="ai_reasoning",
            )
        ], True, True

    monkeypatch.setattr(analysis_api, "build_requirement_matches", _capturing_build_requirement_matches)

    refine_response = client.post(f"/api/analysis/{analysis_id}/refine")

    assert refine_response.status_code == 200
    assert captured["use_ai_refinement"] is True
    refined_body = refine_response.json()
    assert refined_body["ai_refinement_used"] is True
    refined_match = next(m for m in refined_body["matches"] if m["requirement"] == "Python")
    assert refined_match["status"] == "MATCH"
    assert refined_match["signal"] == "ai_reasoning"

    # The refined result is persisted, not just returned once.
    get_response = client.get(f"/api/analysis/{analysis_id}")
    assert get_response.json()["matches"] == refined_body["matches"]


def test_refine_returns_404_for_unknown_analysis():
    response = client.post("/api/analysis/999999/refine")
    assert response.status_code == 404


def test_run_does_not_cache_a_failed_ai_fallback(monkeypatch):
    """A resume/JD analysis that fell back to the deterministic result
    (ai_used=False, e.g. after a transient provider outage) must not be
    permanently cached - otherwise one bad request would lock that
    resume/job into "AI unavailable" forever, even once the provider
    recovers. The next /run call should retry AI from scratch."""
    resume_id = _upload_resume()
    job_id = _create_job()

    call_count = {"n": 0}

    def flaky_then_ok_analyze_resume(text):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ResumeAnalysis(skills=[], ai_used=False, warnings=["AI unavailable"])
        return ResumeAnalysis(skills=[], ai_used=True)

    monkeypatch.setattr(analysis_api, "analyze_resume", flaky_then_ok_analyze_resume)
    monkeypatch.setattr(analysis_api, "analyze_job_description", lambda text: JDAnalysis(required_skills=[]))

    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})
    client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})

    assert call_count["n"] == 2


def test_run_reuses_existing_analysis_instead_of_recomputing(monkeypatch):
    resume_id = _upload_resume()
    job_id = _create_job()

    call_count = {"n": 0}

    def counting_analyze_resume(text):
        call_count["n"] += 1
        return ResumeAnalysis(skills=[])

    monkeypatch.setattr(analysis_api, "analyze_resume", counting_analyze_resume)
    monkeypatch.setattr(analysis_api, "analyze_job_description", lambda text: JDAnalysis(required_skills=[]))

    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})
    client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})

    assert call_count["n"] == 1
