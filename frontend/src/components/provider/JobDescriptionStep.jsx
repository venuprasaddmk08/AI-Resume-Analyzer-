import { ArrowRight } from "lucide-react";
import { useState } from "react";
import JobDescriptionPicker from "../shared/JobDescriptionPicker";

export default function JobDescriptionStep({ onContinue, disabled }) {
  const [jdMode, setJdMode] = useState("paste");
  const [jdFile, setJdFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [validationError, setValidationError] = useState("");

  function handleContinue() {
    if (jdMode === "paste" && !jdText.trim()) {
      setValidationError("Please paste the job description text.");
      return;
    }
    if (jdMode === "upload" && !jdFile) {
      setValidationError("Please upload a job description .txt file.");
      return;
    }
    setValidationError("");
    onContinue({ jdMode, jdFile, jdText });
  }

  return (
    <div className="provider-step">
      <h2>Set the Job Description</h2>
      <p className="tab-intro">
        This job description will be used to evaluate every candidate you upload next, using the same evidence-based
        matching and scoring as the Job Seeker mode.
      </p>

      <div className="upload-grid single">
        <JobDescriptionPicker
          label="Job Description"
          jdMode={jdMode}
          setJdMode={setJdMode}
          jdText={jdText}
          setJdText={setJdText}
          jdFile={jdFile}
          setJdFile={setJdFile}
        />
      </div>

      {validationError && <p className="inline-error">{validationError}</p>}

      <button type="button" className="btn-primary btn-analyze" disabled={disabled} onClick={handleContinue}>
        <span>Continue</span>
        <ArrowRight size={18} />
      </button>
    </div>
  );
}
