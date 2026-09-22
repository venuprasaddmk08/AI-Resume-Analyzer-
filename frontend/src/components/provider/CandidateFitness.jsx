import { useState } from "react";
import { LayoutDashboard, ListChecks, GraduationCap, MessagesSquare, UserSquare2, UserPlus, ChevronLeft } from "lucide-react";
import OverviewTab from "../OverviewTab";
import SkillsTab from "../SkillsTab";
import GapsLearningTab from "../GapsLearningTab";
import InterviewTab from "../InterviewTab";
import CandidateProfileSummary from "./CandidateProfileSummary";
import CandidateList from "./CandidateList";

const TABS = [
  { id: "profile", label: "Profile", icon: UserSquare2 },
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "skills", label: "Skills & Evidence", icon: ListChecks },
  { id: "gaps", label: "Skill Gaps & Learning", icon: GraduationCap },
  { id: "interview", label: "Interview Prep", icon: MessagesSquare },
];

export default function CandidateFitness({ candidates, selectedId, onSelectCandidate, onAddCandidate, onChangeJd, jdRoleTitle }) {
  const [activeTab, setActiveTab] = useState("overview");
  const candidate = candidates.find((c) => c.id === selectedId);
  if (!candidate) return null;

  const { resumeAnalysis, analysis, filename } = candidate;
  const displayName = resumeAnalysis?.candidate_name || filename;

  return (
    <div className="provider-fitness">
      <CandidateList candidates={candidates} selectedId={selectedId} onSelect={onSelectCandidate} onAddCandidate={onAddCandidate} />

      <div className="candidate-detail">
        <div className="dashboard-header">
          <div>
            <h1>{displayName}</h1>
            <p className="role-subtitle">Candidate Fitness{jdRoleTitle ? ` — ${jdRoleTitle}` : ""}</p>
          </div>
          <div className="provider-header-actions">
            <button type="button" className="btn-secondary" onClick={onChangeJd}>
              <ChevronLeft size={15} />
              <span>Change Job Description</span>
            </button>
            <button type="button" className="btn-secondary" onClick={onAddCandidate}>
              <UserPlus size={15} />
              <span>Next Candidate</span>
            </button>
          </div>
        </div>

        <nav className="tab-nav">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                className={`tab-nav-btn ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="tab-panel">
          {activeTab === "profile" && <CandidateProfileSummary resumeAnalysis={resumeAnalysis} />}
          {activeTab === "overview" && <OverviewTab score={analysis.score} warnings={analysis.warnings} />}
          {activeTab === "skills" && <SkillsTab matches={analysis.matches} />}
          {activeTab === "gaps" && <GapsLearningTab matches={analysis.matches} audience="provider" />}
          {activeTab === "interview" && <InterviewTab analysis={analysis} jdRoleTitle={jdRoleTitle} audience="provider" />}
        </div>
      </div>
    </div>
  );
}
