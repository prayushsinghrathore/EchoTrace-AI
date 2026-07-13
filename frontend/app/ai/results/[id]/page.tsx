"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { getEvidence } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { siteConfig } from "@/config/site";

/* ── Risk Score Gauge ─────────────────────────────────────────────────── */

function RiskGauge({ score, label }: { score: number; label: string }) {
  const color = score >= 70 ? "text-red-500" : score >= 40 ? "text-yellow-500" : "text-green-500";
  const bg = score >= 70 ? "stroke-red-500" : score >= 40 ? "stroke-yellow-500" : "stroke-green-500";
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative h-24 w-24">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" fill="none" stroke="currentColor" strokeWidth="8"
            className="text-muted/30" />
          <circle cx="50" cy="50" r="40" fill="none" strokeWidth="8"
            className={bg}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 1s ease-out" }}
          />
        </svg>
        <div className={`absolute inset-0 flex items-center justify-center text-2xl font-bold ${color}`}>
          {score}
        </div>
      </div>
      <span className="text-xs text-muted-foreground font-medium">{label}</span>
    </div>
  );
}

/* ── Entity Card ──────────────────────────────────────────────────────── */

const ENTITY_ICONS: Record<string, string> = {
  person: "👤", email: "📧", phone: "📱", device: "💻", file: "📄",
  domain: "🌐", url: "🔗", ip: "🌍", hash: "#️⃣", account: "👥",
  location: "📍", custom: "📌",
};

const ENTITY_COLORS: Record<string, string> = {
  person: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  email: "bg-amber-100 text-amber-700",
  phone: "bg-emerald-100 text-emerald-700",
  device: "bg-blue-100 text-blue-700",
  file: "bg-violet-100 text-violet-700",
  domain: "bg-pink-100 text-pink-700",
  url: "bg-teal-100 text-teal-700",
  ip: "bg-indigo-100 text-indigo-700",
  hash: "bg-lime-100 text-lime-700",
  account: "bg-orange-100 text-orange-700",
  location: "bg-green-100 text-green-700",
  custom: "bg-gray-100 text-gray-700",
};

