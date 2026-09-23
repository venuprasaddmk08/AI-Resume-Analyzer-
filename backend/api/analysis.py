from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Analysis, JobDescription, Resume
from schemas import (
    AnalysisRunRequest,
    AnalysisResponse,
    AtsRecruiterResponse,
    EvidenceGraphResponse,
    InsightsResponse,
    InterviewEvaluateRequest,
    InterviewEvaluateResponse,
    JDAnalysis,
    RequirementMatch,
    ResumeAnalysis,
    ScoreBreakdown,
    ScoreResponse,
    SkillsCategorizedResponse,
)
from services.ats_recruiter import build_ats_preview, compute_keyword_diff, compute_six_second_scan
from services.evidence_engine import build_requirement_matches
from services.insights_engine import generate_career_insights
from services.interview_engine import evaluate_answer
from services.jd_analyzer import analyze_job_description
from services.resume_analyzer import analyze_resume
from services.scoring_engine import compute_score

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


def _ensure_both_analyzed(resume: Resume, job: JobDescription, db: Session) -> tuple[ResumeAnalysis, JDAnalysis]:
    """When neither has been analyzed yet, runs the resume and job AI
    structured-analysis calls concurrently instead of sequentially —
    they're independent, so this roughly halves the wall-clock wait on a
    first-time resume/JD pair, which is the common case for /run. Only
    the pure AI calls run in the background threads; all db reads/writes
    stay on the calling thread since SQLAlchemy sessions aren't safe to
    share across threads."""
    if resume.analysis is None and job.analysis is None:
        with ThreadPoolExecutor(max_workers=2) as executor:
            resume_future = executor.submit(analyze_resume, resume.normalized_text)
            job_future = executor.submit(analyze_job_description, job.normalized_text)
            resume_analysis = resume_future.result()
            jd_analysis = job_future.result()

        resume.analysis = resume_analysis.model_dump(mode="json")
        resume.analyzed_at = datetime.now(timezone.utc)
        job.analysis = jd_analysis.model_dump(mode="json")
        job.analyzed_at = datetime.now(timezone.utc)
        db.commit()
        return resume_analysis, jd_analysis

    return _ensure_resume_analyzed(resume, db), _ensure_job_analyzed(job, db)


def _analysis_to_response(analysis: Analysis, role_title: str | None = None) -> AnalysisResponse:
    return AnalysisResponse(
        analysis_id=analysis.id,
        resume_id=analysis.resume_id,
        job_id=analysis.job_id,
        matches=[RequirementMatch.model_validate(m) for m in analysis.matches],
        semantic_model_available=analysis.semantic_model_available,
        ai_refinement_used=analysis.ai_refinement_used,
        warnings=analysis.warnings,
        created_at=analysis.created_at,
        score=ScoreBreakdown.model_validate(analysis.score) if analysis.score is not None else None,
        role_title=role_title,
    )


