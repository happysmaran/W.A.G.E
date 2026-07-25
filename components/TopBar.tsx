"use client";

import { useEffect, useState } from "react";
import { Job, OllamaStatus } from "@/lib/types";

interface TopBarProps {
  jobs: Job[];
  ollamaStatus: OllamaStatus;
}

function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function formatTime(d: Date) {
  return d.toLocaleTimeString("en-US", { hour12: false });
}

export function TopBar({ jobs, ollamaStatus }: TopBarProps) {
  const now = useClock();
  const avgScore = jobs.length ? Math.round(jobs.reduce((sum, j) => sum + j.score, 0) / jobs.length) : null;
  const activeCount = jobs.filter((j) => j.status !== "archived").length;

  return (
    <div className="w-full border-b border-base-line bg-base-bg px-4 py-2 flex items-center justify-between text-[11px] font-mono uppercase tracking-wideish">
      <div className="flex items-center gap-5">
        <span className="text-ink-primary font-medium tracking-wide">JOBRADAR</span>
        <span className="text-ink-muted hidden sm:inline">TRACKED {jobs.length}</span>
        <span className="text-ink-muted hidden sm:inline">ACTIVE {activeCount}</span>
        <span className="text-ink-muted hidden md:inline">
          AVG FIT {avgScore !== null ? avgScore : "—"}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 ${ollamaStatus.connected ? "bg-signal-go" : "bg-signal-stop"}`} />
          <span className="text-ink-muted hidden sm:inline">{ollamaStatus.mode}</span>
        </div>
        <span className="text-ink-secondary tabular-nums">{now ? formatTime(now) : "--:--:--"}</span>
      </div>
    </div>
  );
}
