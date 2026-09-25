// Copy this file to secrets.h (same folder) and fill it in.
// secrets.h is in .gitignore, so your Wi-Fi password never reaches the repo.
#pragma once

// 2.4 GHz network only. The ESP32 cannot see 5 GHz Wi-Fi.
#define WIFI_SSID        "YOUR_WIFI_NAME"
#define WIFI_PASSWORD    "YOUR_WIFI_PASSWORD"

// Must match LEAFNODE_NODE_KEY in pi/.env. setup.sh prints it at the end.
// The Pi refuses every frame that does not carry it.
#define NODE_KEY         "PASTE_THE_KEY_FROM_SETUP_SH"
