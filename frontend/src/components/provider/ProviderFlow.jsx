import { useState } from "react";
import JobDescriptionStep from "./JobDescriptionStep";
import CandidateUploadStep from "./CandidateUploadStep";
import CandidateFitness from "./CandidateFitness";
import LoadingProgress from "../LoadingProgress";
import ErrorState from "../ErrorState";
import {
  analyzeJobDescription,
  analyzeResumeStructured,
  createJobDescriptionFromText,
  runAnalysis,
  uploadJobDescriptionFile,
  uploadResume,
} from "../../services/api";

const STEPS = ["Uploading resume", "Extracting candidate profile", "Matching skills & scoring"];

let candidateCounter = 0;

export default function ProviderFlow() {
  const [phase, setPhase] = useState("jd-setup"); // jd-setup | candidate-upload | loading | fitness | error
  const [currentStep, setCurrentStep] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [jdRoleTitle, setJdRoleTitle] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [lastResumeFile, setLastResumeFile] = useState(null);

  async function handleJdContinue(request) {
    setPhase("loading");
    setCurrentStep(0);
    setErrorMessage("");
    try {
      const jobResult =
        request.jdMode === "paste" ? await createJobDescriptionFromText(request.jdText) : await uploadJobDescriptionFile(request.jdFile);
      setJobId(jobResult.job_id);
      setCandidates([]);
      setSelectedId(null);

      // Best-effort role title for display only — matching itself doesn't
      // depend on this, so a failure here shouldn't block the flow.
      try {
        const jobAnalysis = await analyzeJobDescription(jobResult.job_id);
        setJdRoleTitle(jobAnalysis.analysis?.role_title || null);
      } catch {
        setJdRoleTitle(null);
      }

      setPhase("candidate-upload");
    } catch (err) {
      setErrorMessage(err.message || "An unexpected error occurred.");
      setPhase("error");
    }
  }

  async function analyzeCandidate(resumeFile) {
    setLastResumeFile(resumeFile);
    setPhase("loading");
    setCurrentStep(0);
    setErrorMessage("");
    try {
      const resumeResult = await uploadResume(resumeFile);
      setCurrentStep(1);

      const resumeAnalysis = await analyzeResumeStructured(resumeResult.resume_id);
      setCurrentStep(2);

      const analysis = await runAnalysis(resumeResult.resume_id, jobId);

      const newCandidate = {
        id: ++candidateCounter,
        resumeId: resumeResult.resume_id,
        filename: resumeResult.filename,
        resumeAnalysis: resumeAnalysis.analysis,
        analysis,
      };
      setCandidates((prev) => [...prev, newCandidate]);
      setSelectedId(newCandidate.id);
      setPhase("fitness");
    } catch (err) {
      setErrorMessage(err.message || "An unexpected error occurred.");
      setPhase("error");
    }
  }

  function handleRetry() {
    if (phase === "error" && lastResumeFile) {
      analyzeCandidate(lastResumeFile);
    } else {
      setPhase(candidates.length > 0 ? "fitness" : "candidate-upload");
    }
  }

  function handleChangeJd() {
    setPhase("jd-setup");
    setJobId(null);
    setCandidates([]);
    setSelectedId(null);
    setJdRoleTitle(null);
  }

  function handleAddCandidate() {
    setPhase("candidate-upload");
  }

  return (
    <div className="provider-flow">
      {phase === "jd-setup" && <JobDescriptionStep onContinue={handleJdContinue} disabled={false} />}

      {phase === "candidate-upload" && (
        <CandidateUploadStep
          onAnalyze={analyzeCandidate}
          onChangeJd={handleChangeJd}
          disabled={false}
          candidateNumber={candidates.length + 1}
        />
      )}

      {phase === "loading" && <LoadingProgress steps={STEPS} currentStep={currentStep} />}

      {phase === "error" && <ErrorState message={errorMessage} onRetry={handleRetry} />}

      {phase === "fitness" && (
        <CandidateFitness
          candidates={candidates}
          selectedId={selectedId}
          onSelectCandidate={setSelectedId}
          onAddCandidate={handleAddCandidate}
          onChangeJd={handleChangeJd}
          jdRoleTitle={jdRoleTitle}
        />
      )}
    </div>
  );
}
