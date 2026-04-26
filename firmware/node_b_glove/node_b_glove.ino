#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>

// TFT_eSPI — must appear before #include <TFT_eSPI.h>.
// Pins for ESP32-S3 wiring: CS=20, RST=19, A0/DC=2, SDA/MOSI=42, SCK=41.
#define USER_SETUP_LOADED 1
#define ST7735_DRIVER
#define TFT_WIDTH 128
#define TFT_HEIGHT 128
#define TFT_MOSI 42
#define TFT_SCLK 41
#define TFT_CS 20
#define TFT_DC 2
#define TFT_RST 19
#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF
#define SPI_FREQUENCY 20000000
#define SPI_READ_FREQUENCY 20000000

#include <TFT_eSPI.h>
#include "esp_http_server.h"

// WLAN + orchestrator endpoint
const char* WIFI_SSID = "Spheal";
const char* WIFI_PASSWORD = "amonguss";
const char* ORCHESTRATOR_IP = "192.168.1.10";
const uint16_t ORCHESTRATOR_UDP_PORT = 9002;

// MPU-6050 (TFT SPI uses 41/42 — keep I2C off those lines)
constexpr uint8_t MPU_ADDR = 0x68;
constexpr int I2C_SDA = 1;
constexpr int I2C_SCL = 3;

// IR Sensor
constexpr int IR_PIN = 33;

// Passive buzzer (driven by LEDC PWM)
constexpr int BUZZER_PIN = 12;
constexpr uint32_t BUZZER_PWM_RES_BITS = 8;
constexpr uint32_t BUZZER_PWM_DUTY = 128;  // 50% of 8-bit range

// Fall detection threshold
constexpr float FALL_THRESHOLD_G = 2.4f;

TFT_eSPI tft = TFT_eSPI();
WiFiUDP udp;
static httpd_handle_t stream_httpd = NULL;

static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
static const char* STREAM_BOUNDARY = "\r\n--frame\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

float ax = 0.0f;
float ay = 0.0f;
float az = 1.0f;
float magnitude = 1.0f;
bool irTriggered = false;
bool fallDetected = false;
unsigned long lastUdpMs = 0;
unsigned long lastScreenMs = 0;
unsigned long lastIrBuzzMs = 0;
constexpr unsigned long IR_BUZZ_COOLDOWN_MS = 300;

static camera_config_t camera_config_init() {
  // NOTE: pins below are the AI-Thinker ESP32-CAM mapping. They CONFLICT with
  // the new TFT pin map (TFT RST=19 collides with cam D2=19). Replace this
  // block with the camera pinout for whatever ESP32-S3 board is being used
  // before flashing (e.g. Freenove ESP32-S3-CAM, XIAO Sense, etc.).
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 5;
  config.pin_d1 = 18;
  config.pin_d2 = 19;
  config.pin_d3 = 21;
  config.pin_d4 = 36;
  config.pin_d5 = 39;
  config.pin_d6 = 34;
  config.pin_d7 = 35;
  config.pin_xclk = 0;
  config.pin_pclk = 22;
  config.pin_vsync = 25;
  config.pin_href = 23;
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
  config.pin_pwdn = 32;
  config.pin_reset = -1;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 14;
  config.fb_count = 2;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;
  return config;
}

static esp_err_t stream_handler(httpd_req_t* req) {
  char buf[64];
  esp_err_t res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) {
    return res;
  }

  while (true) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      return ESP_FAIL;
    }

    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) {
      size_t hlen = snprintf(buf, sizeof(buf), STREAM_PART, fb->len);
      res = httpd_resp_send_chunk(req, buf, hlen);
    }
    if (res == ESP_OK) {
      res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
    }
    esp_camera_fb_return(fb);
    if (res != ESP_OK) {
      break;
    }
  }
  return res;
}

static esp_err_t buzz_handler(httpd_req_t* req) {
  char query[64] = {0};
  uint16_t freq = 1100;
  uint16_t dur = 500;

  if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK) {
    char val[16];
    if (httpd_query_key_value(query, "freq", val, sizeof(val)) == ESP_OK) {
      freq = (uint16_t)atoi(val);
    }
    if (httpd_query_key_value(query, "dur", val, sizeof(val)) == ESP_OK) {
      dur = (uint16_t)atoi(val);
    }
  }

  beepAlert(freq, dur);

  httpd_resp_set_type(req, "application/json");
  const char* resp_body = "{\"ok\":true}";
  httpd_resp_send(req, resp_body, strlen(resp_body));
  return ESP_OK;
}

