import { useState } from "react";
import {
  LayoutDashboard,
  ListChecks,
  GraduationCap,
  MessagesSquare,
  UserSquare2,
  UserPlus,
  ChevronLeft,
  Compass,
  HeartPulse,
  ScanSearch,
  Globe2,
} from "lucide-react";
import OverviewTab from "../OverviewTab";
import SkillsTab from "../SkillsTab";
import GapsLearningTab from "../GapsLearningTab";
import InterviewTab from "../InterviewTab";
import CareerIntelligenceTab from "../CareerIntelligenceTab";
import ResumeIntelligenceTab from "../ResumeIntelligenceTab";
import AtsRecruiterTab from "../AtsRecruiterTab";
import ExternalEvidenceTab from "../ExternalEvidenceTab";
import CandidateProfileSummary from "./CandidateProfileSummary";
import CandidateList from "./CandidateList";
import useAnalysisInsights from "../../hooks/useAnalysisInsights";
import useCareerIntelligence from "../../hooks/useCareerIntelligence";
import useResumeIntelligence from "../../hooks/useResumeIntelligence";
import useAtsRecruiterView from "../../hooks/useAtsRecruiterView";
import useExternalEvidence from "../../hooks/useExternalEvidence";

const TABS = [
  { id: "profile", label: "Profile", icon: UserSquare2 },
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "skills", label: "Skills & Evidence", icon: ListChecks },
  { id: "gaps", label: "Skill Gaps & Learning", icon: GraduationCap },
  { id: "interview", label: "Interview Prep", icon: MessagesSquare },
  { id: "career", label: "Career Intelligence", icon: Compass },
  { id: "resume-health", label: "Resume Intelligence", icon: HeartPulse },
  { id: "ats", label: "ATS / Recruiter View", icon: ScanSearch },
  { id: "external", label: "External Evidence", icon: Globe2 },
];

export default function CandidateFitness({ candidates, selectedId, onSelectCandidate, onAddCandidate, onChangeJd, jdRoleTitle }) {
  const [activeTab, setActiveTab] = useState("overview");
  const candidate = candidates.find((c) => c.id === selectedId);
  if (!candidate) return null;

  const { resumeAnalysis, analysis, filename } = candidate;
  const displayName = resumeAnalysis?.candidate_name || filename;
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
              audience="provider"
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
    </div>
  );
}
