"""Tests for the centralized AI client. These never call the real Anthropic API —
per the testing rules, AI behavior is verified against mocked responses only."""

import json
from types import SimpleNamespace

import anthropic
import httpx
import pytest
from pydantic import BaseModel

import services.ai_client as ai_client
from services.ai_client import AIUnavailableError, generate_structured


def _provider_error(exc_type, message: str = "provider error"):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    if exc_type is anthropic.APIConnectionError:
        return exc_type(message=message, request=request)
    response = httpx.Response(429 if exc_type is anthropic.RateLimitError else 400, request=request)
    return exc_type(message, response=response, body=None)


class _DummySchema(BaseModel):
    value: str


class _FakeSettings:
    def __init__(self, ai_available=True, anthropic_model="test-model"):
        self.ai_available = ai_available
        self.anthropic_model = anthropic_model


def _text_block(text: str):
    return SimpleNamespace(type="text", text=text)


def _fake_response(content: str):
    return SimpleNamespace(content=[_text_block(content)])


def test_raises_when_ai_not_available(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings(ai_available=False))

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)


def test_returns_validated_model_on_success(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fake_client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kwargs: _fake_response(json.dumps({"value": "hello"})))
    )
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)

    assert isinstance(result, _DummySchema)
    assert result.value == "hello"


def test_unwraps_markdown_code_fence(monkeypatch):
    """Unlike OpenRouter's strict JSON mode, Claude has no hard JSON-only
    mode and can wrap its output in a ```json fence despite the prompt
    asking for JSON only. That must still parse successfully."""
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fenced = "```json\n" + json.dumps({"value": "hello"}) + "\n```"
    fake_client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: _fake_response(fenced)))
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

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    result = generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)

    assert result.value == "fixed"
    assert call_count["n"] == 2


def test_gives_up_after_max_repair_attempts(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    fake_client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kwargs: _fake_response("still not json"))
    )
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)


def test_sends_system_prompt_and_configured_model(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings(anthropic_model="claude-test-model"))

    captured_kwargs = {}

    def fake_create(**kwargs):
        captured_kwargs.update(kwargs)
        return _fake_response(json.dumps({"value": "hello"}))

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    generate_structured(system_prompt="be precise", user_prompt="do the thing", schema=_DummySchema)

    assert captured_kwargs["model"] == "claude-test-model"
    assert captured_kwargs["system"] == "be precise"
    assert captured_kwargs["messages"][0] == {"role": "user", "content": "do the thing"}


@pytest.mark.parametrize("exc_type", [anthropic.APITimeoutError, anthropic.APIConnectionError, anthropic.RateLimitError])
def test_provider_errors_raise_ai_unavailable_without_retry(monkeypatch, exc_type):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    call_count = {"n": 0}

    def raising_create(**kwargs):
        call_count["n"] += 1
        if exc_type is anthropic.APITimeoutError:
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            raise exc_type(request=request)
        raise _provider_error(exc_type)

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=raising_create))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema, max_repair_attempts=1)

    assert call_count["n"] == 1


def test_unexpected_exception_does_not_crash_and_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    def raising_create(**kwargs):
        raise RuntimeError("simulated provider outage")

    fake_client = SimpleNamespace(messages=SimpleNamespace(create=raising_create))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)
