import { useState } from "react";

export default function AgentToggles({ agents, onUpdate }) {
  const [loading, setLoading] = useState("");
  const entries = Object.entries(agents || {});

  if (entries.length === 0) {
    return <p className="text-sm text-slate-400">No agents loaded yet.</p>;
  }

  const updateAgent = async (name, enabled) => {
    setLoading(name);
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(name)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        onUpdate((prev) => ({ ...prev, [name]: enabled }));
      }
    } finally {
      setLoading("");
    }
  };

  return (
    <div className="space-y-2">
      {entries.map(([name, enabled]) => (
        <label
          key={name}
          className="flex cursor-pointer items-center justify-between rounded border border-slate-800 px-3 py-2 text-sm"
        >
          <span className="text-slate-200">{name}</span>
          <button
            type="button"
            disabled={loading === name}
            onClick={() => updateAgent(name, !enabled)}
            className={`h-6 w-12 rounded-full transition ${
              enabled ? "bg-accent" : "bg-slate-700"
            } ${loading === name ? "opacity-60" : ""}`}
            aria-label={`Toggle ${name}`}
          >
            <span
              className={`block h-6 w-6 rounded-full border border-slate-900 bg-white transition ${
                enabled ? "translate-x-6" : "translate-x-0"
              }`}
            />
          </button>
        </label>
      ))}
    </div>
  );
}
