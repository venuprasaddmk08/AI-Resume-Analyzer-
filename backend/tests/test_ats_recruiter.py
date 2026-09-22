from schemas import ContactInfo, ExperienceEntry, ResumeAnalysis, SkillEvidence
from services.ats_recruiter import build_ats_preview, compute_keyword_diff, compute_six_second_scan


def test_ats_preview_flags_tables():
    preview = build_ats_preview("some text", [], [[["a", "b"]]], [])
    assert preview.table_count == 1
    assert any("table" in w.lower() for w in preview.warnings)


def test_ats_preview_passes_through_section_headers():
    preview = build_ats_preview("text", [{"section": "Experience"}, {"section": "Education"}], [], [])
    assert preview.section_headers_detected == ["Experience", "Education"]


def _block(text, page=1, x0=50.0, y0=100.0, is_heading=False):
    return {"text": text, "page_number": page, "bbox": [x0, y0, x0 + 100, y0 + 12], "font_size": 10.0, "is_heading": is_heading}


def test_ats_preview_no_layout_warnings_for_normal_single_column():
    blocks = [_block(f"line {i}", y0=100.0 + i * 20) for i in range(6)]
    preview = build_ats_preview("normal resume text", [], [], [], blocks)
    assert not any("reading-order" in w.lower() or "multi-column" in w.lower() for w in preview.warnings)


def test_ats_preview_flags_backward_reading_order():
    # Simulates a column that got flattened out of order: y0 repeatedly
    # jumps back up the page mid-stream.
    blocks = []
    y = 100.0
    for i in range(10):
        blocks.append(_block(f"line {i}", y0=y))
        y = y - 40.0 if i % 2 == 0 else y + 60.0
    preview = build_ats_preview("text", [], [], [], blocks)
    assert any("reading-order" in w.lower() for w in preview.warnings)


def test_ats_preview_flags_multi_column_layout():
    left_column = [_block(f"left {i}", x0=50.0, y0=100.0 + i * 20) for i in range(4)]
    right_column = [_block(f"right {i}", x0=320.0, y0=100.0 + i * 20) for i in range(4)]
    blocks = left_column + right_column
    preview = build_ats_preview("text", [], [], [], blocks)
    assert any("multi-column" in w.lower() for w in preview.warnings)


def test_ats_preview_flags_garbled_content():
    garbled_text = "Resume text\x01\x02\x03\x04\x05\x06" * 5
    preview = build_ats_preview(garbled_text, [], [], [])
    assert any("garbled" in w.lower() for w in preview.warnings)


def test_ats_preview_flags_empty_section():
    blocks = [
        _block("Experience", is_heading=True, y0=100.0),
        _block("Education", is_heading=True, y0=120.0),
        _block("State University", is_heading=False, y0=140.0),
    ]
    preview = build_ats_preview("text", [], [], [], blocks)
    assert any("empty section" in w.lower() and "Experience" in w for w in preview.warnings)


def test_ats_preview_no_layout_warnings_without_enough_positioned_blocks():
    # DOCX/TXT resumes never populate bbox — should never trigger layout
    # heuristics that only make sense for PDFs.
    blocks = [{"text": "line", "page_number": None, "bbox": None, "font_size": None, "is_heading": False}]
    preview = build_ats_preview("text", [], [], [], blocks)
    assert not any("reading-order" in w.lower() or "multi-column" in w.lower() for w in preview.warnings)


def test_keyword_diff_finds_shared_and_unique_terms():
    jd_text = "We need Python and Kubernetes experience for this backend role."
    resume_text = "I have strong Python skills and built REST APIs."
    diff = compute_keyword_diff(jd_text, resume_text)
    assert "python" in diff.shared_keywords
    assert "kubernetes" in diff.jd_only_keywords
    assert "apis" in diff.resume_only_keywords or "rest" in diff.resume_only_keywords


def test_six_second_scan_passes_healthy_resume():
    resume = ResumeAnalysis(
        contact=ContactInfo(email="jane@example.com"),
        skills=[SkillEvidence(skill="Python", evidence_text="Python", evidence_type="OTHER")],
        experience=[ExperienceEntry(title="Engineer", description="Built things.")],
    )
    text = "jane@example.com\n" + ("word " * 300)
    scan = compute_six_second_scan(resume, text)
    assert scan.score > 0
    contact_check = next(c for c in scan.checks if c.label == "Contact info near the top")
    assert contact_check.passed is True


def test_six_second_scan_flags_missing_signals():
    scan = compute_six_second_scan(ResumeAnalysis(), "short resume")
    failed_labels = {c.label for c in scan.checks if not c.passed}
    assert "Contact info near the top" in failed_labels
    assert "Skills clearly listed" in failed_labels
