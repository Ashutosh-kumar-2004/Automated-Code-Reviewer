"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Search,
  Lock,
  Globe,
  GitBranch,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Plus,
} from "lucide-react";

interface GitHubRepo {
  id: string;
  full_name: string;
  private: boolean;
  default_branch: string;
  language: string | null;
  description: string | null;
  html_url: string;
  permissions_push: boolean;
}

interface ConnectRepoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRepoConnected: () => void;
}

export default function ConnectRepoModal({
  open,
  onOpenChange,
  onRepoConnected,
}: ConnectRepoModalProps) {
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [connectedIds, setConnectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (open) {
      loadRepos();
    }
  }, [open]);

  async function loadRepos() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/github/repos");
      if (!res.ok) {
        throw new Error("Failed to load repositories from GitHub");
      }
      const data = await res.json();
      setRepos(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || "Could not fetch GitHub repositories");
    } finally {
      setLoading(false);
    }
  }

  async function handleConnect(repo: GitHubRepo) {
    setConnectingId(repo.id);
    setError(null);
    try {
      const res = await fetch("/api/repos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_repo_id: repo.id }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to connect repository");
      }

      setConnectedIds((prev) => new Set([...prev, repo.id]));
      onRepoConnected();
      setTimeout(() => {
        onOpenChange(false);
      }, 500);
    } catch (err: any) {
      setError(err.message || "Failed to connect repository");
    } finally {
      setConnectingId(null);
    }
  }

  const filteredRepos = repos.filter(
    (r) =>
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description && r.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[650px] max-h-[85vh] flex flex-col bg-card border-border">
        <DialogHeader className="pb-2">
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-primary" />
            Connect GitHub Repository
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            Select a repository with push permissions to enable automated scanning and remediation.
          </DialogDescription>
        </DialogHeader>

        {/* Search */}
        <div className="relative my-2">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search your repositories..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-muted/40 border border-border rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive text-sm rounded-lg flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Repos list */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[400px]">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <p className="text-sm">Fetching your GitHub repositories...</p>
            </div>
          ) : filteredRepos.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-sm font-medium">No repositories found</p>
              {search && <p className="text-xs mt-1">Try a different search query</p>}
            </div>
          ) : (
            filteredRepos.map((repo) => {
              const isConnected = connectedIds.has(repo.id);
              const isConnecting = connectingId === repo.id;

              return (
                <div
                  key={repo.id}
                  className="flex items-center justify-between p-3.5 rounded-lg border border-border bg-card/60 hover:bg-muted/40 transition-colors"
                >
                  <div className="min-w-0 flex-1 mr-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-sm truncate">
                        {repo.full_name}
                      </span>
                      {repo.private ? (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 gap-1 text-muted-foreground border-border">
                          <Lock className="h-2.5 w-2.5" /> Private
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 gap-1 text-muted-foreground border-border">
                          <Globe className="h-2.5 w-2.5" /> Public
                        </Badge>
                      )}
                    </div>
                    {repo.description && (
                      <p className="text-xs text-muted-foreground truncate mb-1.5">
                        {repo.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      {repo.language && (
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-primary" />
                          {repo.language}
                        </span>
                      )}
                      <span>Branch: {repo.default_branch}</span>
                    </div>
                  </div>

                  <div>
                    {isConnected ? (
                      <Button size="sm" variant="ghost" disabled className="gap-1.5 text-green-400">
                        <CheckCircle2 className="h-4 w-4" /> Connected
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleConnect(repo)}
                        disabled={isConnecting || !repo.permissions_push}
                        className="gap-1.5 font-medium"
                      >
                        {isConnecting ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Connecting...
                          </>
                        ) : !repo.permissions_push ? (
                          "Read Only"
                        ) : (
                          <>
                            <Plus className="h-3.5 w-3.5" />
                            Connect
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
