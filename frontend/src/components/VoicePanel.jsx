import { Mic, MicOff, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const WS_PROTOCOL = window.location.protocol === "https:" ? "wss" : "ws";
const WS_BASE = `${WS_PROTOCOL}://${window.location.host}`;

const INTENT_LABELS = {
  vision: "Vision Agent",
  talk: "Conversation",
  track: "Tracking",
  chat: "Chatbot",
};

export default function VoicePanel() {
  const [enabled, setEnabled] = useState(false);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [intent, setIntent] = useState("");
  const [agent, setAgent] = useState("");
  const [busy, setBusy] = useState(false);
  const [supported, setSupported] = useState(true);

  const recognitionRef = useRef(null);
  const enabledRef = useRef(false);
  const busyRef = useRef(false);
  const wsRef = useRef(null);

  // Keep refs in sync with state
  useEffect(() => { enabledRef.current = enabled; }, [enabled]);
  useEffect(() => { busyRef.current = busy; }, [busy]);

  // WebSocket: receive push TTS alerts (fall / IR) from backend
  useEffect(() => {
    let ws;
    const connect = () => {
      ws = new WebSocket(`${WS_BASE}/ws/voice`);
      wsRef.current = ws;
      ws.binaryType = "arraybuffer";
      ws.onmessage = (e) => {
        if (e.data instanceof ArrayBuffer && e.data.byteLength > 0) {
          const blob = new Blob([e.data], { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          new Audio(url).play().catch(() => {});
        }
      };
      ws.onclose = () => setTimeout(connect, 2000);
    };
    connect();
    return () => ws?.close();
  }, []);

  // Continuous speech recognition
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setSupported(false);
      return;
    }

    if (!enabled) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const recognition = new SR();
    recognition.continuous = false; // one utterance at a time, then restart
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    const startListening = () => {
      if (!enabledRef.current || busyRef.current) return;
      try {
        recognition.start();
      } catch {
        // already started — ignore
      }
    };

    recognition.onstart = () => setListening(true);

    recognition.onresult = async (event) => {
      const text = event.results[0][0].transcript.trim();
      if (!text) return;

      setTranscript(text);
      setBusy(true);
      busyRef.current = true;
      setListening(false);
      setResponse("");
      setIntent("");
      setAgent("");

      const done = () => {
        setBusy(false);
        busyRef.current = false;
        startListening();
      };

      try {
        const resp = await fetch("/api/voice/text-chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });

        // Always read text headers first — they're present even on errors
        const xResponse = resp.headers.get("X-Response") || "";
        const xAgent = resp.headers.get("X-Agent") || "Agent";
        const xIntent = resp.headers.get("X-Intent") || "chat";

        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          setResponse(body.detail || xResponse || "Backend error.");
          setAgent(xAgent || "Error");
          setIntent(xIntent);
          done();
          return;
        }

        // Show text immediately so the user can read while audio loads
        setResponse(decodeURIComponent(xResponse));
        setAgent(xAgent);
        setIntent(xIntent);

        const audioBytes = await resp.arrayBuffer();
        if (audioBytes.byteLength > 0) {
          const blob = new Blob([audioBytes], { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.onended = () => { URL.revokeObjectURL(url); done(); };
          audio.onerror = () => { URL.revokeObjectURL(url); done(); };
          audio.play().catch(done);
        } else {
          // No audio (TTS not configured) — text already shown, just continue
          done();
        }
      } catch {
        setResponse("Could not reach backend.");
        done();
      }
    };

    recognition.onerror = (e) => {
      if (e.error === "no-speech" || e.error === "audio-capture") {
        // normal — just restart
      }
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
      if (enabledRef.current && !busyRef.current) {
        setTimeout(startListening, 300);
      }
    };

    startListening();

    return () => {
      recognition.onend = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.stop();
    };
  }, [enabled]);

  if (!supported) {
    return (
      <p className="text-xs text-red-400">
        Continuous speech recognition requires Chrome or Edge.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Toggle row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {listening ? (
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-green-400" />
            </span>
          ) : (
            <span className={`h-3 w-3 rounded-full ${enabled ? "bg-yellow-400" : "bg-slate-600"}`} />
          )}
          <span className="text-xs text-slate-400">
            {!enabled
              ? "Voice assistant off"
              : busy
              ? "Responding…"
              : listening
              ? "Listening…"
              : "Waiting for speech…"}
          </span>
        </div>

        <button
          onClick={() => setEnabled((v) => !v)}
          className={`flex h-8 w-8 items-center justify-center rounded-full border transition-colors ${
            enabled
              ? "border-green-500 bg-green-500/20 text-green-400 hover:bg-green-500/30"
              : "border-slate-600 bg-slate-800 text-slate-400 hover:border-slate-500"
          }`}
          title={enabled ? "Disable voice assistant" : "Enable voice assistant"}
        >
          {enabled ? <Mic size={15} /> : <MicOff size={15} />}
        </button>
      </div>

      {/* Keywords hint */}
      {enabled && !transcript && !response && (
        <p className="text-xs text-slate-500">
          Say <span className="text-slate-300">"scan"</span>,{" "}
          <span className="text-slate-300">"talk"</span>,{" "}
          <span className="text-slate-300">"track"</span>, or ask anything.
        </p>
      )}

      {transcript && (
        <div className="rounded bg-slate-800 p-2 text-sm">
          <p className="text-xs text-slate-400">You said:</p>
          <p className="mt-0.5 text-slate-200">{transcript}</p>
        </div>
      )}

      {response && (
        <div className="rounded bg-slate-800 p-2 text-sm">
          <div className="flex items-center gap-2">
            <Volume2 size={11} className="text-slate-400" />
            <p className="text-xs text-slate-400">{agent || "Agent"}:</p>
            {intent && intent !== "chat" && (
              <span className="rounded bg-accent/20 px-1.5 py-0.5 text-xs font-medium text-accent capitalize">
                {INTENT_LABELS[intent] ?? intent}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-green-300">{response}</p>
        </div>
      )}
    </div>
  );
}
