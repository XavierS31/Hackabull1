import { CameraOff } from "lucide-react";
import { useState } from "react";

export default function CameraPanel({ src, label = "Glasses · Live" }) {
  const [errored, setErrored] = useState(false);

  return (
    <div className="relative flex-1 overflow-hidden rounded-lg border border-border bg-black shadow-glow">
      {/* Frame */}
      <img
        src={src}
        alt="Live camera frame"
        className="h-full w-full object-cover"
        onLoad={() => errored && setErrored(false)}
        onError={() => setErrored(true)}
      />

      {errored && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-bg/90 text-muted">
          <CameraOff size={28} className="text-accent" />
          <p className="text-xs">Waiting for camera frame…</p>
        </div>
      )}

      {/* Live badge */}
      <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-2 rounded-full border border-accent/40 bg-bg/70 px-3 py-1 backdrop-blur-sm">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-70" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-accent">
          {label}
        </span>
      </div>
    </div>
  );
}
