import { Mic, MicOff, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const WS_PROTOCOL = window.location.protocol === "https:" ? "wss" : "ws";
const WS_BASE = `${WS_PROTOCOL}://${window.location.host}`;

export default function VoicePanel() {
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("idle");

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const wsRef = useRef(null);

  useEffect(() => {
    let ws;
    const connect = () => {
      ws = new WebSocket(`${WS_BASE}/ws/voice`);
      wsRef.current = ws;
      ws.binaryType = "arraybuffer";

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer && event.data.byteLength > 0) {
          const blob = new Blob([event.data], { type: "audio/mpeg" });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play().catch(() => {});
          audio.onended = () => URL.revokeObjectURL(url);
        }
      };

      ws.onclose = () => setTimeout(connect, 2000);
    };
    connect();
    return () => ws?.close();
  }, []);

  const startRecording = async () => {
    if (recording || busy) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setRecording(true);
      setStatus("recording");
      setTranscript("");
      setResponse("");
    } catch {
      setResponse("Microphone access denied.");
    }
  };

  const stopRecording = async () => {
    if (!recording || !mediaRecorderRef.current) return;
    setRecording(false);
    setStatus("processing");
    setBusy(true);

    const mr = mediaRecorderRef.current;
    mr.stop();
    mr.stream.getTracks().forEach((t) => t.stop());

    await new Promise((resolve) => {
      mr.onstop = resolve;
    });

    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");

    try {
      const resp = await fetch("/api/voice/chat", { method: "POST", body: formData });

      if (resp.ok) {
        const rawTranscript = resp.headers.get("X-Transcript") || "";
        const rawResponse = resp.headers.get("X-Response") || "";
        setTranscript(decodeURIComponent(rawTranscript));
        setResponse(decodeURIComponent(rawResponse));

        const audioBytes = await resp.arrayBuffer();
        if (audioBytes.byteLength > 0) {
          const audioBlob = new Blob([audioBytes], { type: "audio/mpeg" });
          const url = URL.createObjectURL(audioBlob);
          const audio = new Audio(url);
          audio.play().catch(() => {});
          audio.onended = () => URL.revokeObjectURL(url);
        }
      } else {
        const body = await resp.json().catch(() => ({}));
        setResponse(body.detail || "Voice service unavailable (check ELEVENLABS_API_KEY).");
      }
    } catch {
      setResponse("Network error contacting backend.");
    } finally {
      setBusy(false);
      setStatus("idle");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">
          {status === "recording" && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-red-500" />
              Recording…
            </span>
          )}
          {status === "processing" && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 animate-spin rounded-full border border-accent border-t-transparent" />
              Processing…
            </span>
          )}
          {status === "idle" && "Hold to talk"}
        </span>
        <Volume2 size={14} className="text-slate-500" />
      </div>

      <div className="flex justify-center">
        <button
          className={`flex h-16 w-16 items-center justify-center rounded-full border-2 transition-all duration-150 ${
            recording
              ? "scale-110 border-red-500 bg-red-500/20 text-red-400"
              : busy
              ? "cursor-not-allowed border-slate-600 bg-slate-800 text-slate-500"
              : "border-accent bg-accent/10 text-accent hover:bg-accent/20 active:scale-95"
          }`}
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
          onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
          disabled={busy}
          aria-label={recording ? "Stop recording" : "Start recording"}
        >
          {recording ? <MicOff size={28} /> : <Mic size={28} />}
        </button>
      </div>

      {transcript && (
        <div className="rounded bg-slate-800 p-2 text-sm">
          <p className="text-xs text-slate-400">You said:</p>
          <p className="mt-0.5 text-slate-200">{transcript}</p>
        </div>
      )}

      {response && (
        <div className="rounded bg-slate-800 p-2 text-sm">
          <p className="text-xs text-slate-400">Agent:</p>
          <p className="mt-0.5 text-green-300">{response}</p>
        </div>
      )}
    </div>
  );
}
