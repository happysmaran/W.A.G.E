"use client";

import { useCallback, useEffect, useState } from "react";
import { PersonaVault } from "@/components/PersonaVault";
import { RadarFeed } from "@/components/RadarFeed";
import { BattleRoom } from "@/components/BattleRoom";
import { UploadPersonaModal } from "@/components/UploadPersonaModal";
import { AddJobModal } from "@/components/AddJobModal";
import { DiscoverJobsModal } from "@/components/DiscoverJobsModal";
import { TopBar } from "@/components/TopBar";
import { SettingsModal } from "@/components/SettingsModal";
import { api } from "@/lib/api";
import { EmbeddingStatus, Job, OllamaStatus, Persona, WorkMode } from "@/lib/types";

export default function DashboardPage() {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activePersonaId, setActivePersonaId] = useState<string>("");
  const [salaryFloor, setSalaryFloor] = useState(0);
  const [workModes, setWorkModes] = useState<WorkMode[]>([]);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus>({
    mode: "local",
    model: "connecting...",
    connected: false
  });
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus>({
    status: "not_started",
    error: null
  });
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUploadPersona, setShowUploadPersona] = useState(false);
  const [showAddJob, setShowAddJob] = useState(false);
  const [showDiscoverJobs, setShowDiscoverJobs] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialData() {
      try {
        const [personaList, status] = await Promise.all([api.listPersonas(), api.getOllamaStatus()]);
        if (cancelled) return;

        setPersonas(personaList);
        setOllamaStatus(status);

        if (personaList.length > 0) {
          const firstId = personaList[0].id;
          setActivePersonaId(firstId);
          setSalaryFloor(personaList[0].salaryFloor);
          setWorkModes(personaList[0].workModes);
          const jobList = await api.listJobs(firstId);
          if (!cancelled) setJobs(jobList);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? `Couldn't reach the API: ${err.message}` : "Couldn't reach the API."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadInitialData();
    return () => {
      cancelled = true;
    };
  }, []);

  // Poll the bundled local embedding model's first-run download/load status
  // until it settles, so the UI can show "preparing matching model..."
  // instead of the first resume upload just silently hanging.
  useEffect(() => {
    if (embeddingStatus.status === "ready" || embeddingStatus.status === "error") return;
    let cancelled = false;
    const id = setInterval(async () => {
      try {
        const status = await api.getEmbeddingStatus();
        if (!cancelled) setEmbeddingStatus(status);
      } catch {
        // keep polling silently; the API may just not be up yet
      }
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [embeddingStatus.status]);

  const refetchJobs = useCallback(async (personaId: string) => {
    try {
      const jobList = await api.listJobs(personaId);
      setJobs(jobList);
    } catch {
      // keep whatever's currently shown rather than blanking the feed
    }
  }, []);

  async function handleSelectPersona(id: string) {
    setActivePersonaId(id);
    setSelectedJobId(null);
    const persona = personas.find((p) => p.id === id);
    if (persona) {
      setSalaryFloor(persona.salaryFloor);
      setWorkModes(persona.workModes);
    }
    await refetchJobs(id);
  }

  function handleToggleWorkMode(mode: WorkMode) {
    setWorkModes((prev) => (prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]));
  }

  // Toggles local <-> cloud, calling the real backend switch endpoint so
  // the change actually takes effect server-side.
  async function handleToggleOllama() {
    const nextMode = ollamaStatus.mode === "local" ? "cloud" : "local";
    const previous = ollamaStatus;
    setOllamaStatus((prev) => ({ ...prev, mode: nextMode, connected: false }));
    try {
      const updated = await api.switchOllamaMode(nextMode);
      setOllamaStatus(updated);
    } catch {
      setOllamaStatus(previous);
    }
  }

  async function handlePersonaCreated(persona: Persona) {
    setPersonas((prev) => [...prev, persona]);
    setActivePersonaId(persona.id);
    setSalaryFloor(persona.salaryFloor);
    setWorkModes(persona.workModes);
    setShowUploadPersona(false);
    await refetchJobs(persona.id);
  }

  async function handleDeletePersona(id: string) {
    const persona = personas.find((p) => p.id === id);
    if (!persona) return;
    if (!confirm(`Delete "${persona.name}"? This also deletes all jobs scored against it.`)) return;

    try {
      await api.deletePersona(id);
      const remaining = personas.filter((p) => p.id !== id);
      setPersonas(remaining);

      if (activePersonaId === id) {
        if (remaining.length > 0) {
          await handleSelectPersona(remaining[0].id);
        } else {
          setActivePersonaId("");
          setJobs([]);
          setSelectedJobId(null);
        }
      }
    } catch {
      // leave state as-is; the person can retry
    }
  }

  function handleJobCreated(job: Job) {
    setJobs((prev) => [...prev, job]);
    setShowAddJob(false);
    setSelectedJobId(job.id);
  }

  function handleJobImported(job: Job) {
    setJobs((prev) => [...prev, job]);
    setShowDiscoverJobs(false);
    setSelectedJobId(job.id);
  }

  function handleJobDeleted(jobId: string) {
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
    setSelectedJobId(null);
  }

  function handleJobStatusChanged(updatedJob: Job) {
    setJobs((prev) => prev.map((j) => (j.id === updatedJob.id ? updatedJob : j)));
  }

  const selectedJob = jobs.find((j) => j.id === selectedJobId) ?? null;
  const hasPersona = personas.length > 0 && activePersonaId !== "";

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-sm font-mono text-ink-muted uppercase tracking-wideish">
          connecting to api<span className="animate-pulse">_</span>
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <p className="text-[11px] font-mono text-signal-stop uppercase tracking-wideish mb-2">
            connection failed
          </p>
          <p className="text-sm text-ink-secondary mb-3">{error}</p>
          <p className="text-xs font-mono text-ink-muted">
            Make sure the backend is running (uvicorn app.main:app --port 8000) and
            NEXT_PUBLIC_API_BASE_URL matches its address.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex flex-col">
      <TopBar
        jobs={jobs}
        ollamaStatus={ollamaStatus}
        embeddingStatus={embeddingStatus}
        onOpenSettings={() => setShowSettings(true)}
      />
      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
      <PersonaVault
        personas={personas}
        activePersonaId={activePersonaId}
        onSelectPersona={handleSelectPersona}
        onAddPersona={() => setShowUploadPersona(true)}
        onDeletePersona={handleDeletePersona}
        salaryFloor={salaryFloor}
        onSalaryFloorChange={setSalaryFloor}
        workModes={workModes}
        onToggleWorkMode={handleToggleWorkMode}
        ollamaStatus={ollamaStatus}
        onToggleOllama={handleToggleOllama}
      />

      {hasPersona ? (
        <>
          <RadarFeed
            jobs={jobs}
            selectedJobId={selectedJobId}
            onSelectJob={setSelectedJobId}
            onAddJob={() => setShowAddJob(true)}
            onDiscoverJobs={() => setShowDiscoverJobs(true)}
          />
          {selectedJob && (
            <BattleRoom
              job={selectedJob}
              onClose={() => setSelectedJobId(null)}
              onDeleted={handleJobDeleted}
              onStatusChanged={handleJobStatusChanged}
            />
          )}
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center px-6">
          <div className="text-center max-w-sm">
            <p className="text-sm text-ink-primary mb-2">No persona yet</p>
            <p className="text-xs text-ink-secondary mb-4">
              Upload a resume in the sidebar to create your first persona before adding jobs.
            </p>
            <button
              onClick={() => setShowUploadPersona(true)}
              className="text-[11px] font-mono uppercase tracking-wideish text-ink-primary border border-base-line px-3 py-1.5"
            >
              + Add persona
            </button>
          </div>
        </div>
      )}
      </div>

      {showUploadPersona && (
        <UploadPersonaModal onClose={() => setShowUploadPersona(false)} onCreated={handlePersonaCreated} />
      )}
      {showAddJob && hasPersona && (
        <AddJobModal
          personaId={activePersonaId}
          onClose={() => setShowAddJob(false)}
          onCreated={handleJobCreated}
        />
      )}
      {showDiscoverJobs && hasPersona && (
        <DiscoverJobsModal
          personaId={activePersonaId}
          onClose={() => setShowDiscoverJobs(false)}
          onImported={handleJobImported}
        />
      )}
      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
          onSaved={async () => {
            try {
              setOllamaStatus(await api.getOllamaStatus());
            } catch {
              // leave whatever status was already showing
            }
          }}
        />
      )}
    </main>
  );
}
