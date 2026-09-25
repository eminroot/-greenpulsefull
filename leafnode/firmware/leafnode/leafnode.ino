// ---------------------------------------------------------------------------
// LeafNode - autonomous leaf capture node (AI-Thinker ESP32-CAM)
//
// Loop, once every CAPTURE_INTERVAL_S:
//   1. wake the camera, grab a JPEG
//   2. read the optional soil / air sensors
//   3. POST image + sensor JSON to the Raspberry Pi
//   4. read the risk score the Pi sends back and blink it out on the red LED
//
// In between, it answers the Pi: POST /capture with a fresh JPEG, which is
// how "take a photo now" in the app reaches the camera, and a few settings
// the Pi can change over Wi-Fi (extra networks, the photo interval, a new
// firmware). So a phone hotspot for a demo is added from the Pi, no reflash.
//
// The Pi does all the thinking. This board never sees the model.
// ---------------------------------------------------------------------------

#include "config.h"

#include <WiFi.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <WiFiMulti.h>
#include <Preferences.h>
#include <Update.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "esp_sleep.h"

#define FIRMWARE_VERSION "1.2.0"

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
// `discard` is how many: 3 for a scheduled shot, 1 when someone is waiting.
camera_fb_t* captureSettledFrame(int discard) {
#if USE_FLASH_LED
  digitalWrite(LED_FLASH_PIN, HIGH);
  delay(120);
#endif

  for (int i = 0; i < discard; i++) {
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
// Settings kept in flash (NVS), so the Pi can change them over Wi-Fi without
// a rebuild: extra Wi-Fi networks (a phone hotspot for a demo, say) and how
// often to take a photo. The network in secrets.h is always tried as well, so
// a mistake here can never lock the board out of its home Wi-Fi.
// ---------------------------------------------------------------------------
#define MAX_SAVED_NETWORKS 5

struct SavedNetwork { String ssid; String pass; };
SavedNetwork savedNetworks[MAX_SAVED_NETWORKS];
int savedCount = 0;
uint32_t captureIntervalS = CAPTURE_INTERVAL_S;

Preferences prefs;

void loadSettings() {
  prefs.begin("leafnode", true);
  savedCount = prefs.getInt("n", 0);
  if (savedCount < 0 || savedCount > MAX_SAVED_NETWORKS) savedCount = 0;
  for (int i = 0; i < savedCount; i++) {
    savedNetworks[i].ssid = prefs.getString(("s" + String(i)).c_str(), "");
    savedNetworks[i].pass = prefs.getString(("p" + String(i)).c_str(), "");
  }
  captureIntervalS = prefs.getUInt("interval", CAPTURE_INTERVAL_S);
  prefs.end();
  if (captureIntervalS < 10 || captureIntervalS > 3600) captureIntervalS = CAPTURE_INTERVAL_S;
  Serial.printf("[cfg] %d saved network(s), photo every %u s\n", savedCount, (unsigned)captureIntervalS);
}

void saveNetworks() {
  prefs.begin("leafnode", false);
  for (int i = 0; i < MAX_SAVED_NETWORKS; i++) {
    prefs.remove(("s" + String(i)).c_str());
    prefs.remove(("p" + String(i)).c_str());
  }
  for (int i = 0; i < savedCount; i++) {
    prefs.putString(("s" + String(i)).c_str(), savedNetworks[i].ssid);
    prefs.putString(("p" + String(i)).c_str(), savedNetworks[i].pass);
  }
  prefs.putInt("n", savedCount);
  prefs.end();
}

// ---------------------------------------------------------------------------
// Wi-Fi. Every known network is offered, and the strongest one in range wins:
// at home that is the home Wi-Fi, at a venue the phone hotspot saved earlier.
// ---------------------------------------------------------------------------
bool connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(DEVICE_ID);
  WiFi.setSleep(false);          // sleep here costs more in retries than it saves

  WiFiMulti multi;
  multi.addAP(WIFI_SSID, WIFI_PASSWORD);
  for (int i = 0; i < savedCount; i++) {
    multi.addAP(savedNetworks[i].ssid.c_str(),
                savedNetworks[i].pass.length() ? savedNetworks[i].pass.c_str() : NULL);
  }

  Serial.printf("[wifi] looking for %d known network(s)\n", 1 + savedCount);
  if (multi.run(WIFI_CONNECT_TIMEOUT_MS) != WL_CONNECTED) {
    Serial.println("[wifi] none of them answered");
    return false;
  }
  Serial.printf("[wifi] on %s, ip=%s rssi=%d\n", WiFi.SSID().c_str(),
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
  return true;
}

// ---------------------------------------------------------------------------
// Finding the Pi. Two ways, whichever comes first:
//   - the Pi says hello (POST /hello, with the node key) every half minute;
//     the address it calls from is the Pi. This works on any network, a
//     phone hotspot included, because the Pi goes looking for the camera.
//   - the camera asks for leafnode.local over mDNS before each upload.
// The last answer is kept (PI_HOST before there is one).
// ---------------------------------------------------------------------------
String piHost = PI_HOST;
unsigned long piHelloAt = 0;       // millis() of the last hello, 0 = never
bool lastUploadOk = true;
bool captureSoon = false;          // set when a hello finds us after a failed upload

// Also announces this board as DEVICE_ID.local, which the Pi uses to find it
// on a network where it has not posted a frame yet.
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
  // A hello in the last ten minutes already told us where the Pi is. Asking
  // mDNS again would only add up to two seconds to every photo.
  if (piHelloAt && millis() - piHelloAt < 600000UL) return;
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
  http.setConnectTimeout(HTTP_CONNECT_TIMEOUT_MS);
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
// The node's own small web server, answered between captures. Everything but
// /status needs the node key, the same one the Pi checks on /analyze.
//   POST /capture   take a photo now; the answer is the JPEG (the Pi scores it)
//   POST /hello     the Pi checking in; tells the node where the Pi is
//   GET  /wifi      the saved networks (names only)
//   POST /wifi      action=add|remove, ssid, password: change them
//   POST /config    interval_s: how often to take a photo
//   POST /update    a new firmware .bin, written over the air, then a reboot
//   GET  /status    who this is, which network, when the next photo is due
// ---------------------------------------------------------------------------
#define CAPTURE_SERVER_ON (ENABLE_CAPTURE_SERVER && !USE_DEEP_SLEEP)

unsigned long nextCaptureAt = 0;

#if CAPTURE_SERVER_ON
WebServer web(CAPTURE_SERVER_PORT);
uint32_t photosOnRequest = 0;

// Every byte is compared whatever the length, so the time taken says nothing
// about how close a guess was.
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

bool authorised() {
  if (keyMatches(web.header("X-Node-Key"))) return true;
  Serial.printf("[web] refused %s from %s: bad node key\n", web.uri().c_str(),
                web.client().remoteIP().toString().c_str());
  web.send(401, "application/json", "{\"detail\":\"bad node key\"}");
  return false;
}

void sendJson(int code, JsonDocument& doc) {
  String out;
  serializeJson(doc, out);
  web.send(code, "application/json", out);
}

void sendError(int code, const char* detail) {
  JsonDocument doc;
  doc["detail"] = detail;
  sendJson(code, doc);
}

void handleCapture() {
  if (!authorised()) return;

  ledOn();
  // The sensor runs all the time between captures, so its exposure is already
  // settled: one stale frame to drop is enough, which keeps the tap quick.
  camera_fb_t* fb = captureSettledFrame(1);
  if (!fb) {
    ledOff();
    Serial.println("[web] photo on request: camera gave no frame");
    sendError(503, "camera_failed");
    return;
  }

  String sensorJson = readSensorsJson();
  web.sendHeader("X-Device-Id", DEVICE_ID);
  web.sendHeader("X-Firmware", FIRMWARE_VERSION);
  if (sensorJson.length()) web.sendHeader("X-Sensors", sensorJson);
  web.sendHeader("Cache-Control", "no-store");
  web.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  Serial.printf("[web] photo on request: %u bytes, %ux%u\n",
                (unsigned)fb->len, fb->width, fb->height);

  esp_camera_fb_return(fb);
  ledOff();
  photosOnRequest++;
}

void fillStatus(JsonDocument& doc) {
  doc["device_id"]         = DEVICE_ID;
  doc["firmware"]          = FIRMWARE_VERSION;
  doc["uptime_s"]          = millis() / 1000;
  doc["ip"]                = WiFi.localIP().toString();
  doc["ssid"]              = WiFi.SSID();
  doc["rssi"]              = WiFi.RSSI();
  doc["interval_s"]        = captureIntervalS;
  long wait = (long)(nextCaptureAt - millis()) / 1000;
  doc["next_capture_s"]    = wait > 0 ? wait : 0;
  doc["photos_on_request"] = photosOnRequest;
  doc["saved_networks"]    = savedCount;
  doc["free_heap"]         = ESP.getFreeHeap();
}

void handleStatus() {
  JsonDocument doc;
  fillStatus(doc);
  sendJson(200, doc);
}

void handleHello() {
  if (!authorised()) return;
  String from = web.client().remoteIP().toString();
  if (from != piHost) Serial.printf("[pi] the Pi is at %s\n", from.c_str());
  piHost = from;
  piHelloAt = millis();
  if (!piHelloAt) piHelloAt = 1;
  // The last photo could not be delivered, most likely because the Pi was not
  // known yet on this network. Now it is, so do not make the dashboard wait.
  if (!lastUploadOk) captureSoon = true;

  JsonDocument doc;
  fillStatus(doc);
  doc["pi_host"] = piHost;
  sendJson(200, doc);
}

void sendNetworks() {
  JsonDocument doc;
  doc["built_in"] = WIFI_SSID;
  JsonArray list = doc["saved"].to<JsonArray>();
  for (int i = 0; i < savedCount; i++) list.add(savedNetworks[i].ssid);
  doc["connected"] = WiFi.SSID();
  sendJson(200, doc);
}

void handleWifiGet() {
  if (!authorised()) return;
  sendNetworks();
}

void handleWifiPost() {
  if (!authorised()) return;
  String action = web.arg("action");
  String ssid   = web.arg("ssid");
  String pass   = web.arg("password");

  if (ssid.length() < 1 || ssid.length() > 32) return sendError(400, "ssid must be 1 to 32 bytes");

  int found = -1;
  for (int i = 0; i < savedCount; i++) if (savedNetworks[i].ssid == ssid) found = i;

  if (action == "add") {
    // WPA2 needs 8 to 63 characters; empty means an open network.
    if (pass.length() && (pass.length() < 8 || pass.length() > 63)) {
      return sendError(400, "password must be 8 to 63 characters, or empty for an open network");
    }
    if (found < 0) {
      if (savedCount >= MAX_SAVED_NETWORKS) return sendError(409, "already 5 saved networks; remove one first");
      found = savedCount++;
    }
    savedNetworks[found].ssid = ssid;
    savedNetworks[found].pass = pass;
    Serial.printf("[cfg] saved network %s\n", ssid.c_str());
  } else if (action == "remove") {
    if (found < 0) return sendError(404, "no saved network by that name");
    for (int i = found; i < savedCount - 1; i++) savedNetworks[i] = savedNetworks[i + 1];
    savedCount--;
    Serial.printf("[cfg] forgot network %s\n", ssid.c_str());
  } else {
    return sendError(400, "action must be add or remove");
  }
  saveNetworks();
  sendNetworks();
}

void handleConfig() {
  if (!authorised()) return;
  if (web.hasArg("interval_s")) {
    long s = web.arg("interval_s").toInt();
    if (s < 10 || s > 3600) return sendError(400, "interval_s must be 10 to 3600");
    captureIntervalS = (uint32_t)s;
    prefs.begin("leafnode", false);
    prefs.putUInt("interval", captureIntervalS);
    prefs.end();
    // Applies to the wait already under way, not only the next one.
    unsigned long due = millis() + captureIntervalS * 1000UL;
    if ((long)(nextCaptureAt - due) > 0) nextCaptureAt = due;
    Serial.printf("[cfg] photo every %u s\n", (unsigned)captureIntervalS);
  }
  JsonDocument doc;
  fillStatus(doc);
  sendJson(200, doc);
}

// Over-the-air update. The Pi posts the sketch's .bin (not the merged one) as
// multipart field "firmware"; it is written to the spare app slot and booted
// only if the whole image arrived and checked out.
bool otaAuthorised = false;

void handleUpdateUpload() {
  HTTPUpload& up = web.upload();
  if (up.status == UPLOAD_FILE_START) {
    otaAuthorised = keyMatches(web.header("X-Node-Key"));
    if (!otaAuthorised) return;
    Serial.printf("[ota] receiving %s\n", up.filename.c_str());
    ledOn();
    if (!Update.begin(UPDATE_SIZE_UNKNOWN)) Update.printError(Serial);
  } else if (up.status == UPLOAD_FILE_WRITE) {
    if (otaAuthorised && Update.isRunning() &&
        Update.write(up.buf, up.currentSize) != up.currentSize) {
      Update.printError(Serial);
    }
  } else if (up.status == UPLOAD_FILE_END) {
    if (otaAuthorised) {
      if (Update.end(true)) Serial.printf("[ota] %u bytes written\n", (unsigned)up.totalSize);
      else Update.printError(Serial);
    }
  } else if (up.status == UPLOAD_FILE_ABORTED) {
    if (otaAuthorised) Update.abort();
    Serial.println("[ota] upload aborted");
  }
}

void handleUpdateDone() {
  ledOff();
  if (!otaAuthorised) {
    Serial.printf("[web] refused /update from %s: bad node key\n",
                  web.client().remoteIP().toString().c_str());
    return sendError(401, "bad node key");
  }
  otaAuthorised = false;
  if (Update.hasError() || !Update.isFinished()) return sendError(500, "update_failed");
  web.send(200, "application/json", "{\"status\":\"ok\",\"rebooting\":true}");
  Serial.println("[ota] rebooting into the new firmware");
  delay(400);
  ESP.restart();
}

void startWebServer() {
  static const char* headerKeys[] = {"X-Node-Key"};
  web.collectHeaders(headerKeys, 1);
  web.on("/capture", HTTP_POST, handleCapture);
  web.on("/hello", HTTP_POST, handleHello);
  web.on("/wifi", HTTP_GET, handleWifiGet);
  web.on("/wifi", HTTP_POST, handleWifiPost);
  web.on("/config", HTTP_POST, handleConfig);
  web.on("/update", HTTP_POST, handleUpdateDone, handleUpdateUpload);
  web.on("/status", HTTP_GET, handleStatus);
  web.onNotFound([]() { sendError(404, "not found"); });
  web.begin();
  Serial.printf("[web] listening on port %d\n", CAPTURE_SERVER_PORT);
}
#endif

// Waits for the next scheduled capture while answering the Pi. Also brings
// Wi-Fi back if it dropped, trying every known network, so the node can be
// reached between shots and not only once it next has a frame to send.
void waitForNextCapture() {
  nextCaptureAt = millis() + captureIntervalS * 1000UL;
  unsigned long lastWifiTry = millis();
  while ((long)(nextCaptureAt - millis()) > 0 && !captureSoon) {
#if CAPTURE_SERVER_ON
    web.handleClient();
#endif
    if (WiFi.status() != WL_CONNECTED && millis() - lastWifiTry > 30000UL) {
      Serial.println("[wifi] link lost, looking again");
      connectWifi();
      startMdns();
      lastWifiTry = millis();
    }
    delay(2);
  }
  captureSoon = false;
}

// ---------------------------------------------------------------------------
// One full cycle.
// ---------------------------------------------------------------------------
void runCaptureCycle() {
  ledOn();   // LED stays on for the whole working phase

  camera_fb_t* fb = captureSettledFrame(3);
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
    startMdns();
    resolvePi();
    for (int attempt = 1; attempt <= MAX_UPLOAD_RETRIES && !sent; attempt++) {
      if (attempt > 1) {
        Serial.printf("[http] retry %d of %d\n", attempt, MAX_UPLOAD_RETRIES);
        delay(1500L * attempt);
      }
      sent = uploadFrame(fb, sensorJson);
    }
  }
  lastUploadOk = sent;

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
  Serial.println("\n[boot] LeafNode " DEVICE_ID " firmware " FIRMWARE_VERSION);

  pinMode(LED_STATUS_PIN, OUTPUT);
  ledOff();
#if USE_FLASH_LED
  pinMode(LED_FLASH_PIN, OUTPUT);
  digitalWrite(LED_FLASH_PIN, LOW);
#endif

  loadSettings();

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
  Serial.printf("[sleep] deep sleeping %u s\n", (unsigned)captureIntervalS);
  Serial.flush();
  esp_sleep_enable_timer_wakeup((uint64_t)captureIntervalS * 1000000ULL);
  esp_deep_sleep_start();
#endif
}

void loop() {
#if !USE_DEEP_SLEEP
  runCaptureCycle();
  waitForNextCapture();
#endif
}
