"""Integration tests for the /analyze endpoints. Mocks the analyzer
functions at the API layer so no live AI calls happen here."""

from fastapi.testclient import TestClient

import api.jobs as jobs_api
import api.resume as resume_api
from main import app
from schemas import JDAnalysis, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def test_resume_analyze_returns_404_for_unknown_id():
    response = client.post("/api/resume/analyze", json={"resume_id": 999999})
    assert response.status_code == 404


def test_resume_analyze_happy_path(monkeypatch):
    upload = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", b"Jane Doe\nSkills\nPython, SQL", "text/plain")},
    )
    resume_id = upload.json()["resume_id"]

    canned = ResumeAnalysis(
        candidate_name="Jane Doe",
        skills=[
            SkillEvidence(
                skill="Python",
                evidence_text="Python, SQL",
                evidence_type="OTHER",
                confidence=0.6,
            )
        ],
    )
    monkeypatch.setattr(resume_api, "analyze_resume", lambda text: canned)

    response = client.post("/api/resume/analyze", json={"resume_id": resume_id})

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["analysis"]["candidate_name"] == "Jane Doe"
    assert body["analysis"]["skills"][0]["skill"] == "Python"


def test_job_analyze_returns_404_for_unknown_id():
    response = client.post("/api/jobs/analyze", json={"job_id": 999999})
    assert response.status_code == 404


def test_job_analyze_happy_path(monkeypatch):
    upload = client.post(
        "/api/jobs/create",
        json={"text": "Backend Developer\nRequirements\nPython, SQL"},
    )
    job_id = upload.json()["job_id"]

    canned = JDAnalysis(role_title="Backend Developer", required_skills=["Python", "SQL"])
    monkeypatch.setattr(jobs_api, "analyze_job_description", lambda text: canned)

    response = client.post("/api/jobs/analyze", json={"job_id": job_id})

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["analysis"]["role_title"] == "Backend Developer"
    assert "Python" in body["analysis"]["required_skills"]
