import { UserRound, Plus } from "lucide-react";

function scoreColor(score) {
  if (score === null || score === undefined) return "#94a3b8";
  if (score >= 70) return "#1a8a5f";
  if (score >= 40) return "#d97706";
  return "#c0392b";
}

// Sorted by score for display convenience only — this is not a claim of
// "best candidate," just ordering an already-computed, disclosed number.
// The provider still sees each candidate's full evidence before deciding.
export default function CandidateList({ candidates, selectedId, onSelect, onAddCandidate }) {
  const sorted = [...candidates].sort((a, b) => (b.analysis.score?.overall_score ?? -1) - (a.analysis.score?.overall_score ?? -1));

  return (
    <div className="candidate-list">
      <div className="candidate-list-head">
        <span>{candidates.length} candidate{candidates.length === 1 ? "" : "s"}</span>
      </div>
      {sorted.map((c) => {
        const score = c.analysis.score?.overall_score;
        return (
          <button
            key={c.id}
            type="button"
            className={`candidate-list-item ${c.id === selectedId ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
          >
            <UserRound size={16} />
            <span className="candidate-list-name">{c.resumeAnalysis?.candidate_name || c.filename}</span>
            <span className="candidate-list-score" style={{ color: scoreColor(score) }}>
              {score !== null && score !== undefined ? Math.round(score) : "—"}
            </span>
          </button>
        );
      })}
      <button type="button" className="candidate-list-add" onClick={onAddCandidate}>
        <Plus size={15} />
        <span>Add candidate</span>
      </button>
    </div>
  );
}
