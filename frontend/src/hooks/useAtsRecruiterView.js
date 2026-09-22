import { useEffect, useState } from "react";
import { getAtsRecruiterView } from "../services/api";

const cache = new Map();
const IDLE = { status: "idle", data: null, error: null };

export default function useAtsRecruiterView(analysisId, enabled) {
  const [state, setState] = useState(() => (analysisId && cache.has(analysisId) ? cache.get(analysisId) : IDLE));

  useEffect(() => {
    if (!enabled || !analysisId) return;

    const cached = cache.get(analysisId);
    if (cached && cached.status === "success") {
      setState(cached);
      return;
    }

    let cancelled = false;
    setState({ status: "loading", data: null, error: null });

    getAtsRecruiterView(analysisId)
      .then((data) => {
        if (cancelled) return;
        const next = { status: "success", data, error: null };
        cache.set(analysisId, next);
        setState(next);
      })
      .catch((err) => {
        if (cancelled) return;
        const next = { status: "error", data: null, error: err.message || "Failed to load ATS/recruiter view." };
        cache.set(analysisId, next);
        setState(next);
      });

    return () => {
      cancelled = true;
    };
  }, [analysisId, enabled]);

  return state;
}
