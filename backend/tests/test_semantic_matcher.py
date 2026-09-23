"""Tests for semantic_matcher.py. Never downloads the real model — that
network call is exercised manually outside the test suite. These tests
verify the graceful-degradation contract and the similarity math."""

import numpy as np

import services.semantic_matcher as semantic_matcher


def _reset_load_state(monkeypatch):
    monkeypatch.setattr(semantic_matcher, "_model", None)
    monkeypatch.setattr(semantic_matcher, "_terminal", False)
    monkeypatch.setattr(semantic_matcher, "_unavailable_reason", None)
    monkeypatch.setattr(semantic_matcher, "_load_thread", None)
    monkeypatch.setattr(semantic_matcher, "_load_result", {})


def test_reports_unavailable_when_model_fails_to_load(monkeypatch):
    _reset_load_state(monkeypatch)

    def raise_on_construct(*args, **kwargs):
        raise RuntimeError("simulated: no network access to download model")

    # Patch the SentenceTransformer symbol where it's imported inside _load_into_result.
    import sentence_transformers

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", raise_on_construct)

    assert semantic_matcher.is_available() is False
    assert semantic_matcher.unavailable_reason() is not None
    assert semantic_matcher.embed_texts(["python"]) is None


def test_reports_unavailable_when_load_exceeds_time_budget(monkeypatch):
    import time

    _reset_load_state(monkeypatch)
    monkeypatch.setattr(semantic_matcher, "_LOAD_TIMEOUT_SECONDS", 0.2)

    def hang_forever(*args, **kwargs):
        time.sleep(5)

    import sentence_transformers

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", hang_forever)

    started = time.monotonic()
    assert semantic_matcher.is_available() is False
    elapsed = time.monotonic() - started

    assert elapsed < 2.0  # bounded by the 0.2s budget, not the 5s "hang"
    assert "Timeout" in semantic_matcher.unavailable_reason()


def test_later_call_recovers_once_the_slow_background_load_finishes(monkeypatch):
    """A slow first-time download (e.g. no local HF cache yet) can still be
    running in the background after one call already timed out on it. A
    later call must not stay stuck reporting "unavailable" forever — it
    should rejoin the same background thread and pick up the model the
    moment it's actually ready, instead of starting a redundant reload."""
    import threading
    import time

    _reset_load_state(monkeypatch)
    monkeypatch.setattr(semantic_matcher, "_LOAD_TIMEOUT_SECONDS", 0.2)

    release_load = threading.Event()
    construct_calls = {"n": 0}
    fake_model = object()

    def slow_then_ready(*args, **kwargs):
        construct_calls["n"] += 1
        release_load.wait(timeout=5)
        return fake_model

    import sentence_transformers

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", slow_then_ready)

    # First call: the background load is still blocked, so it reports
    # unavailable after the (short) timeout budget rather than hanging.
    assert semantic_matcher.is_available() is False
    assert construct_calls["n"] == 1

    # The "download" finishes in the background, after the first call's
    # timeout already gave up on it.
    release_load.set()
    time.sleep(0.3)  # give the background thread a moment to finish

    # A later call must rejoin the same thread and adopt the now-ready
    # model — not restart a second load, and not stay latched unavailable.
    assert semantic_matcher.is_available() is True
    assert construct_calls["n"] == 1
    assert semantic_matcher.unavailable_reason() is None


def test_embed_texts_returns_none_for_empty_input(monkeypatch):
    monkeypatch.setattr(semantic_matcher, "_terminal", True)
    monkeypatch.setattr(semantic_matcher, "_model", None)

    assert semantic_matcher.embed_texts([]) is None


def test_cosine_similarity_matrix_matches_normalized_vectors():
    # Two orthogonal unit vectors -> similarity 0; identical vectors -> similarity 1.
    query = np.array([[1.0, 0.0], [0.0, 1.0]])
    candidates = np.array([[1.0, 0.0], [0.0, 1.0]])

    result = semantic_matcher.cosine_similarity_matrix(query, candidates)

    assert result.shape == (2, 2)
    assert result[0, 0] == 1.0
    assert result[0, 1] == 0.0
    assert result[1, 1] == 1.0
