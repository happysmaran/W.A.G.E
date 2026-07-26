"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { BackendSettings } from "@/lib/types";

interface SettingsModalProps {
  onClose: () => void;
  onSaved: () => void;
}

export function SettingsModal({ onClose, onSaved }: SettingsModalProps) {
  const [settings, setSettings] = useState<BackendSettings | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [embeddingModel, setEmbeddingModel] = useState("");
  const [numCtx, setNumCtx] = useState(2048);
  const [mockLlm, setMockLlm] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setSettings(s);
        setBaseUrl(s.base_url);
        setModel(s.model);
        setEmbeddingModel(s.embedding_model);
        setNumCtx(s.num_ctx);
        setMockLlm(s.mock_llm);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Couldn't load settings."))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const payload: Partial<Omit<BackendSettings, "mode">> = {
        base_url: baseUrl,
        model,
        embedding_model: embeddingModel,
        num_ctx: numCtx,
        mock_llm: mockLlm
      };
      if (apiKey && !apiKey.startsWith("•")) {
        payload.api_key = apiKey;
      }
      await api.updateSettings(payload);
      setSaved(true);
      onSaved();
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-base-panel border border-base-line w-full max-w-md p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-ink-primary">Settings</p>
          <button onClick={onClose} className="text-ink-muted hover:text-ink-primary text-xs font-mono">
            CLOSE
          </button>
        </div>

        {loading ? (
          <p className="text-xs font-mono text-ink-muted">loading...</p>
        ) : (
          <>
            <div className="mb-3">
              <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
                Ollama base URL
              </label>
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="http://localhost:11434"
                className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary font-mono focus:outline-none focus:border-ink-secondary"
              />
            </div>

            <div className="mb-3">
              <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
                API key (Ollama Cloud only)
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={settings?.api_key ? "set — type to replace" : "not set"}
                className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary font-mono focus:outline-none focus:border-ink-secondary"
              />
            </div>

            <div className="flex gap-3 mb-3">
              <div className="flex-1">
                <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
                  Chat model
                </label>
                <input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary font-mono focus:outline-none focus:border-ink-secondary"
                />
              </div>
              <div className="flex-1">
                <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish block mb-1">
                  Embedding model
                </label>
                <input
                  value={embeddingModel}
                  onChange={(e) => setEmbeddingModel(e.target.value)}
                  className="w-full bg-base-card border border-base-line px-2.5 py-2 text-sm text-ink-primary font-mono focus:outline-none focus:border-ink-secondary"
                />
              </div>
            </div>

            <div className="mb-4">
              <div className="flex justify-between items-baseline mb-1">
                <label className="text-[11px] font-mono text-ink-muted uppercase tracking-wideish">
                  Context window
                </label>
                <span className="text-xs font-mono text-ink-primary">{numCtx}</span>
              </div>
              <input
                type="range"
                min={512}
                max={8192}
                step={256}
                value={numCtx}
                onChange={(e) => setNumCtx(Number(e.target.value))}
                className="w-full"
              />
              <p className="text-[11px] text-ink-muted mt-1">
                Lower reduces GPU memory pressure; raise it if descriptions are getting truncated.
              </p>
            </div>

            <button
              onClick={() => setMockLlm((m) => !m)}
              className="w-full flex items-center justify-between border border-base-line px-3 py-2 mb-4"
            >
              <span className="text-xs text-ink-secondary">Mock mode (no real Ollama calls)</span>
              <span className={`text-[11px] font-mono uppercase ${mockLlm ? "text-signal-go" : "text-ink-muted"}`}>
                {mockLlm ? "ON" : "OFF"}
              </span>
            </button>

            {error && <p className="text-xs text-signal-stop mb-3">{error}</p>}

            <div className="flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 text-sm bg-ink-primary text-base-bg py-2 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save"}
              </button>
              {saved && <span className="text-[11px] font-mono text-signal-go">saved</span>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
