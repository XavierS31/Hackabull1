export default function AgentToggles({ agents }) {
  const entries = Object.entries(agents || {});

  if (entries.length === 0) {
    return <p className="text-sm text-slate-400">No agents loaded yet.</p>;
  }

  return (
    <div className="space-y-1.5">
      {entries.map(([name, enabled]) => (
        <div
          key={name}
          className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/50 px-3 py-2"
        >
          <span className="text-sm text-slate-200">{name}</span>

          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-medium ${
                enabled ? "text-green-400" : "text-red-400"
              }`}
            >
              {enabled ? "Online" : "Offline"}
            </span>
            <span className="relative flex h-2.5 w-2.5">
              {enabled && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-50" />
              )}
              <span
                className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                  enabled ? "bg-green-400" : "bg-red-500"
                }`}
              />
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
