"use client";

import { Suspense, useState, useRef, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listEvidence, listProjects, listWorkspaces } from "@/lib/workspace-client";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";

const MAX_SIZE_MB = 500;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

function UploadFormContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const preselectedEvId = searchParams.get("evidence_id") || "";

  const [selectedWs, setSelectedWs] = useState("");
  const [selectedProj, setSelectedProj] = useState("");
  const [selectedEv, setSelectedEv] = useState(preselectedEvId);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
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
    setUploading(true);
    setError("");
    setSuccess("");
    setProgress(10);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const token = localStorage.getItem("et_access_token");
      const xhr = new XMLHttpRequest();

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 80) + 10);
      };

      await new Promise<void>((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            setProgress(100);
            setSuccess(`File "${file.name}" uploaded successfully`);
            queryClient.invalidateQueries({ queryKey: ["evidence"] });
            setTimeout(() => router.push(`/evidence/${selectedEv}`), 1500);
            resolve();
          } else {
            try {
              const body = JSON.parse(xhr.responseText);
              reject(new Error(body.detail || "Upload failed"));
            } catch {
              reject(new Error("Upload failed"));
            }
          }
        };
        xhr.onerror = () => reject(new Error("Network error"));
        xhr.open("POST", `${process.env.NEXT_PUBLIC_API_URL}/evidence/${selectedEv}/upload`);
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.send(formData);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Evidence</h1>
        <p className="text-muted-foreground">Upload a file and attach it to an evidence item</p>
      </div>

      {!preselectedEvId && (
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
              className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="">Select...</option>
              {projects?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </div>
      )}

      {(preselectedEvId || selectedProj) && (
        <div>
          <label className="text-sm font-medium">Evidence Item</label>
          {!preselectedEvId ? (
            <select value={selectedEv} onChange={(e) => setSelectedEv(e.target.value)}
              className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="">Select evidence...</option>
              {evidenceList?.map((ev) => <option key={ev.id} value={ev.id}>{ev.title} ({ev.evidence_number})</option>)}
            </select>
          ) : (
            <p className="mt-1 text-sm text-muted-foreground">Evidence ID: {preselectedEvId}</p>
          )}
        </div>
      )}

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

      {error && <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}
      {success && <div className="rounded-md bg-green-50 p-3 text-sm text-green-700">{success}</div>}

      {/* Progress Bar */}
      {uploading && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Uploading...</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full w-0 rounded-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      <Button onClick={handleUpload} disabled={!selectedEv || !file || uploading} className="w-full" size="lg">
        {uploading ? "Uploading..." : "Upload File"}
      </Button>
    </div>
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl space-y-6"><div className="h-8 w-48 animate-pulse rounded bg-muted" /><div className="h-64 animate-pulse rounded bg-muted" /></div>}>
      <UploadFormContent />
    </Suspense>
  );
}
