export default function ThinkingFeed({ rows }) {
  if (!rows.length) {
    return <p className="text-sm text-slate-400">Reasoning stream is idle.</p>;
  }

  return (
    <div className="h-[calc(100vh-40px)] overflow-y-auto rounded border border-slate-800 bg-slate-950 p-2">
      <ul className="space-y-1">
        {rows.map((row, idx) => (
          <li key={`${row.ts || 0}-${idx}`} className="text-xs text-slate-200">
            <span className="mr-2 text-slate-500">
              {row.ts ? new Date(row.ts * 1000).toLocaleTimeString() : "--:--:--"}
            </span>
            <span>{row.line}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
