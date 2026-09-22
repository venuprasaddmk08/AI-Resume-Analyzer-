import { Sparkles, UserRound, Building2, ShieldCheck, GitBranch, ListChecks } from "lucide-react";

export default function WelcomeScreen({ onSelectRole }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-badge">
        <Sparkles size={18} />
        <span>AI Resume & Career Intelligence</span>
      </div>

      <h1>Understand job fit with real evidence, not guesswork</h1>
      <p className="welcome-lede">
        Upload a resume and a job description and get an evidence-grounded compatibility analysis: what actually
        matches, what's missing, and why — with every claim traceable back to real text, not invented.
      </p>

      <div className="welcome-points">
        <div className="welcome-point">
          <ListChecks size={18} />
          <span>Skill-by-skill matching with expandable evidence</span>
        </div>
        <div className="welcome-point">
          <ShieldCheck size={18} />
          <span>Application-generated score — clearly not an official ATS score</span>
        </div>
        <div className="welcome-point">
          <GitBranch size={18} />
          <span>Same analysis engine for job seekers and hiring teams</span>
        </div>
      </div>

      <h2 className="welcome-choose">How would you like to continue?</h2>
      <div className="role-cards">
        <button type="button" className="role-card" onClick={() => onSelectRole("seeker")}>
          <UserRound size={28} />
          <span className="role-card-title">I'm a Job Seeker</span>
          <span className="role-card-desc">Analyze your resume against a job description you're targeting.</span>
        </button>
        <button type="button" className="role-card" onClick={() => onSelectRole("provider")}>
          <Building2 size={28} />
          <span className="role-card-title">I'm a Job Provider</span>
          <span className="role-card-desc">Set a job description, then evaluate one or more candidates against it.</span>
        </button>
      </div>
    </div>
  );
}
