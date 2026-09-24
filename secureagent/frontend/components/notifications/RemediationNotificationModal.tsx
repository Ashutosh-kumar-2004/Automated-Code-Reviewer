"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Bell,
  ShieldAlert,
  AlertTriangle,
  FolderGit2,
  Sparkles,
  GitPullRequest,
  CheckCircle2,
  Clock,
  ExternalLink,
  X,
} from "lucide-react";
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

interface AffectedRepo {
  repo_id: string;
  repo_name: string;
  count: number;
}

interface UrgentFinding {
  id: string;
  title: string;
  severity: string;
  rule_id: string;
  file_path: string;
  line_start: number | null;
}

interface RemediationNotificationData {
  has_vulnerabilities: boolean;
  total_vulnerabilities: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  interval_minutes: number;
  interval_seconds: number;
  affected_repos: AffectedRepo[];
  urgent_findings: UrgentFinding[];
  alert_title: string;
  alert_message: string;
}

const STORAGE_KEY_SNOOZE = "secureagent_remediation_snoozed_until";

export default function RemediationNotificationModal() {
  const [data, setData] = useState<RemediationNotificationData | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkRemediationStatus(true);

    // Periodic check every 60 seconds
    const interval = setInterval(() => {
      checkRemediationStatus(false);
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  async function checkRemediationStatus(triggerAutoOpen: boolean) {
    try {
      const res = await fetch("/api/notifications/remediation");
      if (!res.ok) return;
      const json: RemediationNotificationData = await res.json();
      setData(json);

      if (json.has_vulnerabilities && triggerAutoOpen) {
        const snoozedUntilStr = localStorage.getItem(STORAGE_KEY_SNOOZE);
        const now = Date.now();
        const snoozedUntil = snoozedUntilStr ? Number(snoozedUntilStr) : 0;

        // If no active snooze or interval has elapsed, trigger the notification modal
        if (!snoozedUntil || now >= snoozedUntil) {
          setIsOpen(true);
          // Set next notification window based on configured interval in seconds
          const nextAlertTime = now + (json.interval_seconds || 3600) * 1000;
          localStorage.setItem(STORAGE_KEY_SNOOZE, String(nextAlertTime));
        }
      }
    } catch (err) {
      console.error("Failed to check remediation status:", err);
    }
  }

  function handleSnooze() {
    if (data) {
      const nextTime = Date.now() + (data.interval_seconds || 3600) * 1000;
      localStorage.setItem(STORAGE_KEY_SNOOZE, String(nextTime));
    }
    setIsOpen(false);
  }

  function handleDismiss() {
    setIsOpen(false);
  }

  const hasAlerts = Boolean(data?.has_vulnerabilities);
  const totalCount = data?.total_vulnerabilities || 0;
  const criticalCount = data?.critical_count || 0;
  const intervalMins = data?.interval_minutes || 60;

  return (
    <>
      {/* TopBar Bell Notification Trigger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors cursor-pointer outline-none"
        title={hasAlerts ? `${totalCount} vulnerabilities require remediation` : "Remediator Agent: Clean"}
      >
        <Bell className={`h-4 w-4 ${hasAlerts ? "text-amber-400" : ""}`} />
        {hasAlerts && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-sm ring-1 ring-background">
            {totalCount > 9 ? "9+" : totalCount}
          </span>
        )}
      </button>

      {/* Remediation Notification Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="sm:max-w-xl bg-card border-border shadow-2xl p-6 overflow-hidden">
          {/* Header Banner */}
          <div className="flex items-start justify-between gap-4 pb-4 border-b border-border/60">
            <div className="flex items-center gap-3">
              <div
                className={`h-10 w-10 rounded-xl flex items-center justify-center border ${
                  criticalCount > 0
                    ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                }`}
              >
                <ShieldAlert className="h-5 w-5" />
              </div>
              <div>
                <DialogTitle className="text-base font-bold tracking-tight text-foreground flex items-center gap-2">
                  <span>Security Remediator Notification</span>
                  <Badge variant="outline" className="text-[10px] font-mono py-0 text-muted-foreground">
                    <Clock className="h-2.5 w-2.5 mr-1" />
                    Every {intervalMins >= 60 ? `${intervalMins / 60}h` : `${intervalMins}m`}
                  </Badge>
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                  Automated scan analysis detected unresolved vulnerabilities needing remediation.
                </DialogDescription>
              </div>
            </div>
          </div>

          {/* Modal Body */}
          <div className="space-y-4 py-2">
            {/* Alert Message Box */}
            <div
              className={`p-3.5 rounded-xl border text-xs leading-relaxed ${
                criticalCount > 0
                  ? "bg-rose-500/10 border-rose-500/20 text-rose-300"
                  : "bg-amber-500/10 border-amber-500/20 text-amber-300"
              }`}
            >
              <p className="font-semibold text-sm mb-1">{data?.alert_title}</p>
              <p>{data?.alert_message}</p>
            </div>

            {/* Severity Breakdown Grid */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="p-2.5 rounded-lg bg-muted/40 border border-border/50">
                <span className="text-[10px] uppercase font-semibold text-muted-foreground block">Total</span>
                <span className="text-lg font-bold text-foreground">{totalCount}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20">
                <span className="text-[10px] uppercase font-semibold text-rose-400 block">Critical</span>
                <span className="text-lg font-bold text-rose-400">{criticalCount}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-orange-500/10 border border-orange-500/20">
                <span className="text-[10px] uppercase font-semibold text-orange-400 block">High</span>
                <span className="text-lg font-bold text-orange-400">{data?.high_count || 0}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
                <span className="text-[10px] uppercase font-semibold text-blue-400 block">Medium/Low</span>
                <span className="text-lg font-bold text-blue-400">
                  {(data?.medium_count || 0) + (data?.low_count || 0)}
                </span>
              </div>
            </div>

            {/* Affected Repositories */}
            {data?.affected_repos && data.affected_repos.length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Affected Repositories
                </h4>
                <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
                  {data.affected_repos.map((r) => (
                    <div
                      key={r.repo_id}
                      className="flex items-center justify-between p-2 rounded-lg bg-muted/20 border border-border/40 text-xs"
                    >
                      <span className="font-mono flex items-center gap-1.5 text-foreground truncate">
                        <FolderGit2 className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                        <span className="truncate">{r.repo_name}</span>
                      </span>
                      <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 text-[11px]">
                        {r.count} {r.count === 1 ? "vulnerability" : "vulnerabilities"}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top Urgent Findings Preview */}
            {data?.urgent_findings && data.urgent_findings.length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Highest Severity Vulnerabilities
                </h4>
                <div className="space-y-1 max-h-32 overflow-y-auto pr-1">
                  {data.urgent_findings.map((f) => (
                    <div
                      key={f.id}
                      className="p-2 rounded-lg bg-muted/20 border border-border/40 text-xs space-y-0.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-foreground truncate">{f.title}</span>
                        <Badge
                          className={`text-[10px] font-bold uppercase ${
                            f.severity === "critical"
                              ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              : "bg-orange-500/10 text-orange-400 border-orange-500/20"
                          }`}
                        >
                          {f.severity}
                        </Badge>
                      </div>
                      <p className="text-[11px] font-mono text-muted-foreground truncate">
                        {f.file_path}{f.line_start ? `:${f.line_start}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Modal Footer Actions */}
          <DialogFooter className="gap-2 sm:gap-2 flex-col-reverse sm:flex-row pt-3 border-t border-border/50">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSnooze}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Snooze ({intervalMins >= 60 ? `${intervalMins / 60}h` : `${intervalMins}m`})
            </Button>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Link
                href="/pull-requests"
                onClick={() => setIsOpen(false)}
                className="w-full sm:w-auto"
              >
                <Button variant="outline" size="sm" className="w-full text-xs gap-1.5">
                  <GitPullRequest className="h-3.5 w-3.5" />
                  Create PR
                </Button>
              </Link>

              <Link
                href="/findings"
                onClick={() => setIsOpen(false)}
                className="w-full sm:w-auto"
              >
                <Button size="sm" className="w-full text-xs gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" />
                  Fix with Gemini AI
                </Button>
              </Link>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
