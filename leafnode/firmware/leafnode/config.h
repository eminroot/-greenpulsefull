// ---------------------------------------------------------------------------
// LeafNode camera node - configuration
// Everything you are likely to change lives in this one file.
// ---------------------------------------------------------------------------
#pragma once

// --- Secrets ---------------------------------------------------------------
// Wi-Fi name, Wi-Fi password and the node key live in secrets.h, which git
// ignores. Copy secrets.example.h to secrets.h and fill it in.
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #error "Copy secrets.example.h to secrets.h and fill in WIFI_SSID, WIFI_PASSWORD and NODE_KEY"
#endif

// --- Network ---------------------------------------------------------------
// The Raspberry Pi running pi/server.py, on the same LAN. The node looks it up
// by name first (PI_MDNS_NAME.local, which Raspberry Pi OS answers out of the
// box), so a new DHCP address on the Pi does not strand the node. PI_HOST is
// only the fallback for networks that block mDNS. Set PI_MDNS_NAME to "" to
// always use PI_HOST.
#define PI_MDNS_NAME     "leafnode"
#define PI_HOST          "192.168.1.123"
#define PI_PORT          8000
#define PI_ANALYZE_PATH  "/analyze"

// Identifies this physical node in the Pi's records. Change it per board.
#define DEVICE_ID        "leafnode-01"

// --- Capture cadence -------------------------------------------------------
// How long to wait between autonomous captures, in seconds. This is only the
// starting value: the Pi can change it over Wi-Fi without a reflash
// (leafnode interval 300), and the board remembers it.
#define CAPTURE_INTERVAL_S   60

// Use deep sleep between captures instead of staying awake.
// 0 = stay awake (fast, good for a live demo, ~160 mA idle)
// 1 = deep sleep (slow to wake, good on battery, ~10 uA idle)
// A sleeping board cannot be asked for a photo, so deep sleep turns off
// "take a photo now" in the app.
#define USE_DEEP_SLEEP       0

// --- Photo on request ------------------------------------------------------
// Between captures the node listens on this port. The Pi asks it for a photo
// (POST /capture with the node key) when the farmer taps "take a photo now",
// checks in (POST /hello), and changes saved networks, the interval or the
// firmware. GET /status answers without the key and says nothing secret.
#define ENABLE_CAPTURE_SERVER 1
#define CAPTURE_SERVER_PORT   80

// --- Camera ----------------------------------------------------------------
// FRAMESIZE_SVGA (800x600) is a good balance for leaf detail vs upload time.
// Go to FRAMESIZE_XGA or UXGA only if the Pi model needs more pixels.
#define CAMERA_FRAMESIZE     FRAMESIZE_SVGA
#define CAMERA_JPEG_QUALITY  10   // 10..63, LOWER number = better quality

// Fire the onboard white LED (GPIO4) while capturing.
// It is extremely bright. Useful in a dark greenhouse, blinding on a desk.
#define USE_FLASH_LED        0

// --- Optional sensors ------------------------------------------------------
// Set to 1 only once the part is physically wired. See WIRING.md.
#define ENABLE_DHT           0   // DHT22 temperature + humidity on GPIO13
#define ENABLE_ADS1115       0   // I2C ADC on GPIO14/15 for the soil probe

#define DHT_PIN              13
#define DHT_TYPE             DHT22
#define I2C_SDA_PIN          14
#define I2C_SCL_PIN          15

// Raw ADS1115 counts for the soil probe in air (dry) and in water (wet).
// Calibrate these with the two-cup test in WIRING.md before trusting the value.
#define SOIL_RAW_DRY         17500
#define SOIL_RAW_WET         7200

// --- Behaviour -------------------------------------------------------------
#define HTTP_TIMEOUT_MS      20000  // the Pi may take seconds on first inference
// Short on purpose: after a network change the old Pi address is dead, and
// while the node waits on it, it cannot answer the Pi's hello either.
#define HTTP_CONNECT_TIMEOUT_MS 4000
#define WIFI_CONNECT_TIMEOUT_MS 20000
#define MAX_UPLOAD_RETRIES   3
