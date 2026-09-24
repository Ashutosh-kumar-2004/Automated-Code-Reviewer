import { auth } from "@/lib/auth";
import { Shield, GitBranch, AlertTriangle, TrendingUp, Play, ArrowRight, ExternalLink } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { mintBffJwt, BACKEND_URL } from "@/lib/bff";

export const metadata = {
  title: "Dashboard — SecureAgent",
  description: "Your security overview across all connected repositories",
};

export default async function DashboardPage() {
  const session = await auth();
  const login = (session as any)?.login as string;
  const userId = ((session as any)?.userId || (session as any)?.githubId || session?.user?.id) as string;

  let summary = {
    repo_count: 0,
    findings_by_severity: { critical: 0, high: 0, medium: 0, low: 0 },
    recent_scans: [] as any[],
    average_score: null as number | null,
  };

  let connectedRepos: any[] = [];

  if (userId) {
    try {
      const bffToken = await mintBffJwt(userId, login || "user");
      const [sumRes, reposRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/v1/dashboard/summary`, {
          headers: { Authorization: `Bearer ${bffToken}` },
          cache: "no-store",
        }),
        fetch(`${BACKEND_URL}/api/v1/repos`, {
          headers: { Authorization: `Bearer ${bffToken}` },
          cache: "no-store",
        }),
      ]);

      if (sumRes.ok) {
        summary = await sumRes.json();
      }
      if (reposRes.ok) {
        connectedRepos = await reposRes.json();
      }
    } catch (e) {
      console.error("Dashboard fetch error:", e);
    }
  }

  const totalFindings =
    (summary.findings_by_severity?.critical || 0) +
    (summary.findings_by_severity?.high || 0) +
    (summary.findings_by_severity?.medium || 0) +
    (summary.findings_by_severity?.low || 0);

  const avgScore = summary.average_score !== null ? `${summary.average_score}/100` : summary.repo_count > 0 ? "100/100" : "—";

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Welcome back, {login} 👋
          </h1>
          <p className="text-muted-foreground mt-1">
            Here's your live security overview across all connected repositories.
          </p>
        </div>
        <Link href="/repos">
          <Button className="gap-2 font-semibold shadow-sm">
            <GitBranch className="h-4 w-4" />
            Manage Repositories
          </Button>
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Connected Repos",
            value: summary.repo_count,
            icon: <GitBranch className="h-5 w-5 text-blue-400" />,
            href: "/repos",
          },
          {
            label: "Open Findings",
            value: totalFindings,
            icon: <AlertTriangle className="h-5 w-5 text-orange-400" />,
            href: "/findings",
          },
          {
            label: "Avg Security Score",
            value: avgScore,
            icon: <Shield className="h-5 w-5 text-green-400" />,
          },
          {
            label: "Fixes Applied",
            value: "0",
            icon: <TrendingUp className="h-5 w-5 text-violet-400" />,
          },
        ].map((stat) => (
          <Link
            key={stat.label}
            href={stat.href || "#"}
            className={stat.href ? "cursor-pointer" : "cursor-default"}
          >
            <Card className="p-5 border-border bg-card/50 hover:border-primary/40 transition-all">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  {stat.label}
                </span>
                {stat.icon}
              </div>
              <div className="text-3xl font-bold tracking-tight">{stat.value}</div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Connected Repositories / Empty State */}
      {connectedRepos.length === 0 ? (
        <div className="border border-border rounded-xl p-16 text-center bg-card/30">
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-5">
            <GitBranch className="h-7 w-7 text-primary" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No repositories connected yet</h3>
          <p className="text-muted-foreground text-sm mb-6 max-w-sm mx-auto">
            Connect a GitHub repository to start scanning for security vulnerabilities.
          </p>
          <Link
            href="/repos"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <GitBranch className="h-4 w-4" />
            Connect a Repository
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold tracking-tight">Active Repositories</h2>
            <Link href="/repos" className="text-xs text-primary hover:underline flex items-center gap-1 font-medium">
              View all repos <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {connectedRepos.slice(0, 4).map((repo) => (
              <Card key={repo.id} className="p-5 border-border bg-card/50 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Link href={`/repos/${repo.id}`} className="font-bold text-base hover:text-primary transition-colors truncate">
                      {repo.full_name}
                    </Link>
                    {repo.language && (
                      <Badge variant="outline" className="text-xs">
                        {repo.language}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3">
                    {repo.description || "No description provided."}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <span className="text-xs text-muted-foreground">
                    {repo.last_scanned_at ? `Scanned ${new Date(repo.last_scanned_at).toLocaleDateString()}` : "Never scanned"}
                  </span>
                  <Link href={`/repos/${repo.id}`}>
                    <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs">
                      <Play className="h-3 w-3 fill-current" /> Scan / Details
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
