"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listEvidence, createEvidence, deleteEvidence, listWorkspaces, listProjects, getEvidenceStats } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  draft: "secondary",
  pending_review: "warning",
  verified: "success",
  rejected: "destructive",
  archived: "outline",
};

export default function EvidencePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedWs, setSelectedWs] = useState("");
  const [selectedProj, setSelectedProj] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("other");
  const [description, setDescription] = useState("");

  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });
  const { data: projects } = useQuery({
    queryKey: ["projs", selectedWs],
    queryFn: () => listProjects(selectedWs),
    enabled: !!selectedWs,
  });
  const { data: evList, isLoading } = useQuery({
    queryKey: ["evidence", selectedProj],
    queryFn: () => listEvidence(selectedProj),
    enabled: !!selectedProj,
  });
  const { data: stats } = useQuery({
    queryKey: ["ev-stats", selectedProj],
    queryFn: () => getEvidenceStats(selectedProj),
    enabled: !!selectedProj,
  });

  const createMut = useMutation({
    mutationFn: () => createEvidence({ project_id: selectedProj, title, category, description: description || undefined }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["evidence"] }); queryClient.invalidateQueries({ queryKey: ["ev-stats"] }); setShowForm(false); setTitle(""); setDescription(""); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteEvidence(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["evidence"] }); queryClient.invalidateQueries({ queryKey: ["ev-stats"] }); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Evidence</h1>
          <p className="text-muted-foreground">Manage digital evidence items</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} disabled={!selectedProj}>
          {showForm ? "Cancel" : "New Evidence"}
        </Button>
      </div>

      {/* Selectors */}
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Workspace</label>
          <select value={selectedWs} onChange={(e) => { setSelectedWs(e.target.value); setSelectedProj(""); }}
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
            <option value="">Select workspace...</option>
            {workspaces?.map((ws) => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Project</label>
          <select value={selectedProj} onChange={(e) => setSelectedProj(e.target.value)}
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
            <option value="">Select project...</option>
            {projects?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-5">
          <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Total</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold">{stats.total}</div></CardContent></Card>
          {Object.entries(stats.by_status).slice(0, 4).map(([k, v]) => (
            <Card key={k}><CardHeader className="pb-2"><CardTitle className="text-xs capitalize">{k.replace("_", " ")}</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-bold">{v as number}</div></CardContent></Card>
          ))}
        </div>
      )}

      {/* Create Form */}
      {showForm && selectedProj && (
        <Card>
          <CardContent className="pt-4">
            <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(); }} className="space-y-3">
              <input placeholder="Evidence title" value={title} onChange={(e) => setTitle(e.target.value)} required
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <div className="flex gap-3">
                <select value={category} onChange={(e) => setCategory(e.target.value)}
                  className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="document">Document</option>
                  <option value="image">Image</option>
                  <option value="video">Video</option>
                  <option value="audio">Audio</option>
                  <option value="archive">Archive</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)}
                className="flex h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <Button type="submit" disabled={createMut.isPending}>
                {createMut.isPending ? "Creating..." : "Create Evidence"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Evidence List */}
      {isLoading ? (
        <div className="space-y-2"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>
      ) : evList && evList.length > 0 ? (
        <div className="space-y-2">
          {evList.map((ev) => (
            <Card key={ev.id} className="hover-card cursor-pointer" onClick={() => router.push(`/evidence/${ev.id}`)}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{ev.title}</span>
                    <Badge variant={STATUS_COLORS[ev.status] || "outline"} className="text-[10px]">{ev.status}</Badge>
                    <Badge variant="outline" className="text-[10px]">{ev.priority}</Badge>
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="font-mono">{ev.evidence_number}</span>
                    <span>{ev.category}</span>
                    {ev.original_filename && <span>{ev.original_filename}</span>}
                    {ev.sha256_hash && <span className="font-mono">SHA256:{ev.sha256_hash.slice(0, 12)}...</span>}
                  </div>
                  {ev.tag_names.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {ev.tag_names.map((t) => (
                        <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-[10px]">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                  onClick={(e) => { e.stopPropagation(); if (confirm("Delete evidence?")) deleteMut.mutate(ev.id); }}>
                  ✕
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : selectedProj ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          No evidence in this project. Create evidence or upload files to get started.
        </CardContent></Card>
      ) : (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          Select a workspace and project to view evidence.
        </CardContent></Card>
      )}
    </div>
  );
}
