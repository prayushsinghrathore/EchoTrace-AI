/**
 * HTTP API client for EchoTrace AI backend.
 *
 * Provides a typed fetch wrapper with error handling, request/response
 * interceptors, and configurable base URL.
 */

import { siteConfig } from "@/config/site";
import type { ApiError, ApiResponse } from "@/types";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}`,
        status_code: response.status,
        timestamp: new Date().toISOString(),
      }));
      throw new ApiClientError(error.detail, response.status, error.error_code);
    }

    return response.json() as Promise<T>;
  }

  async get<T>(endpoint: string, params?: Record<string, string>) {
    const query = params ? `?${new URLSearchParams(params)}` : "";
    return this.request<T>(`${endpoint}${query}`);
  }

  async post<T>(endpoint: string, data?: unknown) {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data: unknown) {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string) {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  async health() {
    return this.get<ApiResponse<unknown>>("/health");
  }
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorCode?: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export const api = new ApiClient(siteConfig.apiUrl);
