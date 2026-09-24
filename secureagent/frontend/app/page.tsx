import Link from "next/link";
import { auth, signIn } from "@/lib/auth";
import { redirect } from "next/navigation";
import { Shield, Zap, GitPullRequest, Eye, Lock, ChevronRight, Code2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export default async function LandingPage() {
  const session = await auth();
  if (session) redirect("/dashboard");

  return (
    <div className="min-h-screen hero-gradient">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 border-b border-border/40 bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="text-lg font-bold tracking-tight">SecureAgent</span>
          </div>
          <form
            action={async () => {
              "use server";
              await signIn("github", { redirectTo: "/dashboard" });
            }}
          >
            <Button variant="outline" size="sm" className="gap-2 border-border hover:border-primary/50 hover:bg-primary/10">
              <GitHubIcon className="h-4 w-4" />
              Sign in with GitHub
            </Button>
          </form>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-40 pb-24 px-6 text-center">
        <Badge variant="outline" className="mb-6 border-primary/30 text-primary bg-primary/10 px-4 py-1.5">
          <Zap className="h-3.5 w-3.5 mr-1.5" />
          Powered by Gemini 2.5 + LangGraph
        </Badge>

        <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight mb-6 bg-gradient-to-br from-white via-white/90 to-white/50 bg-clip-text text-transparent leading-[1.1]">
          Your AI Security<br />
          <span className="bg-gradient-to-r from-blue-400 to-violet-500 bg-clip-text text-transparent">
            Code Reviewer
          </span>
        </h1>

        <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
          Connect a GitHub repo. SecureAgent scans for vulnerabilities, explains them in plain English,
          generates verified fixes, and opens a Pull Request — all without a single line of manual work.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <form
            action={async () => {
              "use server";
              await signIn("github", { redirectTo: "/dashboard" });
            }}
          >
            <Button
              size="lg"
              className="gap-2 bg-primary hover:bg-primary/90 text-white glow-primary px-8 py-6 text-base font-semibold"
            >
              <GitHubIcon className="h-5 w-5" />
              Connect with GitHub
              <ChevronRight className="h-4 w-4" />
            </Button>
          </form>
          <Button variant="ghost" size="lg" className="text-muted-foreground hover:text-foreground px-8 py-6 text-base">
            View Demo
          </Button>
        </div>
      </section>

      {/* Feature grid */}
      <section className="max-w-7xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: <Code2 className="h-6 w-6 text-blue-400" />,
              title: "Multi-Scanner Analysis",
              desc: "Runs Semgrep, Bandit, Trivy, Gitleaks, and dependency audits. All results normalized to one unified finding format.",
              badge: "Semgrep · Bandit · Trivy",
            },
            {
              icon: <Zap className="h-6 w-6 text-violet-400" />,
              title: "LLM-Powered Fixes",
              desc: "The agent triages false positives, maps findings to CWE & OWASP, generates minimal patches, and verifies them in a Docker sandbox.",
              badge: "Gemini 2.5 Pro",
            },
            {
              icon: <GitPullRequest className="h-6 w-6 text-green-400" />,
              title: "Human-Approved PRs",
              desc: "Verified fixes are presented for your review. You approve, reject, or dismiss each one. The agent never auto-merges.",
              badge: "Human-in-the-loop",
            },
            {
              icon: <Eye className="h-6 w-6 text-orange-400" />,
              title: "Live Progress Stream",
              desc: "Watch the agent work in real time — cloning, scanning, triaging, fixing, verifying — with streaming logs.",
              badge: "Server-Sent Events",
            },
            {
              icon: <AlertTriangle className="h-6 w-6 text-yellow-400" />,
              title: "CWE & OWASP Tagged",
              desc: "Every finding is mapped to CWE IDs and OWASP Top 10 categories with a plain-English explanation and confidence score.",
              badge: "OWASP Top 10",
            },
            {
              icon: <Lock className="h-6 w-6 text-red-400" />,
              title: "Sandboxed & Secure",
              desc: "Cloned code never executes outside an isolated Docker container. Prompt injection is blocked via nonce delimiters.",
              badge: "Docker · Non-root",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="card-hover border border-border rounded-xl p-6 bg-card/50 backdrop-blur-sm"
            >
              <div className="mb-4">{f.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed mb-4">{f.desc}</p>
              <Badge variant="outline" className="text-xs border-border/60">
                {f.badge}
              </Badge>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 py-8 text-center text-sm text-muted-foreground">
        <p>SecureAgent — Never auto-merges. Human always approves.</p>
      </footer>
    </div>
  );
}
