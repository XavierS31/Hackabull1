The Master Project Prompt
Context: I am building a medical "Agentic AI" assistance system for patients (e.g., dementia/fall risk) using a PC as a central orchestrator and two ESP32-CAM nodes.

Hardware Configuration:

Node A (Glasses): ESP32-CAM with OV2640. Purpose: FPV Vision for obstacle/object detection. Protocol: MJPEG stream over HTTP/WebSockets.

Node B (Glove): ESP32-CAM (OV2640) + MPU-6050 (IMU) + IR Sensor + Speaker (MAX98357A I2S) + 1.44" SPI TFT Screen. Purpose: Fall detection (XYZ), interaction (Speaker/Screen), and close-up vision (QR scanning).

Software Architecture:

Pipeline 1 (Onboarding): Capture a medical QR code (image provided). Use Gemma 4 (via Gemini API) to parse patient data and dynamically activate specific "Agents" (e.g., Medication Monitor, Fall Guardian).

Orchestrator (PC): A Python FastAPI/Node.js backend that:

Aggregates two simultaneous camera streams.

Monitors IMU data via UDP/WebSockets.

Orchestrates "Gemma 4" for vision-to-logic reasoning.

Maintains a "Reasoning Log" (Thinking Process) for every action taken.

GUI (Frontend): A React/Tailwind dashboard showing:

Full-stack Patient Profile.

Dual-camera view (Glasses + Glove).

Real-time "Agent Status" toggles.

Live "Thinking" feed from the LLM.

A "Critical Events" gallery for saved videos triggered by IMU/Vision events.

Task Requirements:

Embedded C++: Provide the ESP32-CAM code using TFT_eSPI for the screen and ESP32-CAM libraries, ensuring no GPIO conflicts between the SPI screen, I2C IMU, and Camera (Handling the shared GPIO pins on the AI-Thinker board).

Python Backend: Provide the FastAPI logic for the stream relay and the Gemma 4 API integration, including a system prompt that enforces JSON outputs for agent selection.

Trigger Logic: Implement a buffer system where the PC saves 10 seconds of video before and after the IMU detects a "Fall" event.

UI: Provide the React components for the dashboard layout and the WebSocket integration for the live "Thinking" log.

Key Technical Reminders for the Setup
GPIO Pin-Mapping: On the ESP32-CAM, remember that the camera uses almost everything. You'll likely need to use GPIO 14, 13, 15, and 2 for the SPI/I2C peripherals.

The "Thinking" Prompt: Ensure the model is instructed to output its reasoning step-by-step so your GUI's "Thinking" box stays populated.

Power: Ensure the Glove is powered via a 5V rail to prevent the ESP32 from crashing when the Camera and WiFi transmit simultaneously.