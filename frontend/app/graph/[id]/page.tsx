"use client";

import { useQuery } from "@tanstack/react-query";
import { getInvestigation, getGraph } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";

const TYPE_COLORS: Record<string, string> = {
  person: "bg-red-500", email: "bg-amber-500", phone: "bg-emerald-500", device: "bg-blue-500",
  file: "bg-violet-500", domain: "bg-pink-500", url: "bg-teal-500", ip: "bg-indigo-500",
  hash: "bg-lime-500", account: "bg-orange-500", location: "bg-green-500", custom: "bg-gray-500",
};

export default function GraphPage() {
  const params = useParams();
  const invId = params.id as string;
  const router = useRouter();

  const { data: inv } = useQuery({ queryKey: ["investigation", invId], queryFn: () => getInvestigation(invId) });
  const { data: graph, isLoading } = useQuery({ queryKey: ["graph", invId], queryFn: () => getGraph(invId) });

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-[500px] w-full" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/investigations")} className="hover:text-foreground">Investigations</button>
        <span>/</span>
        <button onClick={() => router.push(`/investigations/${invId}`)} className="hover:text-foreground">{inv?.title || "..."}</button>
        <span>/</span>
        <span className="text-foreground">Graph</span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Graph</h1>
          <p className="text-muted-foreground">{graph ? `${graph.nodes.length} nodes, ${graph.edges.length} edges` : "Loading..."}</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline">Zoom: scroll</Badge>
          <Badge variant="outline">Pan: drag</Badge>
        </div>
      </div>

      {/* Graph Visualization */}
      <Card className="overflow-hidden">
        <div className="relative min-h-[500px] bg-muted/20 p-6">
          {graph && graph.nodes.length > 0 ? (
            <div className="space-y-8">
              {/* Force-directed layout simulation via concentric circles */}
              <div className="flex flex-wrap justify-center gap-8">
                {graph.nodes.map((node, i) => {
                  const angle = (i / graph.nodes.length) * 2 * Math.PI;
                  const radius = Math.min(graph.nodes.length * 20, 180);
                  const x = 50 + (radius * Math.cos(angle)) / 3;
                  const y = 50 + (radius * Math.sin(angle)) / 3;
                  return (
                    <div key={node.id} className="flex flex-col items-center gap-1" style={{ transform: `translate(${x}px, ${y}px)` }}>
                      <div className={`flex h-14 w-14 items-center justify-center rounded-full text-white text-xl shadow-lg ${TYPE_COLORS[node.type] || "bg-gray-500"}`}
                        title={node.label}>
                        {node.icon || node.label[0]}
                      </div>
                      <span className="text-xs font-medium max-w-[80px] truncate text-center">{node.label}</span>
                      <span className="text-[10px] text-muted-foreground">{node.type}</span>
                    </div>
                  );
                })}
              </div>

              {/* Edges list */}
              <div>
                <h3 className="mb-2 text-sm font-medium">Relationships ({graph.edges.length})</h3>
                <div className="space-y-1">
                  {graph.edges.map((edge) => {
                    const src = graph.nodes.find((n) => n.id === edge.source);
                    const tgt = graph.nodes.find((n) => n.id === edge.target);
                    return (
                      <div key={edge.id} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">{src?.label || "?"}</span>
                        <Badge variant="outline" className="text-[9px]">{edge.type}</Badge>
                        <span className="font-medium text-foreground">{tgt?.label || "?"}</span>
                        {edge.confidence && <span>({Math.round(edge.confidence * 100)}%)</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex h-[500px] items-center justify-center text-muted-foreground">
              <div className="text-center">
                <div className="text-6xl mb-4">🔗</div>
                <p className="text-lg font-medium">No graph data</p>
                <p className="text-sm">Add entities and relationships to see the knowledge graph.</p>
                <button onClick={() => router.push(`/investigations/${invId}`)}
                  className="mt-4 text-sm text-primary hover:underline">
                  Back to Investigation →
                </button>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Node Legend */}
      <Card>
        <CardHeader><CardTitle className="text-sm">Legend</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {Object.entries(TYPE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1 text-xs">
                <div className={`h-3 w-3 rounded-full ${color}`} />
                <span className="capitalize">{type.replace("_", " ")}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
