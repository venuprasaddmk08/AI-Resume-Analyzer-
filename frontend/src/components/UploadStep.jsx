import { FileText, ArrowRight } from "lucide-react";
import { useState } from "react";
import FilePicker from "./shared/FilePicker";
import JobDescriptionPicker from "./shared/JobDescriptionPicker";

const RESUME_ACCEPT = ".pdf,.doc,.docx,.txt";

export default function UploadStep({ onAnalyze, disabled }) {
  const [resumeFile, setResumeFile] = useState(null);
  const [jdMode, setJdMode] = useState("paste"); // "paste" | "upload"
  const [jdFile, setJdFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [validationError, setValidationError] = useState("");

  const canAnalyze = resumeFile && (jdMode === "paste" ? jdText.trim().length > 0 : jdFile);

  function handleAnalyzeClick() {
    if (!resumeFile) {
      setValidationError("Please upload a resume first.");
      return;
    }
    if (jdMode === "paste" && !jdText.trim()) {
      setValidationError("Please paste the job description text.");
      return;
    }
    if (jdMode === "upload" && !jdFile) {
      setValidationError("Please upload a job description .txt file.");
      return;
    }
    setValidationError("");
    onAnalyze({ resumeFile, jdMode, jdFile, jdText });
  }

  return (
    <div className="upload-step">
      <div className="upload-grid">
        <FilePicker
          label="1. Resume"
          accept={RESUME_ACCEPT}
          hint="PDF, DOC/DOCX, or TXT"
          file={resumeFile}
          onChange={setResumeFile}
          icon={FileText}
        />

        <JobDescriptionPicker
          label="2. Job Description"
          jdMode={jdMode}
          setJdMode={setJdMode}
          jdText={jdText}
          setJdText={setJdText}
          jdFile={jdFile}
          setJdFile={setJdFile}
        />
      </div>

      {validationError && <p className="inline-error">{validationError}</p>}

      <button type="button" className="btn-primary btn-analyze" disabled={disabled || !canAnalyze} onClick={handleAnalyzeClick}>
        <span>Analyze</span>
        <ArrowRight size={18} />
      </button>
    </div>
  );
}
