"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Check, ArrowRight, ExternalLink, Key, Zap, Brain, Shield } from "lucide-react";

type Step = "welcome" | "api_key" | "model" | "done";

const MODELS = [
  {
    id: "gpt-oss:20b-cloud",
    name: "Standard",
    badge: "Recommended",
    speed: "Fast",
    quality: "Great",
    desc: "Perfect balance of speed and reasoning. Great for standard job hunting."
  },
  {
    id: "gpt-oss:120b-cloud",
    name: "Pro",
    badge: "",
    speed: "Slower",
    quality: "Excellent",
    desc: "Heavier model with deep reasoning. Worth the wait for important applications."
  },
  {
    id: "glm-4.6:cloud",
    name: "Fast",
    badge: "",
    speed: "Very Fast",
    quality: "Good",
    desc: "Lightweight and snappy. Good for rapid triage."
  }
];

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("welcome");
  
  const [apiKey, setApiKey] = useState("");
  const [selectedModel, setSelectedModel] = useState("gpt-oss:20b-cloud");
  
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleVerifyKey = async () => {
    if (!apiKey.trim()) {
      setError("Please paste your API key.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await api.updateSettings({
        api_key: apiKey.trim(),
        base_url: "https://ollama.com",
      });
      setStep("model");
    } catch (e: any) {
      setError(e.message || "Failed to save API key.");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveModel = async () => {
    setSaving(true);
    try {
      await api.updateSettings({
        model: selectedModel,
        mock_llm: false
      });
      setStep("done");
    } catch (e: any) {
      setError(e.message || "Failed to save model choice.");
    } finally {
      setSaving(false);
    }
  };

  const handleFinish = () => {
    router.replace("/");
  };

  return (
    <div className="min-h-screen bg-base-bg flex items-center justify-center p-6 text-ink-primary font-sans antialiased">
      <div className="w-full max-w-xl">
        
        {step === "welcome" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-4xl tracking-tight mb-4">W.A.G.E.</h1>
            <p className="text-xl text-ink-secondary mb-8">
              Your personal, highly-capable, pre-application strategy engine.
            </p>
            <p className="text-sm text-ink-muted leading-relaxed mb-10">
              Before you can start analyzing jobs and tailoring your resume, we need to connect W.A.G.E. to an AI engine. 
              This takes about 2 minutes and is completely free.
            </p>
            <button
              onClick={() => setStep("api_key")}
              className="group flex items-center gap-2 bg-ink-primary text-base-bg px-6 py-3 text-sm font-mono uppercase tracking-wideish hover:bg-ink-secondary transition-colors"
            >
              Get Started
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </button>
          </div>
        )}

        {step === "api_key" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-full border border-base-line flex items-center justify-center text-xs font-mono">1</div>
              <h2 className="text-2xl tracking-tight">Connect to Ollama Cloud</h2>
            </div>
            
            <p className="text-sm text-ink-secondary leading-relaxed mb-8">
              W.A.G.E. uses Ollama Cloud to read job descriptions and write outreach drafts. You need a free API key.
            </p>

            <div className="bg-base-panel border border-base-line p-5 mb-8">
              <h3 className="text-sm font-mono uppercase tracking-wideish mb-3 text-ink-muted">Instructions</h3>
              <ol className="list-decimal list-inside text-sm text-ink-secondary space-y-3">
                <li>Create a free account on Ollama.</li>
                <li>Go to your account settings.</li>
                <li>Click <strong>Generate New API Key</strong>.</li>
                <li>Copy the key and paste it below.</li>
              </ol>
              <a 
                href="https://ollama.com" 
                target="_blank" 
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 mt-5 text-sm text-ink-primary hover:underline"
              >
                Open Ollama.com <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            <div className="mb-6">
              <label className="block text-[11px] font-mono text-ink-muted uppercase tracking-wideish mb-2">
                Your API Key
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Paste your key here..."
                  className="w-full bg-base-bg border border-base-line pl-10 pr-4 py-3 text-sm focus:outline-none focus:border-ink-primary transition-colors placeholder:text-ink-muted/50"
                  onKeyDown={(e) => e.key === "Enter" && handleVerifyKey()}
                />
              </div>
              {error && <p className="text-signal-stop text-xs mt-2">{error}</p>}
            </div>

            <div className="flex justify-between items-center">
              <button 
                onClick={() => setStep("welcome")}
                className="text-sm text-ink-muted hover:text-ink-primary transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleVerifyKey}
                disabled={saving || !apiKey.trim()}
                className="bg-ink-primary text-base-bg px-6 py-2.5 text-sm font-mono uppercase tracking-wideish hover:bg-ink-secondary transition-colors disabled:opacity-50"
              >
                {saving ? "Verifying..." : "Verify & Continue"}
              </button>
            </div>
          </div>
        )}

        {step === "model" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-full border border-base-line flex items-center justify-center text-xs font-mono">2</div>
              <h2 className="text-2xl tracking-tight">Choose your AI Model</h2>
            </div>
            
            <p className="text-sm text-ink-secondary leading-relaxed mb-8">
              Select the intelligence engine powering your analysis. You can change this later in settings.
            </p>

            <div className="grid gap-4 mb-8">
              {MODELS.map(m => (
                <button
                  key={m.id}
                  onClick={() => setSelectedModel(m.id)}
                  className={`text-left border p-5 transition-all relative ${
                    selectedModel === m.id 
                      ? "border-ink-primary bg-base-panel/50 ring-1 ring-ink-primary" 
                      : "border-base-line hover:border-ink-muted"
                  }`}
                >
                  {m.badge && (
                    <span className="absolute top-4 right-4 text-[10px] font-mono bg-ink-primary text-base-bg px-2 py-0.5 uppercase tracking-wider">
                      {m.badge}
                    </span>
                  )}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-lg">{m.name}</span>
                    <span className="text-xs text-ink-muted font-mono">{m.id}</span>
                  </div>
                  <p className="text-sm text-ink-secondary mb-4 pr-16">{m.desc}</p>
                  <div className="flex items-center gap-4 text-xs font-mono text-ink-muted">
                    <div className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> {m.speed}</div>
                    <div className="flex items-center gap-1.5"><Brain className="w-3.5 h-3.5" /> {m.quality}</div>
                  </div>
                </button>
              ))}
            </div>

            {error && <p className="text-signal-stop text-xs mb-4">{error}</p>}

            <div className="flex justify-between items-center">
              <button 
                onClick={() => setStep("api_key")}
                className="text-sm text-ink-muted hover:text-ink-primary transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleSaveModel}
                disabled={saving}
                className="bg-ink-primary text-base-bg px-6 py-2.5 text-sm font-mono uppercase tracking-wideish hover:bg-ink-secondary transition-colors disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save & Continue"}
              </button>
            </div>
          </div>
        )}

        {step === "done" && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 text-center">
            <div className="w-16 h-16 rounded-full border-2 border-signal-go text-signal-go flex items-center justify-center mx-auto mb-6">
              <Check className="w-8 h-8" />
            </div>
            <h2 className="text-3xl tracking-tight mb-4">You're all set!</h2>
            <p className="text-ink-secondary mb-10 max-w-md mx-auto">
              W.A.G.E. is connected and ready. Your first step will be to create a Persona by uploading your resume.
            </p>
            <button
              onClick={handleFinish}
              className="bg-ink-primary text-base-bg px-8 py-3 text-sm font-mono uppercase tracking-wideish hover:bg-ink-secondary transition-colors inline-flex items-center gap-2"
            >
              Enter W.A.G.E.
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
