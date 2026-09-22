import { Loader2, ScanLine, FileSearch, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export default function AtsRecruiterTab({ status, data, error }) {
  if (status === "loading" || status === "idle") {
    return (
      <div className="insights-loading">
        <Loader2 size={18} className="spin" />
        <span>Building the ATS parsing preview, keyword diff, and 6-second scan...</span>
      </div>
    );
  }

  if (status === "error") {
    return <p className="empty-state">{error || "Could not load the ATS/recruiter view."}</p>;
  }

  const { ats_preview: atsPreview, keyword_diff: keywordDiff, six_second_scan: scan } = data || {};

  return (
    <div className="ats-tab">
      <p className="tab-intro">
        A recruiter/ATS-style view of the same resume — what a parser sees, how its keywords compare to the job
        description, and a heuristic check for what a human skimming it for 6 seconds would notice.
      </p>

      <h3 className="section-title">
        <ScanLine size={16} /> 6-Second Scan
      </h3>
      <div className="scan-card">
        <div className="resume-health-head">
          <span>Heuristic Scan Score</span>
          <strong className="resume-health-score">{Math.round(scan?.score ?? 0)}/100</strong>
        </div>
        <ul className="resume-health-checks">
          {(scan?.checks || []).map((c, i) => (
            <li key={i} className={c.passed ? "check-pass" : "check-fail"}>
              {c.passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
              <span>
                <strong>{c.label}:</strong> {c.detail}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <h3 className="section-title">Keyword Diff (JD vs Resume)</h3>
      <div className="keyword-diff-grid">
        <div className="keyword-diff-col">
          <h4 className="keyword-diff-head shared">Shared ({keywordDiff?.shared_keywords.length || 0})</h4>
          <div className="keyword-chips">
            {(keywordDiff?.shared_keywords || []).map((k, i) => (
              <span className="keyword-chip shared" key={i}>
                {k}
              </span>
            ))}
          </div>
        </div>
        <div className="keyword-diff-col">
          <h4 className="keyword-diff-head jd-only">JD only ({keywordDiff?.jd_only_keywords.length || 0})</h4>
          <div className="keyword-chips">
            {(keywordDiff?.jd_only_keywords || []).map((k, i) => (
              <span className="keyword-chip jd-only" key={i}>
                {k}
              </span>
            ))}
          </div>
        </div>
        <div className="keyword-diff-col">
          <h4 className="keyword-diff-head resume-only">Resume only ({keywordDiff?.resume_only_keywords.length || 0})</h4>
          <div className="keyword-chips">
            {(keywordDiff?.resume_only_keywords || []).map((k, i) => (
              <span className="keyword-chip resume-only" key={i}>
                {k}
              </span>
            ))}
          </div>
        </div>
      </div>

      <h3 className="section-title">
        <FileSearch size={16} /> ATS Parsing Preview
      </h3>
      {atsPreview?.warnings.length > 0 && (
        <div className="warning-box">
          {atsPreview.warnings.map((w, i) => (
            <p key={i}>
              <AlertTriangle size={13} style={{ verticalAlign: "text-bottom", marginRight: 4 }} />
              {w}
            </p>
          ))}
        </div>
      )}
      <p className="ats-section-headers">
        Section headers detected: {atsPreview?.section_headers_detected.length > 0 ? atsPreview.section_headers_detected.join(", ") : "none"}
      </p>
      <pre className="ats-raw-text">{atsPreview?.normalized_text}</pre>
    </div>
  );
}
