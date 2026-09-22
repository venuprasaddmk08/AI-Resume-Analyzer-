"""External-evidence checks (Phase 13):

- GitHub: calls GitHub's public REST API to see whether the profile the
  resume claims actually exists and whether its public repos' languages
  line up with claimed skills. Never raises — a network failure or
  missing profile degrades to an honest "could not verify" result.
- LinkedIn: no scraping (against LinkedIn's ToS and not reliably
  possible). Instead the candidate pastes their own profile text and we
  cross-check it against their resume — a manual, self-authorized
  workflow, not an automated lookup of a third party.
- Fairness: a heuristic scan for personal details (age, marital status,
  a photo, nationality/religion) that a resume doesn't need and that can
  introduce bias in human or automated screening — this is offered to
  help the candidate, and pairs with the fact that scoring_engine only
  ever scores skills/experience/education/certifications.
- YouTube: a constructed search-results URL (real and always valid),
  never a specific fabricated video link.
"""

import json
import re
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from pydantic import BaseModel

from config import get_settings
from schemas import FairnessCheck, GithubConsistency, LinkedInConsistencyResult, ResumeAnalysis
from services.ai_client import AIUnavailableError, UNTRUSTED_DOCUMENT_NOTICE, generate_structured

_GITHUB_URL_RE = re.compile(r"github\.com/([A-Za-z0-9-]+)", re.IGNORECASE)
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "linkedin_consistency.txt"

_SYSTEM_PROMPT = (
    "You are a careful fact-checker comparing two texts the candidate provided about themselves. "
    "You only report inconsistencies you can point to directly in the text. You respond with JSON only."
)

_FAIRNESS_PATTERNS = {
    "date of birth / age": re.compile(r"\bdate of birth\b|\bdob\b|\bage:?\s*\d{1,3}\b", re.IGNORECASE),
    "marital status": re.compile(r"\b(married|single|divorced|widowed)\b", re.IGNORECASE),
    "photo reference": re.compile(r"\bphoto attached\b|\bheadshot\b", re.IGNORECASE),
    "nationality": re.compile(r"\bnationality\b", re.IGNORECASE),
    "religion": re.compile(r"\breligion\b", re.IGNORECASE),
    "gender": re.compile(r"\bgender\b|\bsex:\s*(male|female)\b", re.IGNORECASE),
}


class _AILinkedInResult(BaseModel):
    consistent: bool
    findings: list[str]


def youtube_search_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def check_github_consistency(github_url: str | None, claimed_skills: list[str]) -> GithubConsistency:
    if not github_url:
        return GithubConsistency(profile_found=False, warnings=["No GitHub URL was found on the resume."])

    match = _GITHUB_URL_RE.search(github_url)
    if not match:
        return GithubConsistency(profile_found=False, warnings=[f"Could not parse a username from '{github_url}'."])
    username = match.group(1)

    settings = get_settings()
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    try:
        with httpx.Client(timeout=5.0, headers=headers) as client:
            profile_resp = client.get(f"https://api.github.com/users/{username}")
            if profile_resp.status_code == 404:
                return GithubConsistency(
                    profile_found=False, username=username, warnings=[f"No GitHub profile found for '{username}'."]
                )
            profile_resp.raise_for_status()
            profile = profile_resp.json()

            repos_resp = client.get(f"https://api.github.com/users/{username}/repos", params={"sort": "updated", "per_page": 20})
            repos_resp.raise_for_status()
            repos = repos_resp.json()
    except httpx.HTTPError as exc:
        return GithubConsistency(
            profile_found=False,
            username=username,
            warnings=[f"Could not reach GitHub to verify this profile. Reason: {type(exc).__name__}."],
        )

    repo_languages = {r["language"].lower() for r in repos if r.get("language")}
    claimed_lower = {s.lower() for s in claimed_skills}

    return GithubConsistency(
        profile_found=True,
        username=username,
        public_repos=profile.get("public_repos"),
        matched_languages=sorted(repo_languages & claimed_lower),
        unclaimed_languages=sorted(repo_languages - claimed_lower),
    )


def check_fairness(normalized_text: str) -> FairnessCheck:
    flagged = [label for label, pattern in _FAIRNESS_PATTERNS.items() if pattern.search(normalized_text)]
    note = (
        "No personal details that could introduce bias were detected."
        if not flagged
        else "Consider removing these details — they aren't needed and can introduce bias in screening."
    )
    note += " Scoring in this app only ever uses skills, experience, education, and certifications."
    return FairnessCheck(flagged_terms=flagged, note=note)


def check_linkedin_consistency(resume_analysis: ResumeAnalysis, linkedin_text: str) -> LinkedInConsistencyResult:
    try:
        ai_result = _check_with_ai(resume_analysis, linkedin_text)
        return LinkedInConsistencyResult(consistent=ai_result.consistent, findings=ai_result.findings, ai_generated=True)
    except AIUnavailableError as exc:
        return _fallback_linkedin_check(resume_analysis, linkedin_text, reason=str(exc))


def _check_with_ai(resume_analysis: ResumeAnalysis, linkedin_text: str) -> "_AILinkedInResult":
    resume_summary = json.dumps(
        {
            "experience": [
                {"title": e.title, "organization": e.organization, "start_date": e.start_date, "end_date": e.end_date}
                for e in resume_analysis.experience
            ],
            "education": [
                {"degree": e.degree, "institution": e.institution} for e in resume_analysis.education
            ],
        }
    )
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    schema_json = json.dumps(_AILinkedInResult.model_json_schema())
    user_prompt = template.format(
        untrusted_notice=UNTRUSTED_DOCUMENT_NOTICE,
        resume_summary=resume_summary,
        linkedin_text=linkedin_text,
        schema_json=schema_json,
    )
    return generate_structured(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt, schema=_AILinkedInResult)


def _fallback_linkedin_check(resume_analysis: ResumeAnalysis, linkedin_text: str, reason: str) -> LinkedInConsistencyResult:
    organizations = [e.organization for e in resume_analysis.experience if e.organization]
    if not organizations:
        return LinkedInConsistencyResult(
            consistent=None,
            findings=[],
            ai_generated=False,
            warnings=[f"AI comparison was unavailable and no resume organizations were found to check. Reason: {reason}"],
        )

    lowered = linkedin_text.lower()
    found = [org for org in organizations if org.lower() in lowered]
    missing = [org for org in organizations if org.lower() not in lowered]

    findings = []
    if missing:
        findings.append(f"Organization(s) not found in the pasted LinkedIn text: {', '.join(missing)}.")
    if found:
        findings.append(f"Organization(s) found in both: {', '.join(found)}.")

    return LinkedInConsistencyResult(
        consistent=None,
        findings=findings,
        ai_generated=False,
        warnings=[
            "AI-personalized comparison was unavailable, so this is only a literal name-matching check, "
            f"not a real consistency judgment. Reason: {reason}",
        ],
    )
