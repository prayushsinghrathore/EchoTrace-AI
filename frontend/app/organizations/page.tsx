"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listOrgs, createOrg, deleteOrg } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function OrganizationsPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");

  const { data: orgs, isLoading } = useQuery({ queryKey: ["orgs"], queryFn: listOrgs });

  const createMutation = useMutation({
    mutationFn: () => createOrg({ name, slug, description: description || undefined }),
    onSuccess: (org) => {
      queryClient.invalidateQueries({ queryKey: ["orgs"] });
      setShowForm(false);
      setName("");
      setSlug("");
      setDescription("");
      router.push(`/workspaces?org_id=${org.id}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteOrg(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orgs"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Organizations</h1>
          <p className="text-muted-foreground">Manage your tenant organizations</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "New Organization"}</Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-lg">Create Organization</CardTitle></CardHeader>
          <CardContent>
            <form
              onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }}
              className="space-y-4"
            >
              <div>
                <label className="text-sm font-medium">Name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="text-sm font-medium">Slug</label>
                <input value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"))} required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono" />
                <p className="text-xs text-muted-foreground mt-1">URL-safe identifier: {slug || "(will be generated)"}</p>
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
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : orgs && orgs.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {orgs.map((org) => (
            <Card key={org.id} className="hover-card">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{org.name}</CardTitle>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                    onClick={() => { if (confirm("Delete this organization?")) deleteMutation.mutate(org.id); }}>
                    ✕
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-3 text-sm text-muted-foreground">{org.description || "No description"}</p>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-mono">{org.slug}</span>
                </div>
                <Link href={`/workspaces?org_id=${org.id}`} className="mt-3 inline-flex w-full items-center justify-center rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent">View Workspaces</Link>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No organizations yet. Create one to get started.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
