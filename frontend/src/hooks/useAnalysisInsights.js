import { useEffect, useState } from "react";
import { getAnalysisInsights } from "../services/api";

// Module-level cache so switching tabs (or switching candidates back and
// forth in Provider mode) doesn't refetch insights already loaded for a
// given analysis_id in this session.
const cache = new Map();

const IDLE = { status: "idle", insights: null, error: null };

// Fetches career insights (learning roadmap + interview questions) for one
// analysis, but only once `enabled` is true — the AI call this triggers is
// slower than the rest of the dashboard, so callers should only enable it
// once the Gaps/Interview tab is actually opened.
export default function useAnalysisInsights(analysisId, enabled) {
  const [state, setState] = useState(() => (analysisId && cache.has(analysisId) ? cache.get(analysisId) : IDLE));

  useEffect(() => {
    if (!enabled || !analysisId) return;

    const cached = cache.get(analysisId);
    if (cached && cached.status === "success") {
      setState(cached);
      return;
    }

    let cancelled = false;
    setState({ status: "loading", insights: null, error: null });

    getAnalysisInsights(analysisId)
      .then((data) => {
        if (cancelled) return;
        const next = { status: "success", insights: data.insights, error: null };
        cache.set(analysisId, next);
        setState(next);
      })
      .catch((err) => {
        if (cancelled) return;
        const next = { status: "error", insights: null, error: err.message || "Failed to load insights." };
        cache.set(analysisId, next);
        setState(next);
      });

    return () => {
      cancelled = true;
    };
  }, [analysisId, enabled]);

  return state;
}
