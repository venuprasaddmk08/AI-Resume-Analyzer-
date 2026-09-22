import { Search, Hammer, ListChecks } from "lucide-react";
import { learningRoadmapFor, priorityLabel, sortByPriority } from "../utils/deriveInsights";

export default function GapsLearningTab({ matches }) {
  const gaps = sortByPriority(matches.filter((m) => m.status === "GAP"));

  if (gaps.length === 0) {
    return <p className="empty-state">No skill gaps were found for this job description — nice work.</p>;
  }

  return (
    <div className="gaps-tab">
      <p className="tab-intro">
        Suggested starting points for each gap. These are generic learning steps, not a personalized AI-generated
        curriculum — search terms instead of possibly-broken links, per the project's no-fabrication policy.
      </p>
      <div className="gap-cards">
        {gaps.map((gap, i) => {
          const roadmap = learningRoadmapFor(gap);
          return (
            <div className="gap-card" key={i}>
              <div className="gap-card-head">
                <h3>{gap.canonical_skill}</h3>
                <span className={`priority-badge priority-${gap.priority.toLowerCase()}`}>{priorityLabel(gap.priority)}</span>
              </div>
              <p className="gap-reason">{gap.reason}</p>

              <div className="gap-section">
                <h4>
                  <ListChecks size={14} /> Suggested sequence
                </h4>
                <ol>
                  {roadmap.steps.map((step, si) => (
                    <li key={si}>{step}</li>
                  ))}
                </ol>
              </div>

              <div className="gap-section">
                <h4>
                  <Search size={14} /> Search terms
                </h4>
                <div className="search-term-chips">
                  {roadmap.searchTerms.map((term, ti) => (
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
                <p>{roadmap.practiceProject}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
