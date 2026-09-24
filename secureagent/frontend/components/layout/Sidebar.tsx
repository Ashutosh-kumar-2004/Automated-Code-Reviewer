/**
 * Sidebar navigation — fixed left panel.
 * Uses next/navigation for active link detection.
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield,
  LayoutDashboard,
  GitBranch,
  AlertTriangle,
  GitPullRequest,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/repos", icon: GitBranch, label: "Repositories" },
  { href: "/findings", icon: AlertTriangle, label: "Findings" },
  { href: "/pull-requests", icon: GitPullRequest, label: "Pull Requests" },
  { href: "/reports", icon: FileText, label: "Reports" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 border-r border-border bg-card/40 backdrop-blur-sm flex flex-col z-40">
      {/* Logo */}
      <Link href="/dashboard" className="flex items-center gap-2.5 px-6 py-5 border-b border-border">
        <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Shield className="h-4 w-4 text-primary" />
        </div>
        <span className="font-bold tracking-tight text-sm">SecureAgent</span>
      </Link>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {navItems.map(({ href, icon: Icon, label }) => {
          const isActive =
            pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Version */}
      <div className="px-6 py-4 border-t border-border">
        <p className="text-xs text-muted-foreground">SecureAgent v0.1.0</p>
      </div>
    </aside>
  );
}
