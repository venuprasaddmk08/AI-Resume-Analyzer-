import { Check, Loader2, Circle } from "lucide-react";

// `currentStep` reflects real progress through the actual sequence of
// backend calls (see App.jsx) — not a fabricated animation unrelated to
// what's actually happening.
export default function LoadingProgress({ steps, currentStep }) {
  return (
    <div className="loading-panel">
      <h2>Analyzing your fit for this role</h2>
      <ul className="progress-steps">
        {steps.map((label, index) => {
          const state = index < currentStep ? "done" : index === currentStep ? "active" : "pending";
          return (
            <li key={label} className={`progress-step ${state}`}>
              <span className="progress-icon">
                {state === "done" && <Check size={16} />}
                {state === "active" && <Loader2 size={16} className="spin" />}
                {state === "pending" && <Circle size={12} />}
              </span>
              <span>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
