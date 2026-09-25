// ---------------------------------------------------------------------------
// LeafNode - autonomous leaf capture node (AI-Thinker ESP32-CAM)
//
// Loop, once every CAPTURE_INTERVAL_S:
//   1. wake the camera, grab a JPEG
//   2. read the optional soil / air sensors
//   3. POST image + sensor JSON to the Raspberry Pi
//   4. read the risk score the Pi sends back and blink it out on the red LED
//
// In between, it answers the Pi's POST /capture with a fresh JPEG, which is
// how "take a photo now" in the app reaches the camera.
//
// The Pi does all the thinking. This board never sees the model.
// ---------------------------------------------------------------------------

#include "config.h"

#include <WiFi.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "esp_sleep.h"

#define FIRMWARE_VERSION "1.1.0"

#if ENABLE_CAPTURE_SERVER && USE_DEEP_SLEEP
  #warning "USE_DEEP_SLEEP is on, so the node sleeps between captures and cannot take a photo on request"
#endif

#if ENABLE_DHT
  #include <DHT.h>
  DHT dht(DHT_PIN, DHT_TYPE);
#endif

#if ENABLE_ADS1115
  #include <Wire.h>
  #include <Adafruit_ADS1X15.h>
  Adafruit_ADS1115 ads;
#endif

// --- AI-Thinker ESP32-CAM pin map ------------------------------------------
// Do not change these unless you are on a different board. GPIO0 is the camera
// clock AND the bootloader strap pin, which is why flashing needs it grounded.
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#define LED_STATUS_PIN    33   // onboard red LED, active LOW
#define LED_FLASH_PIN      4   // onboard white flash LED, active HIGH

// ---------------------------------------------------------------------------
// Status LED. The red LED on the back of the board is the only feedback you
// get once the USB adapter is unplugged, so it carries the whole state machine.
// ---------------------------------------------------------------------------
void ledOn()  { digitalWrite(LED_STATUS_PIN, LOW);  }
void ledOff() { digitalWrite(LED_STATUS_PIN, HIGH); }

void blink(int times, int onMs, int offMs) {
  for (int i = 0; i < times; i++) {
    ledOn();  delay(onMs);
    ledOff(); delay(offMs);
  }
}

// One long blink per risk band, so you can read the result across the room.
void signalRisk(const char* riskLevel) {
  if      (strcmp(riskLevel, "low")      == 0) blink(1, 400, 200);
  else if (strcmp(riskLevel, "medium")   == 0) blink(2, 400, 200);
  else if (strcmp(riskLevel, "high")     == 0) blink(3, 400, 200);
  else if (strcmp(riskLevel, "critical") == 0) blink(6, 120, 120);
  else                                         blink(1, 60, 60);
}

// ---------------------------------------------------------------------------
// Camera
// ---------------------------------------------------------------------------
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode    = CAMERA_GRAB_LATEST;
  config.fb_location  = CAMERA_FB_IN_PSRAM;

  if (psramFound()) {
    config.frame_size   = CAMERA_FRAMESIZE;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;
    config.fb_count     = 2;
  } else {
    // No PSRAM means no room for a large frame. Should not happen on a real
    // AI-Thinker board; if you land here the PSRAM chip or its solder is bad.
    Serial.println("[cam] WARNING: no PSRAM found, falling back to a small buffer");
    config.frame_size   = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count     = 1;
    config.fb_location  = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[cam] init failed: 0x%x\n", err);
    return false;
  }

  sensor_t* s = esp_camera_sensor_get();
  if (s) {
    // Leaves are close, static and usually under mixed light. Slightly raised
    // saturation keeps the chlorosis and necrosis colours separable downstream.
    s->set_saturation(s, 1);
    s->set_brightness(s, 0);
    s->set_contrast(s, 1);
    s->set_whitebal(s, 1);
    s->set_gain_ctrl(s, 1);
    s->set_exposure_ctrl(s, 1);
  }
  return true;
}

// The first frame after power-up is usually green or washed out while the
// sensor settles its exposure. Throw a few away before the one that counts.
camera_fb_t* captureSettledFrame() {
#if USE_FLASH_LED
  digitalWrite(LED_FLASH_PIN, HIGH);
  delay(120);
#endif

  for (int i = 0; i < 3; i++) {
    camera_fb_t* warmup = esp_camera_fb_get();
    if (warmup) esp_camera_fb_return(warmup);
    delay(80);
  }
  camera_fb_t* fb = esp_camera_fb_get();

#if USE_FLASH_LED
  digitalWrite(LED_FLASH_PIN, LOW);
#endif
  return fb;
}

