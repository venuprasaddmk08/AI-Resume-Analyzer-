import { useState } from "react";
import { MessageCircle, Info, Loader2 } from "lucide-react";

export default function InterviewTab({ insightsStatus, insights, insightsError, audience = "seeker" }) {
  const [answers, setAnswers] = useState({});

  if (insightsStatus === "loading" || insightsStatus === "idle") {
    return (
      <div className="insights-loading">
        <Loader2 size={18} className="spin" />
        <span>Generating interview questions from the matched skills and gaps...</span>
      </div>
    );
  }

  if (insightsStatus === "error") {
    return <p className="empty-state">{insightsError || "Could not load interview questions."}</p>;
  }

  const questions = insights?.interview_questions || [];

  if (questions.length === 0) {
    return <p className="empty-state">Not enough analysis data to generate practice questions yet.</p>;
  }

  const subject = audience === "provider" ? "this candidate's" : "your";
  const personalization = insights?.ai_generated ? "AI-personalized" : "Generic (AI was unavailable)";
  const introText =
    `${personalization} questions generated from ${subject} actual matched skills and gaps. ` +
    (audience === "provider"
      ? "Use this space to note expected answer points — there is no AI grading in this MVP."
      : "This is a writing space for your own practice — there is no AI grading of your answers in this MVP.");

  return (
    <div className="interview-tab">
      <p className="tab-intro">
        <Info size={14} /> {introText}
      </p>

      <div className="interview-list">
        {questions.map((q, i) => (
          <div className="interview-card" key={i}>
            <div className="interview-card-head">
              <MessageCircle size={16} />
              <span className="interview-category">{q.category}</span>
              {q.based_on && <span className="interview-basis">based on: {q.based_on}</span>}
            </div>
            <p className="interview-question">{q.question}</p>
            <textarea
              className="interview-answer"
              placeholder={audience === "provider" ? "Notes on expected answer or candidate's response..." : "Type your answer here to practice..."}
              rows={3}
              value={answers[i] || ""}
              onChange={(e) => setAnswers((prev) => ({ ...prev, [i]: e.target.value }))}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
