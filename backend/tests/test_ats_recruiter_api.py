from fastapi.testclient import TestClient

import api.analysis as analysis_api
from main import app
from schemas import JDAnalysis, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def _run_analysis(monkeypatch) -> int:
    upload = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", b"Jane Doe\njane@example.com\nSkills\nPython, SQL", "text/plain")},
    )
    resume_id = upload.json()["resume_id"]
    job = client.post("/api/jobs/create", json={"text": "Backend Developer\nRequirements\nPython, Docker"})
    job_id = job.json()["job_id"]

    monkeypatch.setattr(
        analysis_api,
        "analyze_resume",
        lambda text: ResumeAnalysis(
            skills=[SkillEvidence(skill="Python", evidence_text="Python", evidence_type="OTHER", confidence=0.6)]
        ),
    )
    monkeypatch.setattr(analysis_api, "analyze_job_description", lambda text: JDAnalysis(required_skills=["Python"]))

    import services.evidence_engine as evidence_engine

    monkeypatch.setattr(evidence_engine, "semantic_model_available", lambda: False)

    response = client.post("/api/analysis/run", json={"resume_id": resume_id, "job_id": job_id})
    return response.json()["analysis_id"]


def test_ats_returns_404_for_unknown_analysis():
    response = client.get("/api/analysis/999999/ats")
    assert response.status_code == 404


def test_ats_happy_path(monkeypatch):
    analysis_id = _run_analysis(monkeypatch)

    response = client.get(f"/api/analysis/{analysis_id}/ats")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert "python" in body["keyword_diff"]["shared_keywords"]
    assert "docker" in body["keyword_diff"]["jd_only_keywords"]
    assert body["six_second_scan"]["score"] is not None
    assert body["ats_preview"]["table_count"] == 0
