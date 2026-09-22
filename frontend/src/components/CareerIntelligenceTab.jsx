import {
  Cell,
  Legend,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { ArrowUpCircle, Briefcase, Loader2, TrendingUp } from "lucide-react";

const PIE_COLORS = ["#1a8a5f", "#2f7fbf", "#c1602f", "#8a5cb0", "#b3402c", "#5b8a3a"];

export default function CareerIntelligenceTab({ status, data, error }) {
  if (status === "loading" || status === "idle") {
    return (
      <div className="insights-loading">
        <Loader2 size={18} className="spin" />
        <span>Comparing your resume against common role profiles...</span>
      </div>
    );
  }

  if (status === "error") {
    return <p className="empty-state">{error || "Could not load career intelligence."}</p>;
  }

  const roleFit = data?.role_fit || [];
  const trajectory = data?.career_trajectory || [];
  const nextRole = data?.next_role;
  const radarData = roleFit.map((r) => ({ role: r.role_title, fit: r.fit_score ?? 0 }));
  const pieData = roleFit.map((r) => ({ name: r.role_title, value: r.fit_score ?? 0 }));
  const pieHasSignal = pieData.some((d) => d.value > 0);
  const topRoles = roleFit.slice(0, 3);

  return (
    <div className="career-tab">
      <p className="tab-intro">
        Compared against a fixed set of common role profiles — not a real job description — to show how broadly
        your resume's evidence fits across roles.
      </p>

      {data?.warnings?.length > 0 && (
        <div className="warning-box">
          {data.warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      <h3 className="section-title">
        <TrendingUp size={16} /> Multi-Role Fit
      </h3>
      <p className="tab-intro">
        Resume-to-role fit analysis across the profiles above — a comparison of your own evidence, not an employer
        hiring probability.
      </p>
      <div className="career-charts-grid">
        <div className="career-radar">
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#e7e1d8" />
              <PolarAngleAxis dataKey="role" tick={{ fontSize: 11, fill: "#5b5850" }} />
              <Tooltip formatter={(value) => `${Math.round(value)}/100`} />
              <Radar dataKey="fit" stroke="#1a8a5f" fill="#1a8a5f" fillOpacity={0.35} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <div className="career-pie">
          {pieHasSignal ? (
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={110} label={({ name, value }) => `${name}: ${Math.round(value)}`}>
                  {pieData.map((entry, i) => (
                    <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${Math.round(value)}/100`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="empty-state small">Not enough evidence yet to compare fit proportionally across roles.</p>
          )}
        </div>
      </div>

      <div className="role-fit-cards">
        {topRoles.map((r, i) => (
          <div className="role-fit-card" key={i}>
            <div className="role-fit-card-head">
              <h4>{r.role_title}</h4>
              <span className="role-fit-score">{r.fit_score !== null ? `${Math.round(r.fit_score)}/100` : "N/A"}</span>
            </div>
            {r.evidence_highlights.length > 0 && (
              <ul className="role-fit-evidence">
                {r.evidence_highlights.map((h, hi) => (
                  <li key={hi}>{h}</li>
                ))}
              </ul>
            )}
            {r.gap_skills.length > 0 && (
              <p className="role-fit-gaps">Gaps: {r.gap_skills.join(", ")}</p>
            )}
          </div>
        ))}
      </div>

      <h3 className="section-title">
        <Briefcase size={16} /> Career Trajectory
      </h3>
      {trajectory.length === 0 ? (
        <p className="empty-state small">No work experience entries were found on this resume.</p>
      ) : (
        <div className="career-timeline">
          {trajectory.map((entry, i) => (
            <div className="career-timeline-item" key={i}>
              <div className="career-timeline-dot" />
              <div className="career-timeline-content">
                <p className="career-timeline-title">
                  {entry.title || "Role"} {entry.organization && <span>· {entry.organization}</span>}
                </p>
                {(entry.start_date || entry.end_date) && (
                  <p className="career-timeline-dates">
                    {entry.start_date || "?"} — {entry.end_date || "Present"}
                  </p>
                )}
                {entry.description && <p className="career-timeline-desc">{entry.description}</p>}
              </div>
            </div>
          ))}
        </div>
      )}

      {nextRole && (
        <>
          <h3 className="section-title">
            <ArrowUpCircle size={16} /> Suggested Next Role
          </h3>
          <div className="next-role-card">
            {nextRole.suggested_next_role ? (
              <p className="next-role-path">
                {nextRole.current_level} <span className="next-role-arrow">→</span> {nextRole.suggested_next_role}
              </p>
            ) : (
              <p className="next-role-path">{nextRole.current_level || "Not enough evidence yet"}</p>
            )}
            <p className="next-role-rationale">{nextRole.rationale}</p>
            {nextRole.supporting_evidence.length > 0 && (
              <ul className="role-fit-evidence">
                {nextRole.supporting_evidence.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
