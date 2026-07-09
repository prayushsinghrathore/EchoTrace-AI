"use client";

import { useQuery } from "@tanstack/react-query";
import { getProject, getWorkspace } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useParams, useRouter } from "next/navigation";

const FUTURE_MODULES = [
  { name: "Evidence", icon: "📎", desc: "Upload and manage digital evidence files", stage: "Active", href: "/evidence" },
  { name: "Timeline Reconstruction", icon: "⏱️", desc: "Visual timeline of events and artifacts", stage: "Stage 5" },
  { name: "AI Investigation", icon: "🤖", desc: "AI-powered analysis and anomaly detection", stage: "Stage 6" },
  { name: "Graph Visualization", icon: "🔗", desc: "Interactive relationship graphs", stage: "Stage 7" },
  { name: "Reports", icon: "📄", desc: "Generate and export investigation reports", stage: "Stage 8" },
  { name: "MITRE ATT&CK Mapping", icon: "🛡️", desc: "Map findings to the MITRE ATT&CK framework", stage: "Stage 9" },
];

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const router = useRouter();

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const { data: workspace } = useQuery({
    queryKey: ["workspace", project?.workspace_id],
    queryFn: () => getWorkspace(project!.workspace_id),
    enabled: !!project?.workspace_id,
  });

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;
  if (!project) return <p>Project not found</p>;

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/projects")} className="hover:text-foreground">Projects</button>
        <span>/</span>
        <span className="text-foreground">{project.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
          <p className="text-muted-foreground">{project.description || "No description"}</p>
        </div>
        <Badge variant={project.status === "active" ? "success" : "secondary"} className="text-sm">
          {project.status}
        </Badge>
      </div>

      {/* Details */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Status</CardTitle></CardHeader>
          <CardContent><div className="font-medium capitalize">{project.status}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Workspace</CardTitle></CardHeader>
          <CardContent>
            <button onClick={() => router.push(`/workspaces/${project.workspace_id}`)} className="font-medium text-primary hover:underline">
              {workspace?.name || "..."}
            </button>
          </CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Slug</CardTitle></CardHeader>
          <CardContent><div className="font-mono text-sm">{project.slug}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Created</CardTitle></CardHeader>
          <CardContent><div className="text-sm">{new Date(project.created_at).toLocaleDateString()}</div></CardContent></Card>
      </div>

      {/* Evidence quick link */}
      <Card className="cursor-pointer hover-card" onClick={() => router.push("/evidence")}>
        <CardContent className="flex items-center gap-4 p-6">
          <span className="text-4xl">📎</span>
          <div>
            <h2 className="text-xl font-semibold">Evidence Management</h2>
            <p className="text-sm text-muted-foreground">View and manage evidence items for this investigation</p>
          </div>
          <Badge variant="success" className="ml-auto">Active</Badge>
        </CardContent>
      </Card>

      <Separator />

      {/* Future Modules */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Investigation Modules</h2>
        <p className="mb-6 text-sm text-muted-foreground">
          These modules will be enabled in upcoming stages.
        </p>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FUTURE_MODULES.map((mod) => (
            <Card
              key={mod.name}
              className={`${mod.href ? "cursor-pointer hover-card" : "border-dashed bg-muted/30"}`}
              onClick={() => mod.href && router.push(mod.href)}
            >
              <CardHeader>
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{mod.icon}</span>
                  <CardTitle className="text-base">{mod.name}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{mod.desc}</p>
                <Badge variant={mod.stage === "Active" ? "success" : "outline"} className="mt-3 text-[10px]">{mod.stage}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
