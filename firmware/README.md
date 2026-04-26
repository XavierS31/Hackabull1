# Firmware

Two flashing options are supported -- pick whichever works for your setup:

- **Arduino IDE** (recommended fallback): open `firmware/glasses/glasses.ino` or `firmware/node_b_glove/node_b_glove.ino`, pick the right board in `Tools -> Board`, hit Upload.
- **PlatformIO** (CLI / VS Code): use the `firmware/*.bat` scripts and `platformio.ini` files. Same source, just compiled from `src/main.cpp`.

```
firmware/
├── glasses/
│   ├── glasses.ino           # Arduino IDE entry point
│   ├── platformio.ini        # PlatformIO project
│   └── src/main.cpp          # same code, PIO layout
├── node_b_glove/
│   ├── node_b_glove.ino      # Arduino IDE entry point
│   ├── platformio.ini
│   └── src/main.cpp
├── build_glasses.bat         # PIO: build only
├── upload_glasses.bat        # PIO: build + flash (USB)
├── monitor_glasses.bat       # PIO: serial monitor
├── build_glove.bat
├── upload_glove.bat
├── monitor_glove.bat
├── build_all.bat
└── list_ports.bat
```

## Glove data path -- two options

The glove ESP32 emits its IMU/IR data **two ways simultaneously**, so you can use whichever transport works:

1. **Wi-Fi UDP** (preferred when Wi-Fi is healthy): `udp://<ORCHESTRATOR_IP>:9002`. Configured in `node_b_glove.ino`.
2. **USB Serial JSON** (fallback, no Wi-Fi needed): the sketch prints one JSON line per packet at 10 Hz to USB serial. The PC-side bridge `scripts/serial_bridge.py` reads those lines and forwards them as UDP datagrams to `127.0.0.1:9002`. From the backend's point of view, the two paths are indistinguishable.

Run the bridge with:
```bat
scripts\start_serial_bridge.bat COM5            REM auto-discovers from --list output
scripts\start_serial_bridge.bat COM5 -v         REM verbose: print every packet
```
Or from Claude Code: `/run-bridge`.

> If `WIFI_CONNECT_TIMEOUT_MS` (10 s) elapses without joining the AP, the sketch logs `WiFi failed -- continuing in serial-only mode.` and skips UDP. The Serial path keeps running regardless, so the bridge always works as long as USB is plugged in.

The compiled firmware images land at:

- `firmware/glasses/.pio/build/glasses/firmware.bin`
- `firmware/node_b_glove/.pio/build/node_b_glove/firmware.bin`

---

## 1. Prerequisites (one-time)

