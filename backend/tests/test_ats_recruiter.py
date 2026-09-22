from schemas import ContactInfo, ExperienceEntry, ResumeAnalysis, SkillEvidence
from services.ats_recruiter import build_ats_preview, compute_keyword_diff, compute_six_second_scan


def test_ats_preview_flags_tables():
    preview = build_ats_preview("some text", [], [[["a", "b"]]], [])
    assert preview.table_count == 1
    assert any("table" in w.lower() for w in preview.warnings)


def test_ats_preview_passes_through_section_headers():
    preview = build_ats_preview("text", [{"section": "Experience"}, {"section": "Education"}], [], [])
    assert preview.section_headers_detected == ["Experience", "Education"]


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
