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
