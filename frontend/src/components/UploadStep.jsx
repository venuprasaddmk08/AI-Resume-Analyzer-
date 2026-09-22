import { FileText, Upload, ClipboardPaste, ArrowRight, X } from "lucide-react";
import { useRef, useState } from "react";

const RESUME_ACCEPT = ".pdf,.doc,.docx,.txt";
const JD_ACCEPT = ".txt";

function FilePicker({ label, accept, hint, file, onChange, icon: Icon }) {
  const inputRef = useRef(null);

  return (
    <div className="file-picker">
      <div className="file-picker-label">
        <Icon size={16} />
        <span>{label}</span>
      </div>
      <div className={`file-drop ${file ? "has-file" : ""}`} onClick={() => inputRef.current?.click()}>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          hidden
          onChange={(e) => onChange(e.target.files?.[0] || null)}
        />
        {file ? (
          <div className="file-chip">
            <FileText size={16} />
            <span>{file.name}</span>
            <button
              type="button"
              className="file-chip-remove"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
              }}
              aria-label="Remove file"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <>
            <Upload size={22} />
            <p>Click to choose a file</p>
            <span className="file-hint">{hint}</span>
          </>
        )}
      </div>
    </div>
  );
}

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

        <div className="file-picker">
          <div className="file-picker-label">
            <ClipboardPaste size={16} />
            <span>2. Job Description</span>
          </div>

          <div className="jd-mode-toggle">
            <button
              type="button"
              className={jdMode === "paste" ? "active" : ""}
              onClick={() => setJdMode("paste")}
            >
              Paste text
            </button>
            <button
              type="button"
              className={jdMode === "upload" ? "active" : ""}
              onClick={() => setJdMode("upload")}
            >
              Upload .txt
            </button>
          </div>

          {jdMode === "paste" ? (
            <textarea
              className="jd-textarea"
              placeholder="Paste the full job description here..."
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              rows={8}
            />
          ) : (
            <div className={`file-drop ${jdFile ? "has-file" : ""}`} onClick={() => document.getElementById("jd-file-input")?.click()}>
              <input
                id="jd-file-input"
                type="file"
                accept={JD_ACCEPT}
                hidden
                onChange={(e) => setJdFile(e.target.files?.[0] || null)}
              />
              {jdFile ? (
                <div className="file-chip">
                  <FileText size={16} />
                  <span>{jdFile.name}</span>
                  <button
                    type="button"
                    className="file-chip-remove"
                    onClick={(e) => {
                      e.stopPropagation();
                      setJdFile(null);
                    }}
                    aria-label="Remove file"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <>
                  <Upload size={22} />
                  <p>Click to choose a file</p>
                  <span className="file-hint">Plain text (.txt) only</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {validationError && <p className="inline-error">{validationError}</p>}

      <button type="button" className="btn-primary btn-analyze" disabled={disabled || !canAnalyze} onClick={handleAnalyzeClick}>
        <span>Analyze</span>
        <ArrowRight size={18} />
      </button>
    </div>
  );
}
