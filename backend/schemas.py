from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class Block(BaseModel):
    """A single line of extracted text with whatever layout metadata is available."""

    text: str
    page_number: Optional[int] = None
    bbox: Optional[List[float]] = None
    font_size: Optional[float] = None
    is_heading: bool = False


class SectionPosition(BaseModel):
    section: str
    page_number: Optional[int] = None
    text: str


class ParsedResume(BaseModel):
    file_type: Literal["pdf", "docx", "txt"]
    normalized_text: str
    page_count: Optional[int] = None
    blocks: List[Block] = []
    tables: List[List[List[str]]] = []
    sections_detected: List[SectionPosition] = []
    warnings: List[str] = []


class ResumeUploadResponse(BaseModel):
    resume_id: int
    filename: str
    created_at: datetime
    parsed: ParsedResume


class ParsedJobDescription(BaseModel):
    source: Literal["pdf", "docx", "txt", "pasted"]
    normalized_text: str
    page_count: Optional[int] = None
    blocks: List[Block] = []
    tables: List[List[List[str]]] = []
    sections_detected: List[SectionPosition] = []
    warnings: List[str] = []


class JobDescriptionResponse(BaseModel):
    job_id: int
    filename: Optional[str] = None
    created_at: datetime
    parsed: ParsedJobDescription


class JobDescriptionCreateRequest(BaseModel):
    text: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
