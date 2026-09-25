# LeafNode

An ESP32-CAM photographs a leaf on its own schedule, a Raspberry Pi runs the ML
team's disease classifier on it, and the verdict goes to your server. The model
is the team's YOLO11n tomato and pepper classifier, running on onnxruntime, with
no torch on the Pi.

```
ESP32-CAM ──JPEG over Wi-Fi──▶ Raspberry Pi ──▶ model.py ──▶ risk score
    ▲                               │                            │
    └────── score comes back ───────┘                            │
                                    └── SQLite outbox ──▶ your server
```

The node never holds the model. It takes a picture, posts it, reads the verdict
and blinks it. Swapping models means restarting the Pi service, never reflashing
the board.

Between its scheduled shots the node also listens on port 80, so the farmer can
ask for a photo right now from the app or the web panel:

```
app ─▶ server job ─▶ Pi agent ─▶ Pi POST /capture ─▶ ESP32 POST /capture
                                        │                    │ JPEG back
                                        └─ model, outbox ◀───┘
                                               └─▶ server ─▶ app
```

The Pi learns the camera's address from the frames it posts, so nothing needs
configuring. The photo, its score and the sensors go up exactly like a
scheduled frame. A sleeping node cannot answer, so this needs
`USE_DEEP_SLEEP 0` (the default).

---

## Layout

```
firmware/leafnode/
  leafnode.ino        capture, sensors, upload, status LED, the web server the Pi talks to
  config.h            Pi address, interval, which sensors exist, capture server
  secrets.example.h   copy to secrets.h: Wi-Fi name, password, node key
pi/
  setup.sh            one command on the Pi: venv, .env, node key, services
  server.py           FastAPI: /health, /analyze, /capture, /captures/{id}
  model.py            the model seam: which model answers /analyze
  leaf_classifier.py  the ML team's classifier on onnxruntime, plus the photo checks
  weights/            the .onnx files and models.json (classes, sha256, severity)
  bench.py            latency and memory of the model on this machine
  uploader.py         disk-backed queue + retry to your server
  agent.py            answers the app: scores phone photos, asks the camera for new ones
  leafnode.py         the `leafnode` command: Wi-Fi, interval, status, over-the-air update
  fake_node.py        pretends to be the ESP32, for testing with no hardware
  flash_esp32.sh      flash the ESP32-CAM through the Pi (no USB-TTL needed)
  requirements.txt
  .env.example
  leafnode.service        systemd unit for server.py
  leafnode-agent.service  systemd unit for agent.py
tools/check_chain.py  real server + real Pi service on a laptop, 32 checks
tools/check_parity.py the Pi's code vs ultralytics on the validation images
WIRING.md           the breadboard, the flashing header, the traps
wiring-diagram.svg  the same thing as a picture
```

---

## Bring it up in three stages

Do them in order. Each one works on its own, so when something breaks you know
which stage owns it.

### Stage 1, the Pi alone

```bash
bash ~/leafnode/pi/setup.sh
```

That builds the venv, writes `.env`, generates the node key, installs both
services and prints the two values the firmware needs (`PI_HOST`, `NODE_KEY`).
Then pretend to be the ESP32:

```bash
cd ~/leafnode/pi
set -a && . ./.env && set +a
.venv/bin/python fake_node.py
```

You should get a verdict back (the synthetic frame is a drawing, so ignore
which disease it names). Pass a real leaf photo to see a real one:
`.venv/bin/python fake_node.py leaf.jpg`. Then measure the model on this Pi:

```bash
.venv/bin/python bench.py
```

The pipeline is now proven without a single wire connected.

### Stage 2, add the hardware

Follow [WIRING.md](WIRING.md). Copy `firmware/leafnode/secrets.example.h` to
`secrets.h` and fill in `WIFI_SSID`, `WIFI_PASSWORD` and `NODE_KEY`; set
`PI_HOST` in `config.h`. Flash, then watch the serial monitor at 115200.

A healthy cycle looks like this:

```
[cam] captured 41288 bytes, 800x600
[http] POST http://192.168.1.67:8000/analyze  (41502 bytes)
[http] 200 in 380 ms
[risk] score=94.9 level=critical label=late_blight
```

While waiting, set `CAPTURE_INTERVAL_S` to something short like `30` so you are
not standing around. Put it back to `300` afterwards.

### Stage 3, point it at your server

Pair the device in the app, put `LEAFNODE_UPSTREAM_URL` and
`LEAFNODE_UPSTREAM_TOKEN` in `.env`, and run `setup.sh` again. That restarts
the service, starts the phone scan agent and checks the token. Every record is
queued to `data/queue.db` first, so a dropped connection costs you nothing. A
record the server refuses as malformed moves to a `dead_letter` table rather
than blocking the queue. Watch the depth drain:

