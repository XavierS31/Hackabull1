---
description: Start the Vite dev server (frontend) in the background.
---

Launch the React/Vite dev server. Assumes the backend is already running (Vite proxies/CORS to it).

1. Setup check (idempotent — runs `npm install` only if `node_modules` missing):
   ```bash
   powershell -ExecutionPolicy Bypass -File "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/ensure_setup.ps1"
   ```

2. Start frontend in background (`run_in_background=true`). Save the bash_id.
   ```bash
   cmd /c "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/start_frontend.bat"
   ```

3. Poll its output via `BashOutput` until Vite prints its `Local:` URL (typically `http://localhost:5173/`). Surface that URL to the user along with the bash_id.

4. If the output shows a port conflict or compile error, surface the log lines and stop.
