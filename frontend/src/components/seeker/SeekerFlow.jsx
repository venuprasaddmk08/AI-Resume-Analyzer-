import { useState } from "react";
import UploadStep from "../UploadStep";
import LoadingProgress from "../LoadingProgress";
import ErrorState from "../ErrorState";
import ResultsDashboard from "../ResultsDashboard";
import { createJobDescriptionFromText, refineAnalysis, runAnalysis, uploadJobDescriptionFile, uploadResume } from "../../services/api";

const STEPS = ["Uploading resume", "Submitting job description", "Matching skills & scoring"];

export default function SeekerFlow() {
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

      // The baseline above is fast (no AI adjudication of ambiguous
      // matches). Refine it in the background so the results page is
      // already on screen while any PARTIAL matches get a second look.
      refineAnalysis(analysisResult.analysis_id)
        .then((refined) => {
          setAnalysis((prev) => (prev && prev.analysis_id === refined.analysis_id ? refined : prev));
        })
        .catch(() => {
          // Best-effort only — the baseline result already rendered and
          // stands on its own if refinement fails.
        });
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
    <>
      {phase === "upload" && (
        <div className="intro-panel">
          <h1>Understand your job fit, skill gaps, and interview readiness</h1>
          <p>Upload your resume and a job description to get an evidence-grounded compatibility analysis.</p>
          <UploadStep onAnalyze={handleAnalyze} disabled={false} />
        </div>
      )}

      {phase === "loading" && <LoadingProgress steps={STEPS} currentStep={currentStep} />}

      {phase === "error" && <ErrorState message={errorMessage} onRetry={handleRetry} />}

      {phase === "results" && analysis && <ResultsDashboard analysis={analysis} onStartOver={handleStartOver} />}
    </>
  );
}
