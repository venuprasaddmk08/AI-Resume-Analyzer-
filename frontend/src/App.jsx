import { useState } from "react";
import { Sparkles } from "lucide-react";
import UploadStep from "./components/UploadStep";
import LoadingProgress from "./components/LoadingProgress";
import ErrorState from "./components/ErrorState";
import ResultsDashboard from "./components/ResultsDashboard";
import { createJobDescriptionFromText, runAnalysis, uploadJobDescriptionFile, uploadResume } from "./services/api";
import "./App.css";

const STEPS = ["Uploading resume", "Submitting job description", "Matching skills & scoring"];

export default function App() {
  const [phase, setPhase] = useState("upload"); // upload | loading | results | error
  const [currentStep, setCurrentStep] = useState(0);
  const [analysis, setAnalysis] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [lastRequest, setLastRequest] = useState(null);

  async function handleAnalyze(request) {
    setLastRequest(request);
    setPhase("loading");
    setCurrentStep(0);
    setErrorMessage("");

    try {
      const resumeResult = await uploadResume(request.resumeFile);
      setCurrentStep(1);

      const jobResult =
        request.jdMode === "paste"
          ? await createJobDescriptionFromText(request.jdText)
          : await uploadJobDescriptionFile(request.jdFile);
      setCurrentStep(2);

      const analysisResult = await runAnalysis(resumeResult.resume_id, jobResult.job_id);

      setAnalysis(analysisResult);
      setPhase("results");
    } catch (err) {
      setErrorMessage(err.message || "An unexpected error occurred.");
      setPhase("error");
    }
  }

  function handleRetry() {
    if (lastRequest) {
      handleAnalyze(lastRequest);
    } else {
      setPhase("upload");
    }
  }

  function handleStartOver() {
    setPhase("upload");
    setAnalysis(null);
    setErrorMessage("");
    setLastRequest(null);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <Sparkles size={20} />
          <span>Resume & Career Intelligence</span>
        </div>
        {phase !== "upload" && (
          <p className="brand-tagline">Evidence-based job-fit analysis — not an official ATS score</p>
        )}
      </header>

      <main className="app-main">
        {phase === "upload" && (
          <div className="intro-panel">
            <h1>Understand your job fit, skill gaps, and interview readiness</h1>
            <p>Upload your resume and a job description to get an evidence-grounded compatibility analysis.</p>
            <UploadStep onAnalyze={handleAnalyze} disabled={false} />
          </div>
        )}

        {phase === "loading" && <LoadingProgress steps={STEPS} currentStep={currentStep} />}

        {phase === "error" && <ErrorState message={errorMessage} onRetry={handleRetry} />}

        {phase === "results" && analysis && (
          <ResultsDashboard analysis={analysis} jdRoleTitle={null} onStartOver={handleStartOver} />
        )}
      </main>
    </div>
  );
}
