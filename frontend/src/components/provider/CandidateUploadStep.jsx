import { FileText, ArrowRight, ChevronLeft } from "lucide-react";
import { useState } from "react";
import FilePicker from "../shared/FilePicker";

const RESUME_ACCEPT = ".pdf,.doc,.docx,.txt";

export default function CandidateUploadStep({ onAnalyze, onChangeJd, disabled, candidateNumber }) {
  const [resumeFile, setResumeFile] = useState(null);
  const [validationError, setValidationError] = useState("");

  function handleAnalyzeClick() {
    if (!resumeFile) {
      setValidationError("Please upload a candidate resume first.");
      return;
    }
    setValidationError("");
    onAnalyze(resumeFile);
  }

  return (
    <div className="provider-step">
      <div className="provider-step-head">
        <h2>Upload Candidate #{candidateNumber} Resume</h2>
        <button type="button" className="btn-secondary" onClick={onChangeJd}>
          <ChevronLeft size={15} />
          <span>Change Job Description</span>
        </button>
      </div>

      <div className="upload-grid single">
        <FilePicker
          label="Candidate Resume"
          accept={RESUME_ACCEPT}
          hint="PDF, DOC/DOCX, or TXT"
          file={resumeFile}
          onChange={setResumeFile}
          icon={FileText}
        />
      </div>

      {validationError && <p className="inline-error">{validationError}</p>}

      <button type="button" className="btn-primary btn-analyze" disabled={disabled || !resumeFile} onClick={handleAnalyzeClick}>
        <span>Analyze Candidate</span>
        <ArrowRight size={18} />
      </button>
    </div>
  );
}
