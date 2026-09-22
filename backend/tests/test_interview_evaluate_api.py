"""Integration tests for POST /api/analysis/{id}/interview/evaluate."""

from fastapi.testclient import TestClient

import api.analysis as analysis_api
from main import app
from schemas import JDAnalysis, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def _run_analysis(monkeypatch) -> int:
    upload = client.post("/api/resume/upload", files={"file": ("resume.txt", b"Jane\nSkills\nPython", "text/plain")})
    resume_id = upload.json()["resume_id"]
    job = client.post("/api/jobs/create", json={"text": "Backend Developer\nRequirements\nPython"})
    job_id = job.json()["job_id"]

    monkeypatch.setattr(
        analysis_api,
        "analyze_resume",
        lambda text: ResumeAnalysis(
            skills=[SkillEvidence(skill="Python", evidence_text="Python", evidence_type="OTHER", confidence=0.6)]
        ),
    )
    monkeypatch.setattr(
        analysis_api, "analyze_job_description", lambda text: JDAnalysis(role_title="Backend Developer", required_skills=["Python"])
    )
    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})
    return response.json()["analysis_id"]


def test_evaluate_returns_404_for_unknown_analysis():
    response = client.post(
        "/api/analysis/999999/interview/evaluate",
        json={"question": "Q", "answer": "A"},
    )
    assert response.status_code == 404


def test_evaluate_rejects_empty_answer(monkeypatch):
    analysis_id = _run_analysis(monkeypatch)
    response = client.post(
        f"/api/analysis/{analysis_id}/interview/evaluate",
        json={"question": "Tell me about Python.", "answer": ""},
    )
    assert response.status_code == 422


def test_evaluate_happy_path_uses_fallback_without_ai(monkeypatch):
    analysis_id = _run_analysis(monkeypatch)

    response = client.post(
        f"/api/analysis/{analysis_id}/interview/evaluate",
        json={"question": "Tell me about your Python experience.", "based_on": "Python", "answer": "I used it a lot."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    evaluation = body["evaluation"]
    assert evaluation["ai_generated"] is False
    assert evaluation["warnings"]
    assert evaluation["improvements"]
