"use client";

import { OllamaStatus, Persona, WorkMode } from "@/lib/types";

interface PersonaVaultProps {
  personas: Persona[];
  activePersonaId: string;
  onSelectPersona: (id: string) => void;
  onAddPersona: () => void;
  onDeletePersona: (id: string) => void;
  salaryFloor: number;
  onSalaryFloorChange: (value: number) => void;
  workModes: WorkMode[];
  onToggleWorkMode: (mode: WorkMode) => void;
  ollamaStatus: OllamaStatus;
  onToggleOllama: () => void;
}

const WORK_MODE_LABELS: Record<WorkMode, string> = {
  remote: "REMOTE",
  hybrid: "HYBRID",
  onsite: "ONSITE"
};

export function PersonaVault({
  personas,
  activePersonaId,
  onSelectPersona,
  onAddPersona,
  onDeletePersona,
  salaryFloor,
  onSalaryFloorChange,
  workModes,
  onToggleWorkMode,
  ollamaStatus,
  onToggleOllama
}: PersonaVaultProps) {
  return (
    <aside className="w-full lg:w-64 shrink-0 border-b lg:border-b-0 lg:border-r border-base-line bg-base-panel flex flex-col">
      <div className="px-5 py-4 border-b border-base-line">
        <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish mb-2">Active persona</p>
        <div className="flex flex-col gap-0.5">
          {personas.map((persona) => (
            <div key={persona.id} className="group flex items-center -mx-2">
              <button
                onClick={() => onSelectPersona(persona.id)}
                className={`flex-1 text-left text-sm px-2 py-1.5 transition-colors truncate ${
                  activePersonaId === persona.id
                    ? "text-ink-primary bg-base-card"
                    : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                {persona.name}
              </button>
              <button
                onClick={() => onDeletePersona(persona.id)}
                className="hidden group-hover:block text-ink-muted hover:text-signal-stop text-xs font-mono px-2"
                aria-label={`Delete ${persona.name}`}
                title="Delete persona"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={onAddPersona}
          className="text-[11px] font-mono uppercase tracking-wideish text-ink-muted hover:text-ink-primary mt-3"
        >
          + Add persona
        </button>
      </div>

      <div className="px-5 py-4 border-b border-base-line">
        <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish mb-3">Guardrails</p>

        <div className="mb-4">
          <div className="flex justify-between items-baseline mb-2">
            <span className="text-xs text-ink-secondary">Salary floor</span>
            <span className="text-sm font-mono text-ink-primary tabular-nums">${salaryFloor}k</span>
          </div>
          <input
            type="range"
            min={80}
            max={280}
            step={5}
            value={salaryFloor}
            onChange={(e) => onSalaryFloorChange(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div className="flex gap-1">
          {(Object.keys(WORK_MODE_LABELS) as WorkMode[]).map((mode) => {
            const active = workModes.includes(mode);
            return (
              <button
                key={mode}
                onClick={() => onToggleWorkMode(mode)}
                className={`flex-1 text-[11px] font-mono py-1.5 border transition-colors ${
                  active
                    ? "border-ink-primary text-ink-primary"
                    : "border-base-line text-ink-muted hover:text-ink-secondary"
                }`}
              >
                {WORK_MODE_LABELS[mode]}
              </button>
            );
          })}
        </div>
      </div>

      <div className="px-5 py-4 mt-auto">
        <p className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish mb-3">Ollama</p>
        <button onClick={onToggleOllama} className="w-full text-left group">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-ink-primary">
              {ollamaStatus.mode === "local" ? "Local engine" : "Cloud"}
            </span>
            <span
              className={`w-1.5 h-1.5 ${ollamaStatus.connected ? "bg-signal-go" : "bg-signal-stop"}`}
            />
          </div>
          <p className="text-[11px] font-mono text-ink-muted group-hover:text-ink-secondary transition-colors">
            {ollamaStatus.model}
          </p>
        </button>
      </div>
    </aside>
  );
}
