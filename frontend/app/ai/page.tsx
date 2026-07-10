"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAIProviders,
  listJobs,
  getAIUsage,
  summarizeEvidence,
  extractEntities,
  AIJob,
} from "@/lib/ai-client";
import { listWorkspaces } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

const JOB_STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  completed: "success",
  running: "warning",
  queued: "secondary",
  failed: "destructive",
  cancelled: "outline",
};

export default function AIPage() {
  const queryClient = useQueryClient();
  const [selectedWs, setSelectedWs] = useState("");
  const [selectedEv, setSelectedEv] = useState("");
  const [evResult, setEvResult] = useState<AIJob | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const { data: providers } = useQuery({ queryKey: ["ai-providers"], queryFn: getAIProviders });
  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });

  const { data: jobs } = useQuery({
    queryKey: ["ai-jobs", selectedWs],
    queryFn: () => listJobs(selectedWs),
    enabled: !!selectedWs,
  });

  const { data: usage } = useQuery({
    queryKey: ["ai-usage", selectedWs],
    queryFn: () => getAIUsage(selectedWs),
    enabled: !!selectedWs,
  });

  const handleSummarize = async () => {
    if (!selectedEv) return;
    setAnalyzing(true);
    setEvResult(null);
    try {
      const job = await summarizeEvidence(selectedEv);
      setEvResult(job);
      queryClient.invalidateQueries({ queryKey: ["ai-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["ai-usage"] });
      if (job.status === "failed") {
        toast.error(`Analysis failed: ${job.error}`);
      } else {
        toast.success("Analysis complete");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const activeProvider = providers?.providers.find((p) => p.name === providers.active);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Intelligence Engine</h1>
        <p className="text-muted-foreground">
          AI-assisted analysis with human review — every suggestion requires your approval
        </p>
      </div>

      {/* Provider & Usage Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Provider</CardTitle>
          </CardHeader>
          <CardContent>
            {providers ? (
              <div>
                <div className="text-lg font-semibold capitalize">{providers.active}</div>
                <p className="text-xs text-muted-foreground">{activeProvider?.model || "N/A"}</p>
              </div>
            ) : (
              <Skeleton className="h-8 w-24" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {usage ? (
              <div className="text-3xl font-bold">{usage.total_jobs}</div>
            ) : (
              <Skeleton className="h-8 w-16" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
          </CardHeader>
          <CardContent>
            {usage ? (
              <div className="text-3xl font-bold">${usage.total_cost.toFixed(4)}</div>
            ) : (
              <Skeleton className="h-8 w-16" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Cache Hits</CardTitle>
          </CardHeader>
          <CardContent>
            {usage ? (
              <div className="text-3xl font-bold">{usage.cache_hits}</div>
            ) : (
              <Skeleton className="h-8 w-16" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Analyze */}
      <Card>
        <CardHeader>
          <CardTitle>Analyze Evidence</CardTitle>
          <CardDescription>Select a workspace and evidence item to analyze with AI</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Workspace</label>
              <select
                value={selectedWs}
                onChange={(e) => { setSelectedWs(e.target.value); setSelectedEv(""); }}
                className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Select workspace...</option>
                {workspaces?.map((ws) => (
                  <option key={ws.id} value={ws.id}>{ws.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button onClick={handleSummarize} disabled={!selectedEv || analyzing}>
              {analyzing ? "Analyzing..." : "Summarize"}
            </Button>
            <Button
              variant="outline"
              onClick={async () => {
                if (!selectedEv) return;
                setAnalyzing(true);
                try {
                  const job = await extractEntities(selectedEv);
                  setEvResult(job);
                  queryClient.invalidateQueries({ queryKey: ["ai-suggestions"] });
                  toast.success("Entity extraction complete — pending review");
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Extraction failed");
                } finally {
                  setAnalyzing(false);
                }
              }}
              disabled={!selectedEv || analyzing}
            >
              Extract Entities
            </Button>
          </div>

          {evResult && (
            <div className="rounded-md border p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium">Job Status:</span>
                <Badge variant={JOB_STATUS_COLORS[evResult.status] || "outline"}>
                  {evResult.status}
                </Badge>
                {evResult.cached && <Badge variant="outline">Cached</Badge>}
              </div>
              {evResult.latency_ms && (
                <p className="text-xs text-muted-foreground">
                  Latency: {evResult.latency_ms}ms | Tokens: {evResult.input_tokens ?? "?"} in /{" "}
                  {evResult.output_tokens ?? "?"} out | Cost: ${evResult.cost?.toFixed(6) ?? "0.00"}
                </p>
              )}
              {evResult.error && (
                <p className="mt-2 text-sm text-destructive">{evResult.error}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Jobs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent AI Jobs</CardTitle>
          <CardDescription>Recent analysis jobs and their status</CardDescription>
        </CardHeader>
        <CardContent>
          {!selectedWs ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              Select a workspace to view jobs.
            </p>
          ) : jobs && jobs.length > 0 ? (
            <div className="space-y-2">
              {jobs.slice(0, 10).map((job) => (
                <div key={job.id} className="flex items-center justify-between rounded-md border p-3 text-sm">
                  <div>
                    <span className="font-medium capitalize">{job.job_type.replace("_", " ")}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {job.model} · {job.input_tokens ?? "?"}t in / {job.output_tokens ?? "?"}t out
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {job.cached && <Badge variant="outline" className="text-[10px]">Cached</Badge>}
                    <Badge variant={JOB_STATUS_COLORS[job.status] || "outline"} className="text-[10px]">
                      {job.status}
                    </Badge>
                    {job.cost ? <span className="text-xs text-muted-foreground">${job.cost.toFixed(4)}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">No AI jobs yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
