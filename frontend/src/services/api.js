import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

function extractErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
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

export async function runAnalysis(resumeId, jobId) {
  try {
    const { data } = await client.post("/api/analysis/run", { resume_id: resumeId, job_id: jobId });
    return data;
  } catch (error) {
    throw new Error(extractErrorMessage(error, "Failed to run analysis."));
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
