import { Eye, Phone, Send } from "lucide-react";
import { useRef, useState } from "react";

export default function ChatPanel() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const appendMsg = (role, text) => {
    setMessages((prev) => [...prev, { role, text, ts: Date.now() }].slice(-100));
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  };

  const send = async () => {
    const text = message.trim();
    if (!text || loading) return;
    setMessage("");
    appendMsg("user", text);
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      appendMsg("agent", data.response);
    } catch {
      appendMsg("error", "Request failed — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const analyzeVision = async () => {
    if (loading) return;
    appendMsg("user", "[Vision] Analyzing glasses camera…");
    setLoading(true);
    try {
      const res = await fetch("/api/vision/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera: "glasses" }),
      });
      const data = await res.json();
      appendMsg("agent", `Vision Agent: ${data.description}`);
    } catch {
      appendMsg("error", "Vision analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const triggerTalk = async () => {
    if (loading) return;
    appendMsg("user", "[TALK] Activating conversation agent…");
    setLoading(true);
    try {
      const res = await fetch("/api/triggers/talk", { method: "POST" });
      const data = await res.json();
      appendMsg("agent", `Conversation Agent: ${data.response}`);
    } catch {
      appendMsg("error", "TALK trigger failed.");
    } finally {
      setLoading(false);
    }
  };

  const triggerCall = async () => {
    if (loading) return;
    const to = window.prompt("Emergency contact phone number (E.164 format):\nLeave blank to use default.", "+16893481796") ?? "";
    const location = window.prompt("Patient location (optional — e.g. 'living room'):", "") ?? "";
    appendMsg("user", `[CALL] Initiating emergency call${location ? ` — location: ${location}` : ""}…`);
    setLoading(true);
    try {
      const body = { location: location.trim() };
      if (to.trim()) body.to = to.trim();
      const res = await fetch("/api/call/emergency", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.call_sid) {
        appendMsg("agent", `Emergency call placed to ${data.to}. Call SID: ${data.call_sid}`);
      } else {
        appendMsg("error", data.error || "Call failed.");
      }
    } catch {
      appendMsg("error", "Emergency call request failed.");
    } finally {
      setLoading(false);
    }
  };

  const triggerTrack = async () => {
    if (loading) return;
    const desc = window.prompt("Describe the event to track (Tracking Dementia):");
    if (!desc?.trim()) return;
    try {
      await fetch("/api/triggers/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: desc.trim() }),
      });
      appendMsg("agent", `Tracking Dementia: Logged — "${desc.trim()}"`);
    } catch {
      appendMsg("error", "TRACK trigger failed.");
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="h-44 overflow-y-auto rounded border border-slate-800 bg-slate-950 p-2">
        {messages.length === 0 ? (
          <p className="text-xs text-slate-500">
            Chatbot ready. Type a message or use the buttons below.
          </p>
        ) : (
          <ul className="space-y-1">
            {messages.map((m, i) => (
              <li key={i} className="text-xs leading-snug">
                <span
                  className={
                    m.role === "user"
                      ? "font-semibold text-blue-400"
                      : m.role === "error"
                      ? "font-semibold text-red-400"
                      : "font-semibold text-accent"
                  }
                >
                  {m.role === "user" ? "You" : m.role === "error" ? "Error" : "Agent"}:{" "}
                </span>
                <span className="text-slate-200">{m.text}</span>
              </li>
            ))}
            {loading && (
              <li className="animate-pulse text-xs text-slate-500">Agent thinking…</li>
            )}
          </ul>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-1">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask the chatbot…"
          className="flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-accent"
        />
        <button
          onClick={send}
          disabled={loading || !message.trim()}
          title="Send message"
          className="rounded bg-accent px-2 py-1 text-white disabled:opacity-40"
        >
          <Send size={13} />
        </button>
        <button
          onClick={analyzeVision}
          disabled={loading}
          title="Vision Agent: analyze glasses camera"
          className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-slate-300 disabled:opacity-40"
        >
          <Eye size={13} />
        </button>
      </div>

      <div className="flex gap-1">
        <button
          onClick={triggerTalk}
          disabled={loading}
          className="flex-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:border-accent hover:text-accent disabled:opacity-40"
        >
          TALK
        </button>
        <button
          onClick={triggerTrack}
          disabled={loading}
          className="flex-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:border-accent hover:text-accent disabled:opacity-40"
        >
          TRACK
        </button>
        <button
          onClick={triggerCall}
          disabled={loading}
          title="Call emergency contact"
          className="flex items-center gap-1 rounded border border-red-800 px-2 py-1 text-xs text-red-400 hover:border-red-500 hover:text-red-300 disabled:opacity-40"
        >
          <Phone size={11} /> CALL
        </button>
      </div>
    </div>
  );
}
