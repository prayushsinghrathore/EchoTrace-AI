"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getInvestigation, updateInvestigation, listEntities, createEntity, deleteEntity, listRelationships, createRelationship, deleteRelationship, listTimelineEvents, createTimelineEvent, deleteTimelineEvent } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import { generateReport } from "@/lib/reports-client";

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  open: "success", in_progress: "warning", pending_review: "secondary", closed: "default", archived: "outline",
};

export default function InvestigationDetailPage() {
  const params = useParams();
  const invId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [tab, setTab] = useState<"entities" | "relationships" | "timeline">("entities");

  // Investigation edit state
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editStatus, setEditStatus] = useState("open");
  const [editPriority, setEditPriority] = useState("medium");

  // Entity form
  const [entityType, setEntityType] = useState("person");
  const [entityLabel, setEntityLabel] = useState("");

  // Relationship form
  const [relSource, setRelSource] = useState("");
  const [relTarget, setRelTarget] = useState("");
  const [relType, setRelType] = useState("connected_to");

  // Timeline form
  const [tlTitle, setTlTitle] = useState("");
  const [tlDesc, setTlDesc] = useState("");

  const { data: inv, isLoading } = useQuery({ queryKey: ["investigation", invId], queryFn: () => getInvestigation(invId) });
  const { data: entities } = useQuery({ queryKey: ["entities", invId], queryFn: () => listEntities(invId), enabled: tab === "entities" });
  const { data: rels } = useQuery({ queryKey: ["rels", invId], queryFn: () => listRelationships(invId), enabled: tab === "relationships" });
  const { data: timeline } = useQuery({ queryKey: ["timeline", invId], queryFn: () => listTimelineEvents(invId), enabled: tab === "timeline" });
  const addEntityMut = useMutation({
    mutationFn: () => createEntity(invId, { type: entityType, label: entityLabel }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["entities"] }); setEntityLabel(""); },
  });
  const delEntityMut = useMutation({ mutationFn: (id: string) => deleteEntity(id), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["entities"] }); queryClient.invalidateQueries({ queryKey: ["graph"] }); } });
  const addRelMut = useMutation({
    mutationFn: () => createRelationship(invId, { source_entity_id: relSource, target_entity_id: relTarget, relationship_type: relType }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["rels"] }); queryClient.invalidateQueries({ queryKey: ["graph"] }); setRelSource(""); setRelTarget(""); },
  });
  const delRelMut = useMutation({ mutationFn: (id: string) => deleteRelationship(id), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["rels"] }); queryClient.invalidateQueries({ queryKey: ["graph"] }); } });
  const addTlMut = useMutation({
    mutationFn: () => createTimelineEvent(invId, { event_timestamp: new Date().toISOString(), title: tlTitle, description: tlDesc || undefined }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["timeline"] }); setTlTitle(""); setTlDesc(""); },
  });
  const delTlMut = useMutation({
    mutationFn: (id: string) => deleteTimelineEvent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["timeline"] }),
  });

  const updateMut = useMutation({
    mutationFn: (data: Record<string, unknown>) => updateInvestigation(invId, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["investigation"] }); setEditing(false); },
  });

  const [reportContent, setReportContent] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const result = await generateReport(invId, "markdown", true);
      setReportContent(result.content);
      toast.success("Report generated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setGeneratingReport(false);
    }
  };

  const startEdit = () => {
    if (!inv) return;
    setEditTitle(inv.title);
    setEditDesc(inv.description || "");
    setEditStatus(inv.status);
    setEditPriority(inv.priority);
    setEditing(true);
  };

  const saveEdit = () => {
    if (!inv) return;
    const data: Record<string, unknown> = {};
    if (editTitle !== inv.title) data.title = editTitle;
    if (editDesc !== (inv.description || "")) data.description = editDesc || null;
    if (editStatus !== inv.status) data.status = editStatus;
    if (editPriority !== inv.priority) data.priority = editPriority;
    if (Object.keys(data).length > 0) updateMut.mutate(data);
    else setEditing(false);
  };

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;
  if (!inv) return <p>Investigation not found</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/investigations")} className="hover:text-foreground">Investigations</button>
        <span>/</span><span className="text-foreground">{inv.title}</span>
      </div>

      <div className="flex items-start justify-between">
        <div className="flex-1">
          {editing ? (
            <div className="space-y-2 max-w-xl">
              <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                className="w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-lg font-bold" />
              <div className="flex gap-2">
                <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm">
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="closed">Closed</option>
                  <option value="archived">Archived</option>
                </select>
                <select value={editPriority} onChange={(e) => setEditPriority(e.target.value)}
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
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
                <h1 className="text-3xl font-bold tracking-tight">{inv.title}</h1>
                <Badge variant={STATUS_COLORS[inv.status] || "outline"}>{inv.status.replace("_", " ")}</Badge>
                <Badge variant="outline">{inv.priority}</Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{inv.description || "No description"}</p>
            </>
          )}
        </div>
        <div className="flex gap-2 ml-4">
          {!editing && <Button variant="outline" size="sm" onClick={startEdit}>Edit</Button>}
          <Button variant="outline" size="sm" onClick={() => router.push(`/evidence/upload?investigation_id=${inv.id}&workspace_id=${inv.workspace_id}`)}>
            ⬆️ Upload
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push(`/graph/${inv.id}`)}>View Graph</Button>
          <Button variant="outline" size="sm" onClick={() => router.push(`/timeline/${inv.id}`)}>Timeline</Button>
          <Button variant="outline" size="sm" onClick={handleGenerateReport} disabled={generatingReport}>
            {generatingReport ? "Generating..." : "📄 Report"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Entities</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{inv.entity_count}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Relationships</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{inv.relationship_count}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Timeline</CardTitle></CardHeader>
          <CardContent><div className="text-2xl font-bold">{inv.timeline_count}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Graph</CardTitle></CardHeader>
          <CardContent>
            <button onClick={() => router.push(`/graph/${inv.id}`)} className="text-sm text-primary hover:underline">
              Open Graph →
            </button>
          </CardContent></Card>
      </div>

      {/* Report */}
      {reportContent && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Investigation Report</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => {
                navigator.clipboard.writeText(reportContent);
                toast.success("Copied to clipboard");
              }}>Copy</Button>
              <Button variant="outline" size="sm" onClick={() => setReportContent(null)}>Close</Button>
            </div>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap text-sm font-mono bg-muted/30 rounded-md p-4">{reportContent}</pre>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {(["entities", "relationships", "timeline"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Entities Tab */}
      {tab === "entities" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex gap-2">
                <select value={entityType} onChange={(e) => setEntityType(e.target.value)}
                  className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="person">Person</option><option value="email">Email</option><option value="phone">Phone</option>
                  <option value="device">Device</option><option value="file">File</option><option value="domain">Domain</option>
                  <option value="url">URL</option><option value="ip">IP</option><option value="hash">Hash</option>
                  <option value="account">Account</option><option value="location">Location</option><option value="custom">Custom</option>
                </select>
                <input value={entityLabel} onChange={(e) => setEntityLabel(e.target.value)}
                  placeholder="Entity label..." className="flex-1 h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" />
                <Button onClick={() => addEntityMut.mutate()} disabled={!entityLabel.trim()}>Add</Button>
              </div>
            </CardContent>
          </Card>
          <div className="space-y-2">
            {entities?.map((e) => (
              <Card key={e.id}>
                <CardContent className="flex items-center justify-between p-3">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="text-[10px] w-16 justify-center">{e.type}</Badge>
                    <span className="font-medium">{e.label}</span>
                  </div>
                  <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                    onClick={() => delEntityMut.mutate(e.id)}>✕</Button>
                </CardContent>
              </Card>
            ))}
            {(!entities || entities.length === 0) && <p className="text-sm text-muted-foreground text-center py-4">No entities yet.</p>}
          </div>
        </div>
      )}

      {/* Relationships Tab */}
      {tab === "relationships" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex gap-2">
                <select value={relSource} onChange={(e) => setRelSource(e.target.value)}
                  className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm flex-1">
                  <option value="">Source entity...</option>
                  {entities?.map((e) => <option key={e.id} value={e.id}>{e.label}</option>)}
                </select>
                <select value={relType} onChange={(e) => setRelType(e.target.value)}
                  className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="connected_to">Connected To</option><option value="owns">Owns</option>
                  <option value="uses">Uses</option><option value="sent_to">Sent To</option>
                  <option value="communicated_with">Communicated With</option><option value="located_at">Located At</option>
                  <option value="created">Created</option><option value="custom">Custom</option>
                </select>
                <select value={relTarget} onChange={(e) => setRelTarget(e.target.value)}
                  className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm flex-1">
                  <option value="">Target entity...</option>
                  {entities?.map((e) => <option key={e.id} value={e.id}>{e.label}</option>)}
                </select>
                <Button onClick={() => addRelMut.mutate()} disabled={!relSource || !relTarget}>Add</Button>
              </div>
            </CardContent>
          </Card>
          <div className="space-y-2">
            {rels?.map((r) => {
              const src = entities?.find((e) => e.id === r.source_entity_id);
              const tgt = entities?.find((e) => e.id === r.target_entity_id);
              return (
                <Card key={r.id}>
                  <CardContent className="flex items-center justify-between p-3">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium">{src?.label || r.source_entity_id.slice(0, 8)}</span>
                      <Badge variant="outline" className="text-[10px]">{r.relationship_type}</Badge>
                      <span className="font-medium">{tgt?.label || r.target_entity_id.slice(0, 8)}</span>
                      {r.confidence && <span className="text-muted-foreground">({Math.round(r.confidence * 100)}%)</span>}
                    </div>
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                      onClick={() => delRelMut.mutate(r.id)}>✕</Button>
                  </CardContent>
                </Card>
              );
            })}
            {(!rels || rels.length === 0) && <p className="text-sm text-muted-foreground text-center py-4">No relationships yet.</p>}
          </div>
        </div>
      )}

      {/* Timeline Tab */}
      {tab === "timeline" && (
        <div className="space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex gap-2">
                <input value={tlTitle} onChange={(e) => setTlTitle(e.target.value)}
                  placeholder="Event title..." className="flex-1 h-10 rounded-md border border-input bg-background px-3 py-2 text-sm" />
                <Button onClick={() => addTlMut.mutate()} disabled={!tlTitle.trim()}>Add</Button>
              </div>
            </CardContent>
          </Card>
          <div className="space-y-2">
            {timeline?.map((t) => (
              <Card key={t.id}>
                <CardContent className="flex items-center justify-between p-3">
                  <div>
                    <div className="text-sm font-medium">{t.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(t.event_timestamp).toLocaleString()}{t.description ? ` — ${t.description}` : ""}
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                    onClick={() => delTlMut.mutate(t.id)}>✕</Button>
                </CardContent>
              </Card>
            ))}
            {(!timeline || timeline.length === 0) && <p className="text-sm text-muted-foreground text-center py-4">No timeline events yet.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
