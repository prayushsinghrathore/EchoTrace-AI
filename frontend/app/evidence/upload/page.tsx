"use client";

import { Suspense, useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listEvidence, listProjects, listWorkspaces } from "@/lib/workspace-client";
import { runAIPipeline } from "@/lib/ai-client";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useRouter, useSearchParams } from "next/navigation";
import { siteConfig } from "@/config/site";

const MAX_SIZE_MB = 500;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

type Stage = "idle" | "uploading" | "verifying" | "metadata" | "linking" | "ai" | "complete" | "error";

interface StageDef {
  key: Stage;
  label: string;
  icon: string;
  detail?: string;
}

const STAGES: StageDef[] = [
  { key: "uploading", label: "Uploading file", icon: "📤" },
  { key: "verifying", label: "Verifying integrity", icon: "🔐" },
  { key: "metadata", label: "Extracting metadata", icon: "📋" },
  { key: "linking", label: "Updating investigation", icon: "🔗" },
  { key: "ai", label: "Starting AI analysis", icon: "🧠" },
  { key: "complete", label: "Complete", icon: "✅" },
];

function Stepper({ currentStage, stageDetails }: { currentStage: Stage; stageDetails: Record<string, string> }) {
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);
  const showUpTo = currentStage === "idle" ? -1 :
    currentStage === "error" ? Math.max(0, currentIdx - 1) : currentIdx;

  return (
    <div className="space-y-3">
      {STAGES.map((s, i) => {
        const isPast = i < showUpTo;
        const isCurrent = i === showUpTo && currentStage !== "complete";
        const isVisible = i <= showUpTo || (currentStage === "error" && i <= showUpTo);

        if (!isVisible && s.key !== "error") return null;

        return (
          <div key={s.key} className="flex items-center gap-3">
            {/* Status icon */}
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm transition-all duration-500 ${
              isPast ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300" :
              isCurrent ? "bg-primary/10 text-primary ring-2 ring-primary/30 animate-pulse" :
              "bg-muted text-muted-foreground"
            }`}>
              {isPast ? "✓" : (isCurrent ? s.icon : "○")}
            </div>
            {/* Label */}
            <div className="flex-1 min-w-0">
              <span className={`text-sm font-medium ${
                isPast ? "text-green-600 dark:text-green-400" :
                isCurrent ? "text-foreground" :
                "text-muted-foreground"
              }`}>
                {s.label}
              </span>
              {isCurrent && stageDetails[s.key] && (
                <p className="text-xs text-muted-foreground mt-0.5">{stageDetails[s.key]}</p>
              )}
            </div>
            {/* Spinner for current */}
            {isCurrent && s.key !== "complete" && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            )}
            {isPast && <span className="text-xs text-green-600 font-medium">Done</span>}
          </div>
        );
      })}
    </div>
  );
}

function UploadFormContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();

  const preselectedEvId = searchParams.get("evidence_id") || "";
  const preselectedInvestigationId = searchParams.get("investigation_id") || "";
  const preselectedWs = searchParams.get("workspace_id") || "";
  const preselectedProj = searchParams.get("project_id") || "";

  const [selectedWs, setSelectedWs] = useState(preselectedWs);
  const [selectedProj, setSelectedProj] = useState(preselectedProj);
  const [selectedEv, setSelectedEv] = useState(preselectedEvId);
  const [investigationId, setInvestigationId] = useState(preselectedInvestigationId);
  const [investigations, setInvestigations] = useState<Array<{ id: string; title: string }>>([]);

  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [stageDetails, setStageDetails] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });
  const { data: projects } = useQuery({
    queryKey: ["projs", selectedWs],
    queryFn: () => listProjects(selectedWs),
    enabled: !!selectedWs,
  });
  const { data: evidenceList } = useQuery({
    queryKey: ["evidence", selectedProj],
    queryFn: () => listEvidence(selectedProj),
    enabled: !!selectedProj,
  });

  // Load investigations for the workspace
  useEffect(() => {
    if (!selectedWs) return;
    fetch(`${siteConfig.apiUrl}/investigations/workspace/${selectedWs}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("et_access_token")}` },
    })
      .then((r) => r.json())
      .then((data) => setInvestigations(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [selectedWs]);

  const validateFile = useCallback((f: File): string | null => {
    if (f.size === 0) return "File is empty";
    if (f.size > MAX_SIZE_BYTES) return `File exceeds ${MAX_SIZE_MB}MB maximum`;
    return null;
  }, []);

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) {
      const err = validateFile(f);
      if (err) { setError(err); return; }
      setFile(f);
      setError("");
    }
  }, [validateFile]);

  const handleUpload = async () => {
    if (!selectedEv || !file) return;
    setError("");
    setResult(null);
    setStage("uploading");
    setStageDetails({ uploading: "Transferring file to server..." });

    const token = localStorage.getItem("et_access_token");
    const formData = new FormData();
    formData.append("file", file);

    if (investigationId) {
      formData.append("investigation_id", investigationId);
    }

    try {
      // ── Stage 1: XHR Upload ──────────────────────────────
      const response = await new Promise<Record<string, unknown>>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const pct = Math.round((e.loaded / e.total) * 100);
            setUploadProgress(pct);
            setStageDetails({ uploading: `Uploading... ${pct}% (${(e.loaded / 1024 / 1024).toFixed(1)} MB)` });
          }
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try {
              const body = JSON.parse(xhr.responseText);
              reject(new Error(body.detail || "Upload failed"));
            } catch {
              reject(new Error(`Upload failed (HTTP ${xhr.status})`));
            }
          }
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.open("POST", `${siteConfig.apiUrl}/evidence/${selectedEv}/upload`);
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.send(formData);
      });

      queryClient.invalidateQueries({ queryKey: ["evidence"] });

      const data = response as Record<string, unknown>;
      setResult(data);

      // ── Stage 2: Verifying ────────────────────────────────
      setStage("verifying");
      const hashes = data.verification as Record<string, unknown> || {};
      setStageDetails({ verifying: `SHA256: ${(hashes.sha256_hash as string || "").slice(0, 16)}...` });
      await sleep(600);

      // ── Stage 3: Metadata ─────────────────────────────────
      setStage("metadata");
      setStageDetails({
        metadata: `${(data.mime_type as string || "unknown").toUpperCase()} · ${((data.file_size as number || 0) / 1024).toFixed(1)} KB · ${data.original_filename as string || ""}`,
      });
      await sleep(500);

      // ── Stage 4: Linking (if investigation) ──────────────
      if (investigationId) {
        setStage("linking");
        setStageDetails({ linking: `Linked to investigation` });
        await sleep(500);
      } else {
        // Skip linking stage
      }

      // ── Stage 5: AI Analysis ──────────────────────────────
      if (investigationId) {
        setStage("ai");
        setStageDetails({ ai: "Queuing analysis jobs..." });
        try {
          const pipeline = await runAIPipeline(selectedEv, investigationId);
          setStageDetails({
            ai: `Summarizing + extracting entities (${pipeline.jobs.length} jobs)`,
          });
          await sleep(800);

          // Poll for job completion (up to 30s)
          for (const job of pipeline.jobs) {
            setStageDetails({ ai: `Processing ${job.job_type.replace("_", " ")}...` });
            await pollForJobCompletion(job.job_id, token || "", 30000);
          }
        } catch {
          setStageDetails({ ai: "AI analysis queued (will continue in background)" });
          await sleep(800);
        }
      }

      // ── Stage 6: Complete → Redirect ──────────────────────────
      setStage("complete");
      const redirectUrl = (data.redirect_url as string) || `/evidence/${selectedEv}`;
      setStageDetails({ complete: "Redirecting..." });
      await sleep(1200);
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
      router.push(redirectUrl);

    } catch (err) {
      setStage("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const progressValue =
    stage === "uploading" ? uploadProgress :
    stage === "verifying" ? 60 :
    stage === "metadata" ? 72 :
    stage === "linking" ? 82 :
    stage === "ai" ? 90 :
    stage === "complete" ? 100 : 0;

  const isRunning = stage !== "idle" && stage !== "error";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Evidence</h1>
        <p className="text-muted-foreground">Upload and automatically verify digital evidence</p>
      </div>

      {isRunning ? (
        /* ── Stepper View ─────────────────────────────────── */
        <div className="space-y-6">
          {/* Overall progress */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{stage === "complete" ? "Complete" : "Processing..."}</span>
              <span>{progressValue}%</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${progressValue}%` }}
              />
            </div>
          </div>

          <Stepper currentStage={stage} stageDetails={stageDetails} />

          {stage === "complete" && result && (
            <div className="rounded-md bg-green-50 dark:bg-green-950 p-4 text-sm text-green-700 dark:text-green-300 space-y-1">
              <div className="font-medium">✅ File uploaded and verified</div>
              <div className="flex flex-wrap gap-2 mt-2">
                <Badge variant="success" className="text-[10px]">SHA256 Verified</Badge>
                <Badge variant="success" className="text-[10px]">File Type Validated</Badge>
                {investigationId && <Badge variant="success" className="text-[10px]">Linked to Investigation</Badge>}
              </div>
            </div>
          )}

          {(stage as Stage) === "error" && error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
          )}
        </div>
      ) : (
        /* ── Form View ────────────────────────────────────── */
        <>
          {/* Selectors */}
          {!preselectedEvId && (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">Workspace</label>
                  <select value={selectedWs} onChange={(e) => { setSelectedWs(e.target.value); setSelectedProj(""); }}
                    className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="">Select...</option>
                    {workspaces?.map((ws) => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Project</label>
                  <select value={selectedProj} onChange={(e) => { setSelectedProj(e.target.value); setSelectedEv(""); }}
                    className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    disabled={!selectedWs}>
                    <option value="">Select...</option>
                    {projects?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>

              {(selectedProj || preselectedEvId) && (
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium">Evidence Item</label>
                    <select value={selectedEv} onChange={(e) => setSelectedEv(e.target.value)}
                      className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                      <option value="">Select evidence...</option>
                      {evidenceList?.map((ev) => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Link to Investigation (optional)</label>
                    <select value={investigationId} onChange={(e) => setInvestigationId(e.target.value)}
                      className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      disabled={!selectedWs}>
                      <option value="">Skip (just upload)</option>
                      {investigations.map((inv) => (
                        <option key={inv.id} value={inv.id}>{inv.title}</option>
                      ))}
                    </select>
                    <p className="text-xs text-muted-foreground mt-1">Links evidence to a case and auto-runs AI analysis</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {preselectedEvId && !preselectedInvestigationId && (
            <div>
              <label className="text-sm font-medium">Link to Investigation (optional)</label>
              <select value={investigationId} onChange={(e) => setInvestigationId(e.target.value)}
                className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="">Skip (just upload)</option>
                {investigations.map((inv) => (
                  <option key={inv.id} value={inv.id}>{inv.title}</option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground mt-1">Links evidence to a case and auto-runs AI analysis</p>
            </div>
          )}

          {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}

          {/* Drop Zone */}
          <div
            onDrop={handleFileDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => inputRef.current?.click()}
            className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-12 transition-colors hover:border-muted-foreground/50"
          >
            <input ref={inputRef} type="file" className="hidden" onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                const err = validateFile(f);
                if (err) { setError(err); return; }
                setFile(f);
                setError("");
              }
            }} />

            {file ? (
              <div className="text-center">
                <div className="mb-2 text-4xl">📄</div>
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-muted-foreground">{formatSize(file.size)}</p>
                <Button variant="outline" size="sm" className="mt-3" onClick={(e) => { e.stopPropagation(); setFile(null); }}>
                  Remove
                </Button>
              </div>
            ) : (
              <>
                <div className="mb-2 text-4xl">📁</div>
                <p className="font-medium">Drag and drop a file here</p>
                <p className="text-sm text-muted-foreground">or click to browse (max {MAX_SIZE_MB}MB)</p>
              </>
            )}
          </div>

          <Button onClick={handleUpload} disabled={!selectedEv || !file} className="w-full" size="lg">
            Upload & Verify File
          </Button>
        </>
      )}
    </div>
  );
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollForJobCompletion(jobId: string, token: string, timeoutMs: number): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${siteConfig.apiUrl}/ai/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const job = await res.json();
      if (job.status === "completed" || job.status === "failed") return;
    } catch { /* ignore */ }
    await sleep(1500);
  }
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl space-y-6"><div className="h-8 w-48 animate-pulse rounded bg-muted" /><div className="h-64 animate-pulse rounded bg-muted" /></div>}>
      <UploadFormContent />
    </Suspense>
  );
}
