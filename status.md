# GreenPulse status, 2026-09-25 (evening)

## Done

**Deployed.** Server and web panel at https://greenpulse.5.189.178.58.sslip.io,
from a clone of github.com/eminroot/-greenpulsefull in `/opt/greenpulse`
(compose project `greenpulse`, its Caddy on 127.0.0.1:8095 behind the host
Caddy). Ship a change: `cd /opt/greenpulse && git pull --ff-only && cd server &&
docker compose up -d --build`; a changed `deploy/Caddyfile` also needs
`--force-recreate caddy`. The phone app defaults to this address. A greenhouse
account exists on the server (sign-in handed over in chat, not kept in this
public repo) and the Pi is paired to it.

**Camera firmware 1.2.1 is on the ESP32** (flashed over serial on 2026-09-25,
the last time the jumpers should be needed).
- Photo on request works end to end: tap to photo on the dashboard in 1.5 s
  (median of 5 through production). Before it failed after ~40 s.
- A photo every 60 s on its own (was 300 s), changeable with `leafnode interval`.
- Updates go over Wi-Fi: `leafnode update` sends `~/leafnode/build/leafnode.ino.bin`
  (tested three times; the camera keeps the old firmware if an upload breaks).
- 1.2.0 did not start its camera: `camera_config_t` was never zeroed, and its
  `jpeg_buffer_size` field held stack garbage. It had been luck that 1.0 worked.
  1.2.1 zeroes it, falls back to smaller buffers, and never stops before Wi-Fi.

**Ready for the hotspot.** Both devices keep a list of networks and join the
known one in range. Before leaving home, with both still on the home Wi-Fi:
`ssh -t emin@leafnode.local leafnode wifi add` (asks for the hotspot's name and
password, saves them on the Pi and the camera). Hotspot must be 2.4 GHz, WPA2.
On the new network the Pi finds the camera by name, or by sweeping the subnet
(tested: 2 s), and tells it where the Pi is. Tested add, list and remove with a
dummy network on both.

**Checks.** Server 98 tests (`cd server && pytest`), chain 32
(`leafnode/tools/check_chain.py`), contract checker, both clients type-check.

## Open, in order

1. **The model calls anything a disease.** Photos of wires on a wall come back
   "bacterial spot / late blight, critical" and raise agronomist alerts. The
   `no_leaf` gate in `leafnode/pi/leaf_classifier.py` misses them. Point the
   camera at a real tomato leaf for the demo, and tighten the gate.
2. With a photo every 60 s, every critical frame is an ALERT_AGRONOMIST event,
   so the alert count on the savings page climbs fast. Consider only alerting
   on a change.
3. The assistant is off on the server: `GP_GEMINI_API_KEY` is empty in
   `/opt/greenpulse/server/.env`.
4. Sensors: wire the DHT22/ADS1115, set `ENABLE_*` in `leafnode/firmware/leafnode/config.h`, rebuild, `leafnode update`.
5. Pairing hands out `https://<your-server>/...` as the upstream URL; it should use the real host.

## Gotchas

- Firmware builds with `--fqbn esp32:esp32:esp32cam:PartitionScheme=min_spiffs`
  (OTA layout). A build with the default huge_app layout cannot be sent over
  Wi-Fi and would need the jumpers again.
- `leafnode update` uses curl on purpose: the ESP32 web server aborts the way
  Python requests streams a 1.2 MB upload, every time.
- Serial flash (only if Wi-Fi updates are ever impossible): IO0 to Pi pin 9 (GND),
  pull the ESP32's 5V jumper for 2 s, `bash ~/leafnode/pi/flash_esp32.sh flash
  ~/leafnode/build/leafnode.ino.merged.bin`, then IO0 off GND and pull 5V again.
- Red LED fluttering 5 times, over and over: the camera did not start. 1.2.1
  still joins Wi-Fi then, so `leafnode status` shows `camera: failed` and the
  serial log (`flash_esp32.sh monitor 40`) says why.
- If `leafnode.local` does not resolve from the laptop, use the IP with
  `ssh -o HostKeyAlias=leafnode.local emin@192.168.1.123`.
- Wi-Fi passwords: Emin types them; never read or print them. `secrets.h` is gitignored.
- VPS SSH is rate limited (6 new connections per 30 s): batch commands into one session.
