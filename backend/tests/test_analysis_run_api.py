"""Integration tests for the /api/analysis/* endpoints. Mocks the
analyzer functions and the evidence engine's AI/semantic dependencies so
no live network calls happen here."""

from fastapi.testclient import TestClient

import api.analysis as analysis_api
from main import app
from schemas import JDAnalysis, ResumeAnalysis, SkillEvidence

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


def test_get_analysis_returns_404_for_unknown_id():
    response = client.get("/api/analysis/999999")
    assert response.status_code == 404


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
