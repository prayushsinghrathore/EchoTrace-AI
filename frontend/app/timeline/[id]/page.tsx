"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getInvestigation, listTimelineEvents, createTimelineEvent, deleteTimelineEvent, listActivityEvents } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";
import { useState, useMemo } from "react";

const EVENT_ICONS: Record<string, string> = {
  investigation_created: "🔍",
  investigation_updated: "📝",
  investigation_closed: "✅",
  evidence_created: "📄",
  evidence_uploaded: "📎",
  evidence_verified: "✓",
  evidence_deleted: "🗑️",
  entity_created: "🏷️",
  relationship_created: "🔗",
  comment_added: "💬",
  member_added: "👤",
  report_generated: "📊",
  export_completed: "📦",
};

interface TimelineItem {
  id: string;
  title: string;
  description?: string | null;
  category: string;
  event_timestamp?: string;
  occurred_at?: string;
  created_at?: string;
  timestamp?: string;
}

function groupByDate(items: TimelineItem[]): Array<{ date: string; items: TimelineItem[] }> {
  const groups: Record<string, TimelineItem[]> = {};
  for (const item of items) {
    const ts = String(item.event_timestamp || item.occurred_at || item.created_at || item.timestamp || new Date().toISOString());
    const dateKey = ts.slice(0, 10);
    const existing = groups[dateKey];
    if (existing) {
      existing.push(item);
    } else {
      groups[dateKey] = [item];
    }
  }
  return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a)).map(([date, itemList]) => ({ date, items: itemList }));
}

export default function TimelinePage() {
  const params = useParams();
  const invId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const { data: inv } = useQuery({ queryKey: ["investigation", invId], queryFn: () => getInvestigation(invId) });
  const { data: events, isLoading } = useQuery({ queryKey: ["timeline", invId], queryFn: () => listTimelineEvents(invId) });
  const { data: activityData } = useQuery({ queryKey: ["activity", invId], queryFn: () => listActivityEvents(invId) });

  const unified = useMemo(() => {
    const all: TimelineItem[] = [];
    if (events) {
      for (const ev of events) {
        all.push({ id: ev.id, title: ev.title, description: ev.description, event_timestamp: ev.event_timestamp, category: "manual" });
      }
    }
    if (activityData?.items) {
      for (const act of activityData.items) {
        all.push({ id: `act-${act.id}`, title: act.title, description: act.description, occurred_at: act.occurred_at, category: act.event_type, event_timestamp: act.occurred_at });
      }
    }
    return groupByDate(all);
  }, [events, activityData]);

  const addMut = useMutation({
    mutationFn: () => createTimelineEvent(invId, { event_timestamp: new Date().toISOString(), title, description: description || undefined }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["timeline"] }); setTitle(""); setDescription(""); setShowAdd(false); },
  });
  const delMut = useMutation({
    mutationFn: (id: string) => deleteTimelineEvent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["timeline"] }),
  });

  const formatDate = (ts?: string) => {
    if (!ts) return "";
    const d = new Date(ts);
    return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  };

  const formatTime = (ts?: string) => {
    if (!ts) return "";
    return new Date(ts).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  };

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/investigations")} className="hover:text-foreground">Investigations</button>
        <span>/</span>
        <button onClick={() => router.push(`/investigations/${invId}`)} className="hover:text-foreground">{inv?.title || "..."}</button>
        <span>/</span>
        <span className="text-foreground">Timeline</span>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Investigation Timeline</h1>
          <p className="text-muted-foreground text-sm">
            {unified.length} date groups · {(events?.length || 0) + (activityData?.items?.length || 0)} total events
          </p>
        </div>
        <Button onClick={() => setShowAdd(!showAdd)} variant="outline">{showAdd ? "Cancel" : "Add Event"}</Button>
      </div>

      {/* Add Event Form */}
      {showAdd && (
        <Card>
          <CardHeader><CardTitle className="text-lg">New Timeline Event</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={(e) => { e.preventDefault(); addMut.mutate(); }} className="space-y-3">
              <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Event title" required
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description"
                className="flex h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              <Button type="submit" disabled={addMut.isPending || !title.trim()}>
                {addMut.isPending ? "Adding..." : "Add Event"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Timeline */}
      <div className="space-y-8">
        {unified.length > 0 ? unified.map((group) => (
          <div key={group.date}>
            {/* Date header */}
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur py-2 mb-4">
              <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-border" />
                <span className="text-sm font-semibold text-muted-foreground px-2">
                  {formatDate(group.date)}
                </span>
                <div className="h-px flex-1 bg-border" />
              </div>
            </div>

            <div className="relative space-y-0 pl-8">
              {/* Vertical line */}
              <div className="absolute left-[11px] top-0 bottom-0 w-0.5 bg-border" />
              {group.items.map((item: TimelineItem) => {
                const isActivity = item.id.startsWith("act-");
                const icon = EVENT_ICONS[item.category] || (isActivity ? "⚡" : "📌");
                const ts = String(item.event_timestamp || item.occurred_at || item.created_at || item.timestamp || "");
                return (
                  <div key={item.id} className="relative pb-6">
                    <div className={`absolute -left-8 top-1 h-5 w-5 rounded-full border-2 flex items-center justify-center text-xs bg-background ${isActivity ? "border-muted-foreground" : "border-primary"}`}>
                      {icon}
                    </div>
                    <Card className={isActivity ? "border-muted/40" : ""}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">{item.title}</span>
                              {item.category && item.category !== "manual" && (
                                <Badge variant="secondary" className="text-[10px]">{item.category.replace(/_/g, " ")}</Badge>
                              )}
                              {isActivity && <Badge variant="outline" className="text-[10px]">System</Badge>}
                            </div>
                            {item.description && (
                              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{item.description}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-xs text-muted-foreground whitespace-nowrap">{formatTime(ts)}</span>
                            {!isActivity && (
                              <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                                onClick={() => delMut.mutate(item.id)}>✕</Button>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                );
              })}
            </div>
          </div>
        )) : (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            <div className="text-3xl mb-2">📅</div>
            No timeline events yet. Add events to track the sequence of findings, or interact with evidence to auto-generate activity events.
          </CardContent></Card>
        )}
      </div>
    </div>
  );
}
