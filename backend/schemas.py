from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


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


# ---------------------------------------------------------------------------
# Resume structured analysis (Phase 4)
# ---------------------------------------------------------------------------

EvidenceType = Literal["WORK", "INTERNSHIP", "PROJECT", "EDUCATION", "CERTIFICATION", "COURSE", "OTHER"]


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class SkillEvidence(BaseModel):
    skill: str
    evidence_text: str = Field(
        description="Exact or closely paraphrased quote from the resume that supports this skill. "
        "Never invent this — if there is no supporting text, do not include the skill."
    )
    evidence_type: EvidenceType
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class EducationEntry(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    evidence_text: Optional[str] = None


class ExperienceEntry(BaseModel):
    title: Optional[str] = None
    organization: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    evidence_text: Optional[str] = None


class ProjectEntry(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = []
    evidence_text: Optional[str] = None


class CertificationEntry(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    evidence_text: Optional[str] = None


class ResumeAnalysis(BaseModel):
    candidate_name: Optional[str] = None
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: List[SkillEvidence] = []
    education: List[EducationEntry] = []
    experience: List[ExperienceEntry] = []
    projects: List[ProjectEntry] = []
    certifications: List[CertificationEntry] = []
    achievements: List[str] = []
    languages: List[str] = []
    sections_detected: List[str] = []
    ai_used: bool = True
    warnings: List[str] = []


class ResumeAnalyzeRequest(BaseModel):
    resume_id: int


class ResumeAnalysisResponse(BaseModel):
    resume_id: int
    analyzed_at: datetime
    analysis: ResumeAnalysis


# ---------------------------------------------------------------------------
# Job description structured analysis (Phase 4)
# ---------------------------------------------------------------------------


class JDAnalysis(BaseModel):
    role_title: Optional[str] = None
    seniority: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    nice_to_have_skills: List[str] = []
    experience_requirements: Optional[str] = None
    education_requirements: Optional[str] = None
    certifications: List[str] = []
    responsibilities: List[str] = []
    tools: List[str] = []
    domain_knowledge: List[str] = []
    ai_used: bool = True
    warnings: List[str] = []


class JobAnalyzeRequest(BaseModel):
    job_id: int


class JobAnalysisResponse(BaseModel):
    job_id: int
    analyzed_at: datetime
    analysis: JDAnalysis


# ---------------------------------------------------------------------------
# Matching + evidence (Phase 5)
# ---------------------------------------------------------------------------

RequirementPriority = Literal["MANDATORY", "PREFERRED", "NICE_TO_HAVE"]
MatchStatus = Literal["MATCH", "PARTIAL", "GAP"]
MatchSignal = Literal["exact", "raw_text", "semantic", "ai_reasoning", "none"]


class EvidenceItem(BaseModel):
    text: str
    evidence_type: EvidenceType
    source_page: Optional[int] = None
    source_section: Optional[str] = None
    origin: Literal["ai_extracted", "raw_text"]


class RequirementMatch(BaseModel):
    requirement: str
    canonical_skill: str
    priority: RequirementPriority
    status: MatchStatus
    evidence: List[EvidenceItem] = []
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    signal: MatchSignal


class AnalysisRunRequest(BaseModel):
    resume_id: int
    job_id: int


class AnalysisResponse(BaseModel):
    analysis_id: int
    resume_id: int
    job_id: int
    matches: List[RequirementMatch]
    semantic_model_available: bool
    ai_refinement_used: bool
    warnings: List[str] = []
    created_at: datetime


class SkillsCategorizedResponse(BaseModel):
    analysis_id: int
    matching: List[RequirementMatch]
    partial: List[RequirementMatch]
    gaps: List[RequirementMatch]


class EvidenceGraphResponse(BaseModel):
    analysis_id: int
    evidence_graph: List[RequirementMatch]


class AIRefinementDecision(BaseModel):
    status: MatchStatus
    reason: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
