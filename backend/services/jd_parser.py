"""Job description text extraction for TXT uploads and pasted text.

PDF and DOCX are intentionally NOT supported for job descriptions (only
for resumes) — job descriptions must be plain text (uploaded .txt or
pasted directly). Shares the underlying text extraction with
resume_parser.py via document_extraction.py, but uses a job-description
-specific section vocabulary (responsibilities, requirements, etc.
instead of resume sections like experience/education).
"""

from typing import Optional

from schemas import Block, ParsedJobDescription, SectionPosition
from services.document_extraction import extract_txt, match_section

SUPPORTED_EXTENSIONS = {"txt"}

JD_SECTION_KEYWORDS: dict[str, list[str]] = {
    "about": [
        "about the role",
        "about us",
        "about the company",
        "company overview",
        "job summary",
        "overview",
        "role overview",
    ],
    "responsibilities": [
        "responsibilities",
        "key responsibilities",
        "roles and responsibilities",
        "what you will do",
        "what you'll do",
        "duties",
    ],
    "requirements": [
        "requirements",
        "requirements and qualifications",
        "minimum qualifications",
        "qualifications",
        "required qualifications",
        "must have",
    ],
    "preferred": [
        "preferred qualifications",
        "preferred skills",
        "nice to have",
        "good to have",
        "bonus points",
        "bonus skills",
    ],
    "skills": ["skills", "technical skills", "required skills", "tools and technologies", "tools & technologies"],
    "benefits": ["benefits", "perks", "what we offer", "compensation", "compensation and benefits"],
    "education": ["education", "education requirements", "academic qualifications"],
    "experience": ["experience", "experience requirements", "years of experience"],
}


def _detect_sections(blocks: list[Block]) -> list[SectionPosition]:
    sections: list[SectionPosition] = []
    for block in blocks:
        matched = match_section(block.text, JD_SECTION_KEYWORDS)
        if matched:
            block.is_heading = True
            sections.append(SectionPosition(section=matched, page_number=block.page_number, text=block.text))
    return sections


def parse_job_description(
    *,
    content: Optional[bytes] = None,
    filename: Optional[str] = None,
    pasted_text: Optional[str] = None,
) -> ParsedJobDescription:
    if pasted_text is not None:
        return _parse_pasted(pasted_text)

    if content is None or filename is None:
        raise ValueError("Either a file or pasted text must be provided.")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: .{extension or 'unknown'}")

    blocks, warnings = extract_txt(content)
    text_lines = [block.text for block in blocks]

    sections = _detect_sections(blocks)
    normalized_text = "\n".join(text_lines)
    warnings = list(warnings)
    if not normalized_text.strip():
        warnings.append("No text could be extracted from this document.")

    return ParsedJobDescription(
        source="txt",
        normalized_text=normalized_text,
        page_count=None,
        blocks=blocks,
        tables=[],
        sections_detected=sections,
        warnings=warnings,
    )


def _parse_pasted(text: str) -> ParsedJobDescription:
    lines = [line.strip() for line in text.strip().splitlines()]
    lines = [line for line in lines if line]
    blocks = [Block(text=line, page_number=None, bbox=None, font_size=None, is_heading=False) for line in lines]

    sections = _detect_sections(blocks)
    normalized_text = "\n".join(lines)

    warnings: list[str] = []
    if not normalized_text:
        warnings.append("No text was provided.")

    return ParsedJobDescription(
        source="pasted",
        normalized_text=normalized_text,
        page_count=None,
        blocks=blocks,
        tables=[],
        sections_detected=sections,
        warnings=warnings,
    )
