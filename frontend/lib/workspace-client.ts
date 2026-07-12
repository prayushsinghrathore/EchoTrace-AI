/**
 * Workspace management API client.
 */

import { siteConfig } from "@/config/site";

const API = siteConfig.apiUrl;

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("et_access_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ── Types ──────────────────────────────────────────────────────────────── */

export interface Organization {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  description: string | null;
  created_at: string;
  updated_at?: string;
}

export interface OrganizationCreate {
  name: string;
  slug: string;
  description?: string;
}

export interface Workspace {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceDetail extends Workspace {
  project_count: number;
  member_count: number;
}

export interface WorkspaceCreate {
  organization_id: string;
  name: string;
  slug: string;
  description?: string;
}

export interface Member {
  id: string;
  user_id: string;
  email: string;
  display_name: string | null;
  role: string;
  joined_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  workspace_id: string;
  name: string;
  slug: string;
  description?: string;
}

/* ── API Functions ──────────────────────────────────────────────────────── */

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

/* Organizations */
export function createOrg(data: OrganizationCreate): Promise<Organization> {
  return request(`${API}/organizations`, { method: "POST", body: JSON.stringify(data) });
}
export function listOrgs(): Promise<Organization[]> {
  return request(`${API}/organizations`);
}
export function getOrg(id: string): Promise<Organization> {
  return request(`${API}/organizations/${id}`);
}
export function deleteOrg(id: string): Promise<void> {
  return request(`${API}/organizations/${id}`, { method: "DELETE" });
}

/* Workspaces */
export function createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
  return request(`${API}/workspaces`, { method: "POST", body: JSON.stringify(data) });
}
export function listWorkspaces(): Promise<Workspace[]> {
  return request(`${API}/workspaces`);
}
export function getWorkspace(id: string): Promise<WorkspaceDetail> {
  return request(`${API}/workspaces/${id}`);
}
export function deleteWorkspace(id: string): Promise<void> {
  return request(`${API}/workspaces/${id}`, { method: "DELETE" });
}

/* Members */
export function listMembers(wsId: string): Promise<Member[]> {
  return request(`${API}/workspaces/${wsId}/members`);
}

/* Projects */
export function createProject(data: ProjectCreate): Promise<Project> {
  return request(`${API}/projects`, { method: "POST", body: JSON.stringify(data) });
}
export function listProjects(wsId: string): Promise<Project[]> {
  return request(`${API}/projects?workspace_id=${wsId}`);
}
export function getProject(id: string): Promise<Project> {
  return request(`${API}/projects/${id}`);
}
export function deleteProject(id: string): Promise<void> {
  return request(`${API}/projects/${id}`, { method: "DELETE" });
}

/* Evidence */
export interface EvidenceItem {
  id: string;
  project_id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  evidence_number: string;
  category: string;
  status: string;
  priority: string;
  source: string | null;
  sha256_hash: string | null;
  mime_type: string | null;
  file_size: number | null;
  original_filename: string | null;
  tag_names: string[];
  created_at: string;
}

export interface EvidenceDetail extends EvidenceItem {
  created_by: string;
  collector_id: string | null;
  sha1_hash: string | null;
  md5_hash: string | null;
  stored_filename: string | null;
  upload_timestamp: string | null;
  verification_timestamp: string | null;
  current_version_number: number;
  is_deleted: boolean;
  tags: string[];
  updated_at: string;
}

export interface EvidenceCreate {
  project_id: string;
  title: string;
  description?: string;
  category?: string;
  priority?: string;
  source?: string;
  collector_id?: string;
  tags?: string[];
}

export interface EvidenceComment {
  id: string;
  evidence_id: string;
  author_id: string;
  body: string;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustodyEvent {
  id: string;
  evidence_id: string;
  user_id: string;
  action: string;
  timestamp: string;
  ip_address: string | null;
  notes: string | null;
  details: string | null;
}

export interface EvidenceStats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  total_size_bytes: number;
  recent_uploads: number;
}

export function listEvidence(projectId: string, skip = 0, limit = 50): Promise<EvidenceItem[]> {
  return request(`${API}/evidence?project_id=${projectId}&skip=${skip}&limit=${limit}`);
}

export function getEvidence(id: string): Promise<EvidenceDetail> {
  return request(`${API}/evidence/${id}`);
}

export function createEvidence(data: EvidenceCreate): Promise<EvidenceDetail> {
  return request(`${API}/evidence`, { method: "POST", body: JSON.stringify(data) });
}

export function updateEvidence(id: string, data: Record<string, unknown>): Promise<EvidenceDetail> {
  return request(`${API}/evidence/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteEvidence(id: string): Promise<void> {
  return request(`${API}/evidence/${id}`, { method: "DELETE" });
}

export function restoreEvidence(id: string): Promise<EvidenceDetail> {
  return request(`${API}/evidence/${id}/restore`, { method: "POST" });
}

export function listComments(evId: string): Promise<EvidenceComment[]> {
  return request(`${API}/evidence/${evId}/comments`);
}

export function addComment(evId: string, body: string): Promise<EvidenceComment> {
  return request(`${API}/evidence/${evId}/comments`, { method: "POST", body: JSON.stringify({ body }) });
}

export function editComment(commentId: string, body: string): Promise<EvidenceComment> {
  return request(`${API}/evidence/comments/${commentId}`, { method: "PATCH", body: JSON.stringify({ body }) });
}

export function verifyEvidence(id: string, sha256?: string, sha1?: string, md5?: string): Promise<Record<string, unknown>> {
  const body: Record<string, string | undefined> = {};
  if (sha256) body.sha256_hash = sha256;
  if (sha1) body.sha1_hash = sha1;
  if (md5) body.md5_hash = md5;
  return request(`${API}/evidence/${id}/verify`, { method: "POST", body: JSON.stringify(body) });
}

export function listVersions(evId: string): Promise<EvidenceVersion[]> {
  return request(`${API}/evidence/${evId}/versions`);
}

export interface EvidenceVersion {
  id: string;
  evidence_id: string;
  version_number: number;
  created_by: string;
  original_filename: string | null;
  mime_type: string | null;
  file_size: number | null;
  sha256_hash: string | null;
  change_notes: string | null;
  created_at: string;
}

export function deleteComment(commentId: string): Promise<void> {
  return request(`${API}/evidence/comments/${commentId}`, { method: "DELETE" });
}

export function listCustody(evId: string): Promise<CustodyEvent[]> {
  return request(`${API}/evidence/${evId}/custody`);
}

export function getEvidenceStats(projectId: string): Promise<EvidenceStats> {
  return request(`${API}/evidence/stats/project/${projectId}`);
}

export function searchEvidence(params: Record<string, string>): Promise<{ items: EvidenceItem[]; total: number }> {
  const qs = new URLSearchParams(params).toString();
  return request(`${API}/evidence/search?${qs}`);
}

/* Dashboard */
export interface DashboardStats {
  org_count: number;
  workspace_count: number;
  project_count: number;
  member_count: number;
}

export function getDashboardStats(): Promise<DashboardStats> {
  return request(`${API}/dashboard/stats`);
}

/* ── Investigations ─────────────────────────────────────────────────────── */

export interface Investigation {
  id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  created_by: string;
  lead_investigator: string | null;
  opened_at: string | null;
  closed_at: string | null;
  entity_count: number;
  relationship_count: number;
  timeline_count: number;
  created_at: string;
}

export interface InvestigationCreate {
  workspace_id: string;
  title: string;
  description?: string;
  priority?: string;
}

export interface EntityItem {
  id: string;
  investigation_id: string;
  type: string;
  label: string;
  description: string | null;
  created_by: string;
  created_at: string;
}

export interface RelationshipItem {
  id: string;
  investigation_id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  confidence: number | null;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  investigation_id: string;
  event_timestamp: string;
  title: string;
  description: string | null;
  entity_id: string | null;
  evidence_id: string | null;
  created_at: string;
}

export interface GraphData {
  nodes: Array<{ id: string; label: string; type: string; color: string; icon: string }>;
  edges: Array<{ id: string; source: string; target: string; type: string; confidence: number | null }>;
}

export interface InvestigationDashboard {
  total: number;
  open: number;
  in_progress: number;
  closed: number;
  entities: number;
  relationships: number;
  timeline_events: number;
}

export function createInvestigation(data: InvestigationCreate): Promise<Investigation> {
  return request(`${API}/investigations`, { method: "POST", body: JSON.stringify(data) });
}

export function listInvestigations(wsId: string): Promise<Investigation[]> {
  return request(`${API}/investigations/workspace/${wsId}`);
}

export function getInvestigation(id: string): Promise<Investigation> {
  return request(`${API}/investigations/${id}`);
}

export function updateInvestigation(id: string, data: Record<string, unknown>): Promise<Investigation> {
  return request(`${API}/investigations/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteInvestigation(id: string): Promise<void> {
  return request(`${API}/investigations/${id}`, { method: "DELETE" });
}

export function getInvestigationDashboard(wsId: string): Promise<InvestigationDashboard> {
  return request(`${API}/investigations/dashboard/${wsId}`);
}

export function listEntities(invId: string): Promise<EntityItem[]> {
  return request(`${API}/investigations/${invId}/entities`);
}

export function createEntity(invId: string, data: { type: string; label: string; description?: string }): Promise<EntityItem> {
  return request(`${API}/investigations/${invId}/entities`, { method: "POST", body: JSON.stringify(data) });
}

export function deleteEntity(entityId: string): Promise<void> {
  return request(`${API}/investigations/entities/${entityId}`, { method: "DELETE" });
}

export function listRelationships(invId: string): Promise<RelationshipItem[]> {
  return request(`${API}/investigations/${invId}/relationships`);
}

export function createRelationship(invId: string, data: { source_entity_id: string; target_entity_id: string; relationship_type: string; confidence?: number }): Promise<RelationshipItem> {
  return request(`${API}/investigations/${invId}/relationships`, { method: "POST", body: JSON.stringify(data) });
}

export function deleteRelationship(relId: string): Promise<void> {
  return request(`${API}/investigations/relationships/${relId}`, { method: "DELETE" });
}

export function listTimelineEvents(invId: string): Promise<TimelineEvent[]> {
  return request(`${API}/investigations/${invId}/timeline`);
}

export function createTimelineEvent(invId: string, data: { event_timestamp: string; title: string; description?: string }): Promise<TimelineEvent> {
  return request(`${API}/investigations/${invId}/timeline`, { method: "POST", body: JSON.stringify(data) });
}

export function deleteTimelineEvent(eventId: string): Promise<void> {
  return request(`${API}/investigations/timeline/${eventId}`, { method: "DELETE" });
}

export function getGraph(invId: string): Promise<GraphData> {
  return request(`${API}/investigations/${invId}/graph`);
}
