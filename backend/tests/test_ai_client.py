"""Tests for the centralized AI client. These never call the real OpenRouter API —
per the testing rules, AI behavior is verified against mocked responses only."""

import json
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError
from pydantic import BaseModel

import services.ai_client as ai_client
from services.ai_client import AIUnavailableError, generate_structured


def _bad_request_error(message: str = "unsupported request option") -> BadRequestError:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(400, request=request)
    return BadRequestError(message, response=response, body=None)


class _DummySchema(BaseModel):
    value: str


class _FakeSettings:
    def __init__(self, ai_available=True, openrouter_model="test-model"):
        self.ai_available = ai_available
        self.openrouter_model = openrouter_model


def _fake_response(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_raises_when_ai_not_available(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings(ai_available=False))

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)


def test_returns_validated_model_on_success(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: _fake_response(json.dumps({"value": "hello"}))
            )
        )
    )
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert isinstance(result, _DummySchema)
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

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)

    assert result.value == "fixed"
    assert call_count["n"] == 2


def test_gives_up_after_max_repair_attempts(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: _fake_response("still not json")))
    )
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)


def test_disables_openrouter_fallback_to_unrelated_models(monkeypatch):
    """Without this, OpenRouter's free-tier pool can silently substitute a
    completely unrelated model when the requested one is saturated (seen
    in practice: a content-safety classifier returning "User Safety:
    safe" instead of JSON), wasting a round-trip on a response that can
    never validate. The request must explicitly disable that fallback."""
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    captured_kwargs = {}

    def fake_create(**kwargs):
        captured_kwargs.update(kwargs)
        return _fake_response(json.dumps({"value": "hello"}))

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert captured_kwargs["extra_body"] == {"provider": {"allow_fallbacks": False}}


def test_retries_without_fallback_disable_or_json_mode_on_bad_request_error(monkeypatch):
    """Some models/providers reject the allow_fallbacks option or JSON
    mode (response_format) outright — seen in practice: a free model
    that flatly doesn't support the "structured-outputs" feature, a
    genuine 400, not a saturation error. That must not be treated as a
    hard AI failure — retry once with neither option instead of giving
    up on a model that simply doesn't support them."""
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise _bad_request_error()
        return _fake_response(json.dumps({"value": "hello"}))

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert result.value == "hello"
    assert len(calls) == 2
    assert "extra_body" in calls[0]
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert "extra_body" not in calls[1]
    assert "response_format" not in calls[1]


def test_gives_up_if_bad_request_error_persists_without_fallback_disable(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    def always_bad_request(**kwargs):
        raise _bad_request_error()

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=always_bad_request)))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)


def test_provider_exception_does_not_crash_and_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    def raising_create(**kwargs):
        raise RuntimeError("simulated provider outage")

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=raising_create)))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)
