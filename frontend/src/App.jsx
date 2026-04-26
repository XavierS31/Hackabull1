import { Activity, MessageSquare, Mic, Radar, ShieldPlus, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import AgentToggles from "./components/AgentToggles";
import CameraPanel from "./components/CameraPanel";
import ChatPanel from "./components/ChatPanel";
import DetectionsPanel from "./components/DetectionsPanel";
import EventsGallery from "./components/EventsGallery";
import PatientProfile from "./components/PatientProfile";
import QuickActions from "./components/QuickActions";
import VoicePanel from "./components/VoicePanel";

const API_BASE = "";

export default function App() {
  const [patient, setPatient] = useState({});
  const [agents, setAgents] = useState({});
  const [events, setEvents] = useState([]);
  const [refreshToken, setRefreshToken] = useState(Date.now());

  // Refresh the camera frame at ~3 fps
  useEffect(() => {
    const interval = setInterval(() => setRefreshToken(Date.now()), 350);
    return () => clearInterval(interval);
  }, []);

  // Poll backend snapshots every 3 seconds
  useEffect(() => {
    const load = async () => {
      try {
        const [patientResp, agentsResp, eventsResp] = await Promise.all([
          fetch(`${API_BASE}/api/patient`),
          fetch(`${API_BASE}/api/agents`),
          fetch(`${API_BASE}/api/events`)
        ]);
        if (patientResp.ok) setPatient(await patientResp.json());
        if (agentsResp.ok)  setAgents(await agentsResp.json());
        if (eventsResp.ok)  setEvents(await eventsResp.json());
      } catch {/* ignore transient errors */}
    };
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, []);

  // Live agent-status updates via WS (push on top of the 3s poll)
  useEffect(() => {
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsBase = `${wsProtocol}://${window.location.host}`;
    const statusSocket = new WebSocket(`${wsBase}/ws/status`);
    statusSocket.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        if (parsed.type === "agent_status" && parsed.data) setAgents(parsed.data);
      } catch {/* ignore */}
    };
    return () => statusSocket.close();
  }, []);

  const glassesSrc = useMemo(
    () => `/api/stream/frame/glasses?ts=${refreshToken}`,
    [refreshToken]
  );

  return (
    <main className="mx-auto flex h-screen max-h-screen w-full max-w-[1700px] flex-col gap-3 overflow-hidden p-3">
      {/* HEADER */}
      <header className="flex items-center justify-between gap-4 rounded-lg border border-border bg-panel px-4 py-3 shadow-glow">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md border border-accent/40 bg-accent/10">
            <ShieldPlus size={18} className="text-accent" />
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-accent">
              Healthcare AI · Live
            </p>
            <h1 className="text-xl font-bold tracking-tight text-ink">
              SeeMe <span className="text-accent">Safe</span>
            </h1>
          </div>
        </div>

        <div className="min-w-0 flex-1 max-w-md">
          <PatientProfile patient={patient} onPatientUpdate={setPatient} />
        </div>
      </header>

      {/* MAIN GRID — 3 columns, fixed-height row, then collapsible bottom strip */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 lg:grid-cols-[300px_1fr_300px]">
        {/* LEFT — Conversation (top) + Talkative voice (bottom) */}
        <aside className="grid min-h-0 grid-rows-[1fr_auto] gap-3">
          <Panel title="Conversational" icon={MessageSquare}>
            <ChatPanel />
          </Panel>
          <Panel title="Talkative" icon={Mic}>
            <VoicePanel />
          </Panel>
        </aside>

        {/* CENTER — Glasses camera (only) + quick actions under it */}
        <section className="flex min-h-0 flex-col gap-3">
          <Panel title="Glasses Vision" icon={Radar} className="flex flex-1 flex-col">
            <CameraPanel src={glassesSrc} label="Glasses · Live" />
          </Panel>
          <div className="rounded-lg border border-border bg-panel p-3">
            <QuickActions />
          </div>
        </section>

        {/* RIGHT — Detections (top, 3s refresh) + Agents (bottom) */}
        <aside className="grid min-h-0 grid-rows-[1fr_auto] gap-3">
          <Panel title="Detections" icon={Activity}>
            <DetectionsPanel />
          </Panel>
          <Panel title="Agents" icon={UserRound}>
            <AgentToggles agents={agents} />
          </Panel>
        </aside>
      </div>

      {/* BOTTOM — collapsible falls/critical events strip (scrollable internally) */}
      <EventsGallery events={events} />
    </main>
  );
}

function Panel({ title, icon: Icon, children, className = "" }) {
  return (
    <article className={`flex min-h-0 flex-col rounded-lg border border-border bg-panel p-3 ${className}`}>
      <header className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
        <Icon size={13} />
        <span>{title}</span>
      </header>
      <div className="min-h-0 flex-1">
        {children}
      </div>
    </article>
  );
}
