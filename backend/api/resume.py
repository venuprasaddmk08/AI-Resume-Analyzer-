import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Resume
from schemas import ResumeUploadResponse
from services.resume_parser import SUPPORTED_EXTENSIONS, parse_resume

router = APIRouter()

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9 ._-]")


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "resume")
    base = _UNSAFE_CHARS.sub("_", base).strip()
    return base[:255] or "resume"


def _extension_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


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
