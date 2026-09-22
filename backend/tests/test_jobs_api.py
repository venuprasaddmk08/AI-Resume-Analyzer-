from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_upload_txt_job_description_succeeds():
    file_content = b"Backend Developer\nRequirements\nPython, SQL, FastAPI\nBenefits\nRemote work"
    response = client.post(
        "/api/jobs/upload",
        files={"file": ("jd.txt", file_content, "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "jd.txt"
    assert body["job_id"] > 0
    assert body["parsed"]["source"] == "txt"
    assert "Python, SQL, FastAPI" in body["parsed"]["normalized_text"]


def test_upload_rejects_unsupported_extension():
    response = client.post(
        "/api/jobs/upload",
        files={"file": ("jd.exe", b"not a jd", "application/octet-stream")},
    )

    assert response.status_code == 400


def test_upload_rejects_empty_file():
    response = client.post(
        "/api/jobs/upload",
        files={"file": ("jd.txt", b"", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_rejects_malformed_pdf():
    response = client.post(
        "/api/jobs/upload",
        files={"file": ("jd.pdf", b"not a real pdf", "application/pdf")},
    )

    assert response.status_code == 422


def test_create_job_description_from_pasted_text():
    response = client.post(
        "/api/jobs/create",
        json={"text": "Backend Developer\nResponsibilities\nDesign REST APIs\nRequirements\nPython and SQL required"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] is None
    assert body["parsed"]["source"] == "pasted"
    section_names = {s["section"] for s in body["parsed"]["sections_detected"]}
    assert "responsibilities" in section_names
    assert "requirements" in section_names


def test_create_job_description_rejects_empty_text():
    response = client.post("/api/jobs/create", json={"text": "   "})

    assert response.status_code == 400
