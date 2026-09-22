import { useEffect, useState } from "react";
import { MessageCircle, Info, Loader2, ThumbsUp, Lightbulb, ArrowRight, Sparkles } from "lucide-react";
import { evaluateInterviewAnswer } from "../services/api";

const IDLE_FEEDBACK = { status: "idle", evaluation: null, error: null };

export default function InterviewTab({ analysisId, insightsStatus, insights, insightsError, audience = "seeker" }) {
  const [answers, setAnswers] = useState({});
  const [questions, setQuestions] = useState([]);
  const [feedback, setFeedback] = useState({});

  useEffect(() => {
    if (insights?.interview_questions) {
      setQuestions(insights.interview_questions);
      setAnswers({});
      setFeedback({});
    }
  }, [insights]);

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

  if (questions.length === 0) {
    return <p className="empty-state">Not enough analysis data to generate practice questions yet.</p>;
  }

  const subject = audience === "provider" ? "this candidate's" : "your";
  const personalization = insights?.ai_generated ? "AI-personalized" : "Generic (AI was unavailable)";
  const introText =
    `${personalization} questions generated from ${subject} actual matched skills and gaps. ` +
    (audience === "provider"
      ? "Use this space to note expected answer points — there is no AI grading in this MVP."
      : "Write an answer, then request AI feedback and a follow-up question to keep practicing.");

  async function handleGetFeedback(index, question) {
    const answer = (answers[index] || "").trim();
    if (!answer) return;

    setFeedback((prev) => ({ ...prev, [index]: { status: "loading", evaluation: null, error: null } }));
    try {
      const { evaluation } = await evaluateInterviewAnswer(analysisId, {
        question: question.question,
        basedOn: question.based_on,
        answer,
      });
      setFeedback((prev) => ({ ...prev, [index]: { status: "success", evaluation, error: null } }));
    } catch (err) {
      setFeedback((prev) => ({
        ...prev,
        [index]: { status: "error", evaluation: null, error: err.message || "Failed to get feedback." },
      }));
    }
  }

  function handleAddFollowUp(followUpQuestion, basedOn) {
    setQuestions((prev) => [...prev, { category: "Follow-up", question: followUpQuestion, based_on: basedOn }]);
  }

  return (
    <div className="interview-tab">
      <p className="tab-intro">
        <Info size={14} /> {introText}
      </p>

      <div className="interview-list">
        {questions.map((q, i) => {
          const fb = feedback[i] || IDLE_FEEDBACK;
          const hasAnswer = (answers[i] || "").trim().length > 0;
          return (
            <div className="interview-card" key={i}>
              <div className="interview-card-head">
                <MessageCircle size={16} />
                <span className="interview-category">{q.category}</span>
                {q.based_on && <span className="interview-basis">based on: {q.based_on}</span>}
              </div>
              <p className="interview-question">{q.question}</p>
              <textarea
                className="interview-answer"
                placeholder={
                  audience === "provider" ? "Notes on expected answer or candidate's response..." : "Type your answer here to practice..."
                }
                rows={3}
                value={answers[i] || ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [i]: e.target.value }))}
              />

              <button
                type="button"
                className="btn-secondary interview-feedback-btn"
                disabled={!hasAnswer || fb.status === "loading"}
                onClick={() => handleGetFeedback(i, q)}
              >
                {fb.status === "loading" ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                <span>{fb.status === "loading" ? "Getting feedback..." : "Get feedback"}</span>
              </button>

              {fb.status === "error" && <p className="interview-feedback-error">{fb.error}</p>}

              {fb.status === "success" && fb.evaluation && (
                <div className="interview-feedback">
                  {!fb.evaluation.ai_generated && (
                    <p className="interview-feedback-note">Generic tips shown — AI feedback was unavailable.</p>
                  )}
                  {fb.evaluation.strengths.length > 0 && (
                    <div className="interview-feedback-section">
                      <h4>
                        <ThumbsUp size={13} /> Strengths
                      </h4>
                      <ul>
                        {fb.evaluation.strengths.map((s, si) => (
                          <li key={si}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {fb.evaluation.improvements.length > 0 && (
                    <div className="interview-feedback-section">
                      <h4>
                        <Lightbulb size={13} /> Ways to improve
                      </h4>
                      <ul>
                        {fb.evaluation.improvements.map((s, si) => (
                          <li key={si}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {fb.evaluation.follow_up_question && (
                    <div className="interview-followup">
                      <p>
                        <strong>Follow-up:</strong> {fb.evaluation.follow_up_question}
                      </p>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => handleAddFollowUp(fb.evaluation.follow_up_question, q.based_on)}
                      >
                        <ArrowRight size={13} />
                        <span>Add to practice list</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
