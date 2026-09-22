import pytest

from services.jd_parser import parse_job_description


def test_parse_jd_pdf_is_rejected():
    # Job descriptions must be plain text only — PDF is not allowed, even
    # if the content would otherwise be a well-formed PDF.
    with pytest.raises(ValueError):
        parse_job_description(content=b"%PDF-1.4 not actually parsed", filename="jd.pdf")


def test_parse_jd_docx_is_rejected():
    # Job descriptions must be plain text only — DOCX is not allowed, even
    # if the content would otherwise be a well-formed DOCX.
    with pytest.raises(ValueError):
        parse_job_description(content=b"PK not actually parsed", filename="jd.docx")


def test_parse_jd_txt_extracts_text_and_sections():
    content = b"Backend Developer\nRequirements\nPython, SQL, FastAPI\nBenefits\nRemote work"

    result = parse_job_description(content=content, filename="jd.txt")

    assert result.source == "txt"
    assert "Python, SQL, FastAPI" in result.normalized_text
    section_names = {s.section for s in result.sections_detected}
    assert "requirements" in section_names
    assert "benefits" in section_names


def test_parse_jd_pasted_text_extracts_sections():
    text = "Backend Developer\nResponsibilities\nDesign REST APIs\nRequirements\nPython and SQL required"

    result = parse_job_description(pasted_text=text)

    assert result.source == "pasted"
    assert "Design REST APIs" in result.normalized_text
    section_names = {s.section for s in result.sections_detected}
    assert "responsibilities" in section_names
    assert "requirements" in section_names


def test_parse_jd_pasted_empty_text_warns():
    result = parse_job_description(pasted_text="   \n\n  ")

    assert result.normalized_text == ""
    assert "No text was provided." in result.warnings


def test_parse_jd_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        parse_job_description(content=b"hello", filename="jd.exe")


def test_parse_jd_requires_file_or_pasted_text():
    with pytest.raises(ValueError):
        parse_job_description()
