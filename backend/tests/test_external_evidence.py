"""Tests for external evidence checks. GitHub calls go through a fake
httpx.Client (never a real network call), matching the project's testing
rules. AI-backed LinkedIn checks mock generate_structured."""

import services.external_evidence as external_evidence
from schemas import ExperienceEntry, ResumeAnalysis
from services.ai_client import AIUnavailableError
from services.external_evidence import (
    _AILinkedInResult,
    check_fairness,
    check_github_consistency,
    check_linkedin_consistency,
    get_youtube_resources,
    youtube_search_url,
)


def test_youtube_search_url_is_a_real_search_link():
    url = youtube_search_url("Docker crash course")
    assert url.startswith("https://www.youtube.com/results?search_query=")
    assert "Docker" in url or "docker" in url.lower() or "%20" in url or "+" in url


class _FakeYoutubeSettings:
    def __init__(self, youtube_api_key=""):
        self.youtube_api_key = youtube_api_key


def test_youtube_resources_falls_back_to_search_link_without_api_key(monkeypatch):
    monkeypatch.setattr(external_evidence, "get_settings", lambda: _FakeYoutubeSettings(youtube_api_key=""))

    resources = get_youtube_resources("Docker tutorial")

    assert len(resources) == 1
    assert resources[0].source == "search_link"
    assert resources[0].url == youtube_search_url("Docker tutorial")


class _FakeYoutubeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeYoutubeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None):
        return _FakeYoutubeResponse(
            {
                "items": [
                    {"id": {"videoId": "abc123"}, "snippet": {"title": "Docker Crash Course"}},
                    {"id": {"videoId": "def456"}, "snippet": {"title": "Docker for Beginners"}},
                ]
            }
        )


def test_youtube_resources_returns_real_videos_when_api_key_present(monkeypatch):
    monkeypatch.setattr(external_evidence, "get_settings", lambda: _FakeYoutubeSettings(youtube_api_key="test-key"))
    monkeypatch.setattr(external_evidence.httpx, "Client", _FakeYoutubeClient)

    resources = get_youtube_resources("Docker tutorial")

    assert len(resources) == 2
    assert resources[0].source == "youtube_api"
    assert resources[0].url == "https://www.youtube.com/watch?v=abc123"
    assert resources[0].title == "Docker Crash Course"


class _FailingYoutubeClient(_FakeYoutubeClient):
    def get(self, url, params=None):
        raise external_evidence.httpx.HTTPError("boom")


def test_youtube_resources_falls_back_on_api_failure(monkeypatch):
    monkeypatch.setattr(external_evidence, "get_settings", lambda: _FakeYoutubeSettings(youtube_api_key="test-key"))
    monkeypatch.setattr(external_evidence.httpx, "Client", _FailingYoutubeClient)

    resources = get_youtube_resources("Docker tutorial")

    assert len(resources) == 1
    assert resources[0].source == "search_link"


class _EmptyResultsYoutubeClient(_FakeYoutubeClient):
    def get(self, url, params=None):
        return _FakeYoutubeResponse({"items": []})


def test_youtube_resources_falls_back_when_no_results(monkeypatch):
    monkeypatch.setattr(external_evidence, "get_settings", lambda: _FakeYoutubeSettings(youtube_api_key="test-key"))
    monkeypatch.setattr(external_evidence.httpx, "Client", _EmptyResultsYoutubeClient)

    resources = get_youtube_resources("Docker tutorial")

    assert len(resources) == 1
    assert resources[0].source == "search_link"


def test_github_check_handles_missing_url():
    result = check_github_consistency(None, ["Python"])
    assert result.profile_found is False
    assert "No GitHub URL" in result.warnings[0]


def test_github_check_handles_unparseable_url():
    result = check_github_consistency("not-a-github-url", ["Python"])
    assert result.profile_found is False


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None):
        if url.endswith("/repos"):
            return _FakeResponse(200, [{"language": "Python"}, {"language": "JavaScript"}, {"language": None}])
        return _FakeResponse(200, {"public_repos": 12})


def test_github_check_success_path(monkeypatch):
    monkeypatch.setattr(external_evidence.httpx, "Client", _FakeClient)

    result = check_github_consistency("https://github.com/janedoe", ["Python", "SQL"])

    assert result.profile_found is True
    assert result.username == "janedoe"
    assert result.public_repos == 12
    assert result.matched_languages == ["python"]
    assert result.unclaimed_languages == ["javascript"]


class _NotFoundClient(_FakeClient):
    def get(self, url, params=None):
        return _FakeResponse(404, {})


def test_github_check_profile_not_found(monkeypatch):
    monkeypatch.setattr(external_evidence.httpx, "Client", _NotFoundClient)

    result = check_github_consistency("https://github.com/nosuchuser", [])

    assert result.profile_found is False
    assert "No GitHub profile" in result.warnings[0]


def test_fairness_check_flags_terms():
    result = check_fairness("Name: Jane. Marital Status: married. Nationality: Wakandan.")
    assert "marital status" in result.flagged_terms
    assert "nationality" in result.flagged_terms
    assert "Consider removing" in result.note


def test_fairness_check_clean_resume():
    result = check_fairness("Skills: Python, SQL. Experience: Backend Developer at Acme.")
    assert result.flagged_terms == []
    assert "No personal details" in result.note


def test_linkedin_check_ai_success(monkeypatch):
    ai_result = _AILinkedInResult(consistent=False, findings=["Employer differs: resume says Acme, LinkedIn says Beta."])
    monkeypatch.setattr(external_evidence, "generate_structured", lambda **kwargs: ai_result)

    resume = ResumeAnalysis(experience=[ExperienceEntry(organization="Acme")])
    result = check_linkedin_consistency(resume, "I worked at Beta Inc.")

    assert result.ai_generated is True
    assert result.consistent is False
    assert result.findings


def test_linkedin_check_falls_back_without_ai(monkeypatch):
    def raise_unavailable(**kwargs):
        raise AIUnavailableError("boom")

    monkeypatch.setattr(external_evidence, "generate_structured", raise_unavailable)

    resume = ResumeAnalysis(experience=[ExperienceEntry(organization="Acme")])
    result = check_linkedin_consistency(resume, "I worked at Acme as an engineer.")

    assert result.ai_generated is False
    assert result.consistent is None
    assert any("Acme" in f for f in result.findings)
