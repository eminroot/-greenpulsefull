# GreenPulse status, 2026-09-25

## Done

**ML model wired in.** The ML team's classifier (`GreenPulse 1/`, tomato_clean_v1 + pepper_transfer_v1, YOLO11n) runs on the Pi via onnxruntime, no torch (`leafnode/pi/leaf_classifier.py`, weights in `leafnode/pi/weights/`). Parity with ultralytics is exact (`leafnode/tools/check_parity.py`). Dark or empty photos come back "unreadable" instead of a guessed disease.
- Server: diagnosis in `capture.extra.diagnosis`, parsed by `server/app/engine/diagnosis.py`. A confident disease (≥0.65) alerts the farmer but never switches an actuator. 91 tests pass.
- App + web: `DiagnosisCard` shows disease, confidence and advice (app TR/EN/RU, web EN/TR).
- Chain test: `leafnode/tools/check_chain.py`, 23/23.

**Hardware live.**
- Pi 4 (4 GB), Raspberry Pi OS Lite 64-bit Trixie. `leafnode.local` = 192.168.1.123, user `emin`, laptop SSH key only (use `C:\Windows\System32\OpenSSH\ssh.exe`). LeafNode service runs on :8000 with the model loaded and survives reboots.
- ESP32-CAM flashed with the LeafNode firmware (camera only, sensors off). It joins `ALHN-120A` (2.4 GHz) at 192.168.1.124, and its first frame round-tripped to the Pi (79 ms model, verdict "too_dark", correct).
- Pi 4 bench: 51 ms per ESP32 frame, 134 MB RAM (`leafnode/bench-pi4.json`).

## Open, in order

1. **Results do not reach the app yet.** The GreenPulse server is not deployed, and the Pi's `LEAFNODE_UPSTREAM_URL`/`TOKEN` are empty. Decide where the server runs:
   - Contabo VPS: the host Caddy owns 80/443, so add a subdomain block rather than use the compose Caddy.
   - The laptop on the LAN, for a quick test.
   - The Pi itself.

   Then pair the device in the app, put the token in `~/leafnode/pi/.env` on the Pi, and run `bash ~/leafnode/pi/setup.sh`.
2. **No on-demand photo.** The firmware shoots at boot and then every 300 s. Plan: a `/capture` HTTP endpoint on the ESP32 (serve it inside the loop's wait). An app button creates a server job, the Pi's agent picks it up and calls the ESP32, and the result arrives through the normal path. Not started.
3. Sensors: wire the DHT22/ADS1115, set `ENABLE_*` in `firmware/leafnode/config.h`, rebuild, reflash.
4. Nothing is committed (tecnoproject2 is untracked inside the home-directory repo).

## Gotchas

- ESP32 download mode: IO0 to Pi pin 9 (GND), then pull the ESP32's 5V jumper for 2 s (its RST button faces the breadboard). For a normal boot, IO0 must be off GND.
- Serial wiring: Pi pin 8 to U0R, Pi pin 10 to U0T. Pin 9 is GND; U0T was wrongly there.
- Reflash: `bash ~/leafnode/pi/flash_esp32.sh flash ~/leafnode/build/leafnode.ino.merged.bin` (460800 baud, ~25 s). 115200 browned out twice.
- Build the firmware from PowerShell with System32 on PATH (arduino-cli, FQBN `esp32:esp32:esp32cam`).
- Wi-Fi passwords: Emin types them; never read or print them. `secrets.h` is gitignored; `secrets.example.h` stays blank.
