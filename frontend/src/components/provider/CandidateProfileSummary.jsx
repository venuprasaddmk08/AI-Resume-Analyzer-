import { Briefcase, FolderGit2, Award, GraduationCap } from "lucide-react";

// Shows the candidate's structured resume data (from POST /api/resume/analyze)
// that isn't part of the requirement-matching view: prior roles, projects,
// certifications, education. Nothing here is invented — every field is
// either real extracted data or explicitly left blank by the backend when
// AI extraction was unavailable (never guessed).
export default function CandidateProfileSummary({ resumeAnalysis }) {
  if (!resumeAnalysis) return null;

  const { experience = [], projects = [], certifications = [], education = [], ai_used, warnings = [] } = resumeAnalysis;

  return (
    <div className="candidate-profile">
      {!ai_used && warnings.length > 0 && (
        <div className="warning-box">
          {warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      <div className="profile-grid">
        <div className="profile-section">
          <h4>
            <Briefcase size={14} /> Prior Roles
          </h4>
          {experience.length === 0 ? (
            <p className="empty-state small">No experience entries extracted.</p>
          ) : (
            <ul>
              {experience.map((exp, i) => (
                <li key={i}>
                  <strong>{exp.title || "Role"}</strong>
                  {exp.organization ? ` — ${exp.organization}` : ""}
                  {exp.start_date || exp.end_date ? (
                    <span className="profile-dates">
                      {" "}
                      ({exp.start_date || "?"} – {exp.end_date || "present"})
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="profile-section">
          <h4>
            <FolderGit2 size={14} /> Projects
          </h4>
          {projects.length === 0 ? (
            <p className="empty-state small">No project entries extracted.</p>
          ) : (
            <ul>
              {projects.map((p, i) => (
                <li key={i}>
                  <strong>{p.name || "Project"}</strong>
                  {p.technologies?.length ? ` — ${p.technologies.join(", ")}` : ""}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="profile-section">
          <h4>
            <Award size={14} /> Certifications
          </h4>
          {certifications.length === 0 ? (
            <p className="empty-state small">None found.</p>
          ) : (
            <ul>
              {certifications.map((c, i) => (
                <li key={i}>{c.name}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="profile-section">
          <h4>
            <GraduationCap size={14} /> Education
          </h4>
          {education.length === 0 ? (
            <p className="empty-state small">None found.</p>
          ) : (
            <ul>
              {education.map((e, i) => (
                <li key={i}>
                  {e.degree || "Degree"}
                  {e.institution ? `, ${e.institution}` : ""}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