static void start_camera_server() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.max_uri_handlers = 8;

  httpd_uri_t stream_uri = {
    .uri = "/stream",
    .method = HTTP_GET,
    .handler = stream_handler,
    .user_ctx = NULL
  };

  httpd_uri_t buzz_uri = {
    .uri = "/buzz",
    .method = HTTP_GET,
    .handler = buzz_handler,
    .user_ctx = NULL
  };

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
    httpd_register_uri_handler(stream_httpd, &buzz_uri);
  }
}

void initMpu() {
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  // PWR_MGMT_1
  Wire.write(0x00);  // Wake up
  Wire.endTransmission();
}

void readMpuAccel() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom((int)MPU_ADDR, 6, true);

  int16_t rawAx = (Wire.read() << 8) | Wire.read();
  int16_t rawAy = (Wire.read() << 8) | Wire.read();
  int16_t rawAz = (Wire.read() << 8) | Wire.read();

  ax = rawAx / 16384.0f;
  ay = rawAy / 16384.0f;
  az = rawAz / 16384.0f;
  magnitude = sqrtf((ax * ax) + (ay * ay) + (az * az));
}

void initBuzzer() {
  // Arduino-ESP32 v3.x LEDC API: ledcAttach(pin, freq, resolution_bits).
  ledcAttach(BUZZER_PIN, 2000, BUZZER_PWM_RES_BITS);
  ledcWrite(BUZZER_PIN, 0);
}

void beepAlert(uint16_t freqHz, uint16_t durationMs) {
  if (freqHz == 0 || durationMs == 0) {
    return;
  }
  ledcWriteTone(BUZZER_PIN, freqHz);
  ledcWrite(BUZZER_PIN, BUZZER_PWM_DUTY);
  delay(durationMs);
  ledcWriteTone(BUZZER_PIN, 0);
  ledcWrite(BUZZER_PIN, 0);
}

void updateScreen() {
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setCursor(2, 4, 2);
  tft.println("Node B: Glove");
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.println(WiFi.localIP());
  tft.printf("X: %.2f\nY: %.2f\nZ: %.2f\n", ax, ay, az);
  tft.printf("|g|: %.2f\n", magnitude);
  tft.printf("IR: %s\n", irTriggered ? "TRIG" : "OK");
  tft.setTextColor(fallDetected ? TFT_RED : TFT_GREEN, TFT_BLACK);
  tft.printf("Fall: %s\n", fallDetected ? "YES" : "NO");
}

void sendUdpPacket() {
  char payload[192];
  unsigned long now = millis();
  snprintf(
    payload,
    sizeof(payload),
    "{\"x\":%.3f,\"y\":%.3f,\"z\":%.3f,\"ir_triggered\":%s,\"timestamp\":%.3f}",
    ax,
    ay,
    az,
    irTriggered ? "true" : "false",
    now / 1000.0f
  );

  udp.beginPacket(ORCHESTRATOR_IP, ORCHESTRATOR_UDP_PORT);
  udp.write((const uint8_t*)payload, strlen(payload));
  udp.endPacket();
}

void setup() {
  // With SDA/SCL on GPIO 1/3, avoid regular serial logging after init.
  pinMode(IR_PIN, INPUT);
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setCursor(2, 2, 2);
  tft.println("Booting...");

  initMpu();
  initBuzzer();

  camera_config_t cam_cfg = camera_config_init();
  esp_err_t err = esp_camera_init(&cam_cfg);
  if (err != ESP_OK) {
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.println("Camera init fail");
    while (true) {
      delay(1000);
    }
  }

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
  }
  udp.begin(ORCHESTRATOR_UDP_PORT);

  start_camera_server();
  updateScreen();
}

void loop() {
  readMpuAccel();
  irTriggered = digitalRead(IR_PIN) == HIGH;
  fallDetected = magnitude >= FALL_THRESHOLD_G;

  unsigned long now = millis();
  if (fallDetected) {
    beepAlert(1100, 160);
  } else if (irTriggered && (now - lastIrBuzzMs) >= IR_BUZZ_COOLDOWN_MS) {
    lastIrBuzzMs = now;
    beepAlert(1500, 80);
  }

  if (now - lastUdpMs >= 100) {
    lastUdpMs = now;
    sendUdpPacket();
  }

  if (now - lastScreenMs >= 250) {
    lastScreenMs = now;
    updateScreen();
  }
}
