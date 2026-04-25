export default function EventsGallery({ events }) {
  if (!events.length) {
    return <p className="text-sm text-slate-400">No critical events captured yet.</p>;
  }

  return (
    <div className="grid gap-2 md:grid-cols-2">
      {events.map((event) => (
        <article key={event.id} className="rounded border border-slate-800 bg-slate-950 p-2">
          <header className="mb-2 text-xs text-slate-400">
            <p>{new Date(event.timestamp * 1000).toLocaleString()}</p>
            <p>Trigger: {event.trigger}</p>
          </header>
          <div className="space-y-2">
            {Object.entries(event.media || {}).map(([camera, url]) => (
              <div key={camera}>
                <p className="mb-1 text-xs text-slate-500">{camera}</p>
                <video className="w-full rounded border border-slate-700" controls src={url} />
              </div>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
