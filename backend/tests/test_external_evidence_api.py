from fastapi.testclient import TestClient

import api.resume as resume_api
from main import app
from schemas import ContactInfo, ExperienceEntry, ResumeAnalysis, SkillEvidence

client = TestClient(app)


def _upload_resume() -> int:
    response = client.post(
        "/api/resume/upload", files={"file": ("resume.txt", b"Jane Doe\nSkills\nPython", "text/plain")}
    )
    return response.json()["resume_id"]


def test_external_evidence_returns_404_for_unknown_resume():
    response = client.get("/api/resume/999999/external-evidence")
    assert response.status_code == 404


def test_external_evidence_happy_path_no_github_url(monkeypatch):
    resume_id = _upload_resume()
    canned = ResumeAnalysis(
        contact=ContactInfo(),
        skills=[SkillEvidence(skill="Python", evidence_text="Python", evidence_type="OTHER", confidence=0.6)],
    )
    monkeypatch.setattr(resume_api, "analyze_resume", lambda text: canned)

    response = client.get(f"/api/resume/{resume_id}/external-evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["github"]["profile_found"] is False
    assert body["fairness"]["flagged_terms"] == []


def test_linkedin_consistency_returns_404_for_unknown_resume():
    response = client.post("/api/resume/999999/linkedin-consistency", json={"linkedin_text": "some text"})
    assert response.status_code == 404


def test_linkedin_consistency_rejects_empty_text():
    resume_id = _upload_resume()
    response = client.post(f"/api/resume/{resume_id}/linkedin-consistency", json={"linkedin_text": ""})
    assert response.status_code == 422


def test_linkedin_consistency_happy_path_fallback(monkeypatch):
    resume_id = _upload_resume()
    canned = ResumeAnalysis(experience=[ExperienceEntry(organization="Acme")])
    monkeypatch.setattr(resume_api, "analyze_resume", lambda text: canned)

    response = client.post(
        f"/api/resume/{resume_id}/linkedin-consistency", json={"linkedin_text": "Worked at Acme for 2 years."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["result"]["ai_generated"] is False
