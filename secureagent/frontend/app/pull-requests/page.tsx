"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  GitPullRequest,
  Search,
  ExternalLink,
  RefreshCw,
  ShieldAlert,
  GitBranch,
  CheckCircle2,
  Clock,
  Filter,
  PlusCircle,
  AlertTriangle,
  Loader2,
  FolderGit2,
  Sparkles,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

interface PullRequestItem {
  id: string;
  scan_id: string;
  repo_id: string;
  repo_name?: string;
  repo_url?: string;
  github_pr_number?: number;
  github_pr_url?: string;
  branch_name: string;
  title: string;
  body?: string;
  status: "open" | "merged" | "closed" | "draft";
  has_secret_removal: boolean;
  fixes_count: number;
  created_at: string;
  merged_at?: string;
  updated_at?: string;
}

interface ScanOption {
  id: string;
  repo_id: string;
  repo_name: string;
  total_findings: number;
  security_score: number | null;
  completed_at: string | null;
}

export default function PullRequestsPage() {
  const [prs, setPrs] = useState<PullRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  // Create PR modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [availableScans, setAvailableScans] = useState<ScanOption[]>([]);
  const [loadingScans, setLoadingScans] = useState(false);
  const [selectedScanId, setSelectedScanId] = useState<string>("");
  const [customTitle, setCustomTitle] = useState("");
  const [submittingPr, setSubmittingPr] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    loadPullRequests();
  }, []);

  async function loadPullRequests() {
    setLoading(true);
    try {
      const res = await fetch("/api/prs");
      if (res.ok) {
        const data = await res.json();
        setPrs(data);
      }
    } catch (err) {
      console.error("Failed to load pull requests:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh(prId: string) {
    setRefreshingId(prId);
    try {
      const res = await fetch(`/api/prs/${prId}/refresh`, { method: "POST" });
      if (res.ok) {
        await loadPullRequests();
      }
    } catch (err) {
      console.error("Failed to refresh PR status:", err);
    } finally {
      setRefreshingId(null);
    }
  }

  async function openCreateModal() {
    setModalOpen(true);
    setLoadingScans(true);
    setCreateError(null);
    setSelectedScanId("");
    setCustomTitle("");
    try {
      const reposRes = await fetch("/api/repos");
      if (!reposRes.ok) return;
      const repos = await reposRes.json();

      const options: ScanOption[] = [];
      for (const r of repos) {
        const scansRes = await fetch(`/api/repos/${r.id}/scans`);
        if (scansRes.ok) {
          const scans = await scansRes.json();
          for (const s of scans) {
            if (s.status === "completed") {
              options.push({
                id: s.id,
                repo_id: r.id,
                repo_name: r.full_name,
                total_findings: s.total_findings || 0,
                security_score: s.security_score,
                completed_at: s.completed_at,
              });
            }
          }
        }
      }
      setAvailableScans(options);
      if (options.length > 0) {
        setSelectedScanId(options[0].id);
      }
    } catch (err) {
      console.error("Failed to load candidate scans:", err);
    } finally {
      setLoadingScans(false);
    }
  }

  async function handleCreatePr() {
    if (!selectedScanId) return;
    setSubmittingPr(true);
    setCreateError(null);
    try {
      const res = await fetch("/api/prs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scan_id: selectedScanId,
          title: customTitle.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to create pull request");
      }
      setModalOpen(false);
      await loadPullRequests();
    } catch (err: any) {
      setCreateError(err.message || "An unexpected error occurred");
    } finally {
      setSubmittingPr(false);
    }
  }

  const filteredPrs = prs.filter((pr) => {
    const matchesSearch =
      pr.title.toLowerCase().includes(search.toLowerCase()) ||
      pr.branch_name.toLowerCase().includes(search.toLowerCase()) ||
      (pr.repo_name && pr.repo_name.toLowerCase().includes(search.toLowerCase()));

    const matchesStatus =
      statusFilter === "all" || pr.status.toLowerCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const totalPrs = prs.length;
  const openPrs = prs.filter((p) => p.status === "open").length;
  const mergedPrs = prs.filter((p) => p.status === "merged").length;
  const remediatedFindings = prs.reduce((acc, p) => acc + (p.fixes_count || 0), 0);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
              <GitPullRequest className="h-5 w-5 text-primary" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Pull Requests</h1>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            Automated, verified security remediation pull requests submitted to your GitHub repositories.
          </p>
        </div>

        <Button onClick={openCreateModal} className="flex items-center gap-2">
          <PlusCircle className="h-4 w-4" />
          Create Remediation PR
        </Button>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
              <GitPullRequest className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Total PRs</p>
              <p className="text-xl font-bold">{totalPrs}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Open PRs</p>
              <p className="text-xl font-bold text-emerald-400">{openPrs}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-purple-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Merged</p>
              <p className="text-xl font-bold text-purple-400">{mergedPrs}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <ShieldAlert className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">Remediated Findings</p>
              <p className="text-xl font-bold text-blue-400">{remediatedFindings}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search PR title, repo, or branch..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-muted/40 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-1.5 bg-muted/30 p-1 rounded-lg border border-border self-start sm:self-auto">
          {["all", "open", "merged", "closed", "draft"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-all ${
                statusFilter === st
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* PR Cards List */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-muted-foreground gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm">Loading remediation pull requests...</p>
        </div>
      ) : filteredPrs.length === 0 ? (
        <Card className="border-dashed border-border bg-card/20 p-12 text-center">
          <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
            <GitPullRequest className="h-6 w-6 text-primary" />
          </div>
          <h3 className="text-base font-semibold">No pull requests found</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-6">
            {search || statusFilter !== "all"
              ? "No pull requests matched your search criteria."
              : "SecureAgent has not generated any pull requests yet. Connect a repository and run a scan to auto-generate patches!"}
          </p>
          <Button onClick={openCreateModal} variant="outline" className="gap-2">
            <PlusCircle className="h-4 w-4" />
            Create Remediation PR
          </Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredPrs.map((pr) => {
            const isOpen = pr.status === "open";
            const isMerged = pr.status === "merged";
            const isClosed = pr.status === "closed";

            return (
              <Card
                key={pr.id}
                className="bg-card/40 border-border hover:border-primary/30 transition-all duration-150 overflow-hidden"
              >
                <div className="p-5 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      {isOpen && (
                        <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-medium">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5" />
                          Open PR #{pr.github_pr_number || 1}
                        </Badge>
                      )}
                      {isMerged && (
                        <Badge className="bg-purple-500/10 text-purple-400 border-purple-500/20 font-medium">
                          Merged PR #{pr.github_pr_number || 1}
                        </Badge>
                      )}
                      {isClosed && (
                        <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 font-medium">
                          Closed PR
                        </Badge>
                      )}
                      {pr.status === "draft" && (
                        <Badge className="bg-muted text-muted-foreground border-border font-medium">
                          Draft
                        </Badge>
                      )}

                      {pr.repo_name && (
                        <span className="text-xs font-mono bg-muted/50 px-2 py-0.5 rounded text-foreground/80 flex items-center gap-1">
                          <FolderGit2 className="h-3 w-3 text-muted-foreground" />
                          {pr.repo_name}
                        </span>
                      )}

                      <span className="text-xs font-mono bg-muted/40 px-2 py-0.5 rounded text-muted-foreground flex items-center gap-1">
                        <GitBranch className="h-3 w-3" />
                        {pr.branch_name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRefresh(pr.id)}
                        disabled={refreshingId === pr.id}
                        className="h-8 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <RefreshCw
                          className={`h-3.5 w-3.5 mr-1.5 ${
                            refreshingId === pr.id ? "animate-spin" : ""
                          }`}
                        />
                        Sync Status
                      </Button>

                      {pr.github_pr_url && (
                        <a
                          href={pr.github_pr_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs">
                            View on GitHub
                            <ExternalLink className="h-3 w-3" />
                          </Button>
                        </a>
                      )}
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="text-base font-semibold tracking-tight text-foreground hover:text-primary transition-colors">
                    {pr.title}
                  </h3>

                  {/* Hardcoded Secret Alert Banner */}
                  {pr.has_secret_removal && (
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5 text-xs text-amber-300">
                      <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold">Secret Rotation Advisory:</span> This pull request replaces exposed credentials. Historical git commits must be scrubbed and the affected tokens revoked immediately at the provider.
                      </div>
                    </div>
                  )}

                  {/* Footer metadata */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t border-border/40">
                    <div className="flex items-center gap-3">
                      <span>
                        Targets <strong className="text-foreground">{pr.fixes_count}</strong> vulnerabilities
                      </span>
                      <span>•</span>
                      <span>
                        Created {new Date(pr.created_at).toLocaleDateString()} at{" "}
                        {new Date(pr.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>

                    <Link
                      href={`/findings`}
                      className="text-primary hover:underline font-medium"
                    >
                      View Findings &rarr;
                    </Link>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create PR Dialog Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="sm:max-w-lg bg-card border-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <GitPullRequest className="h-5 w-5 text-primary" />
              Create Remediation Pull Request
            </DialogTitle>
            <DialogDescription className="text-sm">
              Generate an automated GitHub pull request with verified patches for vulnerabilities detected in a scan.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-3">
            {createError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
                {createError}
              </div>
            )}

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
                Select Completed Scan
              </label>
              {loadingScans ? (
                <div className="py-4 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  Loading candidate scans...
                </div>
              ) : availableScans.length === 0 ? (
                <div className="p-3 rounded-lg bg-muted text-xs text-muted-foreground">
                  No completed scans with findings available. Please run a scan from the Repositories page first.
                </div>
              ) : (
                <select
                  value={selectedScanId}
                  onChange={(e) => setSelectedScanId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {availableScans.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.repo_name} — {s.total_findings} findings (Score: {s.security_score ?? "N/A"})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
                PR Title (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. fix(security): Remediate SQLi and hardcoded secrets"
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-muted/50 border border-border text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="ghost"
              onClick={() => setModalOpen(false)}
              disabled={submittingPr}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreatePr}
              disabled={submittingPr || !selectedScanId}
              className="gap-2"
            >
              {submittingPr ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Submitting PR...
                </>
              ) : (
                <>
                  <GitPullRequest className="h-4 w-4" />
                  Open Pull Request
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
