"""Tests for semantic_matcher.py. Never downloads the real model — that
network call is exercised manually outside the test suite. These tests
verify the graceful-degradation contract and the similarity math."""

import numpy as np

import services.semantic_matcher as semantic_matcher


def test_reports_unavailable_when_model_fails_to_load(monkeypatch):
    monkeypatch.setattr(semantic_matcher, "_model", None)
    monkeypatch.setattr(semantic_matcher, "_load_attempted", False)
    monkeypatch.setattr(semantic_matcher, "_unavailable_reason", None)

    def raise_on_construct(*args, **kwargs):
        raise RuntimeError("simulated: no network access to download model")

    # Patch the SentenceTransformer symbol where it's imported inside _ensure_loaded.
    import sentence_transformers

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", raise_on_construct)

    assert semantic_matcher.is_available() is False
    assert semantic_matcher.unavailable_reason() is not None
    assert semantic_matcher.embed_texts(["python"]) is None


def test_reports_unavailable_when_load_exceeds_time_budget(monkeypatch):
    import time

    monkeypatch.setattr(semantic_matcher, "_model", None)
    monkeypatch.setattr(semantic_matcher, "_load_attempted", False)
    monkeypatch.setattr(semantic_matcher, "_unavailable_reason", None)
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


def test_embed_texts_returns_none_for_empty_input(monkeypatch):
    monkeypatch.setattr(semantic_matcher, "_load_attempted", True)
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
