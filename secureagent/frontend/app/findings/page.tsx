"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Search,
  FileCode,
  Shield,
  Loader2,
  CheckCircle2,
  Filter,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Code2,
  ShieldCheck,
  Lightbulb,
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
  cwe_ids: string[];
  owasp_tags: string[];
  status: string;
  repo_name?: string;
}

interface FindingSuggestion {
  finding_id: string;
  explanation: string;
  improved_code: string;
  coding_style_improvements: string[];
  best_practices: string[];
  cwe_mitigation: string;
  model: string;
}

export default function FindingsPage() {
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  // Gemini suggestions state
  const [suggestions, setSuggestions] = useState<Record<string, FindingSuggestion>>({});
  const [loadingSuggestions, setLoadingSuggestions] = useState<Record<string, boolean>>({});
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);

  useEffect(() => {
    loadAllFindings();
  }, []);

  async function loadAllFindings() {
    setLoading(true);
    try {
      // 1. Fetch connected repos
      const reposRes = await fetch("/api/repos");
      if (!reposRes.ok) return;
      const repos = await reposRes.json();

      const allFindings: FindingItem[] = [];
      // 2. For each repo, fetch latest scan findings
      for (const repo of repos) {
        const scansRes = await fetch(`/api/repos/${repo.id}/scans`);
        if (scansRes.ok) {
          const scans = await scansRes.json();
          const latestCompleted = scans.find((s: any) => s.status === "completed");
          if (latestCompleted) {
            const findingsRes = await fetch(`/api/scans/${latestCompleted.id}/findings`);
            if (findingsRes.ok) {
              const findingsData = await findingsRes.json();
              for (const f of findingsData) {
                allFindings.push({ ...f, repo_name: repo.full_name });
              }
            }
          }
        }
      }
      setFindings(allFindings);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function toggleGeminiSuggestion(findingId: string) {
    if (expandedIds.has(findingId)) {
      setExpandedIds((prev) => {
        const next = new Set(prev);
        next.delete(findingId);
        return next;
      });
      return;
    }

    if (suggestions[findingId]) {
      setExpandedIds((prev) => new Set(prev).add(findingId));
      return;
    }

    setLoadingSuggestions((prev) => ({ ...prev, [findingId]: true }));
    try {
      const res = await fetch(`/api/findings/${findingId}/suggest`, {
        method: "POST",
      });
      if (res.ok) {
        const data: FindingSuggestion = await res.json();
        setSuggestions((prev) => ({ ...prev, [findingId]: data }));
        setExpandedIds((prev) => new Set(prev).add(findingId));
      }
    } catch (err) {
      console.error("Failed to load Gemini suggestion:", err);
    } finally {
      setLoadingSuggestions((prev) => ({ ...prev, [findingId]: false }));
    }
  }

  function handleCopy(findingId: string, code: string) {
    navigator.clipboard.writeText(code);
    setCopiedCodeId(findingId);
    setTimeout(() => setCopiedCodeId(null), 2000);
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

  const filteredFindings = findings.filter((f) => {
    const matchesSearch =
      f.title.toLowerCase().includes(search.toLowerCase()) ||
      f.file_path.toLowerCase().includes(search.toLowerCase()) ||
      f.rule_id.toLowerCase().includes(search.toLowerCase());

    const matchesSeverity =
      severityFilter === "all" || f.severity.toLowerCase() === severityFilter.toLowerCase();

    return matchesSearch && matchesSeverity;
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Security Findings</h1>
        <p className="text-muted-foreground mt-1">
          Detailed vulnerability breakdown discovered across all scanned repositories with AI-assisted remediations.
        </p>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-96">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by file, title, or rule ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-muted/40 border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {["all", "critical", "high", "medium", "low"].map((sev) => (
            <Button
              key={sev}
              variant={severityFilter === sev ? "default" : "outline"}
              size="sm"
              onClick={() => setSeverityFilter(sev)}
              className="capitalize text-xs h-8 border-border"
            >
              {sev}
            </Button>
          ))}
        </div>
      </div>

      {/* Findings List */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-medium">Aggregating findings from scans...</p>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="border border-border rounded-xl p-16 text-center bg-card/30">
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="h-7 w-7 text-green-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No security findings found</h3>
          <p className="text-muted-foreground text-sm mb-6 max-w-sm mx-auto">
            {search || severityFilter !== "all"
              ? "No findings matched your search filter criteria."
              : "Connect your GitHub repositories and trigger a scan to start finding and remediating vulnerabilities."}
          </p>
          <Link href="/repos">
            <Button className="font-medium">Go to Repositories</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredFindings.map((f) => {
            const isExpanded = expandedIds.has(f.id);
            const isLoadingSuggestion = Boolean(loadingSuggestions[f.id]);
            const suggestion = suggestions[f.id];

            return (
              <Card
                key={f.id}
                className="p-5 border-border bg-card/50 hover:border-border/80 transition-all space-y-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      {getSeverityBadge(f.severity)}
                      <span className="font-bold text-sm text-foreground">{f.title}</span>
                      {f.repo_name && (
                        <Badge variant="outline" className="text-xs text-muted-foreground border-border">
                          {f.repo_name}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">{f.description}</p>
                  </div>

                  <code className="text-[11px] bg-muted px-2 py-1 rounded text-muted-foreground font-mono">
                    {f.rule_id}
                  </code>
                </div>

                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <FileCode className="h-3.5 w-3.5 text-primary" />
                  <span className="font-mono text-foreground">
                    {f.file_path}:{f.line_start}
                  </span>
                </div>

                {/* Vulnerable Code Snippet */}
                {f.code_snippet && (
                  <div className="bg-black/70 rounded-md p-3 font-mono text-xs overflow-x-auto border border-border/50">
                    <pre className="text-red-400/90 whitespace-pre">{f.code_snippet}</pre>
                  </div>
                )}

                {/* Card Action Footer with Gemini Suggestions Button */}
                <div className="flex items-center justify-between pt-2 border-t border-border/40">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => toggleGeminiSuggestion(f.id)}
                    disabled={isLoadingSuggestion}
                    className={`h-8 gap-1.5 text-xs transition-all ${
                      isExpanded
                        ? "bg-primary/10 border-primary/40 text-primary"
                        : "border-primary/20 text-primary hover:bg-primary/10"
                    }`}
                  >
                    {isLoadingSuggestion ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Analyzing with Gemini...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-3.5 w-3.5" />
                        {isExpanded ? "Hide Gemini Suggestion" : "✨ Gemini Improvements & Coding Style"}
                        {isExpanded ? (
                          <ChevronUp className="h-3.5 w-3.5 ml-1" />
                        ) : (
                          <ChevronDown className="h-3.5 w-3.5 ml-1" />
                        )}
                      </>
                    )}
                  </Button>

                  <span className="text-[11px] text-muted-foreground font-mono">
                    Status: <span className="text-foreground capitalize">{f.status || "open"}</span>
                  </span>
                </div>

                {/* Collapsible Structured Gemini Suggestion Panel */}
                {isExpanded && suggestion && (
                  <div className="mt-3 p-4 rounded-xl bg-card border border-primary/30 shadow-md space-y-4 animate-in fade-in-50 duration-200">
                    {/* Suggestion Header */}
                    <div className="flex items-center justify-between pb-2 border-b border-border/50">
                      <div className="flex items-center gap-2">
                        <div className="h-7 w-7 rounded-md bg-primary/10 border border-primary/20 flex items-center justify-center">
                          <Sparkles className="h-3.5 w-3.5 text-primary" />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-foreground">
                            Gemini Code Improvement & Architecture Review
                          </h4>
                          <span className="text-[10px] text-muted-foreground font-mono">
                            Model: {suggestion.model}
                          </span>
                        </div>
                      </div>

                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCopy(f.id, suggestion.improved_code)}
                        className="h-7 text-xs gap-1.5 text-muted-foreground hover:text-foreground"
                      >
                        {copiedCodeId === f.id ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            Copy Fix
                          </>
                        )}
                      </Button>
                    </div>

                    {/* Section 1: Vulnerability Analysis */}
                    <div className="space-y-1.5">
                      <h5 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Shield className="h-3.5 w-3.5 text-primary" />
                        Vulnerability & Root Cause Analysis
                      </h5>
                      <p className="text-xs text-foreground/90 leading-relaxed bg-muted/30 p-2.5 rounded-lg border border-border/40">
                        {suggestion.explanation}
                      </p>
                    </div>

                    {/* Section 2: Recommended Secure Code */}
                    <div className="space-y-1.5">
                      <h5 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Code2 className="h-3.5 w-3.5 text-emerald-400" />
                        Recommended Secure Code Replacement
                      </h5>
                      <div className="bg-black/80 rounded-lg p-3 font-mono text-xs overflow-x-auto border border-emerald-500/20">
                        <pre className="text-emerald-300 whitespace-pre">{suggestion.improved_code}</pre>
                      </div>
                    </div>

                    {/* Section 3: Coding Style & Modernization Improvements */}
                    {suggestion.coding_style_improvements && suggestion.coding_style_improvements.length > 0 && (
                      <div className="space-y-1.5">
                        <h5 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                          <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                          Coding Style & Modernization Improvements
                        </h5>
                        <ul className="space-y-1 bg-muted/20 p-2.5 rounded-lg border border-border/40 text-xs">
                          {suggestion.coding_style_improvements.map((item, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-muted-foreground">
                              <span className="text-primary font-bold">•</span>
                              <span className="text-foreground/90">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Section 4: Defense-in-Depth & Best Practices */}
                    {suggestion.best_practices && suggestion.best_practices.length > 0 && (
                      <div className="space-y-1.5">
                        <h5 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                          <ShieldCheck className="h-3.5 w-3.5 text-blue-400" />
                          Defense-in-Depth Best Practices
                        </h5>
                        <ul className="space-y-1 bg-muted/20 p-2.5 rounded-lg border border-border/40 text-xs">
                          {suggestion.best_practices.map((item, idx) => (
                            <li key={idx} className="flex items-start gap-2 text-muted-foreground">
                              <span className="text-emerald-400 font-bold">&#10003;</span>
                              <span className="text-foreground/90">{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Section 5: CWE Mitigation */}
                    {suggestion.cwe_mitigation && (
                      <div className="text-[11px] text-muted-foreground pt-1 border-t border-border/30 flex items-center gap-1.5">
                        <span className="font-semibold text-foreground">Compliance Impact:</span>
                        <span>{suggestion.cwe_mitigation}</span>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
