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


def test_upload_rejects_pdf():
    # Job descriptions must be plain text only — PDF is rejected outright,
    # before any parsing is attempted (even a well-formed PDF must fail).
    response = client.post(
        "/api/jobs/upload",
        files={"file": ("jd.pdf", b"%PDF-1.4 well-formed-looking header", "application/pdf")},
    )

    assert response.status_code == 400
    assert "plain text" in response.json()["detail"].lower()


def test_upload_rejects_docx():
    # Job descriptions must be plain text only — DOC/DOCX is rejected
    # outright, before any parsing is attempted.
    response = client.post(
        "/api/jobs/upload",
        files={
            "file": (
                "jd.docx",
                b"PK well-formed-looking docx header",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert "plain text" in response.json()["detail"].lower()


def test_upload_rejects_doc():
    # Legacy .doc must also be rejected — it was never in SUPPORTED_EXTENSIONS.
    response = client.post(
        "/api/jobs/upload",
        files={"file": ("jd.doc", b"legacy doc content", "application/msword")},
    )

    assert response.status_code == 400
    assert "plain text" in response.json()["detail"].lower()


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
