"""Integration tests for GET /api/analysis/{id}/insights. Mocks the
analyzer functions and the AI client so no live network calls happen here."""

from fastapi.testclient import TestClient

import api.analysis as analysis_api
from main import app
from schemas import JDAnalysis, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def _upload_resume(text: bytes = b"Jane Doe\nSkills\nPython, SQL") -> int:
    response = client.post("/api/resume/upload", files={"file": ("resume.txt", text, "text/plain")})
    return response.json()["resume_id"]


def _create_job(text: str = "Backend Developer\nRequirements\nPython, SQL, Docker") -> int:
    response = client.post("/api/jobs/create", json={"text": text})
    return response.json()["job_id"]


def _run_analysis(monkeypatch) -> int:
    resume_id = _upload_resume()
    job_id = _create_job()

    monkeypatch.setattr(
        analysis_api,
        "analyze_resume",
        lambda text: ResumeAnalysis(
            skills=[SkillEvidence(skill="Python", evidence_text="Python, SQL", evidence_type="OTHER", confidence=0.6)]
        ),
    )
    monkeypatch.setattr(
        analysis_api,
        "analyze_job_description",
        lambda text: JDAnalysis(role_title="Backend Developer", required_skills=["Python", "Docker"]),
    )
    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})
    assert response.status_code == 200
    body = response.json()
    assert body["role_title"] == "Backend Developer"
    return body["analysis_id"]


def test_insights_returns_404_for_unknown_analysis():
    response = client.get("/api/analysis/999999/insights")
    assert response.status_code == 404


def test_insights_falls_back_without_ai(monkeypatch):
    analysis_id = _run_analysis(monkeypatch)

    response = client.get(f"/api/analysis/{analysis_id}/insights")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    insights = body["insights"]
    assert insights["ai_generated"] is False
    assert insights["warnings"]
    gap_skills = {step["skill"] for step in insights["learning_roadmap"]}
    assert "Docker" in gap_skills


def test_insights_are_cached_after_first_call(monkeypatch):
    analysis_id = _run_analysis(monkeypatch)

    call_count = {"n": 0}
    import services.insights_engine as insights_engine_module

    original = insights_engine_module.generate_career_insights

    def counting_generate(matches, jd_analysis):
        call_count["n"] += 1
        return original(matches, jd_analysis)

    monkeypatch.setattr(analysis_api, "generate_career_insights", counting_generate)

    first = client.get(f"/api/analysis/{analysis_id}/insights")
    second = client.get(f"/api/analysis/{analysis_id}/insights")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert call_count["n"] == 1