```bash
curl http://<pi-ip>:8000/health | python -m json.tool
```

`/health` also lists the cameras the Pi has heard from and where. To see a
photo on request work without the app, on the Pi:

```bash
set -a && . ~/leafnode/pi/.env && set +a
curl -X POST -H "X-Node-Key: $LEAFNODE_NODE_KEY" http://127.0.0.1:8000/capture
```

A camera that does not answer comes back as 504 `camera_unreachable`; one
whose `NODE_KEY` does not match the Pi's as 502 `camera_refused`. The app
shows both as plain reasons, not a spinner that never ends.

---

## Taking it somewhere else (a phone hotspot)

The Pi and the camera both keep a list of Wi-Fi networks and join whichever
known one is in range. So before you leave, while both are still on the home
Wi-Fi, add the hotspot to both with one command:

```bash
ssh -t emin@leafnode.local leafnode wifi add
```

It lists the networks the Pi can hear (turn the hotspot on first to pick it
from the list), asks for the password without showing it, and saves it on the
Pi and on the camera. Neither leaves the home Wi-Fi; at the venue, turn the
hotspot on and both move to it by themselves.

- The hotspot must be **2.4 GHz** with **WPA2**. On an iPhone turn on
  *Maximize Compatibility*; on Android set the band to 2.4 GHz and security to
  WPA2-Personal. The camera cannot see 5 GHz or WPA3-only networks.
- Keep the hotspot's name and password exactly as saved. iPhone names often
  contain a curly apostrophe (Emin’s iPhone); picking it from the list avoids
  typing it.
- On the new network the two find each other on their own: every 30 s the Pi
  asks for the camera by name (`leafnode-01.local`), or sweeps its subnet if
  the hotspot drops name lookups, and says hello. The camera takes the Pi's
  address from that hello. The first photo lands within a minute of both
  joining.

Other commands, all run on the Pi:

| | |
|---|---|
| `leafnode status` | which network each is on, firmware, signal, photo interval |
| `leafnode wifi list` | the networks each one knows |
| `leafnode wifi remove NAME` | forget one on both (never the one the Pi was installed with) |
| `leafnode interval 60` | how often the camera takes a photo, 10 to 3600 s, remembered |
| `leafnode photo` | take a photo now and print the verdict |
| `leafnode update` | put `~/leafnode/build/leafnode.ino.bin` on the camera over Wi-Fi |

The network in `secrets.h` is always tried too, so nothing saved later can lock
the camera out of the home Wi-Fi.

## Updating the firmware

Firmware 1.2.1 and later update over Wi-Fi: build, copy `leafnode.ino.bin` (the
app, not the merged image) to the Pi's `~/leafnode/build/`, run
`leafnode update`. The camera writes it to its spare slot and restarts into it
only if the whole image arrived.

