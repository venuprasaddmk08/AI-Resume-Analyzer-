import { useState } from "react";
import { ChevronDown, CheckCircle2, AlertCircle, XCircle, FileText } from "lucide-react";
import { priorityLabel } from "../utils/deriveInsights";

const STATUS_META = {
  MATCH: { label: "Matching", icon: CheckCircle2, className: "status-match" },
  PARTIAL: { label: "Partial Match", icon: AlertCircle, className: "status-partial" },
  GAP: { label: "No Evidence", icon: XCircle, className: "status-gap" },
};

function RequirementRow({ match }) {
  const [open, setOpen] = useState(false);
  const meta = STATUS_META[match.status];
  const Icon = meta.icon;
  const hasEvidence = match.evidence?.length > 0;

  return (
    <div className={`requirement-row ${meta.className}`}>
      <button type="button" className="requirement-row-head" onClick={() => setOpen((o) => !o)} disabled={!hasEvidence}>
        <Icon size={18} />
        <span className="requirement-name">{match.canonical_skill}</span>
        <span className={`priority-badge priority-${match.priority.toLowerCase()}`}>{priorityLabel(match.priority)}</span>
        <span className="requirement-confidence">{Math.round(match.confidence * 100)}%</span>
        {hasEvidence && <ChevronDown size={16} className={`chevron ${open ? "open" : ""}`} />}
      </button>
      <p className="requirement-reason">{match.reason}</p>
      {open && hasEvidence && (
        <div className="evidence-panel">
          {match.evidence.map((ev, i) => (
            <div className="evidence-item" key={i}>
              <FileText size={14} />
              <div>
                <p className="evidence-quote">&ldquo;{ev.text}&rdquo;</p>
                <div className="evidence-meta">
                  <span>{ev.evidence_type}</span>
                  {ev.source_section && <span>· {ev.source_section}</span>}
                  {ev.source_page && <span>· page {ev.source_page}</span>}
                  <span>· {ev.origin === "ai_extracted" ? "AI-extracted" : "literal text match"}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SkillsTab({ matches }) {
  const matching = matches.filter((m) => m.status === "MATCH");
  const partial = matches.filter((m) => m.status === "PARTIAL");
  const gaps = matches.filter((m) => m.status === "GAP");

  return (
    <div className="skills-tab">
      <p className="tab-intro">
        Click a requirement to expand the exact evidence found in your resume. Nothing here is shown unless it's
        actually present in the text you submitted.
      </p>

      <div className="skills-columns">
        <div className="skills-column">
          <h3 className="status-match">Matching ({matching.length})</h3>
          {matching.length === 0 && <p className="empty-state small">No matching skills found.</p>}
          {matching.map((m, i) => (
            <RequirementRow match={m} key={i} />
          ))}
        </div>
        <div className="skills-column">
          <h3 className="status-partial">Partial ({partial.length})</h3>
          {partial.length === 0 && <p className="empty-state small">No partial matches.</p>}
          {partial.map((m, i) => (
            <RequirementRow match={m} key={i} />
          ))}
        </div>
        <div className="skills-column">
          <h3 className="status-gap">No Evidence ({gaps.length})</h3>
          {gaps.length === 0 && <p className="empty-state small">No gaps found — great coverage!</p>}
          {gaps.map((m, i) => (
            <RequirementRow match={m} key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
