import { useState } from "react";
import { LayoutDashboard, ListChecks, GraduationCap, MessagesSquare, RotateCcw, Compass, HeartPulse, ScanSearch, Globe2 } from "lucide-react";
import OverviewTab from "./OverviewTab";
import SkillsTab from "./SkillsTab";
import GapsLearningTab from "./GapsLearningTab";
import InterviewTab from "./InterviewTab";
import CareerIntelligenceTab from "./CareerIntelligenceTab";
import ResumeIntelligenceTab from "./ResumeIntelligenceTab";
import AtsRecruiterTab from "./AtsRecruiterTab";
import ExternalEvidenceTab from "./ExternalEvidenceTab";
import useAnalysisInsights from "../hooks/useAnalysisInsights";
import useCareerIntelligence from "../hooks/useCareerIntelligence";
import useResumeIntelligence from "../hooks/useResumeIntelligence";
import useAtsRecruiterView from "../hooks/useAtsRecruiterView";
import useExternalEvidence from "../hooks/useExternalEvidence";

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "skills", label: "Skills & Evidence", icon: ListChecks },
  { id: "gaps", label: "Skill Gaps & Learning", icon: GraduationCap },
  { id: "interview", label: "Mock Interview", icon: MessagesSquare },
  { id: "career", label: "Career Intelligence", icon: Compass },
  { id: "resume-health", label: "Resume Intelligence", icon: HeartPulse },
  { id: "ats", label: "ATS / Recruiter View", icon: ScanSearch },
  { id: "external", label: "External Evidence", icon: Globe2 },
];

export default function ResultsDashboard({ analysis, onStartOver }) {
  const [activeTab, setActiveTab] = useState("overview");
  const insightsEnabled = activeTab === "gaps" || activeTab === "interview";
  const { status: insightsStatus, insights, error: insightsError } = useAnalysisInsights(
    analysis.analysis_id,
    insightsEnabled
  );
  const careerIntelligence = useCareerIntelligence(analysis.resume_id, activeTab === "career");
  const resumeIntelligence = useResumeIntelligence(analysis.resume_id, activeTab === "resume-health");
  const atsView = useAtsRecruiterView(analysis.analysis_id, activeTab === "ats");
  const externalEvidence = useExternalEvidence(analysis.resume_id, activeTab === "external");

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Analysis Results</h1>
          {analysis.role_title && <p className="role-subtitle">Compared against: {analysis.role_title}</p>}
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
        {activeTab === "gaps" && (
          <GapsLearningTab
            matches={analysis.matches}
            insightsStatus={insightsStatus}
            insights={insights}
            insightsError={insightsError}
          />
        )}
        {activeTab === "interview" && (
          <InterviewTab
            analysisId={analysis.analysis_id}
            insightsStatus={insightsStatus}
            insights={insights}
            insightsError={insightsError}
          />
        )}
        {activeTab === "career" && (
          <CareerIntelligenceTab
            status={careerIntelligence.status}
            data={careerIntelligence.data}
            error={careerIntelligence.error}
          />
        )}
        {activeTab === "resume-health" && (
          <ResumeIntelligenceTab
            resumeId={analysis.resume_id}
            status={resumeIntelligence.status}
            data={resumeIntelligence.data}
            error={resumeIntelligence.error}
          />
        )}
        {activeTab === "ats" && <AtsRecruiterTab status={atsView.status} data={atsView.data} error={atsView.error} />}
        {activeTab === "external" && (
          <ExternalEvidenceTab
            resumeId={analysis.resume_id}
            status={externalEvidence.status}
            data={externalEvidence.data}
            error={externalEvidence.error}
          />
        )}
      </div>
    </div>
  );
}
