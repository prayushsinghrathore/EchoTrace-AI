"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getEvidence, listComments, addComment, deleteComment, listCustody, deleteEvidence, restoreEvidence } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  draft: "secondary", pending_review: "warning", verified: "success", rejected: "destructive", archived: "outline",
};

export default function EvidenceDetailPage() {
  const params = useParams();
  const evId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [commentText, setCommentText] = useState("");
  const [tab, setTab] = useState<"details" | "comments" | "custody">("details");

  const { data: ev, isLoading } = useQuery({ queryKey: ["evidence", evId], queryFn: () => getEvidence(evId) });
  const { data: comments } = useQuery({ queryKey: ["comments", evId], queryFn: () => listComments(evId), enabled: tab === "comments" });
  const { data: custody } = useQuery({ queryKey: ["custody", evId], queryFn: () => listCustody(evId), enabled: tab === "custody" });

  const commentMut = useMutation({
    mutationFn: () => addComment(evId, commentText),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["comments"] }); setCommentText(""); },
  });

  const deleteCommentMut = useMutation({
    mutationFn: (id: string) => deleteComment(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["comments"] }),
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteEvidence(evId),
    onSuccess: () => router.push("/evidence"),
  });

  const restoreMut = useMutation({
    mutationFn: () => restoreEvidence(evId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evidence"] }),
  });

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;
  if (!ev) return <p>Evidence not found</p>;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/evidence")} className="hover:text-foreground">Evidence</button>
        <span>/</span>
        <span className="text-foreground">{ev.title}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{ev.title}</h1>
            <Badge variant={STATUS_COLORS[ev.status] || "outline"}>{ev.status}</Badge>
            <Badge variant="outline">{ev.priority}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground font-mono">{ev.evidence_number}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => router.push(`/evidence/upload?evidence_id=${ev.id}`)}>
            Upload File
          </Button>
          {ev.is_deleted ? (
            <Button size="sm" onClick={() => restoreMut.mutate()}>Restore</Button>
          ) : (
            <Button variant="destructive" size="sm" onClick={() => { if (confirm("Delete this evidence?")) deleteMut.mutate(); }}>
              Delete
            </Button>
          )}
        </div>
      </div>

      {/* Detail Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Category</CardTitle></CardHeader>
          <CardContent><div className="font-medium capitalize">{ev.category}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Status</CardTitle></CardHeader>
          <CardContent><div className="font-medium capitalize">{ev.status.replace("_", " ")}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Source</CardTitle></CardHeader>
          <CardContent><div className="font-medium">{ev.source || "—"}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Version</CardTitle></CardHeader>
          <CardContent><div className="font-medium">v{ev.current_version_number}</div></CardContent></Card>
      </div>

      {/* Hashes */}
      {(ev.sha256_hash || ev.md5_hash || ev.sha1_hash) && (
        <Card>
          <CardHeader><CardTitle>File Hashes</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {ev.sha256_hash && <div className="text-xs font-mono"><span className="font-semibold">SHA256:</span> {ev.sha256_hash}</div>}
            {ev.sha1_hash && <div className="text-xs font-mono"><span className="font-semibold">SHA1:</span> {ev.sha1_hash}</div>}
            {ev.md5_hash && <div className="text-xs font-mono"><span className="font-semibold">MD5:</span> {ev.md5_hash}</div>}
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button onClick={() => setTab("details")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "details" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Details
        </button>
        <button onClick={() => setTab("comments")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "comments" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Comments
        </button>
        <button onClick={() => setTab("custody")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "custody" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Chain of Custody
        </button>
      </div>

      {/* Tab Content */}
      {tab === "details" && (
        <Card>
          <CardHeader><CardTitle>Description</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm">{ev.description || "No description"}</p>
          </CardContent>
        </Card>
      )}

      {tab === "comments" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex gap-2">
                <input value={commentText} onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Add a comment..." className="flex-1 h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" />
                <Button onClick={() => commentMut.mutate()} disabled={!commentText.trim() || commentMut.isPending}>
                  {commentMut.isPending ? "..." : "Post"}
                </Button>
              </div>
            </CardContent>
          </Card>
          {comments && comments.length > 0 ? comments.map((c) => (
            <Card key={c.id}>
              <CardContent className="flex items-start justify-between p-4">
                <div>
                  <p className="text-sm">{c.body}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(c.created_at).toLocaleString()}{c.is_edited ? " (edited)" : ""}
                  </p>
                </div>
                <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                  onClick={() => deleteCommentMut.mutate(c.id)}>✕</Button>
              </CardContent>
            </Card>
          )) : (
            <p className="text-sm text-muted-foreground text-center py-4">No comments yet.</p>
          )}
        </div>
      )}

      {tab === "custody" && custody && (
        <div className="space-y-2">
          {custody.map((c) => (
            <Card key={c.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-bold uppercase">
                    {c.action[0]}
                  </div>
                  <div>
                    <div className="text-sm font-medium capitalize">{c.action.replace("_", " ")}</div>
                    <div className="text-xs text-muted-foreground">{c.notes || "—"}</div>
                  </div>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  <div>{new Date(c.timestamp).toLocaleString()}</div>
                  {c.ip_address && <div className="font-mono">{c.ip_address}</div>}
                </div>
              </CardContent>
            </Card>
          ))}
          {custody.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No custody events recorded.</p>}
        </div>
      )}
    </div>
  );
}
