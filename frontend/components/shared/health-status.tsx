"use client";

import { useHealth } from "@/hooks/use-health";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function HealthStatus() {
  const { health, isLoading, error } = useHealth();

  if (isLoading) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-lg">System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <div className="h-2 w-2 animate-pulse rounded-full bg-muted-foreground" />
            Checking system status...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-lg">System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge variant="destructive">Unreachable</Badge>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-lg">System Health</CardTitle>
        <Badge
          variant={
            health?.status === "healthy"
              ? "success"
              : health?.status === "degraded"
                ? "warning"
                : "destructive"
          }
        >
          {health?.status}
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {health?.services.map((service) => (
            <div
              key={service.name}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-muted-foreground">{service.name}</span>
              <div className="flex items-center gap-2">
                {service.latency_ms && (
                  <span className="text-xs text-muted-foreground">
                    {service.latency_ms}ms
                  </span>
                )}
                <Badge
                  variant={
                    service.status === "healthy"
                      ? "success"
                      : "destructive"
                  }
                  className="px-2 py-0 text-[10px]"
                >
                  {service.status}
                </Badge>
              </div>
            </div>
          ))}
          <div className="pt-2 text-xs text-muted-foreground">
            v{health?.version} &middot; {health?.environment}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