It builds with the OTA partition layout, which leaves 1.9 MB for the app:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32cam:PartitionScheme=min_spiffs --export-binaries firmware/leafnode
```

Going from an older firmware to 1.2 takes the serial jumpers once, because the
old layout has no spare slot: `bash ~/leafnode/pi/flash_esp32.sh flash
~/leafnode/build/leafnode.ino.merged.bin` with IO0 grounded.

## The model

`leaf_classifier.py` runs the models the ML team built from 20,619 PlantVillage
leaf photos (18,146 tomato, 2,473 pepper):

| crop | file | classes | their frozen test set |
|---|---|---|---|
| tomato | `tomato_clean_v1.onnx` | 9 diseases + healthy | 99.16% on 2,737 photos |
| pepper | `pepper_transfer_v1.onnx` | bacterial spot + healthy | 98.11% on 371 photos |

`LEAFNODE_CROP` in `.env` picks one. The model cannot tell crops apart, so it
has to be told: a pepper leaf read by the tomato model gets a tomato disease.

**Same answers as the ML team measured.** The Pi does not use ultralytics, so
`leaf_classifier.py` reproduces its preprocessing step for step.
`tools/check_parity.py` proves it: through the Pi's code the validation sets
score exactly the team's figures (tomato 2,711/2,725, pepper 371/371), and the
class probabilities match ultralytics to the last bit, including on 800x600
ESP32 frames and 12 MP phone photos.

**From classes to a score.** Each class has a severity in `weights/models.json`
(late blight 95, yellow leaf curl 90, ... healthy 0). The risk score is the
probability-weighted severity, so a confident late blight scores about 95 and a
leaf the network is torn about lands in between. That table is a first cut, not
a measurement: have an agronomist look at it.

**Frames it will not read.** Before the network runs, the centre of the frame
has to look like a leaf and be neither black nor blown out. Otherwise the answer
is `unreadable` with a reason (`too_dark`, `overexposed`, `no_leaf`,
`too_small`) and no score, instead of a confident disease invented for a
picture of the wall. At night that is every frame: the sensors still go
upstream, so the greenhouse stays scored and watered, and the app keeps showing
the last leaf it could read. A phone scan that cannot be read asks the farmer
to retake it.

**What it is not.** It was trained and tested on PlantVillage photos: one leaf,
plain background, good light. It has not been validated in a real greenhouse,
it cannot detect water stress, and like any classifier it is confidently wrong
on things it has never seen. Every disease the app reports says so and asks
the farmer to confirm by eye. Treat real greenhouse photos as the next test set.

**When the ML team ships a new model:** drop the `.onnx` in `pi/weights/`,
update its entry in `models.json` (file, sha256, classes in output order, a
severity each), run `tools/check_parity.py`, then restart the service. A file
whose sha256 or class list disagrees with `models.json` refuses to load, and
`/health` says why.

`PlaceholderModel` (green versus brown pixels) is still registered as
`LEAFNODE_MODEL=placeholder` for testing the wiring. It is not a diagnosis.

---

## What the upstream record looks like

```json
{
  "capture_id": "1758531600-a3f9c1d2",
  "site_id": "site-01",
  "device_id": "leafnode-01",
  "received_at": "2026-09-22T14:20:00.123456+00:00",
  "latency_ms": 312.4,
  "image_bytes": 41288,
  "image_width": 800,
  "image_height": 600,
  "image_path": "data/captures/1758531600-a3f9c1d2.jpg",
  "sensors": { "temperature": 29.4, "humidity": 48.0, "soil_moisture": 26.5 },
  "risk_score": 94.9,
  "risk_level": "critical",
  "label": "late_blight",
  "confidence": 0.998,
  "model_version": "tomato_clean_v1",
  "extra": {
    "diagnosis": {
      "status": "ok", "crop": "tomato", "code": "late_blight", "healthy": false,
      "confidence": 0.998,
      "top": [{ "code": "late_blight", "p": 0.998 }, { "code": "early_blight", "p": 0.001 }],
      "model": "tomato_clean_v1", "network_ms": 3.1,
      "quality": { "brightness": 118.2, "leaf_share": 0.41, "sharpness": 812.5 }
    }
  },
  "image_b64": "<the JPEG, added at delivery time>",
  "job_id": "<only when answering something asked for in the app>",
  "job_kind": "<camera, when the ESP32 took it on request; the photo then goes up too>"
}
```

An unreadable frame sends `risk_score` and `risk_level` as null and
`extra.diagnosis` as `{"status": "unreadable", "reason": "too_dark", ...}`, and
is only sent at all when it carries sensor readings.

Your endpoint just has to answer 2xx. 400, 413 and 422 mean the record itself
is wrong, so it moves to `dead_letter`; anything else and the row stays queued.
Whatever `model.py` returns is normalised before it is queued (score clamped to
0..100, a valid band, numpy values converted), so a quirk in the model cannot
produce a record the server refuses.

---

## Security

- The Pi refuses any frame without the `X-Node-Key` header. Anything on the
  greenhouse Wi-Fi can reach port 8000, and whatever the Pi accepts gets signed
  with the device token and shown to the farmer, so this is not optional.
- The key travels over plain HTTP on the LAN. That stops anyone on the Wi-Fi
  injecting readings, but not someone who is also capturing its traffic. If the
  greenhouse network is shared, give the node its own SSID.
- Uploads are capped at 8 MB and 50 megapixels; device ids and job ids are
  checked, not cleaned; there is no CORS, so a web page cannot post to the Pi.
- The ESP32's `POST /capture` wants the same node key, compared in constant
  time, so nothing else on the Wi-Fi can pull photos from the camera.
  `GET /status` answers without it and says nothing secret.
- The Pi dials out to the server over HTTPS with its device token. Nothing on
  the Pi needs to be reachable from the internet.

---

## Status blinks

The red LED on the back of the board is your only feedback once the USB adapter
is unplugged.

| Pattern | Meaning |
|---|---|
| solid, a few seconds | capturing and uploading |
| 1 long blink | low risk |
| 2 long blinks | medium |
| 3 long blinks | high |
| 6 fast blinks | critical |
| 2 slow winks | could not reach the Pi |
| solid for about a second, between shots | taking a photo someone asked for |
| solid for several seconds, then a restart | writing a firmware update |
| 5 fast, repeating forever | camera failed to initialise |
