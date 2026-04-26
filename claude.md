# Hackabull Context for Claude

## Project Goal
Build a medical "Agentic AI" assistance system for patients (for example, dementia and fall-risk support) using:
- A PC as central orchestrator
- Two ESP32-CAM hardware nodes

## Hardware
- **Node A (Glasses)**
  - ESP32-CAM + OV2640
  - Role: first-person vision for obstacle/object detection
  - Transport: MJPEG stream over HTTP/WebSockets
  - Firmware: `firmware/glasses/glasses.ino`

- **Node B (Glove)**
  - ESP32-CAM (OV2640) + MPU-6050 IMU + IR sensor + Buzzer + 1.44" SPI TFT
  - Role: fall detection (through MPU), user interaction (audio to laptop/speaking to laptop/screen/Buzzer)

## Software Architecture
- **Pipeline 1: Onboarding**
  - Capture medical QR code from laptop
  - Use Gemma 4 (Gemini API) to parse patient data
  - Dynamically enable agents (for example Medication Monitor, Fall Guardian) using gemma 4

- **Orchestrator (PC backend)**
  - FastAPI/Node.js backend
  - Aggregate dual camera streams
  - Monitor IMU data via UDP/WebSockets
  - IR data from sensor
  - Use Gemma 4 for vision-to-logic reasoning
  - Maintain a reasoning log for every action

- **Frontend (React + Tailwind)**
  - Patient profile
  - Dual-camera view (Glasses + Glove)
  - Agent status toggles
  - Live LLM "thinking" feed
  - Critical-events gallery (saved clips from IMU/vision triggers)

## Implementation Requirements
- **Embedded C++**
  - ESP32-CAM firmware
  - TFT via `TFT_eSPI`
  - Avoid GPIO conflicts among camera, SPI display, and I2C IMU

- **Python Backend**
  - FastAPI stream relay
  - Gemma 4 API integration
  - System prompt must enforce strict JSON output for agent selection

- **Trigger Logic**
  - Video buffering on PC
  - Save 10 seconds before and 10 seconds after IMU fall event

- **UI**
  - Dashboard React components
  - WebSocket integration for live reasoning/thinking log

## Technical Reminders
- ESP32-CAM camera consumes many pins; likely peripheral pins include GPIO 14, 13, 15, and 2.
- Prompting must keep step-by-step reasoning output so the GUI "Thinking" box remains populated.
- Use stable 5V power on the glove node to avoid ESP32 brownouts when camera + Wi-Fi are active.

## Working Expectations
When suggesting or generating code:
- Preserve this architecture and data flow
- Keep outputs structured and machine-parseable where requested (especially agent-selection JSON)
- Prioritize reliability for real-time streaming, fall detection, and event recording







