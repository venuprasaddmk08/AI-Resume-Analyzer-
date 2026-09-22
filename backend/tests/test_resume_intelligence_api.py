from fastapi.testclient import TestClient

import api.resume as resume_api
from main import app
from schemas import ExperienceEntry, ResumeAnalysis

client = TestClient(app)


def _upload_resume() -> int:
    response = client.post(
        "/api/resume/upload", files={"file": ("resume.txt", b"Jane Doe\nSkills\nPython", "text/plain")}
    )
    return response.json()["resume_id"]


def test_intelligence_returns_404_for_unknown_resume():
    response = client.get("/api/resume/999999/intelligence")
    assert response.status_code == 404


def test_intelligence_happy_path(monkeypatch):
    resume_id = _upload_resume()
    canned = ResumeAnalysis(experience=[ExperienceEntry(description="Responsible for the database.")])
    monkeypatch.setattr(resume_api, "analyze_resume", lambda text: canned)

    response = client.get(f"/api/resume/{resume_id}/intelligence")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["tone_seniority"]
    assert body["health"]["score"] is not None
    assert len(body["bullets"]) == 1
    assert body["bullets"][0]["source"] == "experience"


def test_rewrite_returns_404_for_unknown_resume():
    response = client.post("/api/resume/999999/bullets/rewrite", json={"bullet_text": "Worked on things."})
    assert response.status_code == 404


def test_rewrite_rejects_empty_bullet():
    resume_id = _upload_resume()
    response = client.post(f"/api/resume/{resume_id}/bullets/rewrite", json={"bullet_text": ""})
    assert response.status_code == 422


def test_rewrite_happy_path_fallback_without_ai():
    resume_id = _upload_resume()
    response = client.post(
        f"/api/resume/{resume_id}/bullets/rewrite", json={"bullet_text": "Worked on the backend systems."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["rewrite"]["original"] == "Worked on the backend systems."
    assert body["rewrite"]["ai_generated"] is False
