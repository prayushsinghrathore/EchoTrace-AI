"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listWorkspaces, listInvestigations } from "@/lib/workspace-client";
import { generateReport, createExport, listExports, ReportGenerateResponse } from "@/lib/reports-client";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { siteConfig } from "@/config/site";

const FORMAT_OPTIONS = [
  { value: "markdown", label: "Markdown", icon: "📝" },
  { value: "html", label: "HTML", icon: "🌐" },
  { value: "json", label: "JSON", icon: "📊" },
];

const EXPORT_FORMATS = [
  { value: "csv", label: "CSV", icon: "📋" },
  { value: "json", label: "JSON", icon: "📊" },
];

const JOB_STATUS_COLORS: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  completed: "success",
  running: "warning",
  queued: "secondary",
  failed: "destructive",
};

export default function ReportsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedWs, setSelectedWs] = useState("");
  const [selectedInv, setSelectedInv] = useState("");
  const [format, setFormat] = useState("markdown");
  const [exportFormat, setExportFormat] = useState("csv");
  const [reportContent, setReportContent] = useState<ReportGenerateResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState(false);

  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: listWorkspaces });
  const { data: investigations } = useQuery({
    queryKey: ["investigations", selectedWs],
    queryFn: () => listInvestigations(selectedWs),
    enabled: !!selectedWs,
  });
  const { data: exports, isLoading: exportsLoading } = useQuery({
    queryKey: ["exports", selectedWs],
    queryFn: () => listExports(selectedWs),
    enabled: !!selectedWs,
  });

  const handleGenerateReport = async () => {
    if (!selectedInv) return;
    setGenerating(true);
    setReportContent(null);
    try {
      const result = await generateReport(selectedInv, format, true);
      setReportContent(result);
      toast.success("Report generated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    if (!selectedInv || !selectedWs) return;
    setExporting(true);
    try {
      const job = await createExport("investigation", selectedInv, exportFormat, selectedWs);
      queryClient.invalidateQueries({ queryKey: ["exports"] });
      toast.success(`Export job created (${job.status})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
        <p className="text-muted-foreground">Generate investigation reports and manage exports</p>
      </div>

      {/* Workspace / Investigation Selectors */}
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Workspace</label>
          <select value={selectedWs} onChange={(e) => { setSelectedWs(e.target.value); setSelectedInv(""); }}
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
            <option value="">Select workspace...</option>
            {workspaces?.map((ws) => <option key={ws.id} value={ws.id}>{ws.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Investigation</label>
          <select value={selectedInv} onChange={(e) => setSelectedInv(e.target.value)}
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            disabled={!selectedWs}>
            <option value="">Select investigation...</option>
            {investigations?.map((inv) => <option key={inv.id} value={inv.id}>{inv.title}</option>)}
          </select>
        </div>
      </div>

      {/* Report Generation */}
      <Card>
        <CardHeader>
          <CardTitle>Generate Report</CardTitle>
          <CardDescription>Create a report in your preferred format</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            {FORMAT_OPTIONS.map((opt) => (
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
          <div className="flex gap-3">
            <Button onClick={handleGenerateReport} disabled={!selectedInv || generating}
              size="lg">
              {generating ? "Generating..." : `Generate ${format === "markdown" ? "Markdown" : format === "html" ? "HTML" : "JSON"} Report`}
            </Button>
            <Button variant="outline" onClick={() => {
              if (selectedInv) router.push(`/investigations/${selectedInv}`);
            }} disabled={!selectedInv}>
              View Investigation
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Report Content Display */}
      {reportContent && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">{reportContent.title}</CardTitle>
              <CardDescription>
                Generated at {new Date(reportContent.generated_at).toLocaleString()} · {reportContent.format}
              </CardDescription>
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
      {selectedInv && selectedWs && (
        <Card>
          <CardHeader>
            <CardTitle>Export Investigation</CardTitle>
            <CardDescription>Download as PDF, CSV, or JSON file</CardDescription>
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
            <Button onClick={handleExport} disabled={!selectedInv || exporting} variant="secondary">
              {exporting ? "Creating export..." : `Export as ${exportFormat.toUpperCase()}`}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Exports History */}
      <Card>
        <CardHeader>
          <CardTitle>Export History</CardTitle>
          <CardDescription>Recent export jobs and their status</CardDescription>
        </CardHeader>
        <CardContent>
          {!selectedWs ? (
            <p className="text-sm text-muted-foreground text-center py-4">Select a workspace to view exports.</p>
          ) : exportsLoading ? (
            <div className="space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
          ) : exports && exports.length > 0 ? (
            <div className="space-y-2">
              {exports.map((job) => (
                <div key={job.id} className="flex items-center justify-between rounded-md border p-3 text-sm">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{job.format === "csv" ? "📋" : "📊"}</span>
                    <div>
                      <span className="font-medium uppercase">{job.format}</span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {job.entity_type} · {new Date(job.created_at).toLocaleString()}
                      </span>
                      {job.file_size && <span className="ml-2 text-xs text-muted-foreground">· {(job.file_size / 1024).toFixed(1)} KB</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={JOB_STATUS_COLORS[job.status] || "outline"} className="text-[10px]">{job.status}</Badge>
                    {job.download_token && (
                      <Button variant="outline" size="sm" className="h-7 text-xs"
                        onClick={() => window.open(`${siteConfig.apiUrl}/reports/download/${job.download_token}`, "_blank")}>
                        Download
                      </Button>
                    )}
                    {job.error && <span className="text-xs text-destructive">{job.error}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : selectedWs ? (
            <p className="text-sm text-muted-foreground text-center py-4">No export jobs yet.</p>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">Select a workspace to view exports.</p>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      {selectedInv && (
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => router.push(`/investigations/${selectedInv}`)}>
            Investigation Detail →
          </Button>
          <Button variant="outline" onClick={() => router.push(`/graph/${selectedInv}`)}>
            Knowledge Graph →
          </Button>
          <Button variant="outline" onClick={() => router.push(`/timeline/${selectedInv}`)}>
            Timeline →
          </Button>
        </div>
      )}
    </div>
  );
}