// ---------------------------------------------------------------------------
// Sensors. Both are optional; when disabled the Pi just gets no sensor block
// and falls back to whatever default its pipeline uses.
// ---------------------------------------------------------------------------
String readSensorsJson() {
  JsonDocument doc;
  bool any = false;

#if ENABLE_DHT
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t) && !isnan(h)) {
    doc["temperature"] = t;
    doc["humidity"]    = h;
    any = true;
  } else {
    Serial.println("[dht] read failed");
  }
#endif

#if ENABLE_ADS1115
  int16_t raw = ads.readADC_SingleEnded(0);
  // Capacitive probes read HIGH when dry, so the mapping is inverted.
  float pct = 100.0f * (float)(SOIL_RAW_DRY - raw) / (float)(SOIL_RAW_DRY - SOIL_RAW_WET);
  if (pct < 0)   pct = 0;
  if (pct > 100) pct = 100;
  doc["soil_moisture"] = pct;
  doc["soil_raw"]      = raw;
  any = true;
#endif

  if (!any) return String("");
  String out;
  serializeJson(doc, out);
  return out;
}

// ---------------------------------------------------------------------------
// Wi-Fi
// ---------------------------------------------------------------------------
bool connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);          // sleep here costs more in retries than it saves
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("[wifi] connecting");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > WIFI_CONNECT_TIMEOUT_MS) {
      Serial.println(" timed out");
      return false;
    }
    delay(400);
    Serial.print(".");
  }
  Serial.printf(" ok, ip=%s rssi=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
  return true;
}

// ---------------------------------------------------------------------------
// Finding the Pi. Asked by name every cycle, so the node follows the Pi to a
// new address; the last answer (or PI_HOST) is kept when mDNS is silent.
// ---------------------------------------------------------------------------
String piHost = PI_HOST;

// Also announces this board as DEVICE_ID.local, which is the Pi's fallback
// for finding it when it has not posted a frame since the Pi restarted.
bool startMdns() {
  static bool mdnsUp = false;
  if (mdnsUp || WiFi.status() != WL_CONNECTED) return mdnsUp;
  mdnsUp = MDNS.begin(DEVICE_ID);
  if (mdnsUp) {
#if ENABLE_CAPTURE_SERVER && !USE_DEEP_SLEEP
    MDNS.addService("http", "tcp", CAPTURE_SERVER_PORT);
#endif
    Serial.printf("[mdns] this node is %s.local\n", DEVICE_ID);
  }
  return mdnsUp;
}

void resolvePi() {
  if (strlen(PI_MDNS_NAME) == 0) return;
  if (!startMdns()) return;

  IPAddress ip = MDNS.queryHost(PI_MDNS_NAME, 2000);
  if (ip != IPAddress(0, 0, 0, 0)) {
    if (piHost != ip.toString()) {
      piHost = ip.toString();
      Serial.printf("[mdns] %s.local is %s\n", PI_MDNS_NAME, piHost.c_str());
    }
  } else {
    Serial.printf("[mdns] %s.local did not answer, using %s\n", PI_MDNS_NAME, piHost.c_str());
  }
}

