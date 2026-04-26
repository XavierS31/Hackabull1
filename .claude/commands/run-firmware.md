---
description: Build (if needed) and flash both ESP32 firmware images, with interactive prompts for COM port and boot buttons.
---

Run **only the firmware portion** of the stack pipeline. Use the steps from `/run-stack` Step 2, but skip backend/frontend.

Pre-step: ensure the firmware images are built.

```bash
powershell -ExecutionPolicy Bypass -File "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/ensure_setup.ps1"
```

Then:

1. List COM ports:
   ```bash
   pio device list
   ```

2. **Glasses** (AI-Thinker ESP32-CAM, requires FTDI + IO0/RST button dance):
   - Tell the user: *"Plug ONLY the glasses board. Hold IO0 (or short IO0→GND), tap RST, release IO0 ~1s after upload starts. Reply with the COM port."*
   - Upload: `cd "C:/Users/Xavie/OneDrive/Desktop/Hackabull/firmware/glasses" && pio run -t upload --upload-port <COMx>`
   - Offer to open the serial monitor so they can capture the printed stream URL.

3. **Glove** (plain ESP32 dev board, usually no buttons needed):
   - Tell the user: *"Unplug glasses, plug glove. If upload fails: hold BOOT, tap EN, release BOOT."*
   - Confirm `ORCHESTRATOR_IP` in `firmware/node_b_glove/src/main.cpp:19` matches the user's PC LAN IP. If not, edit it before flashing.
   - Upload: `cd "C:/Users/Xavie/OneDrive/Desktop/Hackabull/firmware/node_b_glove" && pio run -t upload --upload-port <COMx>`

4. Report which board(s) flashed successfully and remind the user to update `backend/.env` if any IPs changed.
