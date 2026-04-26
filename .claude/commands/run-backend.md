---
description: Start the FastAPI backend in the background and wait for /healthz to return ok.
---

Launch the backend and verify it's healthy. Skip firmware and frontend.

1. Setup check (idempotent — fast if already done):
   ```bash
   powershell -ExecutionPolicy Bypass -File "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/ensure_setup.ps1"
   ```

2. Start backend in background (`run_in_background=true`). Save the bash_id.
   ```bash
   cmd /c "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/start_backend.bat"
   ```

3. Health check (foreground, exits 0 on healthy, 1 on timeout):
   ```bash
   powershell -ExecutionPolicy Bypass -File "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/health_check.ps1"
   ```

4. If health check fails, `BashOutput` the backend bash_id and show the user the last ~50 log lines, then stop.

5. On success, print: backend URL (`http://localhost:8000`), `/healthz` confirmed, and the bash_id so the user can `KillBash` it later.
