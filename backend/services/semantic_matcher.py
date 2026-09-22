"""Local semantic similarity via Sentence Transformers.

This is a free, local signal (no API key, no per-request cost) used to
catch paraphrases that exact/normalized matching would miss (e.g. JD says
"cloud infrastructure experience", resume says "deployed services on AWS").

The model is downloaded from Hugging Face Hub on first use. If that
download fails for any reason (no network, blocked proxy, disk issue) —
or the sentence-transformers package itself isn't usable — this module
must not crash the app. It reports itself unavailable and the matching
engine falls back to its other signals (exact/normalized/raw-text).

The load is also wall-clock bounded: an unreachable Hugging Face Hub can
otherwise hang for a long time inside its own retry/backoff logic (a
blocked firewall or proxy, not just "no network"), which would stall the
request holding it. A slow load degrades to "unavailable" exactly like a
failed one — never a hang.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
_LOAD_TIMEOUT_SECONDS = 8.0

_model = None
_load_attempted = False
_unavailable_reason: Optional[str] = None


def is_available() -> bool:
    _ensure_loaded()
    return _model is not None


def unavailable_reason() -> Optional[str]:
    _ensure_loaded()
    return _unavailable_reason


def _ensure_loaded() -> None:
    global _model, _load_attempted, _unavailable_reason
    if _load_attempted:
        return
    _load_attempted = True

    result: dict = {}

    def _load():
        try:
            from sentence_transformers import SentenceTransformer

            result["model"] = SentenceTransformer(MODEL_NAME)
        except Exception as exc:  # network failure, missing package, corrupt cache, etc.
            result["error"] = exc

    thread = threading.Thread(target=_load, daemon=True)
    thread.start()
    thread.join(timeout=_LOAD_TIMEOUT_SECONDS)

    if thread.is_alive():
        logger.warning("Semantic matching model unavailable: load exceeded %.0fs timeout.", _LOAD_TIMEOUT_SECONDS)
        _unavailable_reason = "TimeoutError: model load exceeded time budget."
        return

    if "error" in result:
        exc = result["error"]
        logger.warning("Semantic matching model unavailable: %s: %s", type(exc).__name__, exc)
        _unavailable_reason = f"{type(exc).__name__}: could not load local embedding model."
        return

    _model = result.get("model")


def embed_texts(texts: list[str]):
    """Returns embeddings for `texts`, or None if the model is unavailable."""
    if not texts:
        return None
    _ensure_loaded()
    if _model is None:
        return None
    return _model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


def cosine_similarity_matrix(query_embeddings, candidate_embeddings):
    """Both inputs are already L2-normalized (see embed_texts), so cosine
    similarity is just the dot product."""
    return query_embeddings @ candidate_embeddings.T
