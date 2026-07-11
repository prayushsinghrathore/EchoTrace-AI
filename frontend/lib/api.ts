/**
 * HTTP API client for EchoTrace AI backend.
 *
 * Provides a typed fetch wrapper with error handling, request/response
 * interceptors, configurable base URL, retry with exponential backoff,
 * and AbortController-based request timeouts.
 */

import { siteConfig } from "@/config/site";
import type { ApiError, ApiResponse } from "@/types";

const DEFAULT_TIMEOUT_MS = 30_000; // 30 seconds
const MAX_RETRIES = 2;
const RETRYABLE_STATUSES = new Set([408, 429, 502, 503, 504]);

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = DEFAULT_TIMEOUT_MS,
    retries: number = MAX_RETRIES,
  ): Promise<T> {
    // Create an AbortController for timeout management
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    // Merge user-provided signal with our timeout signal
    const userSignal = options.signal;
    const combinedSignal = userSignal
      ? anySignal([controller.signal, userSignal])
      : controller.signal;

    const url = `${this.baseUrl}${endpoint}`;
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, {
          ...options,
          headers,
          signal: combinedSignal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const error: ApiError = await response.json().catch(() => ({
            detail: `HTTP ${response.status}`,
            status_code: response.status,
            timestamp: new Date().toISOString(),
          }));

          // Retry on server/rate-limit errors, bail on client errors
          if (
            attempt < retries &&
            RETRYABLE_STATUSES.has(response.status)
          ) {
            const delay = Math.min(1000 * 2 ** attempt, 8000);
            await sleep(delay);
            continue;
          }

          throw new ApiClientError(
            error.detail,
            response.status,
            error.error_code,
          );
        }

        return response.json() as Promise<T>;
      } catch (err) {
        clearTimeout(timeoutId);

        if (err instanceof ApiClientError) {
          throw err; // Already processed above — don't re-wrap
        }

        if (err instanceof DOMException && err.name === "AbortError") {
          throw new ApiClientError(
            `Request timed out after ${timeoutMs}ms`,
            0,
            "TIMEOUT",
          );
        }

        lastError = err as Error;

        // Retry on network errors
        if (attempt < retries) {
          const delay = Math.min(1000 * 2 ** attempt, 8000);
          await sleep(delay);
          continue;
        }
      }
    }

    throw new ApiClientError(
      lastError?.message || "Request failed",
      0,
      "NETWORK_ERROR",
    );
  }

  async get<T>(
    endpoint: string,
    params?: Record<string, string>,
    timeoutMs?: number,
  ) {
    const query = params ? `?${new URLSearchParams(params)}` : "";
    return this.request<T>(`${endpoint}${query}`, {}, timeoutMs);
  }

  async post<T>(
    endpoint: string,
    data?: unknown,
    timeoutMs?: number,
  ) {
    return this.request<T>(
      endpoint,
      {
        method: "POST",
        body: data ? JSON.stringify(data) : undefined,
      },
      timeoutMs,
    );
  }

  async put<T>(endpoint: string, data: unknown, timeoutMs?: number) {
    return this.request<T>(
      endpoint,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
      timeoutMs,
    );
  }

  async patch<T>(endpoint: string, data: unknown, timeoutMs?: number) {
    return this.request<T>(
      endpoint,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
      timeoutMs,
    );
  }

  async delete<T>(endpoint: string, timeoutMs?: number) {
    return this.request<T>(endpoint, { method: "DELETE" }, timeoutMs);
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

/**
 * Combine multiple AbortSignals into one.
 * The combined signal aborts when ANY input signal aborts.
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }
    signal.addEventListener("abort", () => controller.abort(signal.reason), {
      once: true,
    });
  }
  return controller.signal;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const api = new ApiClient(siteConfig.apiUrl);
