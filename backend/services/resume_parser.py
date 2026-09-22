"""Resume text/layout extraction for PDF, DOCX, and TXT.

No AI involved here — this only extracts what is literally present in the
uploaded file (text, positions, font sizes where available, and a heuristic
guess at section headings). Downstream AI analysis (Phase 4) builds on top
of this, not the other way around.
"""

from schemas import ParsedResume, SectionPosition
from services.document_extraction import extract_docx, extract_pdf, extract_txt, flatten_tables, match_section

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt"}

# Canonical section name -> exact heading phrases (lowercase, no trailing punctuation)
# that count as a match. Kept as exact matches (not substring) so ordinary
# sentences that happen to start with a keyword aren't misread as headings.
RESUME_SECTION_KEYWORDS: dict[str, list[str]] = {
    "summary": ["summary", "profile", "objective", "about me", "professional summary"],
    "experience": [
        "experience",
        "work experience",
        "employment history",
        "professional experience",
    ],
    "internships": ["internship", "internships"],
    "education": ["education", "academic background", "educational qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "key skills"],
    "projects": ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses & certifications"],
    "achievements": ["achievements", "awards", "honors", "honours"],
    "languages": ["languages"],
    "publications": ["publications"],
}


def parse_resume(content: bytes, filename: str) -> ParsedResume:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: .{extension or 'unknown'}")

    tables: list[list[list[str]]] = []

    if extension == "pdf":
        blocks, page_count, warnings = extract_pdf(content)
        text_lines = [block.text for block in blocks]
        empty_warning = "Text could not be extracted from this PDF."
    elif extension == "docx":
        blocks, tables, warnings = extract_docx(content)
        text_lines = [block.text for block in blocks] + flatten_tables(tables)
        page_count = None
        empty_warning = "No text could be extracted from this document."
    else:
        blocks, warnings = extract_txt(content)
        text_lines = [block.text for block in blocks]
        page_count = None
        empty_warning = "No text could be extracted from this document."

    sections: list[SectionPosition] = []
    for block in blocks:
        matched = match_section(block.text, RESUME_SECTION_KEYWORDS)
        if matched:
            block.is_heading = True
            sections.append(SectionPosition(section=matched, page_number=block.page_number, text=block.text))

    normalized_text = "\n".join(text_lines)
    warnings = list(warnings)
    if not normalized_text.strip():
        warnings.append(empty_warning)

    return ParsedResume(
        file_type=extension,
        normalized_text=normalized_text,
        page_count=page_count,
        blocks=blocks,
        tables=tables,
        sections_detected=sections,
        warnings=warnings,
    )
