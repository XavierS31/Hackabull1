---
description: Start the serial-to-UDP bridge that forwards glove IMU/IR data from the COM port to the backend.
---

Run the serial bridge that reads JSON lines from the glove ESP32 over USB and forwards each one as a UDP datagram to the backend's IMU listener (port 9002 by default). Use this when the glove can't reach Wi-Fi (e.g. iPhone hotspot blocking), so the data still gets through over USB.

1. List COM ports so the user can pick the glove (look for `Silicon Labs CP210x` typically):
   ```bash
   "C:/Users/Xavie/OneDrive/Desktop/Hackabull/.venv/Scripts/python.exe" "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/serial_bridge.py" --list
   ```

2. Ask the user which COM port the glove is on (e.g. `COM5`).

3. Start the bridge in the background (`run_in_background=true`). Save the bash_id.
   ```bash
   cmd /c "C:/Users/Xavie/OneDrive/Desktop/Hackabull/scripts/start_serial_bridge.bat" COM5
   ```

4. After ~3 seconds, `BashOutput` the bash_id and confirm you see `[bridge] forwarding ... -> 127.0.0.1:9002` and `[bridge] opened COMx`. If you see `serial error: ... PermissionError`, another app (Arduino IDE Serial Monitor) is holding the port -- ask the user to close it, then `KillBash` and restart.

5. Report the bash_id to the user so they can `KillBash` it later.
