"use client";

import { useMemo, useState } from "react";
import { Job, JobStatus } from "@/lib/types";
import { JobCard } from "./JobCard";

interface RadarFeedProps {
  jobs: Job[];
  selectedJobId: string | null;
  onSelectJob: (id: string) => void;
  onAddJob: () => void;
  onDiscoverJobs: () => void;
}

const STATUS_TABS: { id: JobStatus; label: string }[] = [
  { id: "inbox", label: "Inbox" },
  { id: "reviewing", label: "Reviewing" },
  { id: "applied", label: "Applied" },
  { id: "archived", label: "Archived" }
];

export function RadarFeed({ jobs, selectedJobId, onSelectJob, onAddJob, onDiscoverJobs }: RadarFeedProps) {
  const [statusFilter, setStatusFilter] = useState<JobStatus>("inbox");

  const counts = useMemo(() => {
    const map: Record<JobStatus, number> = { inbox: 0, reviewing: 0, applied: 0, archived: 0 };
    jobs.forEach((j) => map[j.status]++);
    return map;
  }, [jobs]);

  const filtered = useMemo(
    () => jobs.filter((j) => j.status === statusFilter).sort((a, b) => b.score - a.score),
    [jobs, statusFilter]
  );

  const followUpDue = jobs.filter((j) => j.status === "applied").length;

  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <div className="flex items-center justify-between border-b border-base-line px-6 py-3">
        <div className="flex gap-5">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`text-sm pb-2 border-b-2 -mb-3 transition-colors flex items-center gap-1.5 ${
                statusFilter === tab.id
                  ? "border-b-ink-primary text-ink-primary"
                  : "border-b-transparent text-ink-secondary hover:text-ink-primary"
              }`}
            >
              {tab.label}
              <span className="text-[11px] font-mono text-ink-muted">{counts[tab.id]}</span>
            </button>
          ))}
        </div>
        <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish">sort: fit score</p>
      </div>

      <div className="px-6 pt-3 flex gap-2">
        <button
          onClick={onAddJob}
          className="text-[11px] font-mono uppercase tracking-wideish text-ink-secondary hover:text-ink-primary border border-base-line px-3 py-1.5 transition-colors"
        >
          + Add job
        </button>
        <button
          onClick={onDiscoverJobs}
          className="text-[11px] font-mono uppercase tracking-wideish text-ink-secondary hover:text-ink-primary border border-base-line px-3 py-1.5 transition-colors"
        >
          Discover jobs
        </button>
      </div>

      {followUpDue > 0 && (
        <div className="mx-6 mt-3 text-[12px] font-mono text-signal-warn border border-signal-warn/25 bg-signal-warnDim px-3 py-2">
          {followUpDue} application{followUpDue > 1 ? "s" : ""} past 7-day follow-up window
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {filtered.length === 0 ? (
          <div className="border border-dashed border-base-line py-16 text-center">
            <p className="text-sm text-ink-secondary">Nothing in {statusFilter} right now.</p>
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-base-line border-t border-b border-base-line">
            {filtered.map((job) => (
              <JobCard key={job.id} job={job} selected={job.id === selectedJobId} onSelect={onSelectJob} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
