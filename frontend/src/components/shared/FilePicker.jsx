import { FileText, Upload, X } from "lucide-react";
import { useRef } from "react";

export default function FilePicker({ label, accept, hint, file, onChange, icon: Icon }) {
  const inputRef = useRef(null);

  return (
    <div className="file-picker">
      {label && (
        <div className="file-picker-label">
          <Icon size={16} />
          <span>{label}</span>
        </div>
      )}
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
                // Resetting the native input's value is required so that
                // re-selecting the exact same file later still fires a
                // change event (browsers won't fire one if the value
                // appears unchanged otherwise).
                if (inputRef.current) inputRef.current.value = "";
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
