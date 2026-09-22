import { useMemo, useState } from "react";
import { MessageCircle, Info } from "lucide-react";
import { generateInterviewQuestions } from "../utils/deriveInsights";

export default function InterviewTab({ analysis, jdRoleTitle }) {
  const questions = useMemo(() => generateInterviewQuestions(analysis, jdRoleTitle), [analysis, jdRoleTitle]);
  const [answers, setAnswers] = useState({});

  if (questions.length === 0) {
    return <p className="empty-state">Not enough analysis data to generate practice questions yet.</p>;
  }

  return (
    <div className="interview-tab">
      <p className="tab-intro">
        <Info size={14} /> Practice questions generated from your actual matched skills and gaps. This is a writing
        space for your own practice — there is no AI grading of your answers in this MVP.
      </p>

      <div className="interview-list">
        {questions.map((q, i) => (
          <div className="interview-card" key={i}>
            <div className="interview-card-head">
              <MessageCircle size={16} />
              <span className="interview-category">{q.category}</span>
              {q.basedOn && <span className="interview-basis">based on: {q.basedOn}</span>}
            </div>
            <p className="interview-question">{q.question}</p>
            <textarea
              className="interview-answer"
              placeholder="Type your answer here to practice..."
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
