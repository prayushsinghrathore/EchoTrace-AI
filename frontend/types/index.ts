/**
 * Core type definitions for EchoTrace AI.
 *
 * Shared types used across the frontend application.
 */

/* ── API Response Types ────────────────────────────────────────────────── */

export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  status: "success" | "error";
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  error_code?: string;
  status_code: number;
  timestamp: string;
}

/* ── Health Check ──────────────────────────────────────────────────────── */

export interface ServiceStatus {
  name: string;
  status: "healthy" | "unhealthy" | "degraded";
  latency_ms?: number;
  details?: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  environment: string;
  timestamp: string;
  services: ServiceStatus[];
  uptime_seconds: number;
}

/* ── Theme Types ───────────────────────────────────────────────────────── */

export type Theme = "light" | "dark" | "system";

/* ── Utility Types ─────────────────────────────────────────────────────── */

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Nullable<T> = T | null;

export type Optional<T> = T | undefined;
