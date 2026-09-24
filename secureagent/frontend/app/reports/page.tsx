"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  FileText,
  Search,
  Download,
  Printer,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  FolderGit2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Layers,
  Award,
  GitPullRequest,
  ExternalLink,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ReportListItem {
  scan_id: string;
  repo_id: string;
  repo_name: string;
  security_score: number | null;
  grade: string;
  risk_level: string;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  created_at: string;
  completed_at: string | null;
}

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
  cwe_ids: string[];
  owasp_tags: string[];
  status: string;
}

interface ComplianceItem {
  category: string;
  count: number;
  severity: string;
  findings: string[];
}

interface SecurityReportDetail {
  scan_id: string;
  repo_id: string;
  repo_name: string;
  repo_url: string;
  default_branch: string;
  scanned_at: string | null;
  security_score: number;
  grade: string;
  risk_level: string;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  owasp_breakdown: ComplianceItem[];
  cwe_breakdown: ComplianceItem[];
  findings: FindingItem[];
  summary_markdown: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [reportDetail, setReportDetail] = useState<SecurityReportDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    loadReports();
  }, []);

  async function loadReports() {
    setLoading(true);
    try {
      const res = await fetch("/api/reports");
      if (res.ok) {
        const data: ReportListItem[] = await res.json();
        setReports(data);
        if (data.length > 0 && !selectedScanId) {
          selectReport(data[0].scan_id);
        }
      }
    } catch (err) {
      console.error("Failed to load reports:", err);
    } finally {
      setLoading(false);
    }
  }

  async function selectReport(scanId: string) {
    setSelectedScanId(scanId);
    setLoadingDetail(true);
    try {
      const res = await fetch(`/api/reports/${scanId}`);
      if (res.ok) {
        const data = await res.json();
        setReportDetail(data);
      }
    } catch (err) {
      console.error("Failed to load report detail:", err);
    } finally {
      setLoadingDetail(false);
    }
  }

  function handleDownloadMarkdown() {
    if (!selectedScanId) return;
    window.open(`/api/reports/${selectedScanId}/export?format=markdown`, "_blank");
  }

  function handleDownloadJson() {
    if (!selectedScanId) return;
    window.open(`/api/reports/${selectedScanId}/export?format=json`, "_blank");
  }

  function handlePrint() {
    window.print();
  }

  const filteredReports = reports.filter((r) =>
    r.repo_name.toLowerCase().includes(search.toLowerCase())
  );

  // Overall KPIs
  const totalAudits = reports.length;
  const avgScore =
    reports.length > 0
      ? (
          reports.reduce((acc, r) => acc + (r.security_score || 0), 0) /
          reports.length
        ).toFixed(1)
      : "100.0";
  const criticalCountTotal = reports.reduce((acc, r) => acc + r.critical_count, 0);
  const cleanScans = reports.filter((r) => r.total_findings === 0).length;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Security Audit Reports</h1>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            Executive security assessments, OWASP Top 10 compliance metrics, and downloadable audit briefs.
          </p>
        </div>

        {reportDetail && (
          <div className="flex items-center gap-2 print:hidden">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrint}
              className="gap-1.5 text-xs"
            >
              <Printer className="h-3.5 w-3.5" />
              Print / PDF
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadMarkdown}
              className="gap-1.5 text-xs"
            >
              <Download className="h-3.5 w-3.5" />
              Markdown (.md)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadJson}
              className="gap-1.5 text-xs"
            >
              <Download className="h-3.5 w-3.5" />
              JSON
            </Button>
          </div>
        )}
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 print:hidden">
        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
              <Award className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Avg Security Score</p>
              <p className="text-xl font-bold">{avgScore} / 100</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
              <Layers className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Total Audits</p>
              <p className="text-xl font-bold">{totalAudits}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
              <ShieldAlert className="h-5 w-5 text-rose-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Critical Findings</p>
              <p className="text-xl font-bold text-rose-400">{criticalCountTotal}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Clean Audits (100%)</p>
              <p className="text-xl font-bold text-emerald-400">{cleanScans}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-muted-foreground gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm">Loading security reports...</p>
        </div>
      ) : reports.length === 0 ? (
        <Card className="border-dashed border-border bg-card/20 p-12 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <h3 className="text-base font-semibold">No audit reports available</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-6">
            Run a vulnerability scan on any connected repository to generate an automated executive security audit report.
          </p>
          <Link href="/repos">
            <Button className="gap-2">
              <FolderGit2 className="h-4 w-4" />
              Go to Repositories
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Report Picker List (Hidden on print) */}
          <div className="lg:col-span-4 space-y-3 print:hidden">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Filter reports by repo..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-muted/40 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
              {filteredReports.map((r) => {
                const isSelected = r.scan_id === selectedScanId;
                const isClean = r.total_findings === 0;

                return (
                  <div
                    key={r.scan_id}
                    onClick={() => selectReport(r.scan_id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all duration-150 ${
                      isSelected
                        ? "bg-card border-primary/50 shadow-sm ring-1 ring-primary/20"
                        : "bg-card/40 border-border hover:bg-muted/40 hover:border-border/80"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="font-semibold text-sm truncate flex items-center gap-1.5">
                        <FolderGit2 className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                        <span className="truncate">{r.repo_name}</span>
                      </span>
                      <Badge
                        className={`text-[11px] font-bold px-1.5 py-0.5 ${
                          r.grade.startsWith("A")
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : r.grade === "B"
                            ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
                            : r.grade === "C"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                        }`}
                      >
                        Grade {r.grade}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-medium ${
                            isClean ? "text-emerald-400" : "text-amber-400"
                          }`}
                        >
                          {r.total_findings} {r.total_findings === 1 ? "issue" : "issues"}
                        </span>
                        <span>•</span>
                        <span>Score: {r.security_score ?? "N/A"}/100</span>
                      </div>
                      <ChevronRight
                        className={`h-4 w-4 transition-transform ${
                          isSelected ? "text-primary translate-x-0.5" : "text-muted-foreground/50"
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Full Executive Report Detail */}
          <div className="lg:col-span-8">
            {loadingDetail ? (
              <Card className="bg-card/30 border-border p-12 text-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">Loading report details...</p>
              </Card>
            ) : reportDetail ? (
              <div className="space-y-6">
                {/* Executive Summary Card */}
                <Card className="bg-card/60 border-border shadow-sm overflow-hidden">
                  <div className="p-6 border-b border-border bg-muted/20">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold tracking-tight">
                            {reportDetail.repo_name}
                          </h2>
                          <a
                            href={reportDetail.repo_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-muted-foreground hover:text-foreground"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                          <Calendar className="h-3.5 w-3.5" />
                          Evaluated:{" "}
                          {reportDetail.scanned_at
                            ? new Date(reportDetail.scanned_at).toLocaleString()
                            : "Recent"}
                          <span>•</span>
                          <span>Branch: <code className="font-mono">{reportDetail.default_branch}</code></span>
                        </p>
                      </div>

                      {/* Security Score Badge */}
                      <div className="flex items-center gap-3 bg-background/80 px-4 py-2.5 rounded-xl border border-border">
                        <div className="text-right">
                          <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                            Security Posture
                          </p>
                          <p className="text-2xl font-black tracking-tight text-foreground">
                            {reportDetail.security_score}{" "}
                            <span className="text-xs font-normal text-muted-foreground">/ 100</span>
                          </p>
                        </div>
                        <div
                          className={`h-11 w-11 rounded-lg flex items-center justify-center font-black text-lg border ${
                            reportDetail.grade.startsWith("A")
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                              : reportDetail.grade === "B"
                              ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
                              : reportDetail.grade === "C"
                              ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                              : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                          }`}
                        >
                          {reportDetail.grade}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Findings Severity Count Row */}
                  <div className="grid grid-cols-4 divide-x divide-border border-b border-border bg-card/40">
                    <div className="p-4 text-center">
                      <p className="text-xs text-rose-400 font-semibold uppercase tracking-wider">Critical</p>
                      <p className="text-2xl font-bold mt-0.5 text-rose-400">{reportDetail.critical_count}</p>
                    </div>
                    <div className="p-4 text-center">
                      <p className="text-xs text-orange-400 font-semibold uppercase tracking-wider">High</p>
                      <p className="text-2xl font-bold mt-0.5 text-orange-400">{reportDetail.high_count}</p>
                    </div>
                    <div className="p-4 text-center">
                      <p className="text-xs text-amber-400 font-semibold uppercase tracking-wider">Medium</p>
                      <p className="text-2xl font-bold mt-0.5 text-amber-400">{reportDetail.medium_count}</p>
                    </div>
                    <div className="p-4 text-center">
                      <p className="text-xs text-blue-400 font-semibold uppercase tracking-wider">Low</p>
                      <p className="text-2xl font-bold mt-0.5 text-blue-400">{reportDetail.low_count}</p>
                    </div>
                  </div>

                  {/* Risk Assessment Box */}
                  <div className="p-5 flex items-start gap-3 bg-muted/10">
                    <ShieldAlert
                      className={`h-5 w-5 mt-0.5 flex-shrink-0 ${
                        reportDetail.critical_count > 0 ? "text-rose-400" : "text-emerald-400"
                      }`}
                    />
                    <div>
                      <h4 className="text-sm font-semibold">
                        Risk Verdict: <span className="underline">{reportDetail.risk_level}</span>
                      </h4>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        {reportDetail.total_findings === 0
                          ? "Clean audit! Zero known vulnerabilities or hardcoded secrets detected in this revision. Security best practices are currently met."
                          : `Detected ${reportDetail.total_findings} security vulnerabilities. Prioritize remediating ${reportDetail.critical_count} critical and ${reportDetail.high_count} high-severity findings before releasing to production.`}
                      </p>
                    </div>
                  </div>
                </Card>

                {/* Standards & Compliance Cards: OWASP & CWE */}
                {(reportDetail.owasp_breakdown.length > 0 || reportDetail.cwe_breakdown.length > 0) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* OWASP Breakdown */}
                    <Card className="bg-card/40 border-border p-4 space-y-3">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Layers className="h-4 w-4 text-primary" />
                        OWASP Top 10 Mapping
                      </h4>
                      <div className="space-y-2">
                        {reportDetail.owasp_breakdown.map((item) => (
                          <div
                            key={item.category}
                            className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/50 text-xs"
                          >
                            <span className="font-medium text-foreground">{item.category}</span>
                            <Badge variant="secondary" className="text-xs font-bold">
                              {item.count} {item.count === 1 ? "finding" : "findings"}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </Card>

                    {/* CWE Breakdown */}
                    <Card className="bg-card/40 border-border p-4 space-y-3">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                        Common Weakness Enumeration (CWE)
                      </h4>
                      <div className="space-y-2">
                        {reportDetail.cwe_breakdown.map((item) => (
                          <div
                            key={item.category}
                            className="flex items-center justify-between p-2 rounded-lg bg-muted/30 border border-border/50 text-xs"
                          >
                            <span className="font-mono font-medium text-foreground">{item.category}</span>
                            <Badge variant="outline" className="text-xs font-bold">
                              {item.count} {item.count === 1 ? "match" : "matches"}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </Card>
                  </div>
                )}

                {/* Vulnerability Ledger Table */}
                <Card className="bg-card/40 border-border overflow-hidden">
                  <div className="p-4 border-b border-border flex items-center justify-between">
                    <h3 className="text-sm font-semibold">
                      Vulnerability Findings Ledger ({reportDetail.findings.length})
                    </h3>
                    <Link href={`/findings`}>
                      <Button variant="ghost" size="sm" className="h-7 text-xs text-primary gap-1">
                        Open in Findings Explorer &rarr;
                      </Button>
                    </Link>
                  </div>

                  {reportDetail.findings.length === 0 ? (
                    <div className="p-8 text-center text-xs text-muted-foreground">
                      <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto mb-2" />
                      Clean repository. No vulnerabilities found in this audit.
                    </div>
                  ) : (
                    <div className="divide-y divide-border">
                      {reportDetail.findings.map((f) => (
                        <div key={f.id} className="p-4 space-y-2 hover:bg-muted/20 transition-colors">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2">
                              <Badge
                                className={`text-[10px] font-bold uppercase ${
                                  f.severity === "critical"
                                    ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                    : f.severity === "high"
                                    ? "bg-orange-500/10 text-orange-400 border-orange-500/20"
                                    : f.severity === "medium"
                                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                    : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                }`}
                              >
                                {f.severity}
                              </Badge>
                              <span className="text-sm font-semibold text-foreground">
                                {f.title}
                              </span>
                            </div>
                            <span className="text-xs font-mono text-muted-foreground">
                              {f.file_path}:{f.line_start}
                            </span>
                          </div>

                          <p className="text-xs text-muted-foreground leading-relaxed">
                            {f.description}
                          </p>

                          {f.code_snippet && (
                            <pre className="p-2.5 rounded-lg bg-black/40 border border-border text-[11px] font-mono text-zinc-300 overflow-x-auto">
                              <code>{f.code_snippet}</code>
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
