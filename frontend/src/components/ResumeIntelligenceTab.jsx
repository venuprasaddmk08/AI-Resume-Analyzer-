import { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Loader2, Sparkles, HeartPulse, Tag } from "lucide-react";
import { rewriteBullet } from "../services/api";

const SOURCE_LABEL = { experience: "Experience", project: "Project", achievement: "Achievement" };

const IDLE_REWRITE = { status: "idle", rewrite: null, error: null };

export default function ResumeIntelligenceTab({ resumeId, status, data, error }) {
  const [rewrites, setRewrites] = useState({});

  if (status === "loading" || status === "idle") {
    return (
      <div className="insights-loading">
        <Loader2 size={18} className="spin" />
        <span>Checking your resume for bullet quality, quantification, and overall health...</span>
      </div>
    );
  }

  if (status === "error") {
    return <p className="empty-state">{error || "Could not load resume intelligence."}</p>;
  }

  const bullets = data?.bullets || [];
  const health = data?.health;

  async function handleRewrite(index, text) {
    setRewrites((prev) => ({ ...prev, [index]: { status: "loading", rewrite: null, error: null } }));
    try {
      const { rewrite } = await rewriteBullet(resumeId, text);
      setRewrites((prev) => ({ ...prev, [index]: { status: "success", rewrite, error: null } }));
    } catch (err) {
      setRewrites((prev) => ({
        ...prev,
        [index]: { status: "error", rewrite: null, error: err.message || "Failed to rewrite." },
      }));
    }
  }

  return (
    <div className="resume-intel-tab">
      {data?.warnings?.length > 0 && (
        <div className="warning-box">
          {data.warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      <div className="resume-intel-summary">
        <div className="resume-health-card">
          <div className="resume-health-head">
            <HeartPulse size={16} />
            <span>Resume Health</span>
            <strong className="resume-health-score">{Math.round(health?.score ?? 0)}/100</strong>
          </div>
          <ul className="resume-health-checks">
            {(health?.checks || []).map((c, i) => (
              <li key={i} className={c.passed ? "check-pass" : "check-fail"}>
                {c.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                <span>
                  <strong>{c.label}:</strong> {c.detail}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="resume-tone-card">
          <div className="resume-health-head">
            <Tag size={16} />
            <span>Tone / Seniority</span>
          </div>
          <p className="resume-tone-value">{data?.tone_seniority}</p>
        </div>
      </div>

      <h3 className="section-title">Bullet Improvement Workspace</h3>
      {bullets.length === 0 ? (
        <p className="empty-state small">No experience/project/achievement bullets were found to review.</p>
      ) : (
        <div className="bullet-list">
          {bullets.map((b, i) => {
            const rw = rewrites[i] || IDLE_REWRITE;
            return (
              <div className="bullet-card" key={i}>
                <div className="bullet-card-head">
                  <span className="bullet-source">{SOURCE_LABEL[b.source] || b.source}</span>
                  {b.has_quantification && <span className="bullet-quant-badge">Quantified</span>}
                </div>
                <p className="bullet-text">{b.text}</p>
                {b.issues.length > 0 && (
                  <ul className="bullet-issues">
                    {b.issues.map((issue, ii) => (
                      <li key={ii}>
                        <AlertTriangle size={12} /> {issue}
                      </li>
                    ))}
                  </ul>
                )}

                <button
                  type="button"
                  className="btn-secondary"
                  disabled={rw.status === "loading"}
                  onClick={() => handleRewrite(i, b.text)}
                >
                  {rw.status === "loading" ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                  <span>{rw.status === "loading" ? "Rewriting..." : "Rewrite with AI"}</span>
                </button>

                {rw.status === "error" && <p className="interview-feedback-error">{rw.error}</p>}

                {rw.status === "success" && rw.rewrite && (
                  <div className="before-after-card">
                    {!rw.rewrite.ai_generated && (
                      <p className="interview-feedback-note">{rw.rewrite.warnings[0] || "AI rewrite unavailable."}</p>
                    )}
                    <div className="before-after-row">
                      <div className="before-after-col">
                        <span className="before-after-label">Before</span>
                        <p>{rw.rewrite.original}</p>
                      </div>
                      <div className="before-after-col after">
                        <span className="before-after-label">After</span>
                        <p>{rw.rewrite.rewritten}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
