import { ChevronDown, ChevronUp, ShieldAlert } from "lucide-react";
import { useState } from "react";

// Collapsible dropdown of fall/critical events. The list is internally
// scrollable, so it never grows the page height.
export default function EventsGallery({ events }) {
  const [open, setOpen] = useState(false);
  const count = events?.length || 0;

  return (
    <div className="rounded-md border border-border bg-panel">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left transition-colors hover:bg-surface/60"
      >
        <div className="flex items-center gap-2">
          <ShieldAlert size={15} className="text-accent" />
          <span className="text-sm font-semibold uppercase tracking-wider text-ink">
            Critical Events
          </span>
          <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] font-semibold text-muted">
            {count}
          </span>
        </div>
        {open ? (
          <ChevronUp size={16} className="text-muted" />
        ) : (
          <ChevronDown size={16} className="text-muted" />
        )}
      </button>

      {open && (
        <div className="thin-scroll max-h-72 overflow-y-auto border-t border-border px-3 pb-3 pt-2">
          {count === 0 ? (
            <p className="text-xs text-muted">No critical events captured yet.</p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {events.map((event) => (
                <article
                  key={event.id}
                  className="rounded-md border border-border bg-surface/40 p-2"
                >
                  <header className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wider">
                    <span className="font-semibold text-bad">{event.type}</span>
                    <span className="text-muted">
                      {new Date(event.timestamp * 1000).toLocaleString()}
                    </span>
                  </header>
                  <p className="mb-2 text-[11px] text-muted">
                    Trigger: {event.trigger}
                  </p>
                  <div className="space-y-1">
                    {Object.entries(event.media || {}).map(([camera, url]) => (
                      <div key={camera}>
                        <p className="mb-1 text-[10px] uppercase tracking-wider text-muted">
                          {camera}
                        </p>
                        <video
                          className="w-full rounded border border-border"
                          controls
                          src={url}
                        />
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
