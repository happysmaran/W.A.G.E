"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Persona, WorkMode } from "@/lib/types";

interface UploadPersonaModalProps {
  onClose: () => void;
  onCreated: (persona: Persona) => void;
}

export function UploadPersonaModal({ onClose, onCreated }: UploadPersonaModalProps) {
  const [name, setName] = useState("");
  const [salaryFloor, setSalaryFloor] = useState(150);
  const [workModes, setWorkModes] = useState<WorkMode[]>(["remote"]);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleMode(mode: WorkMode) {
    setWorkModes((prev) => (prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]));
  }

  async function handleSubmit() {
    if (!file || !name.trim()) {
      setError("Give it a name and choose a resume file (PDF or .txt).");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("salary_floor", String(salaryFloor));
      workModes.forEach((m) => formData.append("work_modes", m));
      formData.append("resume", file);

      const persona = await api.createPersona(formData);
      onCreated(persona);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-base-panel border border-base-line w-full max-w-sm p-5">
        <p className="text-sm text-ink-primary mb-4">New persona</p>

        <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
          Name
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Full-stack dev profile"
          className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary mb-4 focus:outline-none focus:border-ink-secondary"
        />

        <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
          Resume file (PDF or .txt)
        </label>
        <input
          type="file"
          accept=".pdf,.txt,.md"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full text-sm text-ink-secondary mb-4"
        />

        <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
          Salary floor
        </label>
        <div className="flex items-center gap-3 mb-4">
          <input
            type="range"
            min={80}
            max={280}
            step={5}
            value={salaryFloor}
            onChange={(e) => setSalaryFloor(Number(e.target.value))}
            className="flex-1"
          />
          <span className="text-sm font-mono text-ink-primary w-14 text-right">${salaryFloor}k</span>
        </div>

        <div className="flex gap-1 mb-5">
          {(["remote", "hybrid", "onsite"] as WorkMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => toggleMode(mode)}
              className={`flex-1 text-[11px] font-mono py-1.5 border transition-colors ${
                workModes.includes(mode)
                  ? "border-ink-primary text-ink-primary"
                  : "border-base-line text-ink-muted"
              }`}
            >
              {mode.toUpperCase()}
            </button>
          ))}
        </div>

        {error && <p className="text-xs text-signal-stop mb-3">{error}</p>}

        <div className="flex gap-3">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 text-sm bg-ink-primary text-base-bg py-2 disabled:opacity-50"
          >
            {submitting ? "Uploading..." : "Create persona"}
          </button>
          <button onClick={onClose} className="text-sm text-ink-secondary px-3">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
