import { BackendSettings, DiscoverResult, EmbeddingStatus, Job, JobStatus, OllamaStatus, Persona } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function extractErrorDetail(body: string): string {
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed?.detail === "string") return parsed.detail;
  } catch {
    // not JSON — fall through to raw text
  }
  return body;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers
    }
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(extractErrorDetail(body) || `Request to ${path} failed (${res.status}).`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listPersonas: () => request<Persona[]>("/personas"),

  createPersona: async (formData: FormData): Promise<Persona> => {
    const res = await fetch(`${API_BASE}/personas`, { method: "POST", body: formData });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(extractErrorDetail(body) || `Couldn't create persona (${res.status}).`);
    }
    return res.json();
  },

  deletePersona: (personaId: string) =>
    request<void>(`/personas/${personaId}`, { method: "DELETE" }),

  listJobs: (personaId?: string, status?: JobStatus) => {
    const params = new URLSearchParams();
    if (personaId) params.set("persona_id", personaId);
    if (status) params.set("status", status);
    const qs = params.toString();
    return request<Job[]>(qs ? `/jobs?${qs}` : "/jobs");
  },

  createJob: (payload: { personaId: string; title?: string; company?: string; jobDescription: string }) =>
    request<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify({
        persona_id: payload.personaId,
        title: payload.title ?? "",
        company: payload.company ?? "",
        job_description: payload.jobDescription
      })
    }),

  discoverJobs: (query: string, maxResults: number = 10) =>
    request<DiscoverResult[]>(
      `/jobs/discover?query=${encodeURIComponent(query)}&max_results=${maxResults}`
    ),

  importDiscoveredJob: (payload: { personaId: string; url: string; titleHint?: string; companyHint?: string }) =>
    request<Job>("/jobs/discover/import", {
      method: "POST",
      body: JSON.stringify({
        persona_id: payload.personaId,
        url: payload.url,
        title_hint: payload.titleHint ?? "",
        company_hint: payload.companyHint ?? ""
      })
    }),

  deleteJob: (jobId: string) => request<void>(`/jobs/${jobId}`, { method: "DELETE" }),

  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),

  updateJobStatus: (jobId: string, status: JobStatus) =>
    request<Job>(`/jobs/${jobId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    }),

  scoreJob: (personaId: string, jobTitle: string, company: string, jobDescription: string) =>
    request<{ score: number; tag: string; matches: unknown[]; gaps: unknown[] }>("/jobs/score", {
      method: "POST",
      body: JSON.stringify({
        persona_id: personaId,
        job_title: jobTitle,
        company,
        job_description: jobDescription
      })
    }),

  tailorJob: (personaId: string, jobId: string) =>
    request<{ bullet_before: string; bullet_after: string }>("/jobs/tailor", {
      method: "POST",
      body: JSON.stringify({ persona_id: personaId, job_id: jobId })
    }),

  generateOutreach: (personaId: string, jobId: string, contactName?: string, channel: string = "email") =>
    request<{ message: string }>("/jobs/outreach", {
      method: "POST",
      body: JSON.stringify({ persona_id: personaId, job_id: jobId, contact_name: contactName, channel })
    }),

  getOllamaStatus: () => request<OllamaStatus>("/ollama/status"),

  getEmbeddingStatus: () => request<EmbeddingStatus>("/embeddings/status"),

  switchOllamaMode: (mode: OllamaStatus["mode"]) =>
    request<OllamaStatus>("/ollama/status", {
      method: "PATCH",
      body: JSON.stringify({ mode })
    }),

  getSettings: () => request<BackendSettings>("/settings"),

  getSetupStatus: () => request<{ needs_setup: boolean; has_api_key: boolean }>("/settings/status/setup"),

  updateSettings: (payload: Partial<BackendSettings>) =>
    request<BackendSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(payload)
    })
};
