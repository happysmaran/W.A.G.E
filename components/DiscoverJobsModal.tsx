"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";

interface DiscoverJobsModalProps {
  personaId: string;
  onClose: () => void;
  onDiscovered: (jobs: Job[]) => void;
}

type Source = "greenhouse" | "lever" | "company-site";

export function DiscoverJobsModal({ personaId, onClose, onDiscovered }: DiscoverJobsModalProps) {
  const [source, setSource] = useState<Source>("greenhouse");
  const [identifier, setIdentifier] = useState("");
  const [fallbackTitle, setFallbackTitle] = useState("");
  const [fallbackCompany, setFallbackCompany] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultCount, setResultCount] = useState<number | null>(null);

  async function handleSubmit() {
    if (!identifier.trim()) {
      setError(source === "company-site" ? "Paste the careers page URL." : "Enter the company's board slug.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setResultCount(null);
    try {
      const jobs = await api.discoverJobs({
        personaId,
        source,
        identifier,
        fallbackTitle: fallbackTitle || undefined,
        fallbackCompany: fallbackCompany || undefined
      });
      setResultCount(jobs.length);
      onDiscovered(jobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-base-panel border border-base-line w-full max-w-md p-5">
        <p className="text-sm text-ink-primary mb-1">Discover jobs</p>
        <p className="text-xs text-ink-secondary mb-4">
          Pulls real postings from a live board and scores each one automatically.
        </p>

        <div className="flex gap-1 mb-4">
          {(["greenhouse", "lever", "company-site"] as Source[]).map((s) => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={`flex-1 text-[11px] font-mono uppercase tracking-wideish py-1.5 border transition-colors ${
                source === s ? "border-ink-primary text-ink-primary" : "border-base-line text-ink-muted"
              }`}
            >
              {s === "company-site" ? "Company site" : s}
            </button>
          ))}
        </div>

        <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
          {source === "company-site" ? "Careers page URL" : "Company board slug"}
        </label>
        <input
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          placeholder={
            source === "greenhouse"
              ? "e.g. stripe (from boards.greenhouse.io/stripe)"
              : source === "lever"
              ? "e.g. netflix (from jobs.lever.co/netflix)"
              : "https://company.com/careers/12345"
          }
          className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary mb-4 focus:outline-none focus:border-ink-secondary"
        />

        {source === "company-site" && (
          <>
            <p className="text-xs text-ink-secondary mb-3">
              Company pages don&apos;t expose structured data, so title/company extraction is
              best-effort. Fill these in if it can&apos;t figure it out automatically.
            </p>
            <div className="flex gap-3 mb-4">
              <input
                value={fallbackTitle}
                onChange={(e) => setFallbackTitle(e.target.value)}
                placeholder="Fallback title"
                className="flex-1 bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
              />
              <input
                value={fallbackCompany}
                onChange={(e) => setFallbackCompany(e.target.value)}
                placeholder="Fallback company"
                className="flex-1 bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
              />
            </div>
          </>
        )}

        {error && <p className="text-xs text-signal-stop mb-3">{error}</p>}
        {resultCount !== null && !error && (
          <p className="text-xs text-signal-go mb-3">
            Added {resultCount} new job{resultCount === 1 ? "" : "s"}
            {resultCount === 0 ? " (rest were already in your feed)" : ""}.
          </p>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 text-sm bg-ink-primary text-base-bg py-2 disabled:opacity-50"
          >
            {submitting ? "Fetching..." : "Discover"}
          </button>
          <button onClick={onClose} className="text-sm text-ink-secondary px-3">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
