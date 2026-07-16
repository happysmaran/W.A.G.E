"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Job } from "@/lib/types";

interface AddJobModalProps {
  personaId: string;
  onClose: () => void;
  onCreated: (job: Job) => void;
}

export function AddJobModal({ personaId, onClose, onCreated }: AddJobModalProps) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!description.trim()) {
      setError("Paste the job posting text.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const job = await api.createJob({
        personaId,
        title: title || undefined,
        company: company || undefined,
        jobDescription: description
      });
      onCreated(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't process that posting.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-base-panel border border-base-line w-full max-w-md p-5">
        <p className="text-sm text-ink-primary mb-1">Add a job</p>
        <p className="text-xs text-ink-secondary mb-4">
          Paste the posting as-is — nav menus, cookie banners, whatever came along with the
          copy. Title and company get pulled out automatically if you leave them blank.
        </p>

        <div className="flex gap-3 mb-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title (optional)"
            className="flex-1 bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
          />
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Company (optional)"
            className="flex-1 bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary focus:outline-none focus:border-ink-secondary"
          />
        </div>

        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={10}
          placeholder="Paste the full job posting here"
          className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary resize-none mb-4 focus:outline-none focus:border-ink-secondary"
        />

        {error && <p className="text-xs text-signal-stop mb-3">{error}</p>}

        <div className="flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 text-sm bg-ink-primary text-base-bg py-2 disabled:opacity-50"
          >
            {submitting ? "Cleaning and scoring..." : "Add job"}
          </button>
          <button onClick={onClose} className="text-sm text-ink-secondary px-3">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
