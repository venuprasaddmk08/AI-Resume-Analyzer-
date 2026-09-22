import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Resume
from schemas import (
    BulletRewriteRequest,
    BulletRewriteResponse,
    CareerIntelligenceResponse,
    ExternalEvidenceResponse,
    LinkedInConsistencyRequest,
    LinkedInConsistencyResponse,
    ResumeAnalysis,
    ResumeAnalysisResponse,
    ResumeAnalyzeRequest,
    ResumeIntelligenceResponse,
    ResumeUploadResponse,
)
from services.career_intelligence import build_career_trajectory, compute_role_fit
from services.external_evidence import check_fairness, check_github_consistency, check_linkedin_consistency
from services.resume_analyzer import analyze_resume
from services.resume_intelligence import collect_bullets, compute_resume_health, detect_tone_seniority, rewrite_bullet
from services.resume_parser import SUPPORTED_EXTENSIONS, parse_resume

router = APIRouter()

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9 ._-]")


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "resume")
    base = _UNSAFE_CHARS.sub("_", base).strip()
    return base[:255] or "resume"


def _extension_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _get_resume_or_404(resume_id: int, db: Session) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail=f"No resume found with id {resume_id}.")
    return resume


def _ensure_resume_analyzed(resume: Resume, db: Session) -> ResumeAnalysis:
    if resume.analysis is not None:
        return ResumeAnalysis.model_validate(resume.analysis)

    analysis = analyze_resume(resume.normalized_text)
    resume.analysis = analysis.model_dump(mode="json")
    resume.analyzed_at = datetime.now(timezone.utc)
    db.commit()
    return analysis


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    settings = get_settings()
    safe_name = _sanitize_filename(file.filename or "")
    extension = _extension_of(safe_name)

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{extension or 'unknown'}'. Supported types: PDF, DOCX, TXT.",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the maximum allowed size of {settings.max_upload_size_mb} MB.",
        )

    try:
        parsed = parse_resume(content, safe_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    resume = Resume(
        original_filename=safe_name,
        file_type=parsed.file_type,
        normalized_text=parsed.normalized_text,
        page_count=parsed.page_count,
        blocks=[block.model_dump() for block in parsed.blocks],
        tables=parsed.tables,
        sections=[section.model_dump() for section in parsed.sections_detected],
        warnings=parsed.warnings,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeUploadResponse(
        resume_id=resume.id,
        filename=resume.original_filename,
        created_at=resume.created_at,
        parsed=parsed,
    )


@router.post("/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume_endpoint(payload: ResumeAnalyzeRequest, db: Session = Depends(get_db)):
    resume = db.get(Resume, payload.resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail=f"No resume found with id {payload.resume_id}.")

    analysis = analyze_resume(resume.normalized_text)

    resume.analysis = analysis.model_dump(mode="json")
    resume.analyzed_at = datetime.now(timezone.utc)
    db.commit()

    return ResumeAnalysisResponse(
        resume_id=resume.id,
        analyzed_at=resume.analyzed_at,
        analysis=analysis,
    )


@router.get("/{resume_id}/career-intelligence", response_model=CareerIntelligenceResponse)
def get_career_intelligence(resume_id: int, db: Session = Depends(get_db)):
    resume = _get_resume_or_404(resume_id, db)
    resume_analysis = _ensure_resume_analyzed(resume, db)

    warnings = []
    if not resume_analysis.ai_used:
        warnings.append(
            "Resume structured analysis was unavailable, so role fit relies only on literal "
            "text matches, not AI-extracted skills, and career trajectory could not be derived."
        )

    role_fit = compute_role_fit(resume_analysis, resume.blocks, resume.sections)
    career_trajectory = build_career_trajectory(resume_analysis)

    return CareerIntelligenceResponse(
        resume_id=resume.id,
        role_fit=role_fit,
        career_trajectory=career_trajectory,
        warnings=warnings,
    )


@router.get("/{resume_id}/intelligence", response_model=ResumeIntelligenceResponse)
def get_resume_intelligence(resume_id: int, db: Session = Depends(get_db)):
    resume = _get_resume_or_404(resume_id, db)
    resume_analysis = _ensure_resume_analyzed(resume, db)

    warnings = []
    if not resume_analysis.ai_used:
        warnings.append(
            "Resume structured analysis was unavailable, so this reflects only what could be "
            "parsed without AI (contact info); bullet, health, and tone checks may be incomplete."
        )

    bullets = collect_bullets(resume_analysis)
    health = compute_resume_health(resume_analysis, bullets)
    tone_seniority = detect_tone_seniority(resume_analysis)

    return ResumeIntelligenceResponse(
        resume_id=resume.id,
        tone_seniority=tone_seniority,
        health=health,
        bullets=bullets,
        warnings=warnings,
    )


@router.post("/{resume_id}/bullets/rewrite", response_model=BulletRewriteResponse)
def rewrite_resume_bullet(resume_id: int, payload: BulletRewriteRequest, db: Session = Depends(get_db)):
    _get_resume_or_404(resume_id, db)
    rewrite = rewrite_bullet(payload.bullet_text)
    return BulletRewriteResponse(resume_id=resume_id, rewrite=rewrite)


@router.get("/{resume_id}/external-evidence", response_model=ExternalEvidenceResponse)
def get_external_evidence(resume_id: int, db: Session = Depends(get_db)):
    resume = _get_resume_or_404(resume_id, db)
    resume_analysis = _ensure_resume_analyzed(resume, db)

    claimed_skills = [s.skill for s in resume_analysis.skills]
    github = check_github_consistency(resume_analysis.contact.github_url, claimed_skills)
    fairness = check_fairness(resume.normalized_text)

    return ExternalEvidenceResponse(resume_id=resume.id, github=github, fairness=fairness)


@router.post("/{resume_id}/linkedin-consistency", response_model=LinkedInConsistencyResponse)
def post_linkedin_consistency(resume_id: int, payload: LinkedInConsistencyRequest, db: Session = Depends(get_db)):
    resume = _get_resume_or_404(resume_id, db)
    resume_analysis = _ensure_resume_analyzed(resume, db)

    result = check_linkedin_consistency(resume_analysis, payload.linkedin_text)
    return LinkedInConsistencyResponse(resume_id=resume.id, result=result)