1. Install PlatformIO Core. Either:
   - Install the [PlatformIO IDE extension](https://platformio.org/install/ide?install=vscode) in VS Code (it installs the CLI for you), **or**
   - `pip install platformio` and make sure `pio` is on `PATH`.
2. Install the CP210x or CH340 USB-serial driver for your ESP32 board if Windows shows no COM port when you plug it in.
3. Quick check: `pio --version` should print something like `PlatformIO Core, version 6.x`.

The first build will download the Espressif 32 platform + Arduino framework + xtensa toolchain (~hundreds of MB). That's normal and only happens once.

---

## 2. Configure WiFi + orchestrator IP

Edit the constants at the top of each `src/main.cpp` before flashing:

**`firmware/glasses/src/main.cpp`**
```cpp
const char* WIFI_SSID = "Spheal";
const char* WIFI_PASSWORD = "amonguss";
```

**`firmware/node_b_glove/src/main.cpp`**
```cpp
const char *WIFI_SSID = "Spheal";
const char *WIFI_PASSWORD = "amonguss";
const char *ORCHESTRATOR_IP = "192.168.1.10";   // your PC's LAN IP
const uint16_t ORCHESTRATOR_UDP_PORT = 9002;    // matches backend imu_udp_port
```

Find your PC's LAN IP with `ipconfig` (Wi-Fi adapter → IPv4 Address). The backend listens for IMU UDP on port `9002` (`backend/app/config.py: imu_udp_port`).

---

## 3. Flash the firmware

Plug in **one** ESP32 at a time so it's obvious which COM port is which.

### Find the COM ports

```bat
firmware\list_ports.bat
```

Look for entries with description like *Silicon Labs CP210x* or *USB-SERIAL CH340* — that's your ESP32.

### Glasses (Node A)

```bat
firmware\upload_glasses.bat            REM auto-detect port
firmware\upload_glasses.bat COM3       REM force a specific port
```

> If you have an AI-Thinker ESP32-CAM **without** a USB connector, you'll be using a separate FTDI/USB-TTL adapter. You must hold **GPIO0 → GND** while pressing reset to enter flash mode, then release after upload starts.

### Glove (Node B)

```bat
firmware\upload_glove.bat
firmware\upload_glove.bat COM4
```

### Watch the serial output

```bat
firmware\monitor_glasses.bat           REM or pass COMx
firmware\monitor_glove.bat
```

The glasses sketch prints its stream URL on boot:

```
WiFi connected
Stream URL: http://192.168.x.y:81/stream
```

Write that IP down — the backend needs it.

---

## 4. Data flow → backend

The two nodes talk to the backend in **opposite** directions:

| Node    | What it sends           | How                                                           |
|---------|--------------------------|---------------------------------------------------------------|
| Glasses | MJPEG video             | **Hosts** an HTTP server on `:81/stream`; backend pulls it.   |
| Glove   | IMU (x/y/z) + IR flag   | **Pushes** JSON UDP datagrams at 10 Hz to `<PC_IP>:9002`.     |

The glove has **no camera** — only IMU, IR, buzzer, and TFT display.

Once both nodes are flashed and on the WiFi:

1. Find your PC's LAN IP with `ipconfig`. Update `ORCHESTRATOR_IP` in `node_b_glove/src/main.cpp:19` if it changed, then re-flash.
2. Open `backend/.env` (create it next to `backend/app/config.py` if it doesn't exist) and set:

   ```env
   GLASSES_STREAM_URL=http://192.168.x.y:81/stream
   GLASSES_IP=192.168.x.y
   GLOVE_IP=192.168.x.z
   IMU_UDP_PORT=9002
   ```

   > Leave `GLOVE_STREAM_URL` empty — there is no glove camera. The backend skips it when blank (`backend/app/main.py:57`).

3. Make sure Windows Firewall lets inbound UDP on port 9002 reach Python — otherwise the IMU packets get silently dropped. Quick test from the PC after flashing:

   ```bat
   python -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('',9002));print(s.recvfrom(512))"
   ```

   You should see a packet within ~1 second.

4. Start the backend (`uvicorn app.main:app --host 0.0.0.0 --port 8000`). It will:
   - Pull the MJPEG stream from `GLASSES_STREAM_URL`.
   - Receive IMU/IR UDP packets from the glove on port `9002` and route them through `backend/app/services/imu.py`.

If a board is unreachable, double-check WiFi creds, that the PC and the ESP32 are on the **same** subnet, and that no AP-isolation / "guest" mode is active.

---

## 5. Pin map (Node B)

| Peripheral     | Signal | GPIO |
|----------------|--------|------|
| TFT (SPI)      | MOSI   | 23   |
| TFT (SPI)      | SCK    | 18   |
| TFT (SPI)      | CS     | 5    |
| TFT (SPI)      | DC     | 27   |
| TFT (SPI)      | RST    | 4    |
| MPU-6050 (I²C) | SDA    | 21   |
| MPU-6050 (I²C) | SCL    | 22   |
| IR sensor      | DO     | 13   |
| Buzzer         | +      | 12   |

> The glove runs on a plain ESP32 dev board (`board = esp32dev`), **not** an ESP32-CAM. It has no camera; the pin choices above (5, 18, 23, 27, …) would collide with the camera bus on an ESP32-CAM, so don't try to flash this firmware to a CAM-style board without remapping.

The TFT_eSPI library is configured entirely from `platformio.ini` `build_flags` (`USER_SETUP_LOADED=1` + `ST7735_DRIVER`, `TFT_*` pins, etc.). Don't edit `User_Setup.h` inside the library folder — your changes will be wiped on the next dependency reinstall.

---

## 6. Common issues

| Symptom                                            | Fix                                                                                                |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `A fatal error occurred: Could not open COMx`      | Wrong/closed port, board not in flash mode, or another app (Arduino monitor) holds it.            |
| Upload starts then `Timed out waiting for packet`  | Hold GPIO0→GND, tap RESET, release GPIO0 once flashing begins.                                    |
| Camera init `0x20001`/`0x20004`                    | Bad 5V supply (USB 2.0 port can brown out the cam). Use a powered hub or external 5V.             |
| TFT shows white/garbled                            | Wrong driver. Try `ST7735_REDTAB`/`ST7735_BLACKTAB` instead of `ST7735_GREENTAB` in `build_flags`. |
| Backend can't pull stream                          | Browse to `http://<esp_ip>:81/stream` from your PC first; if that fails, it's a network issue.    |
| `pio` not found                                    | Reopen the terminal after install, or use the VS Code PlatformIO toolbar (✓ build, → upload).      |

---

## 7. Typical workflow

```bat
REM 1. Flash both boards (one USB cable at a time)
firmware\upload_glasses.bat
firmware\upload_glove.bat

REM 2. Confirm they came up on WiFi
firmware\monitor_glasses.bat   REM note the printed stream URL, then Ctrl+C

REM 3. Update backend\.env with the printed IPs

REM 4. Start the backend (separate terminal, from project root)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The backend will then pull video from both cameras and IMU telemetry from the glove.
