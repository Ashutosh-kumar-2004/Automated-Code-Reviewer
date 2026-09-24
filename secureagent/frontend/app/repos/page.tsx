"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  GitBranch,
  Play,
  Lock,
  Globe,
  Trash2,
  ExternalLink,
  Shield,
  Loader2,
  AlertCircle,
  Plus,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import ConnectRepoModal from "@/components/repo/ConnectRepoModal";

interface ConnectedRepo {
  id: string;
  github_repo_id: string;
  full_name: string;
  clone_url: string;
  html_url: string;
  default_branch: string;
  language: string | null;
  description: string | null;
  is_private: boolean;
  is_active: boolean;
  last_scanned_at: string | null;
  created_at: string;
}

export default function ReposPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<ConnectedRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [scanningRepoId, setScanningRepoId] = useState<string | null>(null);

  useEffect(() => {
    loadConnectedRepos();
  }, []);

  async function loadConnectedRepos() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/repos");
      if (!res.ok) throw new Error("Failed to load connected repositories");
      const data = await res.json();
      setRepos(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || "Failed to load repositories");
    } finally {
      setLoading(false);
    }
  }

  async function handleTriggerScan(repoId: string) {
    setScanningRepoId(repoId);
    try {
      const res = await fetch("/api/scans", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_id: repoId }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to start scan");
      }

      const scan = await res.json();
      router.push(`/repos/${repoId}?scanId=${scan.id}`);
    } catch (err: any) {
      alert(`Error starting scan: ${err.message}`);
    } finally {
      setScanningRepoId(null);
    }
  }

  async function handleDisconnect(repoId: string, fullName: string) {
    if (!confirm(`Are you sure you want to disconnect ${fullName}?`)) return;

    try {
      const res = await fetch(`/api/repos/${repoId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to disconnect repository");
      setRepos((prev) => prev.filter((r) => r.id !== repoId));
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Connected Repositories</h1>
          <p className="text-muted-foreground mt-1">
            Manage your monitored repositories and trigger automated security scans.
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="gap-2 shadow-sm font-semibold">
          <Plus className="h-4 w-4" />
          Connect Repository
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-xl flex items-center gap-3">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-medium">Loading connected repositories...</p>
        </div>
      ) : repos.length === 0 ? (
        <div className="border border-border rounded-xl p-16 text-center bg-card/30">
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-5">
            <GitBranch className="h-7 w-7 text-primary" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No repositories connected</h3>
          <p className="text-muted-foreground text-sm mb-6 max-w-sm mx-auto">
            Connect a GitHub repository to start scanning and automatically remediating security vulnerabilities.
          </p>
          <Button onClick={() => setIsModalOpen(true)} className="gap-2 font-medium">
            <Plus className="h-4 w-4" />
            Connect Your First Repo
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {repos.map((repo) => {
            const isScanning = scanningRepoId === repo.id;

            return (
              <Card
                key={repo.id}
                className="p-5 border-border bg-card/50 hover:border-primary/40 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <Link
                        href={`/repos/${repo.id}`}
                        className="font-bold text-base hover:text-primary transition-colors truncate"
                      >
                        {repo.full_name}
                      </Link>
                      {repo.is_private ? (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 gap-1 text-muted-foreground">
                          <Lock className="h-2.5 w-2.5" /> Private
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 gap-1 text-muted-foreground">
                          <Globe className="h-2.5 w-2.5" /> Public
                        </Badge>
                      )}
                    </div>

                    <a
                      href={repo.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors p-1"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>

                  {repo.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                      {repo.description}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground mb-4">
                    {repo.language && (
                      <span className="flex items-center gap-1.5 font-medium text-foreground">
                        <span className="h-2 w-2 rounded-full bg-primary" />
                        {repo.language}
                      </span>
                    )}
                    <span>Branch: <code className="bg-muted px-1.5 py-0.5 rounded text-[11px]">{repo.default_branch}</code></span>
                    {repo.last_scanned_at ? (
                      <span>Last scan: {new Date(repo.last_scanned_at).toLocaleDateString()}</span>
                    ) : (
                      <span className="text-amber-400">Never scanned</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border/60">
                  <Link
                    href={`/repos/${repo.id}`}
                    className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
                  >
                    View Scans & Findings →
                  </Link>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDisconnect(repo.id, repo.full_name)}
                      className="h-8 px-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 border-border"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>

                    <Button
                      size="sm"
                      onClick={() => handleTriggerScan(repo.id)}
                      disabled={isScanning}
                      className="h-8 gap-1.5 font-medium"
                    >
                      {isScanning ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5 fill-current" />
                          Scan Now
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Connect Repo Modal */}
      <ConnectRepoModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        onRepoConnected={loadConnectedRepos}
      />
    </div>
  );
}
