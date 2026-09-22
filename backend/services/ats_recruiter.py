"""ATS-style parsing preview, a JD/resume keyword diff, and a heuristic
'6-second recruiter scan' (Phase 12). Everything here is deterministic —
no AI call — since these are meant to be fast, always-available checks
a recruiter could sanity-check by eye.
"""

import re

from schemas import AtsParsingPreview, KeywordDiff, ResumeAnalysis, ScanCheck, SixSecondScan
from services.resume_intelligence import collect_bullets

_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{2,}")

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "are", "was", "were", "this", "that", "have",
    "has", "had", "will", "from", "our", "their", "they", "them", "who", "what", "when", "where",
    "how", "why", "not", "but", "can", "all", "any", "each", "more", "most", "other", "some",
    "such", "only", "than", "too", "very", "into", "out", "over", "under", "again", "also",
    "about", "above", "after", "before", "between", "during", "through", "within", "without",
    "role", "job", "work", "team", "years", "year", "experience", "including", "etc", "use",
    "using", "used", "able", "strong", "good", "well",
}

_TOP_N_KEYWORDS = 40
_MAX_DIFF_ITEMS = 25

_GARBLED_CHARS_RE = re.compile(r"[�\x00-\x08\x0b\x0c\x0e-\x1f]")
_GARBLED_RATIO_THRESHOLD = 0.02

_COLUMN_BUCKET_WIDTH = 60.0
_Y_BACKWARD_TOLERANCE = 5.0
_BACKWARD_JUMP_RATIO_THRESHOLD = 0.15
_MIN_COLUMN_BLOCKS = 3
_MIN_POSITIONED_BLOCKS = 4


def _keywords(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in _WORD_RE.finditer(text.lower()):
        word = match.group(0)
        if word in _STOPWORDS or word.isdigit():
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def _top_words(counts: dict[str, int], n: int) -> set[str]:
    return {w for w, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]}


def build_ats_preview(
    normalized_text: str,
    sections: list[dict],
    tables: list,
    parse_warnings: list[str],
    blocks: list[dict] | None = None,
) -> AtsParsingPreview:
    headers = [s.get("section") for s in sections if s.get("section")]
    warnings = list(parse_warnings)
    if tables:
        warnings.append(
            f"This resume has {len(tables)} table(s) — many ATS parsers read tables poorly or "
            "out of order. Consider using plain text/bullets instead if possible."
        )

    blocks = blocks or []
    warnings.extend(_detect_layout_warnings(blocks))
    warnings.extend(_detect_garbled_content(normalized_text))
    warnings.extend(_detect_empty_sections(blocks))

    return AtsParsingPreview(
        normalized_text=normalized_text,
        section_headers_detected=headers,
        table_count=len(tables),
        warnings=warnings,
    )


def _detect_layout_warnings(blocks: list[dict]) -> list[str]:
    """Uses the bbox/page_number metadata already extracted from the PDF
    to flag things a real ATS parser would likely stumble on — reading
    order that jumps backward on the page, or a probable multi-column
    layout. Only runs when there's enough positioned block data (PDFs
    only; DOCX/TXT never populate bbox, so this is a no-op for them)."""
    positioned = [b for b in blocks if b.get("bbox") and b.get("page_number") is not None]
    if len(positioned) < _MIN_POSITIONED_BLOCKS:
        return []

    warnings = []

    backward_jumps = 0
    same_page_pairs = 0
    for prev, curr in zip(positioned, positioned[1:]):
        if prev["page_number"] != curr["page_number"]:
            continue
        same_page_pairs += 1
        if curr["bbox"][1] < prev["bbox"][1] - _Y_BACKWARD_TOLERANCE:
            backward_jumps += 1
    if same_page_pairs > 0 and (backward_jumps / same_page_pairs) > _BACKWARD_JUMP_RATIO_THRESHOLD:
        warnings.append(
            f"Possible reading-order issue: the extracted text jumps backward up the page in "
            f"{backward_jumps} of {same_page_pairs} places — often caused by a multi-column layout "
            "that an ATS parser may read out of visual order."
        )

    buckets: dict[int, list[dict]] = {}
    for b in positioned:
        bucket = round(b["bbox"][0] / _COLUMN_BUCKET_WIDTH)
        buckets.setdefault(bucket, []).append(b)
    wide_buckets = sorted(k for k, v in buckets.items() if len(v) >= _MIN_COLUMN_BLOCKS)
    if len(wide_buckets) >= 2 and wide_buckets[-1] - wide_buckets[0] >= 2:
        warnings.append(
            "Possible multi-column layout detected — text starts at multiple distinct horizontal "
            "positions on the page. Many ATS parsers read columns out of visual order."
        )

    return warnings