// ---------------------------------------------------------------------------
// Upload. Builds one multipart/form-data body in PSRAM and hands it to
// HTTPClient, which is far more reliable than hand-rolling the socket writes.
// ---------------------------------------------------------------------------
bool uploadFrame(camera_fb_t* fb, const String& sensorJson) {
  const String boundary = "----leafnode7a3f";

  String head = "--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"image\"; filename=\"leaf.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";

  String tail = "\r\n--" + boundary + "\r\n"
                "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n" + String(DEVICE_ID);

  if (sensorJson.length() > 0) {
    tail += "\r\n--" + boundary + "\r\n"
            "Content-Disposition: form-data; name=\"sensor\"\r\n\r\n" + sensorJson;
  }
  tail += "\r\n--" + boundary + "--\r\n";

  size_t total = head.length() + fb->len + tail.length();

  uint8_t* body = (uint8_t*) (psramFound() ? ps_malloc(total) : malloc(total));
  if (!body) {
    Serial.printf("[http] could not allocate a %u byte body\n", (unsigned)total);
    return false;
  }

  size_t off = 0;
  memcpy(body + off, head.c_str(), head.length());  off += head.length();
  memcpy(body + off, fb->buf, fb->len);             off += fb->len;
  memcpy(body + off, tail.c_str(), tail.length());  off += tail.length();

  String url = "http://" + piHost + ":" + String(PI_PORT) + PI_ANALYZE_PATH;

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.setConnectTimeout(HTTP_TIMEOUT_MS);
  http.begin(url);
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  http.addHeader("X-Node-Key", NODE_KEY);

  Serial.printf("[http] POST %s  (%u bytes)\n", url.c_str(), (unsigned)total);
  unsigned long t0 = millis();
  int code = http.POST(body, total);
  unsigned long elapsed = millis() - t0;

  bool ok = false;
  if (code == 200) {
    String payload = http.getString();
    Serial.printf("[http] 200 in %lu ms: %s\n", elapsed, payload.c_str());

    JsonDocument res;
    DeserializationError err = deserializeJson(res, payload);
    if (err) {
      Serial.printf("[http] response was not JSON: %s\n", err.c_str());
    } else {
      float score       = res["risk_score"] | -1.0f;
      const char* level = res["risk_level"] | "unknown";
      const char* label = res["label"]      | "";
      Serial.printf("[risk] score=%.1f level=%s label=%s\n", score, level, label);
      signalRisk(level);
      ok = true;
    }
  } else if (code > 0) {
    Serial.printf("[http] server said %d: %s\n", code, http.getString().c_str());
  } else {
    Serial.printf("[http] transport error: %s\n", http.errorToString(code).c_str());
  }

  http.end();
  free(body);
  return ok;
}

// ---------------------------------------------------------------------------
// Photo on request. The Pi calls POST /capture when the farmer taps "take a
// photo now". The answer is the JPEG itself, with the sensor readings in a
// header; the Pi scores it and sends it upstream like a scheduled frame.
// ---------------------------------------------------------------------------
#define CAPTURE_SERVER_ON (ENABLE_CAPTURE_SERVER && !USE_DEEP_SLEEP)

unsigned long nextCaptureAt = 0;

#if CAPTURE_SERVER_ON
WebServer web(CAPTURE_SERVER_PORT);
uint32_t photosOnRequest = 0;

// The same key the Pi checks on /analyze. Every byte is compared whatever
// the length, so the time taken says nothing about how close a guess was.
bool keyMatches(const String& given) {
  const char* want = NODE_KEY;
  size_t wantLen = strlen(want);
  if (wantLen == 0) return false;
  uint8_t diff = given.length() == wantLen ? 0 : 1;
  for (size_t i = 0; i < given.length(); i++) {
    diff |= (uint8_t)given[i] ^ (uint8_t)want[i % wantLen];
  }
  return diff == 0;
}

void handleCapture() {
  if (!keyMatches(web.header("X-Node-Key"))) {
    Serial.printf("[web] refused /capture from %s: bad node key\n",
                  web.client().remoteIP().toString().c_str());
    web.send(401, "application/json", "{\"detail\":\"bad node key\"}");
    return;
  }

  ledOn();
  camera_fb_t* fb = captureSettledFrame();
  if (!fb) {
    ledOff();
    Serial.println("[web] photo on request: camera gave no frame");
    web.send(503, "application/json", "{\"detail\":\"camera_failed\"}");
    return;
  }

  String sensorJson = readSensorsJson();
  web.sendHeader("X-Device-Id", DEVICE_ID);
  if (sensorJson.length()) web.sendHeader("X-Sensors", sensorJson);
  web.sendHeader("Cache-Control", "no-store");
  web.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  Serial.printf("[web] photo on request: %u bytes, %ux%u\n",
                (unsigned)fb->len, fb->width, fb->height);

  esp_camera_fb_return(fb);
  ledOff();
  photosOnRequest++;
}

