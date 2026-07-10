/**
 * Reports, Export, Notifications, Activity, and Search API client.
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

/* ── Notifications ──────────────────────────────────────────────────────── */

export interface Notification {
  id: string;
  user_id: string;
  workspace_id: string | null;
  notification_type: string;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  read_at: string | null;
  actor_id: string | null;
  created_at: string;
}

export interface NotificationsResponse {
  items: Notification[];
  total: number;
  skip: number;
  limit: number;
}

export function listNotifications(unreadOnly = false): Promise<NotificationsResponse> {
  return request(`${API}/reports/notifications?unread_only=${unreadOnly}`);
}

export function getUnreadCount(): Promise<{ count: number }> {
  return request(`${API}/reports/notifications/unread-count`);
}

export function markNotificationRead(id: string): Promise<Notification> {
  return request(`${API}/reports/notifications/${id}/read`, { method: "POST" });
}

export function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  return request(`${API}/reports/notifications/read-all`, { method: "POST" });
}

/* ── Reports ────────────────────────────────────────────────────────────── */

export interface ReportGenerateResponse {
  title: string;
  format: string;
  content: string;
  generated_at: string;
  statistics: Record<string, unknown>;
}

export function generateReport(
  investigationId: string,
  format = "markdown",
  includeAi = true
): Promise<ReportGenerateResponse> {
  return request(`${API}/reports/generate`, {
    method: "POST",
    body: JSON.stringify({
      investigation_id: investigationId,
      format,
      include_ai_findings: includeAi,
    }),
  });
}

/* ── Exports ────────────────────────────────────────────────────────────── */

export interface ExportJob {
  id: string;
  entity_type: string;
  entity_id: string;
  format: string;
  status: string;
  file_size: number | null;
  download_token: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export function createExport(
  entityType: string,
  entityId: string,
  format: string,
  workspaceId: string
): Promise<ExportJob> {
  return request(`${API}/reports/export`, {
    method: "POST",
    body: JSON.stringify({
      entity_type: entityType,
      entity_id: entityId,
      format,
      workspace_id: workspaceId,
    }),
  });
}

export function listExports(workspaceId: string): Promise<ExportJob[]> {
  return request(`${API}/reports/exports?workspace_id=${workspaceId}`);
}

/* ── Activity ───────────────────────────────────────────────────────────── */

export interface ActivityEvent {
  id: string;
  workspace_id: string;
  investigation_id: string | null;
  actor_id: string;
  event_type: string;
  title: string;
  description: string | null;
  occurred_at: string;
}

export interface ActivityResponse {
  items: ActivityEvent[];
  total: number;
  skip: number;
  limit: number;
}

export function getWorkspaceActivity(workspaceId: string): Promise<ActivityResponse> {
  return request(`${API}/reports/activity?workspace_id=${workspaceId}`);
}

export function getInvestigationActivity(investigationId: string): Promise<ActivityResponse> {
  return request(`${API}/reports/activity/investigation/${investigationId}`);
}

/* ── Analytics ──────────────────────────────────────────────────────────── */

export interface WorkspaceDashboard {
  total_investigations: number;
  open_investigations: number;
  in_progress_investigations: number;
  closed_investigations: number;
  total_evidence: number;
  total_entities: number;
  total_relationships: number;
  total_timeline_events: number;
  recent_activity: ActivityEvent[];
  top_investigators: Array<{ id: string; display_name: string | null; email: string; event_count: number }>;
}

export function getWorkspaceAnalytics(workspaceId: string): Promise<WorkspaceDashboard> {
  return request(`${API}/reports/analytics/workspace/${workspaceId}`);
}

/* ── Search ─────────────────────────────────────────────────────────────── */

export interface SearchResult {
  id: string;
  type: string;
  title: string;
  description: string | null;
  match_field: string | null;
  score: number;
  link: string;
  workspace_id: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export function globalSearch(q: string, entityType?: string): Promise<SearchResponse> {
  let qs = `q=${encodeURIComponent(q)}`;
  if (entityType) qs += `&entity_type=${entityType}`;
  return request(`${API}/reports/search?${qs}`);
}
