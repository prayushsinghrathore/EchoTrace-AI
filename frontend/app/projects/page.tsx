"use client";

import { useQuery } from "@tanstack/react-query";
import { listWorkspaces, listProjects } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function ProjectsPage() {
  const router = useRouter();
  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });
  const [selectedWs, setSelectedWs] = useState<string>("");

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects", selectedWs],
    queryFn: () => listProjects(selectedWs),
    enabled: !!selectedWs,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
        <p className="text-muted-foreground">Investigation projects across your workspaces</p>
      </div>

      <div>
        <label className="text-sm font-medium">Select Workspace</label>
        <select value={selectedWs} onChange={(e) => setSelectedWs(e.target.value)}
          className="mt-1 flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm">
          <option value="">Choose a workspace...</option>
          {workspaces?.map((ws) => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
        </select>
      </div>

      {selectedWs && (
        <>
          {isLoading ? (
            <div className="space-y-3"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>
          ) : projects && projects.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {projects.map((proj) => (
                <Card key={proj.id} className="hover-card cursor-pointer" onClick={() => router.push(`/projects/${proj.id}`)}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">{proj.name}</CardTitle>
                      <Badge variant={proj.status === "active" ? "success" : "secondary"}>{proj.status}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{proj.description || "No description"}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card><CardContent className="py-12 text-center text-muted-foreground">
              No projects in this workspace yet.
            </CardContent></Card>
          )}
        </>
      )}
    </div>
  );
}
