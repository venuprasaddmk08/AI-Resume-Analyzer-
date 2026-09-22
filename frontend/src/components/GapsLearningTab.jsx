import { Search, Hammer, ListChecks, Loader2, Sparkles, AlertTriangle, Play } from "lucide-react";
import { priorityLabel } from "../utils/deriveInsights";

export default function GapsLearningTab({ matches, insightsStatus, insights, insightsError }) {
  const gaps = matches.filter((m) => m.status === "GAP");

  if (gaps.length === 0) {
    return <p className="empty-state">No skill gaps were found for this job description — nice work.</p>;
  }

  if (insightsStatus === "loading" || insightsStatus === "idle") {
    return (
      <div className="insights-loading">
        <Loader2 size={18} className="spin" />
        <span>Generating a learning roadmap for each gap...</span>
      </div>
    );
  }

  if (insightsStatus === "error") {
    return <p className="empty-state">{insightsError || "Could not load the learning roadmap."}</p>;
  }

  const roadmap = insights?.learning_roadmap || [];

  return (
    <div className="gaps-tab">
      <p className="tab-intro">
        {insights?.ai_generated ? (
          <>
            <Sparkles size={14} /> AI-personalized learning roadmap, generated from this specific gap analysis.
          </>
        ) : (
          <>
            <AlertTriangle size={14} /> AI-personalized roadmap was unavailable, so a generic starting-point template
            is shown instead — search terms and a real YouTube search link, never a specific fabricated video, per
            the project's no-fabrication policy.
          </>
        )}
      </p>
      <div className="gap-cards">
        {roadmap.map((step, i) => {
          const gapMatch = matches.find((m) => m.canonical_skill === step.skill);
          return (
            <div className="gap-card" key={i}>
              <div className="gap-card-head">
                <h3>{step.skill}</h3>
                <span className={`priority-badge priority-${step.priority.toLowerCase()}`}>
                  {priorityLabel(step.priority)}
                </span>
              </div>
              {gapMatch && <p className="gap-reason">{gapMatch.reason}</p>}

              <div className="gap-section">
                <h4>
                  <ListChecks size={14} /> Suggested sequence
                </h4>
                <ol>
                  {step.steps.map((s, si) => (
                    <li key={si}>{s}</li>
                  ))}
                </ol>
              </div>

              <div className="gap-section">
                <h4>
                  <Search size={14} /> Search terms
                </h4>
                <div className="search-term-chips">
                  {step.resources.map((term, ti) => (
                    <span className="search-term-chip" key={ti}>
                      {term}
                    </span>
                  ))}
                </div>
              </div>

              <div className="gap-section">
                <h4>
                  <Hammer size={14} /> Practice project
                </h4>
                <p>{step.practice_project}</p>
              </div>

              {step.youtube_resources?.length > 0 && (
                <div className="gap-section">
                  <h4>
                    <Play size={14} /> Video resources
                  </h4>
                  <ul className="youtube-resource-list">
                    {step.youtube_resources.map((res, ri) => (
                      <li key={ri}>
                        <a href={res.url} target="_blank" rel="noopener noreferrer">
                          {res.title}
                        </a>
                        {res.source === "search_link" && <span className="youtube-resource-tag">search link</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
