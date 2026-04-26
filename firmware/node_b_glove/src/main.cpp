#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <TFT_eSPI.h>

// TFT_eSPI is configured via build_flags in platformio.ini.
// (USER_SETUP_LOADED=1 + ST7735_DRIVER, TFT_MOSI=23, TFT_SCLK=18,
//  TFT_CS=5, TFT_DC=27, TFT_RST=4, SPI_FREQUENCY=27000000).

// --- Pin Definitions ---
#define BUZZER_PIN 12
#define IR_PIN     13
const uint8_t MPU_ADDR = 0x68;

// --- Network Config ---
const char *WIFI_SSID = "Spheal";
const char *WIFI_PASSWORD = "amonguss";
const char *ORCHESTRATOR_IP = "172.20.10.7";
const uint16_t ORCHESTRATOR_UDP_PORT = 9002;
constexpr unsigned long WIFI_CONNECT_TIMEOUT_MS = 10000;

// --- Variables ---
TFT_eSPI tft = TFT_eSPI();
WiFiUDP udp;
float ax = 0, ay = 0, az = 0, magnitude = 0;
bool irTriggered = false;
bool fallDetected = false;
bool mpu_ok = false;
bool wifi_ok = false;
unsigned long lastSerialMs = 0;
unsigned long lastScreenMs = 0;
unsigned long lastFallBeepMs = 0;
constexpr float FALL_THRESHOLD_G = 2.4f;
constexpr unsigned long TX_INTERVAL_MS = 100;  // 10 Hz

void initMpu() {
  Wire.begin(21, 22);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0x00);
  mpu_ok = (Wire.endTransmission() == 0);
}

void readMpuAccel() {
  if (!mpu_ok) return;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (size_t)6, true);

  int16_t rawAx = (Wire.read() << 8) | Wire.read();
  int16_t rawAy = (Wire.read() << 8) | Wire.read();
  int16_t rawAz = (Wire.read() << 8) | Wire.read();

  ax = rawAx / 16384.0f;
  ay = rawAy / 16384.0f;
  az = rawAz / 16384.0f;
  magnitude = sqrtf((ax * ax) + (ay * ay) + (az * az));
}

void beepAlert() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(80);
  digitalWrite(BUZZER_PIN, LOW);
}

void updateScreen() {
  tft.fillScreen(TFT_BLACK);
  tft.setCursor(0, 0, 2);
  tft.setTextColor(TFT_GREEN);
  tft.println("ESP32 Monitor");
  tft.setTextColor(TFT_WHITE);
  tft.printf("WiFi:%s\n", wifi_ok ? WiFi.localIP().toString().c_str() : "OFFLINE");
  tft.printf("MPU: %s\n", mpu_ok ? "OK" : "ERR");
  tft.printf("G: %.2f\n", magnitude);
  tft.printf("IR: %s\n", irTriggered ? "DETECT" : "CLEAR");
  if (fallDetected) {
    tft.setTextColor(TFT_RED);
    tft.println("FALL DETECTED!");
  }
}

size_t buildPayload(char *buf, size_t bufsz) {
  return snprintf(
      buf, bufsz,
      "{\"x\":%.3f,\"y\":%.3f,\"z\":%.3f,\"ir_triggered\":%s}",
      ax, ay, az, irTriggered ? "true" : "false");
}

void sendUdpPacket(const char *payload, size_t len) {
  if (!wifi_ok || WiFi.status() != WL_CONNECTED) return;
  udp.beginPacket(ORCHESTRATOR_IP, ORCHESTRATOR_UDP_PORT);
  udp.write(reinterpret_cast<const uint8_t *>(payload), len);
  udp.endPacket();
}

void setup() {
  Serial.begin(115200);
  pinMode(IR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.println("Connecting WiFi...");

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    Serial.print(".");
  }
  wifi_ok = (WiFi.status() == WL_CONNECTED);
  Serial.println();
  if (wifi_ok) {
    udp.begin(0);
    Serial.print("WiFi connected, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi failed -- continuing in serial-only mode.");
  }

  initMpu();
  updateScreen();
}

void loop() {
  readMpuAccel();
  irTriggered = digitalRead(IR_PIN) == HIGH;
  fallDetected = magnitude >= FALL_THRESHOLD_G;

  unsigned long now = millis();

  if (now - lastSerialMs >= TX_INTERVAL_MS) {
    lastSerialMs = now;
    char payload[160];
    size_t len = buildPayload(payload, sizeof(payload));
    if (len > 0) {
      Serial.println(payload);
      sendUdpPacket(payload, len);
    }
  }

  if (fallDetected && (now - lastFallBeepMs >= 2000)) {
    lastFallBeepMs = now;
    beepAlert();
  }

  if (now - lastScreenMs >= 500) {
    lastScreenMs = now;
    updateScreen();
  }
}
