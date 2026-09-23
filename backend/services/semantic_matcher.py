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
failed one — never a hang. Only one background load is ever started: if
it's still running past the timeout (e.g. a slow first-time download with
no local cache yet), the call that hit the timeout reports "unavailable"
for itself, but a later call rejoins that same thread and picks up the
result — success or failure — the moment it's actually done, rather than
staying stuck on "unavailable" for the rest of the process's life.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
_LOAD_TIMEOUT_SECONDS = 8.0

_model = None
_unavailable_reason: Optional[str] = None
_terminal = False  # True once a definitive success/failure is known (not a mere timeout)

_lock = threading.Lock()
_load_thread: Optional[threading.Thread] = None
_load_result: dict = {}


def is_available() -> bool:
    _ensure_loaded()
    return _model is not None


def unavailable_reason() -> Optional[str]:
    _ensure_loaded()
    return _unavailable_reason


def _load_into_result() -> None:
    try:
        from sentence_transformers import SentenceTransformer

        _load_result["model"] = SentenceTransformer(MODEL_NAME)
    except Exception as exc:  # network failure, missing package, corrupt cache, etc.
        _load_result["error"] = exc


def _ensure_loaded() -> None:
    """A slow first-time download (no local cache yet) can exceed the
    timeout below even though it keeps downloading successfully in the
    background — reported as timed out for the current call, but not a
    dead end. Only one load thread is ever started; a later call rejoins
    that same thread, so once it finishes (this run or a later one), every
    call afterward picks up the result instantly instead of staying
    latched to "unavailable" for the rest of the process's life."""
    global _model, _unavailable_reason, _terminal, _load_thread

    with _lock:
        if _terminal:
            return
        if _load_thread is None:
            _load_thread = threading.Thread(target=_load_into_result, daemon=True)
            _load_thread.start()
        thread = _load_thread

    thread.join(timeout=_LOAD_TIMEOUT_SECONDS)

    with _lock:
        if _terminal:
            return

        if thread.is_alive():
            logger.warning("Semantic matching model unavailable: load exceeded %.0fs timeout.", _LOAD_TIMEOUT_SECONDS)
            _unavailable_reason = "TimeoutError: model load exceeded time budget."
            return

        _terminal = True
        if "error" in _load_result:
            exc = _load_result["error"]
            logger.warning("Semantic matching model unavailable: %s: %s", type(exc).__name__, exc)
            _unavailable_reason = f"{type(exc).__name__}: could not load local embedding model."
            return

        _model = _load_result.get("model")
        _unavailable_reason = None


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
