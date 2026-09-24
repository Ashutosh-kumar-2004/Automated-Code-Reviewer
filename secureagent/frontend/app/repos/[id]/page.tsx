"use client";

import { use, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  GitBranch,
  Play,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Terminal,
  ArrowLeft,
  Loader2,
  FileCode,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface FindingItem {
  id: string;
  rule_id: string;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  file_path: string;
  line_start: number;
  line_end: number;
  code_snippet: string;
  status: string;
}

interface ScanItem {
  id: string;
  status: string;
  security_score: number | null;
  total_findings: number;
  started_at: string;
  completed_at: string | null;
}

interface RepoDetail {
  id: string;
  full_name: string;
  clone_url: string;
  html_url: string;
  default_branch: string;
  language: string | null;
  description: string | null;
}

export default function RepoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: repoId } = use(params);
  const searchParams = useSearchParams();
  const initialScanId = searchParams.get("scanId");

  const [repo, setRepo] = useState<RepoDetail | null>(null);
  const [scans, setScans] = useState<ScanItem[]>([]);
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [activeScanId, setActiveScanId] = useState<string | null>(initialScanId);
  const [scanStatus, setScanStatus] = useState<string>("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadRepoData();
  }, [repoId]);

  useEffect(() => {
    if (activeScanId) {
      connectSseStream(activeScanId);
    }
  }, [activeScanId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  async function loadRepoData() {
    setLoading(true);
    try {
      // 1. Fetch repo detail
      const repoRes = await fetch(`/api/repos/${repoId}`);
      if (!repoRes.ok) throw new Error("Failed to load repo details");
      const repoData = await repoRes.json();
      setRepo(repoData);

      // 2. Fetch scan history
      const scansRes = await fetch(`/api/repos/${repoId}/scans`);
      if (scansRes.ok) {
        const scansData = await scansRes.json();
        setScans(Array.isArray(scansData) ? scansData : []);

        // If there's an ongoing or recent scan, load its findings
        const latestCompleted = scansData.find((s: ScanItem) => s.status === "completed");
        if (latestCompleted) {
          loadScanFindings(latestCompleted.id);
        }

        const running = scansData.find((s: ScanItem) =>
          ["pending", "cloning", "scanning", "triaging", "fixing"].includes(s.status)
        );
        if (running && !activeScanId) {
          setActiveScanId(running.id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function loadScanFindings(scanId: string) {
    try {
      const res = await fetch(`/api/scans/${scanId}/findings`);
      if (res.ok) {
        const data = await res.json();
        setFindings(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error(e);
    }
  }

  function connectSseStream(scanId: string) {
    setScanStatus("running");
    setLogs((prev) => [...prev, `[SSE] Connected to live scan stream (${scanId})...`]);

    const eventSource = new EventSource(`/api/scans/${scanId}/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.message) {
          setLogs((prev) => [...prev, `[${data.node || "agent"}] ${data.message}`]);
        }
      } catch (err) {
        setLogs((prev) => [...prev, event.data]);
      }
    };

    eventSource.addEventListener("done", (event) => {
      const data = JSON.parse(event.data);
      setScanStatus(data.status || "completed");
      setLogs((prev) => [...prev, `[system] Scan reached status: ${data.status}`]);
      eventSource.close();
      loadRepoData();
      loadScanFindings(scanId);
    });

    eventSource.onerror = (err) => {
      console.error("SSE stream error:", err);
      eventSource.close();
    };
  }

  async function handleStartScan() {
    setTriggering(true);
    try {
      const res = await fetch("/api/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_id: repoId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to trigger scan");
      }

      const newScan = await res.json();
      setActiveScanId(newScan.id);
      setLogs([`Triggered new scan: ${newScan.id}`]);
      connectSseStream(newScan.id);
    } catch (err: any) {
      alert(`Error starting scan: ${err.message}`);
    } finally {
      setTriggering(false);
    }
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return <Badge className="bg-red-500/10 text-red-400 border-red-500/20">Critical</Badge>;
      case "high":
        return <Badge className="bg-orange-500/10 text-orange-400 border-orange-500/20">High</Badge>;
      case "medium":
        return <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20">Medium</Badge>;
      case "low":
        return <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Low</Badge>;
      default:
        return <Badge variant="outline">Info</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm font-medium">Loading repository details...</p>
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="text-center py-20">
        <p className="text-destructive font-medium mb-3">Repository not found</p>
        <Link href="/repos" className="text-sm text-primary hover:underline">
          ← Back to repositories
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Back button & Repo Header */}
      <div>
        <Link
          href="/repos"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to all repositories
        </Link>

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{repo.full_name}</h1>
              <a
                href={repo.html_url}
                target="_blank"
                rel="noreferrer"
                className="text-muted-foreground hover:text-foreground"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
              <span>Branch: <code className="bg-muted px-1.5 py-0.5 rounded">{repo.default_branch}</code></span>
              {repo.language && (
                <span className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-primary" />
                  {repo.language}
                </span>
              )}
            </div>
          </div>

          <Button
            onClick={handleStartScan}
            disabled={triggering || scanStatus === "running"}
            className="gap-2 shadow-sm font-semibold"
          >
            {triggering || scanStatus === "running" ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Scanning in progress...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current" />
                Trigger Scan
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Live Scan & SSE Stepper */}
      {(activeScanId || scanStatus === "running") && (
        <Card className="border-border bg-card/70 overflow-hidden">
          <div className="p-5 border-b border-border/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-3 w-3 rounded-full bg-primary animate-pulse" />
              <h2 className="font-semibold text-sm">Live Scan Stepper & Event Stream</h2>
            </div>
            <Badge variant="outline" className="capitalize text-xs">
              {scanStatus}
            </Badge>
          </div>

          {/* Stepper Progress */}
          <div className="grid grid-cols-3 gap-2 p-5 bg-muted/20 border-b border-border text-center text-xs">
            <div className="flex flex-col items-center gap-1.5">
              <div className="h-7 w-7 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold">
                1
              </div>
              <span className="font-medium">Ingest & Clone</span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className="h-7 w-7 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold">
                2
              </div>
              <span className="font-medium">Semgrep Scanner</span>
            </div>
            <div className="flex flex-col items-center gap-1.5">
              <div className={`h-7 w-7 rounded-full ${scanStatus === "completed" ? "bg-green-500/20 text-green-400" : "bg-muted text-muted-foreground"} flex items-center justify-center font-bold`}>
                3
              </div>
              <span className="font-medium">Completed</span>
            </div>
          </div>

          {/* Live Terminal Log */}
          <div className="bg-black/90 p-4 font-mono text-xs text-green-400/90 h-48 overflow-y-auto space-y-1">
            <div className="text-muted-foreground mb-2 flex items-center gap-1.5">
              <Terminal className="h-3.5 w-3.5" />
              <span>Real-Time SSE Agent Logs</span>
            </div>
            {logs.map((log, idx) => (
              <div key={idx} className="leading-relaxed whitespace-pre-wrap">
                {log}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </Card>
      )}

      {/* Discovered Findings Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-400" />
            Detected Security Findings ({findings.length})
          </h2>
        </div>

        {findings.length === 0 ? (
          <Card className="p-8 text-center text-muted-foreground border-border bg-card/40">
            <CheckCircle2 className="h-8 w-8 text-green-400 mx-auto mb-2" />
            <p className="font-medium text-sm">No vulnerabilities detected</p>
            <p className="text-xs text-muted-foreground mt-1">
              Trigger a scan above to run Semgrep static analysis on this repository.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {findings.map((f) => (
              <Card key={f.id} className="p-5 border-border bg-card/50 hover:border-border/80 transition-colors">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {getSeverityBadge(f.severity)}
                      <span className="font-bold text-sm">{f.title}</span>
                      <code className="text-[11px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                        {f.rule_id}
                      </code>
                    </div>
                    <p className="text-xs text-muted-foreground">{f.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-muted-foreground my-2.5">
                  <FileCode className="h-3.5 w-3.5 text-primary" />
                  <span className="font-mono text-foreground">{f.file_path}:{f.line_start}</span>
                </div>

                {f.code_snippet && (
                  <div className="bg-black/60 rounded-md p-3 font-mono text-xs text-muted-foreground overflow-x-auto border border-border/50">
                    <pre className="text-red-400/90 whitespace-pre">{f.code_snippet}</pre>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Past Scans History */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold tracking-tight flex items-center gap-2">
          <Clock className="h-5 w-5 text-blue-400" />
          Scan History ({scans.length})
        </h2>

        {scans.length === 0 ? (
          <p className="text-xs text-muted-foreground">No previous scans recorded.</p>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden bg-card/40">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 text-muted-foreground border-b border-border">
                <tr>
                  <th className="p-3">Status</th>
                  <th className="p-3">Score</th>
                  <th className="p-3">Findings</th>
                  <th className="p-3">Started</th>
                  <th className="p-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {scans.map((s) => (
                  <tr key={s.id} className="hover:bg-muted/20">
                    <td className="p-3 capitalize font-medium flex items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${s.status === "completed" ? "bg-green-400" : s.status === "failed" ? "bg-red-400" : "bg-primary animate-pulse"}`} />
                      {s.status}
                    </td>
                    <td className="p-3 font-semibold text-foreground">
                      {s.security_score !== null ? `${s.security_score}/100` : "—"}
                    </td>
                    <td className="p-3">{s.total_findings} vulnerabilities</td>
                    <td className="p-3 text-muted-foreground">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                    <td className="p-3">
                      <button
                        onClick={() => {
                          setActiveScanId(s.id);
                          loadScanFindings(s.id);
                        }}
                        className="text-primary hover:underline font-medium"
                      >
                        View Findings
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
