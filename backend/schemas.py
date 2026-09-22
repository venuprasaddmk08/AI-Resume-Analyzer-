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
    source: Literal["txt", "pasted"]
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
    score: Optional["ScoreBreakdown"] = None
    role_title: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Job-fit scoring (Phase 6)
# ---------------------------------------------------------------------------

ComponentName = Literal["skills", "experience", "projects", "education", "certifications"]


class ComponentScore(BaseModel):
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    insufficient_evidence: bool
    detail: str


class EvidenceSummary(BaseModel):
    total_requirements: int
    matched: int
    partial: int
    gaps: int
    mandatory_matched: int
    mandatory_total: int
    preferred_matched: int
    preferred_total: int
    nice_to_have_matched: int
    nice_to_have_total: int


class ScoreBreakdown(BaseModel):
    component_scores: dict[ComponentName, ComponentScore]
    overall_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    positive_factors: List[str]
    partial_factors: List[str]
    negative_factors: List[str]
    evidence_summary: EvidenceSummary
    score_method: str


class ScoreResponse(BaseModel):
    analysis_id: int
    score: ScoreBreakdown


# ---------------------------------------------------------------------------
# Career insights: learning roadmap + interview questions (Phase 7)
# ---------------------------------------------------------------------------

InterviewCategory = Literal["Technical", "Project", "Behavioral", "Gap-focused"]


class YoutubeResource(BaseModel):
    title: str
    url: str
    source: Literal["youtube_api", "search_link"] = Field(
        description="'youtube_api' when fetched live from the YouTube Data API; 'search_link' when it's a "
        "constructed search-results URL used as a fallback (no API key, or the call failed)."
    )


class LearningStep(BaseModel):
    skill: str
    priority: RequirementPriority
    steps: List[str] = Field(description="Concrete, ordered steps to learn this skill.")
    resources: List[str] = Field(description="Search terms to find learning resources, not live URLs.")
    practice_project: str
    youtube_search_url: Optional[str] = Field(
        default=None, description="A real YouTube search-results URL for this skill, not a specific fabricated video."
    )
    youtube_resources: List[YoutubeResource] = Field(
        default=[], description="Real videos from the YouTube Data API when a key is configured, else a single search-link fallback."
    )


class InterviewQuestion(BaseModel):
    category: InterviewCategory
    question: str
    based_on: Optional[str] = None


class CareerInsights(BaseModel):
    learning_roadmap: List[LearningStep] = []
    interview_questions: List[InterviewQuestion] = []
    ai_generated: bool
    warnings: List[str] = []


class InsightsResponse(BaseModel):
    analysis_id: int
    insights: CareerInsights


# ---------------------------------------------------------------------------
# Mock interview: answer evaluation + follow-up (Phase 8)
# ---------------------------------------------------------------------------


class InterviewEvaluateRequest(BaseModel):
    question: str
    based_on: Optional[str] = None
    answer: str = Field(min_length=1)


class InterviewEvaluation(BaseModel):
    strengths: List[str] = Field(description="What the answer already does well. Empty if none apply.")
    improvements: List[str] = Field(description="Specific, actionable ways to strengthen the answer.")
    follow_up_question: Optional[str] = Field(
        default=None, description="One natural follow-up question probing deeper on the same topic."
    )
    ai_generated: bool
    warnings: List[str] = []


class InterviewEvaluateResponse(BaseModel):
    analysis_id: int
    evaluation: InterviewEvaluation


# ---------------------------------------------------------------------------
# Career intelligence: multi-role fit + trajectory (Phase 10)
# ---------------------------------------------------------------------------


class RoleFitResult(BaseModel):
    role_title: str
    fit_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    matched_skills: List[str] = []
    gap_skills: List[str] = []
    evidence_highlights: List[str] = Field(
        default=[], description="Reasons for the top matched skills, grounded in this resume's actual evidence."
    )


class CareerTrajectoryEntry(BaseModel):
    title: Optional[str] = None
    organization: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class NextRoleSuggestion(BaseModel):
    current_role_family: Optional[str] = None
    current_level: Optional[str] = None
    suggested_next_role: Optional[str] = None
    rationale: str
    supporting_evidence: List[str] = []


class CareerIntelligenceResponse(BaseModel):
    resume_id: int
    role_fit: List[RoleFitResult]
    career_trajectory: List[CareerTrajectoryEntry]
    next_role: NextRoleSuggestion
    warnings: List[str] = []


# ---------------------------------------------------------------------------
# Resume intelligence: bullets, health, tone (Phase 11)
# ---------------------------------------------------------------------------

BulletSource = Literal["experience", "project", "achievement"]


class BulletAnalysis(BaseModel):
    source: BulletSource
    text: str
    has_quantification: bool
    issues: List[str] = []


class ResumeHealthCheck(BaseModel):
    label: str
    passed: bool
    detail: str


class ResumeHealth(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    checks: List[ResumeHealthCheck]


class ResumeIntelligenceResponse(BaseModel):
    resume_id: int
    tone_seniority: str
    health: ResumeHealth
    bullets: List[BulletAnalysis]
    warnings: List[str] = []


class BulletRewriteRequest(BaseModel):
    bullet_text: str = Field(min_length=1)


class BulletRewrite(BaseModel):
    original: str
    rewritten: str
    ai_generated: bool
    warnings: List[str] = []


class BulletRewriteResponse(BaseModel):
    resume_id: int
    rewrite: BulletRewrite


# ---------------------------------------------------------------------------
# ATS / recruiter view (Phase 12)
# ---------------------------------------------------------------------------


class AtsParsingPreview(BaseModel):
    normalized_text: str
    section_headers_detected: List[str]
    table_count: int
    warnings: List[str] = []


class KeywordDiff(BaseModel):
    shared_keywords: List[str]
    jd_only_keywords: List[str]
    resume_only_keywords: List[str]


class ScanCheck(BaseModel):
    label: str
    passed: bool
    detail: str


class SixSecondScan(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    checks: List[ScanCheck]


class AtsRecruiterResponse(BaseModel):
    analysis_id: int
    ats_preview: AtsParsingPreview
    keyword_diff: KeywordDiff
    six_second_scan: SixSecondScan


# ---------------------------------------------------------------------------
# External evidence: GitHub, LinkedIn, fairness (Phase 13)
# ---------------------------------------------------------------------------


class GithubConsistency(BaseModel):
    profile_found: bool
    username: Optional[str] = None
    public_repos: Optional[int] = None
    matched_languages: List[str] = []
    unclaimed_languages: List[str] = Field(
        default=[], description="Languages seen in public repos that aren't in the resume's claimed skills."
    )
    warnings: List[str] = []


class FairnessCheck(BaseModel):
    flagged_terms: List[str] = Field(
        default=[], description="Personal-detail terms found in the resume text that carry discrimination risk."
    )
    note: str


class ExternalEvidenceResponse(BaseModel):
    resume_id: int
    github: GithubConsistency
    fairness: FairnessCheck


class LinkedInConsistencyRequest(BaseModel):
    linkedin_text: str = Field(min_length=1)


class LinkedInConsistencyResult(BaseModel):
    consistent: Optional[bool] = None
    findings: List[str] = []
    ai_generated: bool
    warnings: List[str] = []


class LinkedInConsistencyResponse(BaseModel):
    resume_id: int
    result: LinkedInConsistencyResult


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# AnalysisResponse forward-references ScoreBreakdown (defined later in this
# file, once Phase 6 scoring was added) — rebuild it now that both exist.
AnalysisResponse.model_rebuild()
