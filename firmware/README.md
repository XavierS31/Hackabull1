# Firmware Setup

This project uses two AI-Thinker ESP32-CAM boards.

## Node A: Glasses (FPV stream)
- Purpose: obstacle/object vision feed.
- Output: MJPEG stream on `http://<ip>:81/stream`.

## Node B: Glove (fall + interaction)
- Purpose: IMU/IR fall telemetry, close-up camera feed, screen/speaker interaction.
- Output:
  - MJPEG stream on `http://<ip>:81/stream`
  - UDP IMU packets to PC orchestrator

## Pin Mapping (Node B)

The AI-Thinker camera pins are fixed and already consumed by the OV2640:
`GPIO 0,5,18,19,21,22,23,25,26,27,32,34,35,36,39`

Peripheral mapping below avoids those camera pins:

| Peripheral | Signal | GPIO |
|---|---|---|
| TFT (SPI) | SCK | 14 |
| TFT (SPI) | MOSI | 13 |
| TFT (SPI) | CS | 15 |
| TFT (SPI) | DC | 2 |
| TFT (SPI) | RST | tied to 3V3 or EN |
| MPU-6050 (I2C) | SDA | 1 |
| MPU-6050 (I2C) | SCL | 3 |
| IR Sensor | DO | 33 |
| MAX98357A (I2S) | BCLK | 4 |
| MAX98357A (I2S) | LRC/WS | 16 |
| MAX98357A (I2S) | DIN | 12 |

Notes:
- `GPIO 1/3` are serial pins; once I2C is connected there, USB serial logging must be minimized or disabled.
- `GPIO 2`, `GPIO 12`, and `GPIO 15` are boot strap pins; wiring must preserve valid boot levels.
- Use a stable 5V rail for Node B. Camera + WiFi spikes can brown out weak supplies.
