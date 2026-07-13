"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { globalSearch } from "@/lib/reports-client";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";

const TYPE_ICONS: Record<string, string> = {
  evidence: "📎", investigation: "🔍", project: "📋",
  workspace: "📁", entity: "🏷️", user: "👤",
  organization: "🏢", report: "📄",
};

export default function SearchPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [entityType, setEntityType] = useState("");

  useEffect(() => { inputRef.current?.focus(); }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["global-search", query, entityType],
    queryFn: () => globalSearch(query, entityType || undefined),
    enabled: query.length >= 2,
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Global Search</h1>
        <p className="text-muted-foreground">Search across all entities in your workspace</p>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search evidence, investigations, projects..."
            className="w-full h-12 rounded-lg border border-input bg-background pl-10 pr-3 py-2 text-base ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)}
          className="h-12 rounded-lg border border-input bg-background px-3 py-2 text-sm">
          <option value="">All types</option>
          <option value="evidence">Evidence</option>
          <option value="investigation">Investigations</option>
          <option value="project">Projects</option>
          <option value="workspace">Workspaces</option>
          <option value="entity">Entities</option>
        </select>
      </div>

      {query.length > 0 && query.length < 2 && (
        <p className="text-sm text-muted-foreground text-center py-8">Type at least 2 characters to search.</p>
      )}

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <div className="text-4xl mb-3">🔍</div>
            <p className="font-medium">No results found</p>
            <p className="text-sm">Try a different search term or filter.</p>
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{data.total} result{data.total !== 1 ? "s" : ""} for &quot;{query}&quot;</p>
          {data.results.map((r) => (
            <Card key={`${r.type}-${r.id}`}
              className="hover-card cursor-pointer"
              onClick={() => router.push(r.link)}
            >
              <CardContent className="flex items-start gap-4 p-4">
                <span className="text-2xl shrink-0">{TYPE_ICONS[r.type] || "📄"}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{r.title}</span>
                    <Badge variant="outline" className="text-[10px] shrink-0">{r.type}</Badge>
                    {r.score > 0 && (
                      <span className="text-[10px] text-muted-foreground shrink-0">
                        {Math.round(r.score * 100)}% match
                      </span>
                    )}
                  </div>
                  {r.description && (
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{r.description}</p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!query && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <div className="text-5xl mb-4">🔎</div>
            <p className="text-lg font-medium">Search everything</p>
            <p className="text-sm">Find evidence, investigations, projects, and more across all your workspaces.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
