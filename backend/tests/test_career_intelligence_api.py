from fastapi.testclient import TestClient

import api.resume as resume_api
from main import app
from schemas import ExperienceEntry, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def _upload_resume() -> int:
    response = client.post(
        "/api/resume/upload", files={"file": ("resume.txt", b"Jane Doe\nSkills\nPython, SQL", "text/plain")}
    )
    return response.json()["resume_id"]


def test_career_intelligence_returns_404_for_unknown_resume():
    response = client.get("/api/resume/999999/career-intelligence")
    assert response.status_code == 404


def test_career_intelligence_happy_path(monkeypatch):
    resume_id = _upload_resume()

    canned = ResumeAnalysis(
        skills=[SkillEvidence(skill="Python", evidence_text="Python, SQL", evidence_type="OTHER", confidence=0.6)],
        experience=[ExperienceEntry(title="Backend Intern", organization="Acme", start_date="2024")],
    )
    monkeypatch.setattr(resume_api, "analyze_resume", lambda text: canned)

    response = client.get(f"/api/resume/{resume_id}/career-intelligence")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert len(body["role_fit"]) >= 6
    assert body["career_trajectory"][0]["title"] == "Backend Intern"
    assert body["warnings"] == []


def test_career_intelligence_reuses_cached_analysis(monkeypatch):
    resume_id = _upload_resume()

    call_count = {"n": 0}

    def counting_analyze(text):
        call_count["n"] += 1
        return ResumeAnalysis(skills=[])

    monkeypatch.setattr(resume_api, "analyze_resume", counting_analyze)

    client.get(f"/api/resume/{resume_id}/career-intelligence")
    client.get(f"/api/resume/{resume_id}/career-intelligence")

    assert call_count["n"] == 1
