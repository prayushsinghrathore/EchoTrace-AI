"use client";

import { Suspense, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listWorkspaces, listOrgs, createWorkspace, deleteWorkspace } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter, useSearchParams } from "next/navigation";

function WorkspacesPageContent() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedOrg = searchParams.get("org_id") || "";

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [orgId, setOrgId] = useState(preselectedOrg);
  const [description, setDescription] = useState("");

  const { data: workspaces, isLoading } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });
  const { data: orgs } = useQuery({ queryKey: ["orgs"], queryFn: listOrgs });

  const createMutation = useMutation({
    mutationFn: () => createWorkspace({ organization_id: orgId, name, slug, description: description || undefined }),
    onSuccess: (ws) => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      setShowForm(false);
      setName(""); setSlug(""); setDescription("");
      router.push(`/workspaces/${ws.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWorkspace(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspaces"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Workspaces</h1>
          <p className="text-muted-foreground">Collaborative workspaces for your investigations</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "New Workspace"}</Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Create Workspace</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="space-y-4">
              <div>
                <label className="text-sm font-medium">Organization</label>
                <select value={orgId} onChange={(e) => setOrgId(e.target.value)} required
                  className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="">Select organization</option>
                  {orgs?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-sm font-medium">Slug</label>
                <input value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"))} required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono" />
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)}
                  className="flex h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" /><Skeleton className="h-20 w-full" />
        </div>
      ) : workspaces && workspaces.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((ws) => (
            <Card key={ws.id} className="hover-card cursor-pointer" onClick={() => router.push(`/workspaces/${ws.id}`)}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{ws.name}</CardTitle>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                    onClick={(e) => { e.stopPropagation(); if (confirm("Delete workspace?")) deleteMutation.mutate(ws.id); }}>
                    ✕
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-2 text-sm text-muted-foreground">{ws.description || "No description"}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="font-mono">{ws.slug}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card><CardContent className="py-12 text-center text-muted-foreground">
          No workspaces yet. Create one to organize your projects.
        </CardContent></Card>
      )}
    </div>
  );
}

export default function WorkspacesPage() {
  return (
    <Suspense fallback={<div className="space-y-6"><Skeleton className="h-8 w-48" /><Skeleton className="h-64 w-full" /></div>}>
      <WorkspacesPageContent />
    </Suspense>
  );
}
