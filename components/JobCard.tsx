"use client";

import { Job } from "@/lib/types";

interface JobCardProps {
  job: Job;
  selected: boolean;
  onSelect: (id: string) => void;
}

function tone(score: number) {
  if (score >= 80) return { text: "text-signal-go", bar: "bg-signal-go" };
  if (score >= 65) return { text: "text-signal-warn", bar: "bg-signal-warn" };
  return { text: "text-signal-stop", bar: "bg-signal-stop" };
}

function ScoreBar({ score }: { score: number }) {
  const t = tone(score);
  return (
    <div className="flex items-center gap-2 w-full">
      <span className={`font-mono text-lg font-medium tabular-nums ${t.text}`}>{score}</span>
      <div className="flex-1 h-[3px] bg-base-line">
        <div className={`h-full ${t.bar}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export function JobCard({ job, selected, onSelect }: JobCardProps) {
  const t = tone(job.score);
  return (
    <button
      onClick={() => onSelect(job.id)}
      className={`text-left w-full bg-base-card border-l-2 px-4 py-3.5 transition-colors ${
        selected ? "border-l-signal-go bg-[#1a1b1f]" : "border-l-transparent hover:border-l-ink-muted"
      }`}
    >
      <div className="flex justify-between items-baseline gap-3 mb-2">
        <p className="text-sm text-ink-primary truncate tracking-tightish">{job.title}</p>
        <span className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish shrink-0">
          {job.sourceLabel}
        </span>
      </div>
      <p className="text-xs text-ink-secondary mb-3">{job.company}</p>
      <ScoreBar score={job.score} />
      <p className={`text-[11px] font-mono mt-2.5 ${t.text}`}>{job.tag.toUpperCase()}</p>
    </button>
  );
}
