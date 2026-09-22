import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import JobDescription
from schemas import JobDescriptionCreateRequest, JobDescriptionResponse, ParsedJobDescription
from services.jd_parser import SUPPORTED_EXTENSIONS, parse_job_description

router = APIRouter()

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9 ._-]")


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "job_description")
    base = _UNSAFE_CHARS.sub("_", base).strip()
    return base[:255] or "job_description"


def _extension_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _persist(db: Session, filename: str | None, parsed: ParsedJobDescription) -> JobDescription:
    job = JobDescription(
        source=parsed.source,
        original_filename=filename,
        normalized_text=parsed.normalized_text,
        page_count=parsed.page_count,
        blocks=[block.model_dump() for block in parsed.blocks],
        tables=parsed.tables,
        sections=[section.model_dump() for section in parsed.sections_detected],
        warnings=parsed.warnings,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/upload", response_model=JobDescriptionResponse)
async def upload_job_description(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        parsed = parse_job_description(content=content, filename=safe_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    job = _persist(db, safe_name, parsed)
    return JobDescriptionResponse(job_id=job.id, filename=job.original_filename, created_at=job.created_at, parsed=parsed)


@router.post("/create", response_model=JobDescriptionResponse)
async def create_job_description(payload: JobDescriptionCreateRequest, db: Session = Depends(get_db)):
    settings = get_settings()

    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Job description text must not be empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(payload.text.encode("utf-8")) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Text exceeds the maximum allowed size of {settings.max_upload_size_mb} MB.",
        )

    parsed = parse_job_description(pasted_text=payload.text)
    job = _persist(db, None, parsed)
    return JobDescriptionResponse(job_id=job.id, filename=job.original_filename, created_at=job.created_at, parsed=parsed)
