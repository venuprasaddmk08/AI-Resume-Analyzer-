import { AlertTriangle, RotateCcw } from "lucide-react";

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="error-panel">
      <AlertTriangle size={28} />
      <h2>Something went wrong</h2>
      <p>{message}</p>
      <button type="button" className="btn-primary" onClick={onRetry}>
        <RotateCcw size={16} />
        <span>Try again</span>
      </button>
    </div>
  );
}
