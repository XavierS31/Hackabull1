import { AlertTriangle, Eye, Footprints, MessageCircle, Radar } from "lucide-react";
import { useEffect, useState } from "react";

const TYPE_META = {
  fall:    { label: "Fall",      icon: AlertTriangle, tone: "bad"  },
  ir:      { label: "Object",    icon: Radar,         tone: "warn" },
  vision:  { label: "Vision",    icon: Eye,           tone: "accent" },
  track:   { label: "Track",     icon: Footprints,    tone: "accent" },
  talk:    { label: "Talk",      icon: MessageCircle, tone: "accent" }
};

const TONE_CLASS = {
  accent: "text-accent border-accent/40 bg-accent/10",
  good:   "text-good   border-good/40   bg-good/10",
  warn:   "text-warn   border-warn/40   bg-warn/10",
  bad:    "text-bad    border-bad/40    bg-bad/10"
};

// Polls /api/activity every 3 seconds and shows the latest detections.
// Compact, scrollable inside its own container -- never expands the page.
export default function DetectionsPanel() {
  const [rows, setRows] = useState([]);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const res = await fetch("/api/activity");
        if (!res.ok) return;
        const data = await res.json();
        if (!alive) return;
        setRows(Array.isArray(data) ? data : []);
        setPulse(true);
        setTimeout(() => setPulse(false), 350);
      } catch {/* ignore */}
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const latest = rows[0];

  return (
    <div className="flex h-full flex-col gap-2">
      {/* Live status pill */}
      <div className={`flex items-center justify-between rounded-md border px-2 py-1.5 transition-colors ${
        pulse ? "border-accent/60 bg-accent/10" : "border-border bg-surface"
      }`}>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
          </span>
          <span className="text-[11px] uppercase tracking-wider text-muted">Live · 3s poll</span>
        </div>
        {latest && (
          <span className="text-[10px] text-muted">
            {new Date((latest.ts || 0) * 1000).toLocaleTimeString()}
          </span>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="rounded-md border border-border bg-surface/40 p-3 text-xs text-muted">
          Nothing detected yet. Trigger a fall, point at an object, or use the
          buttons below the camera.
        </p>
      ) : (
        <div className="thin-scroll min-h-0 flex-1 overflow-y-auto pr-1">
          <ul className="space-y-1.5">
            {rows.slice(0, 30).map((row, idx) => {
              const meta = TYPE_META[row.type] || { label: row.type || "Event", icon: Eye, tone: "accent" };
              const Icon = meta.icon;
              const tone = TONE_CLASS[meta.tone];
              const detail =
                row.description ||
                row.message ||
                row.response ||
                (row.magnitude_g != null ? `${row.magnitude_g}g impact` : "");
              return (
                <li
                  key={`${row.ts || 0}-${idx}`}
                  className={`rounded-md border px-2 py-1.5 ${tone}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider">
                      <Icon size={12} />
                      <span>{meta.label}</span>
                    </div>
                    <span className="text-[10px] text-muted">
                      {row.ts ? new Date(row.ts * 1000).toLocaleTimeString() : ""}
                    </span>
                  </div>
                  {detail && (
                    <p className="mt-1 text-[12px] leading-snug text-ink/90 line-clamp-2">
                      {detail}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
