"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listWorkspaces, listInvestigations, createInvestigation, deleteInvestigation, getInvestigationDashboard } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";

const STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  open: "success", in_progress: "warning", pending_review: "secondary", closed: "default", archived: "outline",
};

export default function InvestigationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedWs, setSelectedWs] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");

  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });
  const { data: invs, isLoading } = useQuery({
    queryKey: ["investigations", selectedWs],
    queryFn: () => listInvestigations(selectedWs),
    enabled: !!selectedWs,
  });
  const { data: dashboard } = useQuery({
    queryKey: ["inv-dash", selectedWs],
    queryFn: () => getInvestigationDashboard(selectedWs),
    enabled: !!selectedWs,
  });

  const createMut = useMutation({
    mutationFn: () => createInvestigation({ workspace_id: selectedWs, title, description: description || undefined, priority }),
    onSuccess: (inv) => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
      queryClient.invalidateQueries({ queryKey: ["inv-dash"] });
      setShowForm(false); setTitle(""); setDescription("");
      router.push(`/investigations/${inv.id}`);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteInvestigation(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["investigations"] }); queryClient.invalidateQueries({ queryKey: ["inv-dash"] }); },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Investigations</h1>
          <p className="text-muted-foreground">Case management and knowledge graph investigations</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} disabled={!selectedWs}>
          {showForm ? "Cancel" : "New Investigation"}
        </Button>
      </div>

      <div className="max-w-md">
        <label className="text-sm font-medium">Workspace</label>
        <select value={selectedWs} onChange={(e) => { setSelectedWs(e.target.value); setShowForm(false); }}
          className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
          <option value="">Select workspace...</option>
          {workspaces?.map((ws) => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
        </select>
      </div>

      {dashboard && (
        <div className="grid gap-4 md:grid-cols-5">
          <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Total</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold">{dashboard.total}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Open</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold text-green-600">{dashboard.open}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-xs">In Progress</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold text-yellow-600">{dashboard.in_progress}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Entities</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold">{dashboard.entities}</div></CardContent></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-xs">Relationships</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold">{dashboard.relationships}</div></CardContent></Card>
        </div>
      )}

      {showForm && selectedWs && (
        <Card>
          <CardContent className="pt-4">
            <form onSubmit={(e) => { e.preventDefault(); createMut.mutate(); }} className="space-y-3">
              <input placeholder="Investigation title" value={title} onChange={(e) => setTitle(e.target.value)} required
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <div className="flex gap-3">
                <select value={priority} onChange={(e) => setPriority(e.target.value)}
                  className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)}
                className="flex h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <Button type="submit" disabled={createMut.isPending}>
                {createMut.isPending ? "Creating..." : "Create Investigation"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-2"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>
      ) : invs && invs.length > 0 ? (
        <div className="space-y-2">
          {invs.map((inv) => (
            <Card key={inv.id} className="hover-card cursor-pointer" onClick={() => router.push(`/investigations/${inv.id}`)}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{inv.title}</span>
                    <Badge variant={STATUS_COLORS[inv.status] || "outline"} className="text-[10px]">{inv.status.replace("_", " ")}</Badge>
                    <Badge variant="outline" className="text-[10px]">{inv.priority}</Badge>
                  </div>
                  <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                    <span>Entities: {inv.entity_count}</span>
                    <span>Relationships: {inv.relationship_count}</span>
                    <span>Timeline: {inv.timeline_count}</span>
                  </div>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                  onClick={(e) => { e.stopPropagation(); if (confirm("Delete investigation?")) deleteMut.mutate(inv.id); }}>✕</Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : selectedWs ? (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          No investigations in this workspace. Create one to get started.
        </CardContent></Card>
      ) : (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          Select a workspace to view investigations.
        </CardContent></Card>
      )}
    </div>
  );
}
