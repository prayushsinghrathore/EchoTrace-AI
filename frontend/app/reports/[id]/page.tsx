"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { getInvestigation } from "@/lib/workspace-client";
import { generateReport, createExport, listExports, ReportGenerateResponse } from "@/lib/reports-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { siteConfig } from "@/config/site";

const FORMATS = [
  { value: "markdown", label: "Markdown", icon: "📝" },
  { value: "html", label: "HTML", icon: "🌐" },
  { value: "json", label: "JSON", icon: "📊" },
];

const EXPORT_FORMATS = [
  { value: "pdf", label: "PDF", icon: "📄" },
  { value: "csv", label: "CSV", icon: "📋" },
  { value: "json", label: "JSON", icon: "📊" },
];

export default function InvestigationReportsPage() {
  const params = useParams();
  const invId = params.id as string;
  const router = useRouter();
  const queryClient = useQueryClient();

  const [format, setFormat] = useState("markdown");
  const [exportFormat, setExportFormat] = useState("pdf");
  const [reportContent, setReportContent] = useState<ReportGenerateResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);

  const { data: inv, isLoading } = useQuery({
    queryKey: ["investigation", invId],
    queryFn: () => getInvestigation(invId),
    enabled: !!invId,
  });

  // Load exports for the workspace
  const { data: exports, isLoading: exportsLoading } = useQuery({
    queryKey: ["exports", inv?.workspace_id],
    queryFn: () => listExports(inv!.workspace_id),
    enabled: !!inv?.workspace_id,
  });

  const handleGenerateReport = async () => {
    setGenerating(true);
    setReportContent(null);
    try {
      const result = await generateReport(invId, format, true);
      setReportContent(result);
      toast.success("Report generated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    if (!inv?.workspace_id) return;
    setExporting(true);
    try {
      const job = await createExport("investigation", invId, exportFormat, inv.workspace_id);
      queryClient.invalidateQueries({ queryKey: ["exports"] });
      toast.success(`Export created (${job.status})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-40 w-full" /></div>;
  if (!inv) return <p>Investigation not found</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <button onClick={() => router.push("/reports")} className="hover:text-foreground">Reports</button>
        <span>/</span>
        <span className="text-foreground">{inv.title}</span>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{inv.title}</h1>
          <p className="text-muted-foreground">Reports and exports for this investigation</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => router.push(`/investigations/${invId}`)}>
            Investigation Detail
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push(`/graph/${invId}`)}>
            Graph
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push(`/timeline/${invId}`)}>
            Timeline
          </Button>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Status</CardTitle></CardHeader>
          <CardContent><div className="text-lg font-semibold capitalize">{inv.status.replace("_", " ")}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Priority</CardTitle></CardHeader>
          <CardContent><div className="text-lg font-semibold capitalize">{inv.priority}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Entities</CardTitle></CardHeader>
          <CardContent><div className="text-lg font-semibold">{inv.entity_count}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-xs text-muted-foreground">Timeline Events</CardTitle></CardHeader>
          <CardContent><div className="text-lg font-semibold">{inv.timeline_count}</div></CardContent></Card>
      </div>

      {/* Generate Report */}
      <Card>
        <CardHeader>
          <CardTitle>Generate Report</CardTitle>
          <CardDescription>Create a report in your preferred format</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            {FORMATS.map((opt) => (
              <button key={opt.value} onClick={() => setFormat(opt.value)}
                className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors
                  ${format === opt.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-input hover:bg-muted"}`}>
                <span>{opt.icon}</span>
                <span>{opt.label}</span>
              </button>
            ))}
          </div>
          <Button onClick={handleGenerateReport} disabled={generating} size="lg">
            {generating ? "Generating..." : `Generate ${format.charAt(0).toUpperCase() + format.slice(1)} Report`}
          </Button>
        </CardContent>
      </Card>

      {/* Report Content */}
      {reportContent && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">{reportContent.title}</CardTitle>
              <CardDescription>{new Date(reportContent.generated_at).toLocaleString()} · {reportContent.format}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => {
                navigator.clipboard.writeText(reportContent.content);
                toast.success("Copied to clipboard");
              }}>Copy</Button>
              <Button variant="destructive" size="sm" onClick={() => setReportContent(null)}>Close</Button>
            </div>
          </CardHeader>
          <CardContent>
            {reportContent.format === "html" ? (
              <div className="max-h-96 overflow-y-auto rounded-md border bg-background p-4"
                dangerouslySetInnerHTML={{ __html: reportContent.content }} />
            ) : reportContent.format === "json" ? (
              <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap text-sm font-mono bg-muted/30 rounded-md p-4">
                {(() => { try { return JSON.stringify(JSON.parse(reportContent.content), null, 2); } catch { return reportContent.content; } })()}
              </pre>
            ) : (
              <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap text-sm font-mono bg-muted/30 rounded-md p-4">{reportContent.content}</pre>
            )}
          </CardContent>
        </Card>
      )}

      {/* Export */}
      <Card>
        <CardHeader>
          <CardTitle>Export Investigation</CardTitle>
          <CardDescription>Download as PDF, CSV, or JSON</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            {EXPORT_FORMATS.map((opt) => (
              <button key={opt.value} onClick={() => setExportFormat(opt.value)}
                className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium transition-colors
                  ${exportFormat === opt.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-input hover:bg-muted"}`}>
                <span>{opt.icon}</span>
                <span>{opt.label}</span>
              </button>
            ))}
          </div>
          <Button onClick={handleExport} disabled={exporting} variant="secondary">
            {exporting ? "Creating..." : `Export as ${exportFormat.toUpperCase()}`}
          </Button>
        </CardContent>
      </Card>

      {/* Export History */}
      <Card>
        <CardHeader>
          <CardTitle>Export History</CardTitle>
          <CardDescription>Previous export jobs for this investigation</CardDescription>
        </CardHeader>
        <CardContent>
          {exportsLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : exports && exports.length > 0 ? (
            <div className="space-y-2">
              {exports
                .filter((job) => job.entity_id === invId)
                .map((job) => (
                  <div key={job.id} className="flex items-center justify-between rounded-md border p-3 text-sm">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{job.format === "pdf" ? "📄" : job.format === "csv" ? "📋" : "📊"}</span>
                      <div>
                        <span className="font-medium uppercase">{job.format}</span>
                        <span className="ml-2 text-xs text-muted-foreground">· {new Date(job.created_at).toLocaleString()}</span>
                        {job.file_size && <span className="ml-2 text-xs text-muted-foreground">· {(job.file_size / 1024).toFixed(1)} KB</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={job.status === "completed" ? "success" : job.status === "failed" ? "destructive" : "warning"} className="text-[10px]">{job.status}</Badge>
                      {job.download_token && (
                        <Button variant="outline" size="sm" className="h-7 text-xs"
                          onClick={() => window.open(`${siteConfig.apiUrl}/reports/download/${job.download_token}`, "_blank")}>
                          Download
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              {exports.filter((job) => job.entity_id === invId).length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No exports for this investigation yet.</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">No exports yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
