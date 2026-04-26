---
description: Full local pipeline — setup if needed, flash firmware, start backend, health-check, start frontend.
---

You are now running the **full Hackabull stack** for the user. Follow the steps below in order. **Do not skip the user-confirmation prompts** — flashing firmware is interactive and requires the user to plug/unplug USB and (on AI-Thinker ESP32-CAM) hold buttons.

The repo lives at `C:\Users\Xavie\OneDrive\Desktop\Hackabull`. Working directory is the backend/, but use absolute paths from the project root for clarity.

---

## Step 1 — Idempotent setup

Run the setup script. It only does work that hasn't been done yet (creates venv if missing, pip-installs if `requirements.txt` changed, npm-installs if `node_modules` missing, builds firmware if `firmware.bin` missing).

```bash
powershell -ExecutionPolicy Bypass -File "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/ensure_setup.ps1"
```

If this fails, **stop the pipeline** and report the error. Don't try to flash or run the backend on a broken setup.

After it succeeds, briefly tell the user what it did vs. skipped.

---

## Step 2 — Flash firmware (interactive)

Show available serial ports so the user can identify which COM port belongs to which board:

```bash
pio device list
```

Then walk the user through this exactly, **pausing for confirmation at each prompt**:

> **Glasses (Node A — AI-Thinker ESP32-CAM):**
> 1. Plug **only** the glasses ESP32-CAM into USB (via its FTDI/USB-TTL adapter — these boards have no native USB).
> 2. **Hold the IO0 button (or jumper IO0 → GND)**, tap the RST button, then **release IO0** about 1 second after upload starts. This puts the chip in download mode.
> 3. Reply with the COM port (e.g. `COM3`), or `auto` to let PlatformIO detect it.

When the user replies, run the upload (substitute the port they gave; omit `--upload-port` if they said `auto`):

```bash
cd "C:/Users/Xavie/OneDrive/Desktop/Hackabull/firmware/glasses" && pio run -t upload --upload-port COM3
```

If you see `Connecting....___` followed by `Hard resetting via RTS pin...` and `[SUCCESS]`, it worked. After upload completes, ask the user to open a serial monitor briefly to capture the **printed stream URL**:

```bash
cd "C:/Users/Xavie/OneDrive/Desktop/Hackabull/firmware/glasses" && pio device monitor --port COM3
```

(They should see `Stream URL: http://192.168.x.y:81/stream`. Have them copy that IP and Ctrl+C out of the monitor.)

> **Glove (Node B — plain ESP32 dev board):**
> 1. Unplug the glasses, plug in the glove ESP32.
> 2. Most ESP32 dev boards auto-enter flash mode — no buttons needed. If upload fails with `Failed to connect`, hold **BOOT**, tap **EN/RST**, release **BOOT**.
> 3. Reply with the COM port.

Then upload:

```bash
cd "C:/Users/Xavie/OneDrive/Desktop/Hackabull/firmware/node_b_glove" && pio run -t upload --upload-port COM4
```

The glove pushes UDP at 10 Hz to `ORCHESTRATOR_IP:9002` (defined in `firmware/node_b_glove/src/main.cpp:19`). **Before flashing, confirm with the user that this IP matches their PC's LAN IP** — if not, edit the file and re-run upload.

---

## Step 3 — Wire the IPs into backend/.env

Read `backend/.env` and confirm it has at minimum:

```env
GLASSES_STREAM_URL=http://<glasses_ip>:81/stream
GLASSES_IP=<glasses_ip>
GLOVE_IP=<glove_ip>
IMU_UDP_PORT=9002
```

If the user gave you a glasses IP from the serial monitor, update `GLASSES_STREAM_URL` and `GLASSES_IP`. **Leave `GLOVE_STREAM_URL` empty** — the glove has no camera. If `GEMINI_API_KEY` / `GOOGLE_API_KEY` is missing, warn the user (the LLM agents won't work without one) but proceed.

---

## Step 4 — Start backend (background)

Launch the backend with `run_in_background=true`. Save the resulting bash_id.

```bash
cmd /c "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/start_backend.bat"
```

---

## Step 5 — Backend health check

Poll `/healthz` until it answers (max 30 s). Run this in the foreground:

```bash
powershell -ExecutionPolicy Bypass -File "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/health_check.ps1"
```

If it exits non-zero, `BashOutput` the backend bash_id, show the user the last ~50 lines of the backend log, and stop. **Do not start the frontend on an unhealthy backend.**

---

## Step 6 — Start frontend (background)

```bash
cmd /c "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/start_frontend.bat"
```

Use `run_in_background=true`. Then poll its output via `BashOutput` until you see Vite print `Local:   http://localhost:5173/` (or similar). If that doesn't appear within ~15 seconds, surface the log to the user.

---

## Step 7 — Final report

Print a concise summary to the user:

- ✅ Backend live at `http://localhost:8000` (health: ok), bash_id `xxx`
- ✅ Frontend live at `http://localhost:5173`, bash_id `yyy`
- 📷 Glasses stream: `http://<ip>:81/stream`
- 🧤 Glove pushing IMU/IR to UDP 9002
- To stop: `KillBash <bash_id>` for each background process.

**Do not** narrate every intermediate step in long prose — keep updates brief, one sentence per phase.
