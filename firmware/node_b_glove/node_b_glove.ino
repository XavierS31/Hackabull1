#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <TFT_eSPI.h>
#include "esp_http_server.h"
#include "driver/i2s.h"

// WLAN + orchestrator endpoint
const char* WIFI_SSID = "YOUR_SSID";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
const char* ORCHESTRATOR_IP = "192.168.1.10";
const uint16_t ORCHESTRATOR_UDP_PORT = 9002;

// MPU-6050
constexpr uint8_t MPU_ADDR = 0x68;
constexpr int I2C_SDA = 1;
constexpr int I2C_SCL = 3;

// IR Sensor
constexpr int IR_PIN = 33;

// I2S (MAX98357A)
constexpr int I2S_BCLK = 4;
constexpr int I2S_LRC = 16;
constexpr int I2S_DOUT = 12;
constexpr int I2S_PORT = I2S_NUM_0;

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

static camera_config_t camera_config_init() {
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

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
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

void initI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_MSB,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_BCLK,
    .ws_io_num = I2S_LRC,
    .data_out_num = I2S_DOUT,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  i2s_driver_install((i2s_port_t)I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin((i2s_port_t)I2S_PORT, &pin_config);
}

void beepAlert(uint16_t freqHz, uint16_t durationMs) {
  const int sampleRate = 16000;
  const int totalSamples = (sampleRate * durationMs) / 1000;
  const float step = 2.0f * 3.1415926f * freqHz / sampleRate;
  size_t bytesWritten = 0;
  for (int i = 0; i < totalSamples; i++) {
    int16_t sample = (int16_t)(sinf(i * step) * 6000.0f);
    i2s_write((i2s_port_t)I2S_PORT, &sample, sizeof(sample), &bytesWritten, portMAX_DELAY);
  }
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
  initI2S();

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
