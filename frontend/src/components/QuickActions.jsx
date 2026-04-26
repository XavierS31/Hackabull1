import { Eye, Footprints, ScanLine } from "lucide-react";
import { useState } from "react";

// Three primary trigger buttons under the camera: Detect, Scan, Track.
// All three POST to existing backend endpoints; no API changes needed.
const ACTIONS = [
  {
    key: "detect",
    label: "Detect",
    icon: Eye,
    title: "Vision Agent: describe surroundings now",
    run: () => fetch("/api/triggers/vision?camera=glasses", { method: "POST" })
  },
  {
    key: "scan",
    label: "Scan",
    icon: ScanLine,
    title: "Scan glasses frame for objects/obstacles",
    run: () =>
      fetch("/api/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera: "glasses" })
      })
  },
  {
    key: "track",
    label: "Track",
    icon: Footprints,
    title: "Tracking Dementia: log this moment",
    run: () => {
      const description =
        window.prompt("Describe what to remember:", "patient at home, calm") || "";
      if (!description.trim()) return Promise.resolve(null);
      return fetch("/api/triggers/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: description.trim() })
      });
    }
  }
];

export default function QuickActions() {
  const [busy, setBusy] = useState("");
  const [flash, setFlash] = useState("");

  const fire = async (action) => {
    if (busy) return;
    setBusy(action.key);
    try {
      const resp = await action.run();
      if (resp && resp.ok) {
        setFlash(action.key);
        setTimeout(() => setFlash(""), 700);
      }
    } catch {/* swallow */}
    setBusy("");
  };

  return (
    <div className="grid grid-cols-3 gap-2">
      {ACTIONS.map((a) => {
        const Icon = a.icon;
        const isBusy = busy === a.key;
        const isFlash = flash === a.key;
        return (
          <button
            key={a.key}
            onClick={() => fire(a)}
            disabled={!!busy}
            title={a.title}
            className={`group flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold uppercase tracking-wider transition-all ${
              isFlash
                ? "border-good bg-good/20 text-good shadow-glow"
                : isBusy
                ? "border-accent2 bg-accent2/20 text-accent animate-pulse"
                : "border-border bg-surface text-accent hover:border-accent hover:bg-accent/10 hover:shadow-glow"
            } disabled:opacity-50`}
          >
            <Icon size={15} className="transition-transform group-hover:scale-110" />
            <span>{a.label}</span>
          </button>
        );
      })}
    </div>
  );
}