def _detect_garbled_content(normalized_text: str) -> list[str]:
    if not normalized_text:
        return []
    ratio = len(_GARBLED_CHARS_RE.findall(normalized_text)) / len(normalized_text)
    if ratio > _GARBLED_RATIO_THRESHOLD:
        return [
            "Possible garbled content: unusual control characters were found in the extracted text — "
            "this can happen with unusual fonts, text embedded as images, or a corrupted file."
        ]
    return []


def _detect_empty_sections(blocks: list[dict]) -> list[str]:
    warnings = []
    for i, block in enumerate(blocks):
        if not block.get("is_heading"):
            continue
        next_block = blocks[i + 1] if i + 1 < len(blocks) else None
        if next_block is not None and next_block.get("is_heading"):
            heading_text = (block.get("text") or "").strip()
            warnings.append(
                f'Possible empty section: "{heading_text}" appears to have no body text before the next heading.'
            )
    return warnings


def compute_keyword_diff(jd_text: str, resume_text: str) -> KeywordDiff:
    jd_counts = _keywords(jd_text)
    resume_counts = _keywords(resume_text)
    jd_top = _top_words(jd_counts, _TOP_N_KEYWORDS)
    resume_top = _top_words(resume_counts, _TOP_N_KEYWORDS)

    shared = jd_top & resume_top
    jd_only = jd_top - resume_top
    resume_only = resume_top - jd_top

    return KeywordDiff(
        shared_keywords=sorted(shared)[:_MAX_DIFF_ITEMS],
        jd_only_keywords=sorted(jd_only)[:_MAX_DIFF_ITEMS],
        resume_only_keywords=sorted(resume_only)[:_MAX_DIFF_ITEMS],
    )


def compute_six_second_scan(resume_analysis: ResumeAnalysis, normalized_text: str) -> SixSecondScan:
    checks = []

    head = normalized_text[:500].lower()
    contact_near_top = bool(resume_analysis.contact.email and resume_analysis.contact.email.lower() in head) or bool(
        resume_analysis.contact.phone and resume_analysis.contact.phone.lower() in head
    )
    checks.append(
        ScanCheck(
            label="Contact info near the top",
            passed=contact_near_top,
            detail="Found in the first ~500 characters." if contact_near_top else "Not found near the top of the resume.",
        )
    )

    word_count = len(normalized_text.split())
    length_ok = 150 <= word_count <= 1200
    checks.append(
        ScanCheck(
            label="Reasonable length",
            passed=length_ok,
            detail=f"{word_count} words." + ("" if length_ok else " Consider aiming for roughly 300-900 words."),
        )
    )

    has_skills = len(resume_analysis.skills) > 0
    checks.append(
        ScanCheck(
            label="Skills clearly listed",
            passed=has_skills,
            detail=f"{len(resume_analysis.skills)} skill(s) detected." if has_skills else "No skills section detected.",
        )
    )

    bullets = collect_bullets(resume_analysis)
    long_bullets = sum(1 for b in bullets if len(b.text.split()) > 40)
    density_ok = long_bullets == 0
    checks.append(
        ScanCheck(
            label="Not overly dense",
            passed=density_ok,
            detail="No overly long bullets." if density_ok else f"{long_bullets} bullet(s) are quite long — consider tightening them.",
        )
    )

    has_experience_or_education = bool(resume_analysis.experience or resume_analysis.education)
    checks.append(
        ScanCheck(
            label="Experience or education visible",
            passed=has_experience_or_education,
            detail="Found." if has_experience_or_education else "No experience or education entries were found.",
        )
    )

    score = 100.0 * sum(1 for c in checks if c.passed) / len(checks)
    return SixSecondScan(score=round(score, 1), checks=checks)
