# GreenPulse status, 2026-09-25

## Done

**Deployed.** The server and web panel run on the Contabo VPS at
https://greenpulse.5.189.178.58.sslip.io, from a clone of
github.com/eminroot/-greenpulsefull in `/opt/greenpulse` (compose project
`greenpulse`, its Caddy on 127.0.0.1:8095 behind the host Caddy, Let's Encrypt
cert). The sslip.io name needs no DNS; swap in a real subdomain later in
`/etc/caddy/Caddyfile`. Ship a change: `cd /opt/greenpulse && git pull --ff-only
&& cd server && docker compose up -d --build`. If only `deploy/Caddyfile`
changed, add `--force-recreate caddy` (the bind mount keeps the old file).
- The phone app now defaults to that address (`src/config/env.ts`).
- A greenhouse account exists on the server (sign-in handed over in chat, not
  kept in this public repo), and the Pi is paired to its greenhouse.

**Readings reach the server.** The Pi's `.env` points at the deployed server
with a real device token; `setup.sh` says "reachable, token accepted" and the
agent is on. The 10 readings the Pi had queued were delivered with their photos,
and new scheduled frames arrive about a second after they are taken (photo, risk
score, diagnosis).

**Photo on request (built, tested, half live).** "Photograph the leaf now" on
the app dashboard and "Take photo" on the panel's overview and gallery.
Server queues a `camera` scan job (`POST /sites/{id}/camera/capture`) → Pi
agent claims it (`/ingest/jobs?kinds=photo,camera`) → Pi `POST /capture` asks
the ESP32 (address learned from its frames, `.local` name as fallback) → the
frame is scored and sent up with its photo like any scheduled frame.
Failures end with a reason: `camera_unreachable`, `camera_refused`,
`camera_failed`, `unreadable:<reason>`, or expired.
- Tests: server 97 (`pytest`), chain 30 (`leafnode/tools/check_chain.py`, with a
  stand-in ESP32), both clients match the API (`scripts/check-api-contract.mjs`).
- Live on the deployed server and the Pi. A request today ended correctly with
  `camera_unreachable` in 42 s, because the ESP32 still runs the old firmware.

**Repo.** Everything is in github.com/eminroot/-greenpulsefull (public), commits
under Emin's name. `leafnode/` moved here from Desktop/leafnode; a junction at
the old path still works.

## Open, in order

1. **Flash the new firmware (needs hands on the board).** It is built and
   already on the Pi at `~/leafnode/build/leafnode.ino.merged.bin` (firmware
   1.1.0: listens on port 80 between shots). Put IO0 to Pi pin 9 (GND), pull the
   ESP32's 5V jumper for 2 s, then on the Pi:
   `bash ~/leafnode/pi/flash_esp32.sh flash ~/leafnode/build/leafnode.ino.merged.bin`.
   Take IO0 off GND and pull 5V for 2 s again to boot it. Then tap "Take photo".
2. **The model calls anything a disease.** The camera is pointed at jumper wires
   and a wall, and those frames come back "bacterial spot 68%, critical",
   raising agronomist alerts. The `no_leaf` gate in `leafnode/pi/leaf_classifier.py`
   does not catch it. Point the camera at a real leaf for demos, and tighten the gate.
3. The assistant is off on the server: `GP_GEMINI_API_KEY` is empty in
   `/opt/greenpulse/server/.env`. Add the key and `docker compose up -d api`.
4. Sensors: wire the DHT22/ADS1115, set `ENABLE_*` in `leafnode/firmware/leafnode/config.h`, rebuild, reflash.
5. Pairing hands out `https://<your-server>/...` as the upstream URL; it should
   use the real host.

## Gotchas

- ESP32 download mode: IO0 to Pi pin 9 (GND), then pull the ESP32's 5V jumper for 2 s (its RST button faces the breadboard). For a normal boot, IO0 must be off GND.
- Serial wiring: Pi pin 8 to U0R, Pi pin 10 to U0T. Pin 9 is GND; U0T was wrongly there.
- Reflash at 460800 baud (~25 s). 115200 browned out twice.
- Build the firmware from PowerShell with System32 and WindowsPowerShell on PATH (arduino-cli, FQBN `esp32:esp32:esp32cam`, `--export-binaries`).
- Wi-Fi passwords: Emin types them; never read or print them. `secrets.h` is gitignored; `secrets.example.h` stays blank.
- VPS SSH is rate limited (6 new connections per 30 s): batch commands into one session.
