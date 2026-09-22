import { useState } from "react";
import { Code2, ShieldCheck, Contact, Loader2, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { checkLinkedInConsistency } from "../services/api";

export default function ExternalEvidenceTab({ resumeId, status, data, error }) {
  const [linkedinText, setLinkedinText] = useState("");
  const [linkedinResult, setLinkedinResult] = useState({ status: "idle", result: null, error: null });

  if (status === "loading" || status === "idle") {
    return (
      <div className="insights-loading">
        <Loader2 size={18} className="spin" />
        <span>Checking external evidence...</span>
      </div>
    );
  }

  if (status === "error") {
    return <p className="empty-state">{error || "Could not load external evidence."}</p>;
  }

  const github = data?.github;
  const fairness = data?.fairness;

  async function handleCheckLinkedIn() {
    if (!linkedinText.trim()) return;
    setLinkedinResult({ status: "loading", result: null, error: null });
    try {
      const { result } = await checkLinkedInConsistency(resumeId, linkedinText);
      setLinkedinResult({ status: "success", result, error: null });
    } catch (err) {
      setLinkedinResult({ status: "error", result: null, error: err.message || "Failed to check." });
    }
  }

  return (
    <div className="external-evidence-tab">
      <p className="tab-intro">
        Cross-checks against evidence outside the resume itself — a public GitHub profile, a manually-pasted
        LinkedIn summary (nothing is scraped automatically), and a fairness scan for personal details a resume
        doesn't need.
      </p>

      <div className="evidence-grid">
        <div className="evidence-card">
          <div className="resume-health-head">
            <Code2 size={16} />
            <span>GitHub Consistency</span>
          </div>
          {github?.profile_found ? (
            <>
              <p>
                Profile <strong>@{github.username}</strong> found — {github.public_repos} public repos.
              </p>
              {github.matched_languages.length > 0 && (
                <p className="evidence-detail">Languages matching claimed skills: {github.matched_languages.join(", ")}</p>
              )}
              {github.unclaimed_languages.length > 0 && (
                <p className="evidence-detail">Languages used but not claimed as skills: {github.unclaimed_languages.join(", ")}</p>
              )}
            </>
          ) : (
            <p className="evidence-detail">{github?.warnings?.[0] || "GitHub profile could not be verified."}</p>
          )}
        </div>

        <div className="evidence-card">
          <div className="resume-health-head">
            <ShieldCheck size={16} />
            <span>Fairness Check</span>
          </div>
          {fairness?.flagged_terms.length > 0 ? (
            <ul className="bullet-issues">
              {fairness.flagged_terms.map((term, i) => (
                <li key={i}>
                  <AlertTriangle size={12} /> {term}
                </li>
              ))}
            </ul>
          ) : (
            <p className="evidence-detail">
              <CheckCircle2 size={13} style={{ verticalAlign: "text-bottom", marginRight: 4 }} />
              No personal details found that could introduce bias.
            </p>
          )}
          <p className="evidence-detail">{fairness?.note}</p>
        </div>
      </div>

      <h3 className="section-title">
        <Contact size={16} /> LinkedIn Consistency (manual, authorized)
      </h3>
      <p className="tab-intro">
        Paste your own LinkedIn summary below — nothing is fetched automatically. We only compare what you paste
        against your resume.
      </p>
      <textarea
        className="linkedin-textarea"
        rows={5}
        placeholder="Paste your LinkedIn profile summary/experience text here..."
        value={linkedinText}
        onChange={(e) => setLinkedinText(e.target.value)}
      />
      <button
        type="button"
        className="btn-secondary"
        disabled={!linkedinText.trim() || linkedinResult.status === "loading"}
        onClick={handleCheckLinkedIn}
      >
        {linkedinResult.status === "loading" ? <Loader2 size={14} className="spin" /> : <Contact size={14} />}
        <span>{linkedinResult.status === "loading" ? "Checking..." : "Check consistency"}</span>
      </button>

      {linkedinResult.status === "error" && <p className="interview-feedback-error">{linkedinResult.error}</p>}

      {linkedinResult.status === "success" && linkedinResult.result && (
        <div className="linkedin-result">
          {!linkedinResult.result.ai_generated && (
            <p className="interview-feedback-note">{linkedinResult.result.warnings[0]}</p>
          )}
          {linkedinResult.result.consistent === true && (
            <p className="check-pass">
              <CheckCircle2 size={14} /> No inconsistencies found.
            </p>
          )}
          {linkedinResult.result.consistent === false && (
            <p className="check-fail">
              <XCircle size={14} /> Possible inconsistencies found.
            </p>
          )}
          {linkedinResult.result.findings.length > 0 && (
            <ul className="bullet-issues">
              {linkedinResult.result.findings.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
