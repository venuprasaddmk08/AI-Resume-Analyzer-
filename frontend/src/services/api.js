import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

function extractErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (error?.request && !error?.response) {
    return "Could not reach the server. Please check that the backend is running and try again.";
  }
  if (error?.message) return error.message;
  return fallback;
}

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const { data } = await client.post("/api/resume/upload", formData);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to upload resume."));
  }
}

export async function uploadJobDescriptionFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const { data } = await client.post("/api/jobs/upload", formData);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to upload job description."));
  }
}

export async function createJobDescriptionFromText(text) {
  try {
    const { data } = await client.post("/api/jobs/create", { text });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to submit job description text."));
  }
}

export async function analyzeResumeStructured(resumeId) {
  try {
    const { data } = await client.post("/api/resume/analyze", { resume_id: resumeId });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to analyze resume."));
  }
}

export async function analyzeJobDescription(jobId) {
  try {
    const { data } = await client.post("/api/jobs/analyze", { job_id: jobId });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to analyze job description."));
  }
}

export async function runAnalysis(resumeId, jobId) {
  try {
    const { data } = await client.post("/api/analysis/run", { resume_id: resumeId, job_id: jobId });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to run analysis."));
  }
}

export async function getAnalysisInsights(analysisId) {
  try {
    const { data } = await client.get(`/api/analysis/${analysisId}/insights`);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to load learning roadmap and interview questions."));
  }
}

export async function evaluateInterviewAnswer(analysisId, { question, basedOn, answer }) {
  try {
    const { data } = await client.post(`/api/analysis/${analysisId}/interview/evaluate`, {
      question,
      based_on: basedOn ?? null,
      answer,
    });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to evaluate your answer."));
  }
}

export async function getCareerIntelligence(resumeId) {
  try {
    const { data } = await client.get(`/api/resume/${resumeId}/career-intelligence`);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to load career intelligence."));
  }
}

export async function getResumeIntelligence(resumeId) {
  try {
    const { data } = await client.get(`/api/resume/${resumeId}/intelligence`);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to load resume intelligence."));
  }
}

export async function rewriteBullet(resumeId, bulletText) {
  try {
    const { data } = await client.post(`/api/resume/${resumeId}/bullets/rewrite`, { bullet_text: bulletText });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to rewrite bullet."));
  }
}

export async function getAtsRecruiterView(analysisId) {
  try {
    const { data } = await client.get(`/api/analysis/${analysisId}/ats`);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to load ATS/recruiter view."));
  }
}

export async function getExternalEvidence(resumeId) {
  try {
    const { data } = await client.get(`/api/resume/${resumeId}/external-evidence`);
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to load external evidence."));
  }
}

export async function checkLinkedInConsistency(resumeId, linkedinText) {
  try {
    const { data } = await client.post(`/api/resume/${resumeId}/linkedin-consistency`, {
      linkedin_text: linkedinText,
    });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to check LinkedIn consistency."));
  }
}

export async function checkHealth() {
  try {
    const { data } = await client.get("/health");
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Backend is unreachable."));
  }
}
