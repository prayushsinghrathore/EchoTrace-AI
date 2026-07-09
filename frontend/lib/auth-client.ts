/**
 * Auth API client for EchoTrace AI.
 *
 * Provides typed functions for login, register, refresh, logout,
 * and profile management.
 */

import { siteConfig } from "@/config/site";

const API_URL = siteConfig.apiUrl;

/* ── Types ──────────────────────────────────────────────────────────────── */

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  status: string;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface ProfileUpdate {
  display_name?: string;
  avatar_url?: string;
}

/* ── Token Storage ──────────────────────────────────────────────────────── */

const ACCESS_TOKEN_KEY = "et_access_token";
const REFRESH_TOKEN_KEY = "et_refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/* ── Auth Client ────────────────────────────────────────────────────────── */

class AuthClientError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorCode?: string,
  ) {
    super(message);
    this.name = "AuthClientError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({
      detail: `HTTP ${response.status}`,
    }));
    throw new AuthClientError(
      body.detail || "Request failed",
      response.status,
      body.error_code,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/* ── API Functions ──────────────────────────────────────────────────────── */

export async function registerUser(
  data: RegisterRequest,
): Promise<UserProfile> {
  return request<UserProfile>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function loginUser(data: LoginRequest): Promise<TokenResponse> {
  const result = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
  setTokens(result.access_token, result.refresh_token);
  return result;
}

export async function refreshTokens(): Promise<TokenResponse> {
  const storedRefresh = getRefreshToken();
  if (!storedRefresh) {
    throw new AuthClientError("No refresh token available", 401);
  }

  const result = await request<TokenResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: storedRefresh }),
  });
  setTokens(result.access_token, result.refresh_token);
  return result;
}

export async function logoutUser(): Promise<void> {
  try {
    await request<void>("/auth/logout", { method: "POST" });
  } finally {
    clearTokens();
  }
}

export async function getProfile(): Promise<UserProfile> {
  return request<UserProfile>("/users/me");
}

export async function updateProfile(
  data: ProfileUpdate,
): Promise<UserProfile> {
  return request<UserProfile>("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  return request<void>("/users/me/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export type { AuthClientError };
