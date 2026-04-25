import { Activity, Camera, ShieldAlert, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import AgentToggles from "./components/AgentToggles";
import CameraPanel from "./components/CameraPanel";
import EventsGallery from "./components/EventsGallery";
import PatientProfile from "./components/PatientProfile";
import ThinkingFeed from "./components/ThinkingFeed";

const API_BASE = "";

export default function App() {
  const [patient, setPatient] = useState({});
  const [agents, setAgents] = useState({});
  const [events, setEvents] = useState([]);
  const [thinking, setThinking] = useState([]);
  const [refreshToken, setRefreshToken] = useState(Date.now());

  useEffect(() => {
    const interval = setInterval(() => setRefreshToken(Date.now()), 350);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const load = async () => {
      const [patientResp, agentsResp, eventsResp] = await Promise.all([
        fetch(`${API_BASE}/api/patient`),
        fetch(`${API_BASE}/api/agents`),
        fetch(`${API_BASE}/api/events`)
      ]);
      if (patientResp.ok) setPatient(await patientResp.json());
      if (agentsResp.ok) setAgents(await agentsResp.json());
      if (eventsResp.ok) setEvents(await eventsResp.json());
    };
    load();
    const poll = setInterval(load, 3000);
    return () => clearInterval(poll);
  }, []);

  useEffect(() => {
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsBase = `${wsProtocol}://${window.location.host}`;
    const thinkingSocket = new WebSocket(`${wsBase}/ws/thinking`);
    const statusSocket = new WebSocket(`${wsBase}/ws/status`);

    thinkingSocket.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        if (parsed.type === "thinking" && parsed.line) {
          setThinking((prev) => [{ line: parsed.line, ts: parsed.ts }, ...prev].slice(0, 200));
        }
      } catch (_err) {
        // Ignore malformed socket payloads.
      }
    };

    statusSocket.onmessage = (msg) => {
      try {
        const parsed = JSON.parse(msg.data);
        if (parsed.type === "agent_status" && parsed.data) {
          setAgents(parsed.data);
        }
      } catch (_err) {
        // Ignore malformed socket payloads.
      }
    };

    return () => {
      thinkingSocket.close();
      statusSocket.close();
    };
  }, []);

  const cameraSources = useMemo(
    () => ({
      glasses: `/api/stream/frame/glasses?ts=${refreshToken}`,
      glove: `/api/stream/frame/glove?ts=${refreshToken}`
    }),
    [refreshToken]
  );

  return (
    <main className="mx-auto grid min-h-screen max-w-[1600px] gap-3 p-3 lg:grid-cols-[320px_1fr_360px]">
      <section className="grid gap-3">
        <header className="rounded border border-slate-700 bg-panel p-4">
          <p className="text-xs uppercase tracking-wide text-slate-400">Patient Console</p>
          <h1 className="mt-1 text-lg font-semibold text-white">Agentic AI Orchestrator</h1>
        </header>
        <Panel title="Patient Profile" icon={UserRound}>
          <PatientProfile patient={patient} />
        </Panel>
        <Panel title="Agent Status" icon={Activity}>
          <AgentToggles agents={agents} onUpdate={setAgents} />
        </Panel>
      </section>

      <section className="grid gap-3">
        <div className="grid gap-3 md:grid-cols-2">
          <Panel title="Glasses Camera (Node A)" icon={Camera}>
            <CameraPanel src={cameraSources.glasses} />
          </Panel>
          <Panel title="Glove Camera (Node B)" icon={Camera}>
            <CameraPanel src={cameraSources.glove} />
          </Panel>
        </div>
        <Panel title="Critical Events" icon={ShieldAlert}>
          <EventsGallery events={events} />
        </Panel>
      </section>

      <section>
        <Panel title="Reasoning Log (Thinking)" icon={Activity} className="h-full">
          <ThinkingFeed rows={thinking} />
        </Panel>
      </section>
    </main>
  );
}

function Panel({ title, icon: Icon, children, className = "" }) {
  return (
    <article className={`rounded border border-slate-700 bg-panel p-3 ${className}`}>
      <header className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
        <Icon size={16} className="text-accent" />
        <span>{title}</span>
      </header>
      {children}
    </article>
  );
}
