"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getEvidence, listComments, addComment, editComment, deleteComment,
  listCustody, deleteEvidence, restoreEvidence, updateEvidence,
  verifyEvidence, listVersions,
} from "@/lib/workspace-client";
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
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editCommentText, setEditCommentText] = useState("");
  const [tab, setTab] = useState<"details" | "comments" | "custody" | "versions">("details");
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editStatus, setEditStatus] = useState("");
  const [editPriority, setEditPriority] = useState("");

  const { data: ev, isLoading } = useQuery({ queryKey: ["evidence", evId], queryFn: () => getEvidence(evId) });
  const { data: comments } = useQuery({ queryKey: ["comments", evId], queryFn: () => listComments(evId), enabled: tab === "comments" });
  const { data: custody } = useQuery({ queryKey: ["custody", evId], queryFn: () => listCustody(evId), enabled: tab === "custody" });
  const { data: versions } = useQuery({ queryKey: ["versions", evId], queryFn: () => listVersions(evId), enabled: tab === "versions" });

  const verifyMut = useMutation({
    mutationFn: () => verifyEvidence(evId, ev!.sha256_hash || undefined, ev!.sha1_hash || undefined, ev!.md5_hash || undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evidence"] }),
  });

  const commentMut = useMutation({
    mutationFn: () => addComment(evId, commentText),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["comments"] }); setCommentText(""); },
  });

  const editCommentMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) => editComment(id, body),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["comments"] }); setEditingCommentId(null); },
  });

  const deleteCommentMut = useMutation({
    mutationFn: (id: string) => deleteComment(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["comments"] }),
  });

  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateEvidence(evId, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["evidence"] }); setEditing(false); },
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

  const startEdit = () => {
    setEditTitle(ev.title);
    setEditDesc(ev.description || "");
    setEditCategory(ev.category);
    setEditStatus(ev.status);
    setEditPriority(ev.priority);
    setEditing(true);
  };

  const saveEdit = () => {
    const data: Record<string, unknown> = {};
    if (editTitle !== ev.title) data.title = editTitle;
    if (editDesc !== (ev.description || "")) data.description = editDesc || null;
    if (editCategory !== ev.category) data.category = editCategory;
    if (editStatus !== ev.status) data.status = editStatus;
    if (editPriority !== ev.priority) data.priority = editPriority;
    if (Object.keys(data).length > 0) updateMut.mutate(data);
    else setEditing(false);
  };

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
        <div className="flex-1">
          {editing ? (
            <div className="space-y-2 max-w-xl">
              <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-lg font-bold" />
              <div className="flex gap-2">
                <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm">
                  <option value="draft">Draft</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="verified">Verified</option>
                  <option value="rejected">Rejected</option>
                  <option value="archived">Archived</option>
                </select>
                <select value={editPriority} onChange={(e) => setEditPriority(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <select value={editCategory} onChange={(e) => setEditCategory(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm">
                  <option value="document">Document</option><option value="image">Image</option>
                  <option value="video">Video</option><option value="audio">Audio</option>
                  <option value="archive">Archive</option><option value="other">Other</option>
                </select>
              </div>
              <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)}
                className="w-full h-20 rounded-md border border-input bg-background px-3 py-2 text-sm"
                placeholder="Description" />
              <div className="flex gap-2">
                <Button size="sm" onClick={saveEdit} disabled={updateMut.isPending}>Save</Button>
                <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-bold tracking-tight">{ev.title}</h1>
                <Badge variant={STATUS_COLORS[ev.status] || "outline"}>{ev.status.replace("_", " ")}</Badge>
                <Badge variant="outline">{ev.priority}</Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground font-mono">{ev.evidence_number}</p>
            </>
          )}
        </div>
        <div className="flex gap-2 ml-4">
          {!editing && !ev.is_deleted && <Button variant="outline" size="sm" onClick={startEdit}>Edit</Button>}
          {ev.sha256_hash && !ev.is_deleted && (
            <Button variant="outline" size="sm" onClick={() => window.open(`/api/v1/evidence/${evId}/download`, "_blank")}>
              Download
            </Button>
          )}
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

      {/* File Info */}
      {ev.original_filename && (
        <Card>
          <CardHeader><CardTitle>File Information</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div><span className="font-semibold">Filename:</span> {ev.original_filename}</div>
            {ev.file_size && <div><span className="font-semibold">Size:</span> {(ev.file_size / 1024).toFixed(1)} KB</div>}
            {ev.mime_type && <div><span className="font-semibold">MIME:</span> {ev.mime_type}</div>}
            {ev.stored_filename && <div className="text-xs text-muted-foreground"><span className="font-semibold">Stored as:</span> {ev.stored_filename}</div>}
          </CardContent>
        </Card>
      )}

      {/* Hashes */}
      {(ev.sha256_hash || ev.md5_hash || ev.sha1_hash) && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>File Hashes</CardTitle>
            <div className="flex items-center gap-2">
              {verifyMut.isSuccess && <span className="text-xs text-green-500">✓ Verified</span>}
              <Button variant="outline" size="sm" onClick={() => verifyMut.mutate()} disabled={verifyMut.isPending}>
                {verifyMut.isPending ? "Verifying..." : "Verify"}
              </Button>
            </div>
          </CardHeader>
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
          Comments {comments ? `(${comments.length})` : ""}
        </button>
        <button onClick={() => setTab("custody")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "custody" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Chain of Custody
        </button>
        <button onClick={() => setTab("versions")} className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === "versions" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
          Versions {versions ? `(${versions.length})` : ""}
        </button>
      </div>

      {/* Tab: Details */}
      {tab === "details" && (
        <Card>
          <CardHeader><CardTitle>Description</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm whitespace-pre-wrap">{ev.description || "No description"}</p>
          </CardContent>
        </Card>
      )}

      {/* Tab: Comments */}
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
                {editingCommentId === c.id ? (
                  <div className="flex-1 flex gap-2">
                    <input value={editCommentText} onChange={(e) => setEditCommentText(e.target.value)}
                      className="flex-1 h-8 rounded-md border border-input bg-background px-2 text-sm" />
                    <Button size="sm" onClick={() => editCommentMut.mutate({ id: c.id, body: editCommentText })}>Save</Button>
                    <Button size="sm" variant="outline" onClick={() => setEditingCommentId(null)}>Cancel</Button>
                  </div>
                ) : (
                  <div className="flex-1">
                    <p className="text-sm">{c.body}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(c.created_at).toLocaleString()}{c.is_edited ? " (edited)" : ""}
                    </p>
                  </div>
                )}
                <div className="flex gap-1 ml-2">
                  {editingCommentId !== c.id && (
                    <Button variant="ghost" size="icon" className="h-6 w-6"
                      onClick={() => { setEditingCommentId(c.id); setEditCommentText(c.body); }}>
                      ✏️
                    </Button>
                  )}
                  {editingCommentId !== c.id && (
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                      onClick={() => deleteCommentMut.mutate(c.id)}>✕</Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )) : (
            <p className="text-sm text-muted-foreground text-center py-4">No comments yet.</p>
          )}
        </div>
      )}

      {/* Tab: Custody */}
      {tab === "versions" && versions && (
        <div className="space-y-2">
          {versions.length > 0 ? versions.map((v) => (
            <Card key={v.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-bold">
                      v{v.version_number}
                    </div>
                    <div>
                      <div className="text-sm font-medium">{v.original_filename || "No file"}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(v.created_at).toLocaleString()}
                        {v.file_size ? ` · ${(v.file_size / 1024).toFixed(1)} KB` : ""}
                        {v.mime_type ? ` · ${v.mime_type}` : ""}
                      </div>
                      {v.change_notes && <div className="text-xs text-muted-foreground mt-1">{v.change_notes}</div>}
                      {v.sha256_hash && <div className="text-xs font-mono text-muted-foreground mt-1">SHA256: {v.sha256_hash}</div>}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )) : (
            <p className="text-sm text-muted-foreground text-center py-4">No versions recorded.</p>
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