function EntityBadge({ entity }: { entity: { type: string; label: string; confidence?: number } }) {
  const colorClass = ENTITY_COLORS[entity.type] || "bg-gray-100 text-gray-700";
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${colorClass}`}>
      <span>{ENTITY_ICONS[entity.type] || "📌"}</span>
      <span>{entity.label}</span>
      {entity.confidence != null && (
        <span className="opacity-60">({Math.round(entity.confidence * 100)}%)</span>
      )}
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────── */

export default function AIResultsPage() {
  const params = useParams();
  const evidenceId = params.id as string;
  const router = useRouter();

  const { data: evidence, isLoading: evLoading } = useQuery({
    queryKey: ["evidence", evidenceId],
    queryFn: () => getEvidence(evidenceId),
    enabled: !!evidenceId,
  });

  // Load latest AI jobs for this evidence
  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ["ai-jobs-for-evidence", evidenceId],
    queryFn: async () => {
      const res = await fetch(`${siteConfig.apiUrl}/ai/jobs?limit=20`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("et_access_token")}` },
      });
      const all = await res.json();
      // Filter for jobs related to this evidence
      return (Array.isArray(all) ? all : []).filter(
        (j: { evidence_ids?: string[] }) => j.evidence_ids?.includes(evidenceId)
      );
    },
    enabled: !!evidenceId,
  });

  const summarizeJob = Array.isArray(jobs)
    ? jobs.find((j: { job_type: string; status: string }) => j.job_type === "summarize" && j.status === "completed")
    : null;

  const entityJob = Array.isArray(jobs)
    ? jobs.find((j: { job_type: string; status: string }) => j.job_type === "extract_entities" && j.status === "completed")
    : null;

  const isLoading = evLoading || jobsLoading;
  const entityResult = entityJob?.result as Record<string, unknown> | undefined;
  const entities = (entityResult?.entities as Array<Record<string, unknown>>) || [];
  const summaryResult = summarizeJob?.result as Record<string, unknown> | undefined;
  const summaryText = (summaryResult?.summary as string) || "";
  const keyPoints = (summaryResult?.key_points as string[]) || [];

  // Derive risk score from entities and file properties
  const riskScore = evidence ? computeRiskScore(evidence, entities) : 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!evidence) return <p>Evidence not found</p>;

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/ai")} className="hover:text-foreground">AI Analysis</button>
        <span>/</span>
        <span className="text-foreground">{evidence.title}</span>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analysis Results</h1>
          <p className="text-muted-foreground">{evidence.evidence_number} · {evidence.category}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => window.open(`${siteConfig.apiUrl}/evidence/${evidenceId}/download`, "_blank")}>
            Download File
          </Button>
        </div>
      </div>

      {/* Risk Score + File Info Row */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground text-center">Risk Score</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <RiskGauge score={riskScore} label="Overall Risk" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">File Info</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div><span className="font-semibold">Name:</span> {evidence.original_filename || "—"}</div>
            <div><span className="font-semibold">Type:</span> {evidence.mime_type || "—"}</div>
            <div><span className="font-semibold">Size:</span> {evidence.file_size ? `${(evidence.file_size / 1024).toFixed(1)} KB` : "—"}</div>
            <div><span className="font-semibold">Status:</span> <Badge variant="success" className="text-[10px]">{evidence.status}</Badge></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Hashes</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {evidence.sha256_hash && (
              <div className="text-[10px] font-mono truncate" title={evidence.sha256_hash}>
                <span className="font-semibold">SHA256:</span> {evidence.sha256_hash.slice(0, 20)}...
              </div>
            )}
            {evidence.sha1_hash && (
              <div className="text-[10px] font-mono truncate" title={evidence.sha1_hash}>
                <span className="font-semibold">SHA1:</span> {evidence.sha1_hash.slice(0, 16)}...
              </div>
            )}
            {evidence.md5_hash && (
              <div className="text-[10px] font-mono truncate" title={evidence.md5_hash}>
                <span className="font-semibold">MD5:</span> {evidence.md5_hash.slice(0, 14)}...
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">AI Summary</CardTitle></CardHeader>
          <CardContent>
            {summaryText ? (
              <p className="text-sm line-clamp-3">{summaryText}</p>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>⏳</span>
                <span>No AI summary yet. Run analysis from the AI Intelligence page.</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Key Points */}
      {keyPoints.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Key Points</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {keyPoints.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 text-primary">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Indicators */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Entities / IOCs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Indicators of Compromise (IOCs)</CardTitle>
            <CardDescription>{entities.length} entities extracted by AI</CardDescription>
          </CardHeader>
          <CardContent>
            {entities.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {entities.map((e: Record<string, unknown>, i: number) => (
                  <EntityBadge key={i} entity={{ type: (e.type as string) || "custom", label: (e.label as string) || "unknown", confidence: (e.confidence as number) || 0.5 }} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No entities extracted yet. Use the AI Intelligence Engine to extract entities from this evidence.
              </p>
            )}
          </CardContent>
        </Card>

        {/* MITRE-like tactics */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Suspicious Indicators</CardTitle>
            <CardDescription>Automated analysis flags</CardDescription>
          </CardHeader>
          <CardContent>
            {entities.length > 0 ? (
              <div className="space-y-3">
                {/* Derive indicators from entity types */}
                {(() => {
                  const threatIps = entities.filter((e) => ["ip", "domain", "url"].includes((e.type as string) || ""));
                  const threatAll = entities.filter((e) => ["ip", "domain", "url", "hash", "email"].includes((e.type as string) || ""));
                  const hashes = entities.filter((e) => (e.type as string) === "hash");
                  const identities = entities.filter((e) => (e.type as string) === "person" || (e.type as string) === "email");
                  return (<>
                    {threatAll.length > 0 && (
                      <div className="flex items-start gap-3 rounded-md border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/50 p-3">
                        <span className="text-lg">🚨</span>
                        <div>
                          <p className="text-sm font-medium text-red-700 dark:text-red-400">Network Indicators Present</p>
                          <p className="text-xs text-red-600/70 dark:text-red-400/70">{threatIps.length} network artifacts found</p>
                        </div>
                      </div>
                    )}
                    {hashes.length > 0 && (
                      <div className="flex items-start gap-3 rounded-md border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/50 p-3">
                        <span className="text-lg">⚠️</span>
                        <div>
                          <p className="text-sm font-medium text-amber-700 dark:text-amber-400">File Hashes Found</p>
                          <p className="text-xs text-amber-600/70 dark:text-amber-400/70">Check against known threat intel feeds</p>
                        </div>
                      </div>
                    )}
                    {identities.length > 0 && (
                      <div className="flex items-start gap-3 rounded-md border border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/50 p-3">
                        <span className="text-lg">👤</span>
                        <div>
                          <p className="text-sm font-medium text-blue-700 dark:text-blue-400">Identity Artifacts</p>
                          <p className="text-xs text-blue-600/70 dark:text-blue-400/70">{identities.length} identities referenced</p>
                        </div>
                      </div>
                    )}
                  </>);
                })()}
                {entities.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-2">
                    Run entity extraction to see indicators.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No analysis data available.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Jobs Status */}
      {Array.isArray(jobs) && jobs.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Analysis Jobs</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(Array.isArray(jobs) ? jobs : []).map((job, i) => {
                const j = job as Record<string, unknown>;
                return (
                  <div key={i} className="flex items-center justify-between rounded-md border p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">{(j.job_type as string || "").replace(/_/g, " ")}</span>
                      {(j.cached as boolean) && <Badge variant="outline" className="text-[10px]">Cached</Badge>}
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={(j.status as string) === "completed" ? "success" : (j.status as string) === "failed" ? "destructive" : "secondary"} className="text-[10px]">
                        {j.status as string}
                      </Badge>
                      {j.cost !== undefined && j.cost !== null && (
                        <span className="text-xs text-muted-foreground">${Number(j.cost).toFixed(4)}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* CTA */}
      <div className="flex gap-3">
        <Button onClick={() => router.push(`/ai`)} variant="default">
          Full AI Intelligence Engine →
        </Button>
        {evidence.project_id && (
          <Button onClick={() => router.push(`/projects/${evidence.project_id}`)} variant="outline">
            View Project
          </Button>
        )}
      </div>
    </div>
  );
}

/* ── Risk Score Computation ───────────────────────────────────────────── */

function computeRiskScore(
  evidence: { mime_type?: string | null; file_size?: number | null; sha256_hash?: string | null; status?: string },
  entities: Record<string, unknown>[]
): number {
  let score = 10; // base

  // Executable/document macros → higher risk
  const highRiskMimes = [
    "application/x-msdownload", "application/x-msdos-program",
    "application/vnd.microsoft.portable-executable",
    "application/x-executable", "application/x-sh",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ];
  if (evidence.mime_type && highRiskMimes.some((m) => evidence.mime_type?.includes(m))) {
    score += 30;
  }

  // Archive files
  if (evidence.mime_type?.includes("zip") || evidence.mime_type?.includes("rar") || evidence.mime_type?.includes("tar")) {
    score += 15;
  }

  // Large files can hide more data
  if ((evidence.file_size || 0) > 10 * 1024 * 1024) score += 10;
  if ((evidence.file_size || 0) > 100 * 1024 * 1024) score += 15;

  // Entities that indicate threats
  const threatTypes = ["ip", "domain", "url", "hash"];
  for (const entity of entities) {
    const eType = (entity.type as string) || "";
    const eConf = (entity.confidence as number) || 0.5;
    if (threatTypes.includes(eType) && eConf > 0.7) {
      score += 8;
    }
  }

  // Cap at 99
  return Math.min(99, score);
}
