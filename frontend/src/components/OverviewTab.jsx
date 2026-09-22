import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CheckCircle2, XCircle, Info } from "lucide-react";

const COMPONENT_LABELS = {
  skills: "Skills",
  experience: "Experience",
  projects: "Projects",
  education: "Education",
  certifications: "Certifications",
};

function scoreColor(score) {
  if (score === null || score === undefined) return "#94a3b8";
  if (score >= 70) return "#1a8a5f";
  if (score >= 40) return "#d97706";
  return "#c0392b";
}

export default function OverviewTab({ score, warnings }) {
  if (!score) {
    return <p className="empty-state">No score is available for this analysis.</p>;
  }

  const overall = score.overall_score;
  const chartData = Object.entries(score.component_scores).map(([key, comp]) => ({
    name: COMPONENT_LABELS[key] || key,
    score: comp.score,
    insufficient: comp.insufficient_evidence,
  }));

  return (
    <div className="overview-tab">
      <div className="score-hero">
        <div className="score-dial" style={{ "--dial-color": scoreColor(overall) }}>
          <span className="score-number">{overall !== null && overall !== undefined ? Math.round(overall) : "—"}</span>
          <span className="score-suffix">/ 100</span>
        </div>
        <div className="score-hero-text">
          <h2>Application-Generated Job-Fit Score</h2>
          <p className="score-caveat">
            <Info size={14} /> This is not an official ATS score — it's a configurable, explainable estimate.
          </p>
          <p className="score-method">{score.score_method}</p>
        </div>
      </div>

      {warnings?.length > 0 && (
        <div className="warning-box">
          {warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      <h3 className="section-title">Component Breakdown</h3>
      <div className="component-chart">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e7e1d8" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#5b5850" }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#5b5850" }} />
            <Tooltip
              formatter={(value, _name, item) =>
                item.payload.insufficient ? "Insufficient evidence" : `${value}/100`
              }
            />
            <Bar dataKey="score" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.insufficient ? "#c9c2b4" : scoreColor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="component-detail-grid">
        {Object.entries(score.component_scores).map(([key, comp]) => (
          <div className="component-card" key={key}>
            <div className="component-card-head">
              <span>{COMPONENT_LABELS[key] || key}</span>
              <strong style={{ color: scoreColor(comp.score) }}>
                {comp.insufficient_evidence ? "N/A" : `${Math.round(comp.score)}`}
              </strong>
            </div>
            <p>{comp.detail}</p>
          </div>
        ))}
      </div>

      <div className="factors-grid">
        <div className="factors-col positive">
          <h4>
            <CheckCircle2 size={16} /> Positive Factors
          </h4>
          {score.positive_factors.length === 0 && <p className="empty-state small">None found.</p>}
          <ul>
            {score.positive_factors.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
        <div className="factors-col negative">
          <h4>
            <XCircle size={16} /> Negative Factors
          </h4>
          {score.negative_factors.length === 0 && <p className="empty-state small">None found.</p>}
          <ul>
            {score.negative_factors.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="evidence-summary-strip">
        <span>
          <strong>{score.evidence_summary.mandatory_matched}</strong>/{score.evidence_summary.mandatory_total} mandatory
        </span>
        <span>
          <strong>{score.evidence_summary.preferred_matched}</strong>/{score.evidence_summary.preferred_total} preferred
        </span>
        <span>
          <strong>{score.evidence_summary.nice_to_have_matched}</strong>/{score.evidence_summary.nice_to_have_total} nice-to-have
        </span>
      </div>
    </div>
  );
}