@router.post("/run", response_model=AnalysisResponse)
def run_analysis(payload: AnalysisRunRequest, db: Session = Depends(get_db)):
    resume = db.get(Resume, payload.resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail=f"No resume found with id {payload.resume_id}.")

    job = db.get(JobDescription, payload.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job description found with id {payload.job_id}.")

    resume_analysis, jd_analysis = _ensure_both_analyzed(resume, job, db)

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

    # Fast baseline only: skip the per-ambiguous-match AI refinement call so
    # this request returns as soon as exact/raw-text/semantic matching is
    # done. The frontend triggers POST /{analysis_id}/refine right after to
    # upgrade PARTIAL matches in the background, without the loading screen
    # waiting on a sequential AI round-trip per ambiguous match.
    matches, semantic_ok, ai_refinement_used = build_requirement_matches(
        jd_analysis,
        resume_analysis,
        resume.blocks,
        resume.sections,
        use_ai_refinement=False,
    )
    if not semantic_ok:
        warnings.append(
            "The local semantic-similarity model could not be loaded, so matching relied only "
            "on exact/normalized and literal-text signals for this run."
        )

    score = compute_score(jd_analysis, resume_analysis, matches)

    analysis = Analysis(
        resume_id=resume.id,
        job_id=job.id,
        matches=[m.model_dump(mode="json") for m in matches],
        semantic_model_available=semantic_ok,
        ai_refinement_used=ai_refinement_used,
        warnings=warnings,
        score=score.model_dump(mode="json"),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return _analysis_to_response(analysis, role_title=jd_analysis.role_title)


@router.post("/{analysis_id}/refine", response_model=AnalysisResponse)
def refine_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Re-runs matching with AI refinement enabled for any PARTIAL match,
    upgrading the fast baseline that /run produced. Meant to be called
    right after /run, in the background, once the baseline is on screen."""
    analysis = _get_analysis_or_404(analysis_id, db)
    resume = _get_resume_or_404(analysis.resume_id, db)
    job = _get_job_or_404(analysis.job_id, db)

    resume_analysis = _ensure_resume_analyzed(resume, db)
    jd_analysis = _ensure_job_analyzed(job, db)

    matches, semantic_ok, ai_refinement_used = build_requirement_matches(
        jd_analysis,
        resume_analysis,
        resume.blocks,
        resume.sections,
        use_ai_refinement=True,
    )

    analysis.matches = [m.model_dump(mode="json") for m in matches]
    analysis.semantic_model_available = semantic_ok
    analysis.ai_refinement_used = ai_refinement_used
    analysis.score = compute_score(jd_analysis, resume_analysis, matches).model_dump(mode="json")
    analysis.insights = None
    db.commit()
    db.refresh(analysis)

    return _analysis_to_response(analysis, role_title=jd_analysis.role_title)


def _get_analysis_or_404(analysis_id: int, db: Session) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"No analysis found with id {analysis_id}.")
    return analysis


def _get_job_or_404(job_id: int, db: Session) -> JobDescription:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job description found with id {job_id}.")
    return job


def _get_resume_or_404(resume_id: int, db: Session) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail=f"No resume found with id {resume_id}.")
    return resume


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)
    job = db.get(JobDescription, analysis.job_id)
    role_title = job.analysis.get("role_title") if job and job.analysis else None
    return _analysis_to_response(analysis, role_title=role_title)


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


@router.get("/{analysis_id}/score", response_model=ScoreResponse)
def get_analysis_score(analysis_id: int, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)
    if analysis.score is None:
        raise HTTPException(status_code=404, detail="No score has been computed for this analysis.")
    return ScoreResponse(analysis_id=analysis.id, score=ScoreBreakdown.model_validate(analysis.score))


@router.get("/{analysis_id}/insights", response_model=InsightsResponse)
def get_analysis_insights(analysis_id: int, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)

    if analysis.insights is not None:
        return InsightsResponse(analysis_id=analysis.id, insights=analysis.insights)

    job = _get_job_or_404(analysis.job_id, db)
    jd_analysis = _ensure_job_analyzed(job, db)
    matches = [RequirementMatch.model_validate(m) for m in analysis.matches]

    insights = generate_career_insights(matches, jd_analysis)
    analysis.insights = insights.model_dump(mode="json")
    db.commit()

    return InsightsResponse(analysis_id=analysis.id, insights=insights)


@router.post("/{analysis_id}/interview/evaluate", response_model=InterviewEvaluateResponse)
def evaluate_interview_answer(analysis_id: int, payload: InterviewEvaluateRequest, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)
    job = _get_job_or_404(analysis.job_id, db)
    role_title = job.analysis.get("role_title") if job.analysis else None

    evaluation = evaluate_answer(
        question=payload.question,
        answer=payload.answer,
        based_on=payload.based_on,
        role_title=role_title,
    )
    return InterviewEvaluateResponse(analysis_id=analysis.id, evaluation=evaluation)


@router.get("/{analysis_id}/ats", response_model=AtsRecruiterResponse)
def get_ats_recruiter_view(analysis_id: int, db: Session = Depends(get_db)):
    analysis = _get_analysis_or_404(analysis_id, db)
    resume = _get_resume_or_404(analysis.resume_id, db)
    job = _get_job_or_404(analysis.job_id, db)
    resume_analysis = _ensure_resume_analyzed(resume, db)

    ats_preview = build_ats_preview(resume.normalized_text, resume.sections, resume.tables, resume.warnings, resume.blocks)
    keyword_diff = compute_keyword_diff(job.normalized_text, resume.normalized_text)
    six_second_scan = compute_six_second_scan(resume_analysis, resume.normalized_text)

    return AtsRecruiterResponse(
        analysis_id=analysis.id,
        ats_preview=ats_preview,
        keyword_diff=keyword_diff,
        six_second_scan=six_second_scan,
    )
