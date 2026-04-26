# Medical Agentic AI Orchestrator

This repository now includes:
- `backend/`: FastAPI orchestrator (Gemma onboarding, stream handling, IMU UDP/WebSocket ingestion, fall-event clip capture).
- `frontend/`: React + Tailwind dashboard (patient profile, dual camera panels, agent toggles, thinking feed, critical events gallery).
- `firmware/`: ESP32-CAM sketches for Node A (glasses stream) and Node B (glove IMU/IR/TFT/speaker + stream).

## 1) One-command setup

From repo root:

```powershell
.\setup.ps1
```

## 2) Configure backend secrets

Edit:
- `backend/.env`

Set at minimum:
- `GEMINI_API_KEY=...`
- `GLASSES_STREAM_URL=http://<node-a-ip>:81/stream`
- `GLOVE_STREAM_URL=http://<node-b-ip>:81/stream`

## 3) Run services

Backend:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

Open:
- `http://localhost:5173`

## 4) Firmware

Flash:
- `firmware/glasses/glasses.ino`
- `firmware/node_b_glove/node_b_glove.ino`

For Node B TFT pins, see the `TFT_eSPI` `#define` block at the top of:
- `firmware/node_b_glove/node_b_glove.ino`

Pin mapping details:
- `firmware/README.md`
