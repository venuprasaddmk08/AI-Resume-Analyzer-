from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Analysis, JobDescription, Resume
from schemas import (
    AnalysisRunRequest,
    AnalysisResponse,
    EvidenceGraphResponse,
    JDAnalysis,
    RequirementMatch,
    ResumeAnalysis,
    SkillsCategorizedResponse,
)
from services.evidence_engine import build_requirement_matches
from services.jd_analyzer import analyze_job_description
from services.resume_analyzer import analyze_resume

router = APIRouter()


def _ensure_resume_analyzed(resume: Resume, db: Session) -> ResumeAnalysis:
    if resume.analysis is not None:
        return ResumeAnalysis.model_validate(resume.analysis)

    analysis = analyze_resume(resume.normalized_text)
    resume.analysis = analysis.model_dump(mode="json")
    resume.analyzed_at = datetime.now(timezone.utc)
    db.commit()
    return analysis


def _ensure_job_analyzed(job: JobDescription, db: Session) -> JDAnalysis:
    if job.analysis is not None:
        return JDAnalysis.model_validate(job.analysis)

    analysis = analyze_job_description(job.normalized_text)
    job.analysis = analysis.model_dump(mode="json")
    job.analyzed_at = datetime.now(timezone.utc)
    db.commit()
    return analysis


def _analysis_to_response(analysis: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        analysis_id=analysis.id,
        resume_id=analysis.resume_id,
        job_id=analysis.job_id,
        matches=[RequirementMatch.model_validate(m) for m in analysis.matches],
        semantic_model_available=analysis.semantic_model_available,
        ai_refinement_used=analysis.ai_refinement_used,
        warnings=analysis.warnings,
        created_at=analysis.created_at,
    )


@router.post("/run", response_model=AnalysisResponse)
def run_analysis(payload: AnalysisRunRequest, db: Session = Depends(get_db)):
    resume = db.get(Resume, payload.resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail=f"No resume found with id {payload.resume_id}.")

    job = db.get(JobDescription, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job description found with id {payload.job_id}.")

    resume_analysis = _ensure_resume_analyzed(resume, db)
    jd_analysis = _ensure_job_analyzed(job, db)

    warnings: list[str] = []
    if not resume_analysis.ai_used:
        warnings.append(
            "Resume structured analysis was unavailable, so matching relies only on literal "
            "text matches and semantic similarity, not AI-extracted skills."
        )
    if not jd_analysis.ai_used:
        warnings.append(
            "Job description structured analysis was unavailable, so no requirements could be "
            "extracted and matching could not run."
        )

    matches, semantic_ok, ai_refinement_used = build_requirement_matches(
        jd_analysis,
        resume_analysis,
        resume.blocks,
        resume.sections,
    )
    if not semantic_ok:
        warnings.append(
            "The local semantic-similarity model could not be loaded, so matching relied only "
            "on exact/normalized and literal-text signals for this run."
        )

    analysis = Analysis(
        resume_id=resume.id,
        job_id=job.id,
        matches=[m.model_dump(mode="json") for m in matches],
        semantic_model_available=semantic_ok,
        ai_refinement_used=ai_refinement_used,
        warnings=warnings,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return _analysis_to_response(analysis)


def _get_analysis_or_404(analysis_id: int, db: Session) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"No analysis found with id {analysis_id}.")
    return analysis


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    return _analysis_to_response(_get_analysis_or_404(analysis_id, db))


@router.get("/{analysis_id}/skills", response_model=SkillsCategorizedResponse)
def get_analysis_skills(analysis_id: int, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)
    matches = [RequirementMatch.model_validate(m) for m in analysis.matches]
    return SkillsCategorizedResponse(
        analysis_id=analysis.id,
        matching=[m for m in matches if m.status == "MATCH"],
        partial=[m for m in matches if m.status == "PARTIAL"],
        gaps=[m for m in matches if m.status == "GAP"],
    )


@router.get("/{analysis_id}/evidence", response_model=EvidenceGraphResponse)
def get_analysis_evidence(analysis_id: int, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)
    matches = [RequirementMatch.model_validate(m) for m in analysis.matches]
    return EvidenceGraphResponse(analysis_id=analysis.id, evidence_graph=matches)
