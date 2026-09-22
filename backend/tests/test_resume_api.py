from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_upload_txt_resume_succeeds():
    file_content = b"Jane Doe\nSkills\nPython, SQL, FastAPI\nEducation\nB.Tech in CS"
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", file_content, "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "resume.txt"
    assert body["resume_id"] > 0
    assert body["parsed"]["file_type"] == "txt"
    assert "Python, SQL, FastAPI" in body["parsed"]["normalized_text"]


def test_upload_rejects_unsupported_extension():
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.exe", b"not a resume", "application/octet-stream")},
    )

    assert response.status_code == 400


def test_upload_rejects_empty_file():
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.txt", b"", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_rejects_malformed_pdf():
    response = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", b"not a real pdf", "application/pdf")},
    )

    assert response.status_code == 422


def test_upload_sanitizes_unsafe_filename():
    response = client.post(
        "/api/resume/upload",
        files={"file": ("../../etc/passwd.txt", b"Jane Doe\nSkills\nPython", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert "/" not in body["filename"]
    assert ".." not in body["filename"]
