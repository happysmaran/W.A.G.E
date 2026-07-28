"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { DiscoverResult, Job } from "@/lib/types";

interface DiscoverJobsModalProps {
  personaId: string;
  onClose: () => void;
  onImported: (job: Job) => void;
}

export function DiscoverJobsModal({ personaId, onClose, onImported }: DiscoverJobsModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DiscoverResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [importingUrl, setImportingUrl] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [importErrors, setImportErrors] = useState<Record<string, string>>({});
  const [searched, setSearched] = useState(false);

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setSearchError(null);
    setImportErrors({});
    try {
      const found = await api.discoverJobs(query.trim());
      setResults(found);
      setSearched(true);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  async function handleImport(result: DiscoverResult) {
    setImportingUrl(result.url);
    setImportErrors((prev) => {
      const next = { ...prev };
      delete next[result.url];
      return next;
    });
    let companyHint = "";
    const titleMatch = result.title.match(/ at (.+?)$/i);
    const snippetMatch = result.snippet.match(/ at (.+?)(?:\s+!|\s+\[|\.\.\.|$)/i);
    
    if (titleMatch && titleMatch[1]) {
      companyHint = titleMatch[1].trim();
    } else if (snippetMatch && snippetMatch[1]) {
      companyHint = snippetMatch[1].trim();
    }

    try {
      const job = await api.importDiscoveredJob({
        personaId,
        url: result.url,
        titleHint: result.title,
        companyHint
      });
      onImported(job);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Couldn't import that posting.";
      setImportErrors((prev) => ({ ...prev, [result.url]: message }));
    } finally {
      setImportingUrl(null);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-base-panel border border-base-line w-full max-w-lg p-5">
        <p className="text-sm text-ink-primary mb-1">Find job postings</p>
        <p className="text-xs text-ink-secondary mb-4">
          Searches the web via Ollama. Nothing gets added until you pick a result below.
        </p>

        <div className="flex gap-2 mb-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="e.g. backend intern remote"
            autoFocus
            className="flex-1 bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
          />
          <button
            onClick={handleSearch}
            disabled={searching || !query.trim()}
            className="text-sm bg-ink-primary text-base-bg px-4 py-2 disabled:opacity-50"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </div>

        {searchError && <p className="text-xs text-signal-stop mb-3">{searchError}</p>}

        <div className="max-h-80 overflow-y-auto flex flex-col gap-2">
          {searched && results.length === 0 && !searchError && (
            <p className="text-xs text-ink-muted">No results. Try a different query.</p>
          )}
          {results.map((result) => (
            <div key={result.url} className="border border-base-line px-3 py-2.5 flex flex-col gap-1.5">
              <p className="text-sm text-ink-primary leading-snug">{result.title}</p>
              <p className="text-[11px] text-ink-muted leading-snug line-clamp-2">{result.snippet}</p>
              <div className="flex items-center justify-between mt-1">
                <span className="text-[11px] text-ink-muted font-mono truncate max-w-[60%]">{result.url}</span>
                <button
                  onClick={() => handleImport(result)}
                  disabled={importingUrl !== null}
                  className="text-[11px] font-mono border border-base-line px-2.5 py-1 text-ink-primary hover:border-ink-secondary disabled:opacity-50"
                >
                  {importingUrl === result.url ? "IMPORTING..." : "IMPORT"}
                </button>
              </div>
              {importErrors[result.url] && (
                <p className="text-[11px] text-signal-stop leading-snug">
                  Couldn't import this one: {importErrors[result.url]}
                </p>
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-3 mt-4">
          <button onClick={onClose} className="text-sm text-ink-secondary px-3 ml-auto">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
