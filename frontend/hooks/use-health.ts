/**
 * Health check hook.
 *
 * Provides real-time health status polling and connection state.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/types";

interface UseHealthReturn {
  health: HealthResponse | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useHealth(pollIntervalMs: number = 30000): UseHealthReturn {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      setError(null);
      const data = await api.health();
      setHealth(data as unknown as HealthResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Health check failed");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, pollIntervalMs);
    return () => clearInterval(interval);
  }, [fetchHealth, pollIntervalMs]);

  return { health, isLoading, error, refetch: fetchHealth };
}
