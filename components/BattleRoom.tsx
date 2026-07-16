"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { BattleRoomTab, Job, JobStatus } from "@/lib/types";

interface BattleRoomProps {
  job: Job | null;
  onClose: () => void;
  onDeleted: (jobId: string) => void;
  onStatusChanged: (job: Job) => void;
}

const STATUS_OPTIONS: { id: JobStatus; label: string }[] = [
  { id: "inbox", label: "Inbox" },
  { id: "reviewing", label: "Reviewing" },
  { id: "applied", label: "Applied" },
  { id: "archived", label: "Archived" }
];

export function BattleRoom({ job, onClose, onDeleted, onStatusChanged }: BattleRoomProps) {
  const [tab, setTab] = useState<BattleRoomTab>("tailoring");
  const [bulletBefore, setBulletBefore] = useState(job?.bulletBefore ?? "");
  const [bulletAfter, setBulletAfter] = useState(job?.bulletAfter ?? "");
  const [draft, setDraft] = useState(job?.outreachDraft ?? "");
  const [copied, setCopied] = useState(false);
  const [tailoring, setTailoring] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [tailorError, setTailorError] = useState<string | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);

  if (!job) return null;

  async function handleGenerateTailoring() {
    setTailoring(true);
    setTailorError(null);
    try {
      const result = await api.tailorJob(job!.personaId, job!.id);
      setBulletBefore(result.bullet_before);
      setBulletAfter(result.bullet_after);
    } catch (err) {
      setTailorError(err instanceof Error ? err.message : "Couldn't generate a suggestion.");
    } finally {
      setTailoring(false);
    }
  }

  async function handleGenerateOutreach() {
    setDrafting(true);
    setDraftError(null);
    try {
      const result = await api.generateOutreach(job!.personaId, job!.id);
      setDraft(result.message);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : "Couldn't generate a draft.");
    } finally {
      setDrafting(false);
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(draft);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // clipboard permissions denied; user can select and copy manually
    }
  }

  async function handleStatusChange(status: JobStatus) {
    try {
      const updated = await api.updateJobStatus(job!.id, status);
      onStatusChanged(updated);
    } catch {
      // leave UI state as-is; the person can retry
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete "${job!.title}" at ${job!.company}? This can't be undone.`)) return;
    setDeleting(true);
    try {
      await api.deleteJob(job!.id);
      onDeleted(job!.id);
    } catch {
      setDeleting(false);
    }
  }

  return (
    <aside className="w-full lg:w-[420px] shrink-0 border-t lg:border-t-0 lg:border-l border-base-line bg-base-panel flex flex-col">
      <div className="flex items-start justify-between px-5 py-4 border-b border-base-line">
        <div>
          <p className="text-sm text-ink-primary tracking-tightish">{job.title}</p>
          <p className="text-xs text-ink-secondary mt-0.5">
            {job.company} <span className="text-ink-muted mx-1">/</span> match {job.score}
          </p>
        </div>
        <button onClick={onClose} className="text-ink-muted hover:text-ink-primary text-xs font-mono" aria-label="Close">
          CLOSE
        </button>
      </div>

      <div className="flex items-center gap-2 px-5 py-3 border-b border-base-line">
        <select
          value={job.status}
          onChange={(e) => handleStatusChange(e.target.value as JobStatus)}
          className="flex-1 bg-base-card border border-base-line px-2 py-1.5 text-xs text-ink-primary"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-[11px] font-mono uppercase tracking-wideish text-signal-stop border border-signal-stop/30 px-3 py-1.5 hover:bg-signal-stopDim transition-colors disabled:opacity-50"
        >
          {deleting ? "..." : "Delete"}
        </button>
      </div>

      <div className="flex border-b border-base-line">
        <button
          onClick={() => setTab("tailoring")}
          className={`flex-1 text-[11px] font-mono uppercase tracking-wideish py-2.5 border-b-2 -mb-px transition-colors ${
            tab === "tailoring" ? "border-b-ink-primary text-ink-primary" : "border-b-transparent text-ink-muted"
          }`}
        >
          Tailoring
        </button>
        <button
          onClick={() => setTab("outreach")}
          className={`flex-1 text-[11px] font-mono uppercase tracking-wideish py-2.5 border-b-2 -mb-px transition-colors ${
            tab === "outreach" ? "border-b-ink-primary text-ink-primary" : "border-b-transparent text-ink-muted"
          }`}
        >
          Outreach
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        {tab === "tailoring" ? (
          <div className="flex flex-col gap-6">
            <div>
              <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish mb-3">Why this score</p>
              <div className="flex flex-col">
                {job.matches.map((m) => (
                  <div key={m.id} className="flex items-start gap-2.5 py-1.5 border-b border-base-line">
                    <span className="text-signal-go text-xs font-mono mt-0.5 shrink-0">MATCH</span>
                    <span className="text-sm text-ink-secondary">{m.label}</span>
                  </div>
                ))}
                {job.gaps.map((g) => (
                  <div key={g.id} className="flex items-start gap-2.5 py-1.5 border-b border-base-line">
                    <span
                      className={`text-xs font-mono mt-0.5 shrink-0 ${
                        g.severity === "blocker" ? "text-signal-stop" : "text-signal-warn"
                      }`}
                    >
                      GAP
                    </span>
                    <span className="text-sm text-ink-secondary">{g.label}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish">Resume bullet</p>
                <button
                  onClick={handleGenerateTailoring}
                  disabled={tailoring}
                  className="text-[11px] font-mono uppercase tracking-wideish text-ink-secondary hover:text-ink-primary border border-base-line px-2.5 py-1 transition-colors disabled:opacity-50"
                >
                  {tailoring ? "Generating..." : bulletAfter ? "Regenerate" : "Generate"}
                </button>
              </div>
              {tailorError && <p className="text-xs text-signal-stop mb-3">{tailorError}</p>}
              {bulletBefore || bulletAfter ? (
                <>
                  <div className="border-l-2 border-base-line pl-3 py-1 mb-3">
                    <p className="text-[11px] font-mono text-ink-muted mb-1">CURRENT (from your resume)</p>
                    <p className="text-sm text-ink-secondary">{bulletBefore}</p>
                  </div>
                  <div className="border-l-2 border-signal-go pl-3 py-1">
                    <p className="text-[11px] font-mono text-signal-go mb-1">SUGGESTED</p>
                    <p className="text-sm text-ink-primary">{bulletAfter}</p>
                  </div>
                </>
              ) : (
                <p className="text-xs text-ink-muted">
                  Nothing generated yet — click Generate to pull your closest-matching resume bullet
                  and see a version tailored to this posting.
                </p>
              )}
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish">
                Draft — review before sending
              </p>
              <button
                onClick={handleGenerateOutreach}
                disabled={drafting}
                className="text-[11px] font-mono uppercase tracking-wideish text-ink-secondary hover:text-ink-primary border border-base-line px-2.5 py-1 transition-colors disabled:opacity-50"
              >
                {drafting ? "Generating..." : draft ? "Regenerate" : "Generate"}
              </button>
            </div>
            {draftError && <p className="text-xs text-signal-stop mb-3">{draftError}</p>}
            {draft ? (
              <>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={9}
                  className="w-full bg-base-card border border-base-line px-3 py-2.5 text-sm text-ink-primary leading-relaxed resize-none focus:outline-none focus:border-ink-secondary"
                />
                <div className="flex items-center gap-4 mt-3">
                  <button
                    onClick={handleCopy}
                    className="text-[11px] font-mono uppercase tracking-wideish text-ink-secondary hover:text-ink-primary border border-base-line px-3 py-2 transition-colors"
                  >
                    Copy
                  </button>
                  <a
                    href={`mailto:?body=${encodeURIComponent(draft)}`}
                    className="text-[11px] font-mono uppercase tracking-wideish text-ink-secondary hover:text-ink-primary border border-base-line px-3 py-2 transition-colors"
                  >
                    Open in email
                  </a>
                  {copied && <span className="text-[11px] font-mono text-signal-go">copied</span>}
                </div>
              </>
            ) : (
              <p className="text-xs text-ink-muted">
                Nothing generated yet — click Generate for a first-draft outreach message you can
                edit before sending.
              </p>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
