"""Tests for the centralized AI client. These never call the real Gemini API —
per the testing rules, AI behavior is verified against mocked responses only."""

import json
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel

import services.ai_client as ai_client
from services.ai_client import AIUnavailableError, generate_structured


class _DummySchema(BaseModel):
    value: str


class _FakeSettings:
    def __init__(self, ai_available=True, gemini_model="test-model"):
        self.ai_available = ai_available
        self.gemini_model = gemini_model


def _fake_response(text: str):
    return SimpleNamespace(text=text)


def _fake_client(create_fn):
    return SimpleNamespace(models=SimpleNamespace(generate_content=create_fn))


def test_raises_when_ai_not_available(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings(ai_available=False))

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)


def test_returns_validated_model_on_success(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fake_client = _fake_client(lambda **kwargs: _fake_response(json.dumps({"value": "hello"})))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert isinstance(result, _DummySchema)
    assert result.value == "hello"


def test_unwraps_markdown_code_fence(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fenced = "```json\n" + json.dumps({"value": "hello"}) + "\n```"
    fake_client = _fake_client(lambda **kwargs: _fake_response(fenced))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert result.value == "hello"


def test_repairs_malformed_json_on_retry(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    responses = [
        _fake_response("not valid json"),
        _fake_response(json.dumps({"value": "fixed"})),
    ]
    call_count = {"n": 0}

    def fake_create(**kwargs):
        response = responses[call_count["n"]]
        call_count["n"] += 1
        return response

    fake_client = _fake_client(fake_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)

    assert result.value == "fixed"
    assert call_count["n"] == 2


def test_gives_up_after_max_repair_attempts(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fake_client = _fake_client(lambda **kwargs: _fake_response("still not json"))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)


def test_sends_configured_model_and_json_mime_type(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings(gemini_model="gemini-test"))

    captured_kwargs = {}

    def fake_create(**kwargs):
        captured_kwargs.update(kwargs)
        return _fake_response(json.dumps({"value": "hello"}))

    fake_client = _fake_client(fake_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    generate_structured(system_prompt="be precise", user_prompt="do the thing", schema=_DummySchema)

    assert captured_kwargs["model"] == "gemini-test"
    assert captured_kwargs["contents"] == "do the thing"
    assert captured_kwargs["config"].system_instruction == "be precise"
    assert captured_kwargs["config"].response_mime_type == "application/json"


def test_provider_api_error_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(ai_client.time, "sleep", lambda seconds: None)

    def raising_create(**kwargs):
        raise genai_errors.APIError(code=400, response_json={"error": {"message": "bad request"}})

    fake_client = _fake_client(raising_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)


def test_non_transient_error_does_not_retry(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(ai_client.time, "sleep", lambda seconds: None)

    call_count = {"n": 0}

    def raising_create(**kwargs):
        call_count["n"] += 1
        raise genai_errors.APIError(code=404, response_json={"error": {"message": "not found"}})

    fake_client = _fake_client(raising_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert call_count["n"] == 1


def test_transient_error_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    sleep_calls = []
    monkeypatch.setattr(ai_client.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    call_count = {"n": 0}

    def flaky_create(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise genai_errors.APIError(code=503, response_json={"error": {"message": "overloaded"}})
        return _fake_response(json.dumps({"value": "recovered"}))

    fake_client = _fake_client(flaky_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert result.value == "recovered"
    assert call_count["n"] == 2
    assert sleep_calls == [1]


def test_transient_error_exhausts_retries_then_raises(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    sleep_calls = []
    monkeypatch.setattr(ai_client.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    call_count = {"n": 0}

    def raising_create(**kwargs):
        call_count["n"] += 1
        raise genai_errors.APIError(code=503, response_json={"error": {"message": "overloaded"}})

    fake_client = _fake_client(raising_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert call_count["n"] == 3
    assert sleep_calls == [1, 2]


def test_unexpected_exception_does_not_crash_and_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    def raising_create(**kwargs):
        raise RuntimeError("simulated provider outage")

    fake_client = _fake_client(raising_create)
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)
