"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FeedItem, FeedSource, Job, JobFeed } from "@/lib/types";

interface FeedsModalProps {
  personaId: string;
  onClose: () => void;
  onImported: (job: Job) => void;
}

const SOURCES: { id: FeedSource; label: string; hint: string }[] = [
  { id: "greenhouse", label: "Greenhouse", hint: "slug from job-boards.greenhouse.io/<slug>" },
  { id: "lever", label: "Lever", hint: "slug from jobs.lever.co/<slug>" },
  { id: "ashby", label: "Ashby", hint: "slug from jobs.ashbyhq.com/<slug>" }
];

export function FeedsModal({ personaId, onClose, onImported }: FeedsModalProps) {
  const [feeds, setFeeds] = useState<JobFeed[]>([]);
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [source, setSource] = useState<FeedSource>("greenhouse");
  const [identifier, setIdentifier] = useState("");
  const [keywords, setKeywords] = useState("");
  const [adding, setAdding] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [feedList, itemList] = await Promise.all([
        api.listFeeds(personaId),
        api.listFeedItems(personaId, "new")
      ]);
      setFeeds(feedList);
      setItems(itemList);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load feeds.");
    } finally {
      setLoading(false);
    }
  }, [personaId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleAddFeed() {
    if (!identifier.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await api.createFeed({ personaId, source, identifier: identifier.trim(), keywords: keywords.trim() });
      setIdentifier("");
      setKeywords("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't add that feed.");
    } finally {
      setAdding(false);
    }
  }

  async function handleToggle(feed: JobFeed) {
    setBusyId(feed.id);
    try {
      await api.updateFeed(feed.id, { enabled: !feed.enabled });
      await refresh();
    } catch {
      /* leave as-is */
    } finally {
      setBusyId(null);
    }
  }

  async function handleDeleteFeed(feed: JobFeed) {
    if (!confirm(`Remove the ${feed.label} feed? Staged postings from it are also removed.`)) return;
    setBusyId(feed.id);
    try {
      await api.deleteFeed(feed.id);
      await refresh();
    } finally {
      setBusyId(null);
    }
  }

  async function handlePoll(feed: JobFeed) {
    setBusyId(feed.id);
    setError(null);
    try {
      await api.pollFeed(feed.id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Poll failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleImport(item: FeedItem) {
    setBusyId(item.id);
    setError(null);
    try {
      const job = await api.importFeedItem(item.id, personaId);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      onImported(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't import that posting.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDismiss(item: FeedItem) {
    setBusyId(item.id);
    try {
      await api.dismissFeedItem(item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-base-panel border border-base-line w-full max-w-xl p-5 max-h-[85vh] overflow-y-auto">
        <p className="text-sm text-ink-primary mb-1">Job feeds</p>
        <p className="text-xs text-ink-secondary mb-4">
          Subscribe to a company&apos;s Greenhouse, Lever, or Ashby board. New postings are pulled
          automatically on a timer and staged below — nothing is scored until you import it.
        </p>

        {error && <p className="text-xs text-signal-stop mb-3">{error}</p>}

        <div className="border border-base-line p-3 mb-4 flex flex-col gap-2">
          <div className="flex gap-2">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as FeedSource)}
              className="bg-base-card border border-base-line px-2 py-2 text-sm text-ink-primary"
            >
              {SOURCES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
            <input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddFeed()}
              placeholder="company slug or board URL"
              className="flex-1 bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
            />
          </div>
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddFeed()}
            placeholder="title filter, comma-separated (optional) — e.g. backend, intern"
            className="bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
          />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-ink-muted">{SOURCES.find((s) => s.id === source)?.hint}</span>
            <button
              onClick={handleAddFeed}
              disabled={adding || !identifier.trim()}
              className="text-sm bg-ink-primary text-base-bg px-4 py-1.5 disabled:opacity-50"
            >
              {adding ? "Adding..." : "Add feed"}
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-xs text-ink-muted">Loading...</p>
        ) : (
          <>
            <div className="flex flex-col gap-2 mb-5">
              {feeds.length === 0 && <p className="text-xs text-ink-muted">No feeds yet.</p>}
              {feeds.map((feed) => (
                <div key={feed.id} className="border border-base-line px-3 py-2 flex flex-col gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-ink-primary truncate">{feed.label}</span>
                    <div className="flex gap-2 shrink-0 text-[11px] font-mono">
                      <button
                        onClick={() => handlePoll(feed)}
                        disabled={busyId === feed.id}
                        className="border border-base-line px-2 py-0.5 text-ink-primary hover:border-ink-secondary disabled:opacity-50"
                      >
                        POLL
                      </button>
                      <button
                        onClick={() => handleToggle(feed)}
                        disabled={busyId === feed.id}
                        className="border border-base-line px-2 py-0.5 text-ink-primary hover:border-ink-secondary disabled:opacity-50"
                      >
                        {feed.enabled ? "ON" : "OFF"}
                      </button>
                      <button
                        onClick={() => handleDeleteFeed(feed)}
                        disabled={busyId === feed.id}
                        className="border border-base-line px-2 py-0.5 text-signal-stop hover:border-signal-stop disabled:opacity-50"
                      >
                        DEL
                      </button>
                    </div>
                  </div>
                  <span className="text-[11px] text-ink-muted font-mono truncate">
                    {feed.keywords ? `filter: ${feed.keywords} · ` : ""}
                    {feed.lastStatus || "not polled yet"}
                  </span>
                </div>
              ))}
            </div>

            <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish mb-2">
              Staged postings ({items.length})
            </p>
            <div className="flex flex-col gap-2">
              {items.length === 0 && (
                <p className="text-xs text-ink-muted">Nothing staged. Poll a feed or wait for the next cycle.</p>
              )}
              {items.map((item) => (
                <div key={item.id} className="border border-base-line px-3 py-2.5 flex flex-col gap-1.5">
                  <p className="text-sm text-ink-primary leading-snug">{item.title}</p>
                  <p className="text-[11px] text-ink-muted">
                    {item.company} · <span className="font-mono">{item.sourceLabel}</span>
                  </p>
                  <div className="flex items-center justify-between mt-1">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[11px] text-ink-muted font-mono truncate max-w-[55%] hover:text-ink-secondary"
                    >
                      {item.url}
                    </a>
                    <div className="flex gap-2 text-[11px] font-mono">
                      <button
                        onClick={() => handleImport(item)}
                        disabled={busyId === item.id}
                        className="border border-base-line px-2.5 py-1 text-ink-primary hover:border-ink-secondary disabled:opacity-50"
                      >
                        {busyId === item.id ? "..." : "IMPORT"}
                      </button>
                      <button
                        onClick={() => handleDismiss(item)}
                        disabled={busyId === item.id}
                        className="border border-base-line px-2.5 py-1 text-ink-secondary hover:border-ink-secondary disabled:opacity-50"
                      >
                        DISMISS
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="flex mt-5">
          <button onClick={onClose} className="text-sm text-ink-secondary px-3 ml-auto">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
