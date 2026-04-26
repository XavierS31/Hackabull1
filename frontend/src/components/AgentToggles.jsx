export default function AgentToggles({ agents }) {
  const entries = Object.entries(agents || {});

  if (entries.length === 0) {
    return <p className="text-xs text-muted">No agents loaded yet.</p>;
  }

  return (
    <ul className="space-y-1.5">
      {entries.map(([name, enabled]) => (
        <li
          key={name}
          className={`flex items-center justify-between rounded-md border px-2.5 py-1.5 transition-colors ${
            enabled
              ? "border-accent/30 bg-accent/5"
              : "border-border bg-surface/40"
          }`}
        >
          <span className="truncate text-[12px] text-ink">{name}</span>
          <span className="flex items-center gap-2">
            <span
              className={`text-[10px] font-semibold uppercase tracking-wider ${
                enabled ? "text-good" : "text-muted"
              }`}
            >
              {enabled ? "Online" : "Off"}
            </span>
            <span className="relative flex h-2 w-2">
              {enabled && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-good opacity-50" />
              )}
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  enabled ? "bg-good" : "bg-border"
                }`}
              />
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}
