/**
 * AI Intelligence Engine API client.
 *
 * Provides typed functions for all AI operations including
 * analysis, job management, suggestions, and reports.
 */

import { siteConfig } from "@/config/site";

const API = siteConfig.apiUrl;

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("et_access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...opts,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(body.detail || "Request failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/* ── Types ──────────────────────────────────────────────────────────────── */

export interface AIProvider {
  name: string;
  display_name: string;
  available: boolean;
  model: string;
  supports_streaming: boolean;
}

export interface AIProvidersResponse {
  active: string;
  providers: AIProvider[];
}

export interface AIJob {
  id: string;
  user_id: string;
  workspace_id: string;
  investigation_id: string | null;
  job_type: string;
  status: string;
  provider: string;
  model: string;
  evidence_ids: string[] | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost: number | null;
  latency_ms: number | null;
  cached: boolean;
  error: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

export interface AISuggestion {
  id: string;
  job_id: string;
  investigation_id: string;
  suggestion_type: string;
  data: Record<string, unknown>;
  status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

export interface AIUsageStats {
  total_jobs: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
  total_tokens_input: number;
  total_tokens_output: number;
  total_cost: number;
  average_latency_ms: number;
  cache_hits: number;
  jobs_today: number;
  pending_suggestions: number;
}

export interface PromptVersion {
  id: string;
  name: string;
  version: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

/* ── Providers ──────────────────────────────────────────────────────────── */

export function getAIProviders(): Promise<AIProvidersResponse> {
  return request(`${API}/ai/providers`);
}

/* ── Prompts ────────────────────────────────────────────────────────────── */

export function listPrompts(): Promise<PromptVersion[]> {
  return request(`${API}/ai/prompts`);
}

export function getPromptContent(name: string): Promise<{ name: string; content: string }> {
  return request(`${API}/ai/prompts/${name}/content`);
}

/* ── Operations ─────────────────────────────────────────────────────────── */

export function summarizeEvidence(evidenceId: string, maxLength?: number): Promise<AIJob> {
  return request(`${API}/ai/summarize`, {
    method: "POST",
    body: JSON.stringify({ evidence_id: evidenceId, max_length: maxLength }),
  });
}

export function extractEntities(evidenceId: string, investigationId?: string): Promise<AIJob> {
  return request(`${API}/ai/entities`, {
    method: "POST",
    body: JSON.stringify({ evidence_id: evidenceId, investigation_id: investigationId }),
  });
}

export function suggestRelationships(
  investigationId: string,
  evidenceIds?: string[]
): Promise<AIJob> {
  return request(`${API}/ai/relationships`, {
    method: "POST",
    body: JSON.stringify({ investigation_id: investigationId, evidence_ids: evidenceIds }),
  });
}

export function generateTimeline(
  investigationId: string,
  evidenceIds?: string[]
): Promise<AIJob> {
  return request(`${API}/ai/timeline`, {
    method: "POST",
    body: JSON.stringify({ investigation_id: investigationId, evidence_ids: evidenceIds }),
  });
}

export function generateReport(investigationId: string): Promise<AIJob> {
  return request(`${API}/ai/report`, {
    method: "POST",
    body: JSON.stringify({ investigation_id: investigationId }),
  });
}

export function runAIPipeline(evidenceId: string, investigationId?: string): Promise<{
  pipeline: string;
  jobs: Array<{ job_type: string; job_id: string; status: string }>;
  evidence_id: string;
  investigation_id: string | null;
}> {
  let qs = `evidence_id=${evidenceId}`;
  if (investigationId) qs += `&investigation_id=${investigationId}`;
  return request(`${API}/ai/pipeline?${qs}`, { method: "POST" });
}

/* ── Jobs ───────────────────────────────────────────────────────────────── */

export function getJob(jobId: string): Promise<AIJob> {
  return request(`${API}/ai/jobs/${jobId}`);
}

export function listJobs(workspaceId: string): Promise<AIJob[]> {
  return request(`${API}/ai/jobs?workspace_id=${workspaceId}`);
}

/* ── Usage ──────────────────────────────────────────────────────────────── */

export function getAIUsage(workspaceId?: string): Promise<AIUsageStats> {
  const qs = workspaceId ? `?workspace_id=${workspaceId}` : "";
  return request(`${API}/ai/usage${qs}`);
}

/* ── Suggestions / Review ───────────────────────────────────────────────── */

export function listSuggestions(
  investigationId: string,
  status?: string
): Promise<AISuggestion[]> {
  let qs = `investigation_id=${investigationId}`;
  if (status) qs += `&status=${status}`;
  return request(`${API}/ai/suggestions?${qs}`);
}

export function approveSuggestion(suggestionId: string, notes?: string): Promise<AISuggestion> {
  return request(`${API}/ai/review/${suggestionId}/approve`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export function rejectSuggestion(suggestionId: string, notes?: string): Promise<AISuggestion> {
  return request(`${API}/ai/review/${suggestionId}/reject`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export function bulkReview(
  suggestionIds: string[],
  action: "approve" | "reject",
  notes?: string
): Promise<{ approved: number; rejected: number; errors: Array<{ suggestion_id: string; error: string }> }> {
  return request(`${API}/ai/review/bulk`, {
    method: "POST",
    body: JSON.stringify({ suggestion_ids: suggestionIds, action, notes }),
  });
}
