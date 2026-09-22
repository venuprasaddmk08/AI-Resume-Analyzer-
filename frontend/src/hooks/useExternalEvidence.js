import { useEffect, useState } from "react";
import { getExternalEvidence } from "../services/api";

const cache = new Map();
const IDLE = { status: "idle", data: null, error: null };

export default function useExternalEvidence(resumeId, enabled) {
  const [state, setState] = useState(() => (resumeId && cache.has(resumeId) ? cache.get(resumeId) : IDLE));

  useEffect(() => {
    if (!enabled || !resumeId) return;

    const cached = cache.get(resumeId);
    if (cached && cached.status === "success") {
      setState(cached);
      return;
    }

    let cancelled = false;
    setState({ status: "loading", data: null, error: null });

    getExternalEvidence(resumeId)
      .then((data) => {
        if (cancelled) return;
        const next = { status: "success", data, error: null };
        cache.set(resumeId, next);
        setState(next);
      })
      .catch((err) => {
        if (cancelled) return;
        const next = { status: "error", data: null, error: err.message || "Failed to load external evidence." };
        cache.set(resumeId, next);
        setState(next);
      });

    return () => {
      cancelled = true;
    };
  }, [resumeId, enabled]);

  return state;
}