void handleStatus() {
  JsonDocument doc;
  doc["device_id"]         = DEVICE_ID;
  doc["firmware"]          = FIRMWARE_VERSION;
  doc["uptime_s"]          = millis() / 1000;
  doc["rssi"]              = WiFi.RSSI();
  long wait = (long)(nextCaptureAt - millis()) / 1000;
  doc["next_capture_s"]    = wait > 0 ? wait : 0;
  doc["photos_on_request"] = photosOnRequest;
  doc["free_heap"]         = ESP.getFreeHeap();
  String out;
  serializeJson(doc, out);
  web.send(200, "application/json", out);
}

void startWebServer() {
  static const char* headerKeys[] = {"X-Node-Key"};
  web.collectHeaders(headerKeys, 1);
  web.on("/capture", HTTP_POST, handleCapture);
  web.on("/status", HTTP_GET, handleStatus);
  web.onNotFound([]() { web.send(404, "application/json", "{\"detail\":\"not found\"}"); });
  web.begin();
  Serial.printf("[web] listening on port %d for photos on request\n", CAPTURE_SERVER_PORT);
}
#endif

// Waits for the next scheduled capture while answering the Pi. Also brings
// Wi-Fi back if it dropped, so the node can be reached between shots and not
// only once it next has a frame of its own to send.
void waitForNextCapture() {
  nextCaptureAt = millis() + (unsigned long)CAPTURE_INTERVAL_S * 1000UL;
  unsigned long lastWifiTry = millis();
  while ((long)(nextCaptureAt - millis()) > 0) {
#if CAPTURE_SERVER_ON
    web.handleClient();
#endif
    if (WiFi.status() != WL_CONNECTED && millis() - lastWifiTry > 30000UL) {
      lastWifiTry = millis();
      Serial.println("[wifi] link lost, reconnecting");
      WiFi.reconnect();
    }
    delay(5);
  }
}

// ---------------------------------------------------------------------------
// One full cycle.
// ---------------------------------------------------------------------------
void runCaptureCycle() {
  ledOn();   // LED stays on for the whole working phase

  camera_fb_t* fb = captureSettledFrame();
  if (!fb) {
    Serial.println("[cam] capture failed");
    ledOff();
    blink(5, 80, 80);   // fast flutter = camera fault
    return;
  }
  Serial.printf("[cam] captured %u bytes, %ux%u\n",
                (unsigned)fb->len, fb->width, fb->height);

  String sensorJson = readSensorsJson();
  if (sensorJson.length()) Serial.printf("[sensors] %s\n", sensorJson.c_str());

  bool sent = false;
  if (connectWifi()) {
    resolvePi();
    for (int attempt = 1; attempt <= MAX_UPLOAD_RETRIES && !sent; attempt++) {
      if (attempt > 1) {
        Serial.printf("[http] retry %d of %d\n", attempt, MAX_UPLOAD_RETRIES);
        delay(1500L * attempt);
      }
      sent = uploadFrame(fb, sensorJson);
    }
  }

  esp_camera_fb_return(fb);   // always give the buffer back, success or not
  ledOff();

  if (!sent) {
    Serial.println("[http] giving up on this frame");
    blink(2, 80, 400);        // two slow winks = could not reach the Pi
  }
}

// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n[boot] LeafNode " DEVICE_ID);

  pinMode(LED_STATUS_PIN, OUTPUT);
  ledOff();
#if USE_FLASH_LED
  pinMode(LED_FLASH_PIN, OUTPUT);
  digitalWrite(LED_FLASH_PIN, LOW);
#endif

  if (!initCamera()) {
    // Nothing useful left to do. Blink forever so the fault is visible.
    while (true) blink(5, 80, 80);
  }

#if ENABLE_DHT
  dht.begin();
#endif
#if ENABLE_ADS1115
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  if (!ads.begin()) Serial.println("[ads] not found on I2C, check wiring");
#endif

  connectWifi();
  startMdns();
#if CAPTURE_SERVER_ON
  startWebServer();
#endif

#if USE_DEEP_SLEEP
  // In deep sleep mode setup() IS the loop: do one cycle, then sleep. The chip
  // reboots into setup() again when the timer fires.
  runCaptureCycle();
  Serial.printf("[sleep] deep sleeping %d s\n", CAPTURE_INTERVAL_S);
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)CAPTURE_INTERVAL_S * 1000000ULL);
  esp_deep_sleep_start();
#endif
}

void loop() {
#if !USE_DEEP_SLEEP
  runCaptureCycle();
  waitForNextCapture();
#endif
}
