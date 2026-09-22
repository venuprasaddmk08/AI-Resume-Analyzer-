import { useState } from "react";
import { LayoutDashboard, ListChecks, GraduationCap, MessagesSquare, RotateCcw } from "lucide-react";
import OverviewTab from "./OverviewTab";
import SkillsTab from "./SkillsTab";
import GapsLearningTab from "./GapsLearningTab";
import InterviewTab from "./InterviewTab";

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "skills", label: "Skills & Evidence", icon: ListChecks },
  { id: "gaps", label: "Skill Gaps & Learning", icon: GraduationCap },
  { id: "interview", label: "Mock Interview", icon: MessagesSquare },
];

export default function ResultsDashboard({ analysis, jdRoleTitle, onStartOver }) {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Analysis Results</h1>
          {jdRoleTitle && <p className="role-subtitle">Compared against: {jdRoleTitle}</p>}
        </div>
        <button type="button" className="btn-secondary" onClick={onStartOver}>
          <RotateCcw size={15} />
          <span>Start over</span>
        </button>
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
        {activeTab === "overview" && <OverviewTab score={analysis.score} warnings={analysis.warnings} />}
        {activeTab === "skills" && <SkillsTab matches={analysis.matches} />}
        {activeTab === "gaps" && <GapsLearningTab matches={analysis.matches} />}
        {activeTab === "interview" && <InterviewTab analysis={analysis} jdRoleTitle={jdRoleTitle} />}
      </div>
    </div>
  );
}
