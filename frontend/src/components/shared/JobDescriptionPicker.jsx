import { ClipboardPaste } from "lucide-react";
import FilePicker from "./FilePicker";

const JD_ACCEPT = ".txt";

export default function JobDescriptionPicker({ label, jdMode, setJdMode, jdText, setJdText, jdFile, setJdFile }) {
  return (
    <div className="file-picker">
      <div className="file-picker-label">
        <ClipboardPaste size={16} />
        <span>{label}</span>
      </div>

      <div className="jd-mode-toggle">
        <button type="button" className={jdMode === "paste" ? "active" : ""} onClick={() => setJdMode("paste")}>
          Paste text
        </button>
        <button type="button" className={jdMode === "upload" ? "active" : ""} onClick={() => setJdMode("upload")}>
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
        <FilePicker accept={JD_ACCEPT} hint="Plain text (.txt) only" file={jdFile} onChange={setJdFile} />
      )}
    </div>
  );
}
