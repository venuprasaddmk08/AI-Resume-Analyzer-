"""Tests for the centralized AI client. These never call the real OpenRouter API —
per the testing rules, AI behavior is verified against mocked responses only."""

import json
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

import services.ai_client as ai_client
from services.ai_client import AIUnavailableError, generate_structured


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


def test_provider_exception_does_not_crash_and_raises_ai_unavailable(monkeypatch):
    monkeypatch.setattr(ai_client, "get_settings", lambda: _FakeSettings())

    def raising_create(**kwargs):
        raise RuntimeError("simulated provider outage")

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=raising_create)))
    monkeypatch.setattr(ai_client, "_get_client", lambda: fake_client)

    with pytest.raises(AIUnavailableError):
        generate_structured(system_prompt="sys", user_prompt="user", schema=_DummySchema)
