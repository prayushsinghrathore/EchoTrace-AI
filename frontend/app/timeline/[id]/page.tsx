"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getInvestigation, listTimelineEvents, createTimelineEvent, deleteTimelineEvent } from "@/lib/workspace-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

export default function TimelinePage() {
  const params = useParams();
  const invId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const { data: inv } = useQuery({ queryKey: ["investigation", invId], queryFn: () => getInvestigation(invId) });
  const { data: events, isLoading } = useQuery({ queryKey: ["timeline", invId], queryFn: () => listTimelineEvents(invId) });

  const addMut = useMutation({
    mutationFn: () => createTimelineEvent(invId, { event_timestamp: new Date().toISOString(), title, description: description || undefined }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["timeline"] }); setTitle(""); setDescription(""); },
  });
  const delMut = useMutation({
    mutationFn: (id: string) => deleteTimelineEvent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["timeline"] }),
  });

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/investigations")} className="hover:text-foreground">Investigations</button>
        <span>/</span>
        <button onClick={() => router.push(`/investigations/${invId}`)} className="hover:text-foreground">{inv?.title || "..."}</button>
        <span>/</span>
        <span className="text-foreground">Timeline</span>
      </div>

      <h1 className="text-3xl font-bold tracking-tight">Timeline</h1>

      {/* Add Event */}
      <Card>
        <CardHeader><CardTitle className="text-lg">New Event</CardTitle></CardHeader>
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

      {/* Timeline */}
      <div className="relative space-y-0">
        {events && events.length > 0 ? (
          events.map((ev, i) => (
            <div key={ev.id} className="relative flex gap-4 pb-8 pl-8">
              {/* Timeline line */}
              <div className="absolute left-3 top-3 h-full w-0.5 bg-border" />
              <div className={`absolute left-0 top-1 h-6 w-6 rounded-full border-2 flex items-center justify-center text-xs font-bold bg-background ${i === 0 ? "border-primary text-primary" : "border-muted-foreground text-muted-foreground"}`}>
                {i + 1}
              </div>
              <Card className="flex-1">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium">{ev.title}</div>
                      {ev.description && <div className="text-sm text-muted-foreground mt-1">{ev.description}</div>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {new Date(ev.event_timestamp).toLocaleString()}
                      </span>
                      <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive"
                        onClick={() => delMut.mutate(ev.id)}>✕</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ))
        ) : (
          <Card><CardContent className="py-12 text-center text-muted-foreground">
            No timeline events yet. Add events to track the sequence of findings.
          </CardContent></Card>
        )}
      </div>
    </div>
  );
}
