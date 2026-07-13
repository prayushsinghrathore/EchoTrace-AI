"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWorkspace, listMembers, listProjects, createProject, deleteProject, inviteUser, removeMember } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";

const FUTURE_MODULES = [
  { name: "Evidence", icon: "📎", stage: "Live" },
  { name: "Timeline", icon: "⏱️", stage: "Live" },
  { name: "AI Investigation", icon: "🤖", stage: "Live" },
  { name: "Graph Visualization", icon: "🔗", stage: "Live" },
  { name: "Reports", icon: "📄", stage: "Coming Soon" },
  { name: "MITRE ATT&CK", icon: "🛡️", stage: "Planned" },
];

export default function WorkspaceDetailPage() {
  const params = useParams();
  const wsId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [projName, setProjName] = useState("");
  const [projSlug, setProjSlug] = useState("");

  const { data: ws, isLoading: wsLoading } = useQuery({
    queryKey: ["workspace", wsId],
    queryFn: () => getWorkspace(wsId),
  });

  const { data: members } = useQuery({
    queryKey: ["members", wsId],
    queryFn: () => listMembers(wsId),
  });

  const { data: projects, isLoading: projLoading } = useQuery({
    queryKey: ["projects", wsId],
    queryFn: () => listProjects(wsId),
  });

  const createProjMutation = useMutation({
    mutationFn: () => createProject({ workspace_id: wsId, name: projName, slug: projSlug }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", wsId] });
      queryClient.invalidateQueries({ queryKey: ["workspace", wsId] });
      setShowForm(false); setProjName(""); setProjSlug("");
    },
  });

  const deleteProjMutation = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", wsId] });
      queryClient.invalidateQueries({ queryKey: ["workspace", wsId] });
    },
  });

  // Member management
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");

  const inviteMut = useMutation({
    mutationFn: () => inviteUser(wsId, inviteEmail.trim(), inviteRole),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members", wsId] });
      setShowInviteForm(false);
      setInviteEmail("");
      toast.success("Invitation sent");
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Failed to invite");
    },
  });

  const removeMemberMut = useMutation({
    mutationFn: (memberId: string) => removeMember(wsId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members", wsId] });
      queryClient.invalidateQueries({ queryKey: ["workspace", wsId] });
      toast.success("Member removed");
    },
  });

  if (wsLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;
  if (!ws) return <p>Workspace not found</p>;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <button onClick={() => router.push("/workspaces")} className="hover:text-foreground">Workspaces</button>
          <span>/</span>
          <span className="text-foreground">{ws.name}</span>
        </div>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">{ws.name}</h1>
        <p className="text-muted-foreground">{ws.description || "No description"}</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Projects</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold">{ws.project_count}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Members</CardTitle></CardHeader>
          <CardContent><div className="text-3xl font-bold">{ws.member_count}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm">Slug</CardTitle></CardHeader>
          <CardContent><div className="font-mono text-sm">{ws.slug}</div></CardContent></Card>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Projects */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Projects</h2>
            <Button size="sm" onClick={() => setShowForm(!showForm)}>
              {showForm ? "Cancel" : "New Project"}
            </Button>
          </div>

          {showForm && (
            <Card>
              <CardContent className="pt-4">
                <form onSubmit={(e) => { e.preventDefault(); createProjMutation.mutate(); }} className="space-y-3">
                  <input placeholder="Project name" value={projName} onChange={(e) => setProjName(e.target.value)} required
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
                  <input placeholder="project-slug" value={projSlug}
                    onChange={(e) => setProjSlug(e.target.value.toLowerCase().replace(/\s+/g, "-"))} required
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono" />
                  <Button type="submit" size="sm" disabled={createProjMutation.isPending}>
                    {createProjMutation.isPending ? "Creating..." : "Create"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {projLoading ? (
            <div className="space-y-2"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>
          ) : projects && projects.length > 0 ? (
            <div className="space-y-2">
              {projects.map((proj) => (
                <Card key={proj.id} className="hover-card cursor-pointer" onClick={() => router.push(`/projects/${proj.id}`)}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <div className="font-medium">{proj.name}</div>
                      <div className="text-xs text-muted-foreground">{proj.description || "No description"}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant={proj.status === "active" ? "success" : "secondary"}>{proj.status}</Badge>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive"
                        onClick={(e) => { e.stopPropagation(); if (confirm("Delete project?")) deleteProjMutation.mutate(proj.id); }}>
                        ✕
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card><CardContent className="py-8 text-center text-sm text-muted-foreground">
              No projects yet. Create one to start investigating.
            </CardContent></Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Members */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-lg">Members</CardTitle>
              <Button variant="outline" size="sm" onClick={() => setShowInviteForm(!showInviteForm)}>
                {showInviteForm ? "Cancel" : "Invite"}
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {showInviteForm && (
                <div className="space-y-2 pb-3 border-b">
                  <input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="Email address" type="email"
                    className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
                  <div className="flex gap-2">
                    <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}
                      className="h-9 rounded-md border border-input bg-background px-2 text-sm">
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    <Button size="sm" onClick={() => inviteMut.mutate()} disabled={!inviteEmail.trim() || inviteMut.isPending}>
                      {inviteMut.isPending ? "..." : "Send"}
                    </Button>
                  </div>
                </div>
              )}
              {members && members.length > 0 ? (
                <div className="space-y-2">
                  {members.map((m) => (
                    <div key={m.id} className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium truncate">{m.display_name || m.email}</div>
                        <div className="text-xs text-muted-foreground truncate">{m.email}</div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <Badge variant="outline" className="text-[10px]">{m.role}</Badge>
                        <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                          onClick={() => { if (confirm(`Remove ${m.display_name || m.email}?`)) removeMemberMut.mutate(m.id); }}>
                          ✕
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-2">Loading members...</p>
              )}
            </CardContent>
          </Card>

          {/* Future Modules */}
          <Card>
            <CardHeader><CardTitle className="text-lg">Modules</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                {FUTURE_MODULES.map((mod) => (
                  <div key={mod.name} className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
                    <div className="flex items-center gap-2 text-sm">
                      <span>{mod.icon}</span>
                      <span>{mod.name}</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground">{mod.stage}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
