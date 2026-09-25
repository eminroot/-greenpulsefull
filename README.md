# GreenPulse

Proactive greenhouse management for Türkiye's Aegean and Mediterranean growers.
GreenPulse reads biological changes in plant leaves and responds hours before
visible stress appears, targeting up to 45% less water and 30% lower energy use.

## How the pieces fit

```
                                                              ┌──▶ farmer's phone
ESP32-CAM ──JPEG──▶ Raspberry Pi ──score──▶ GreenPulse server ┤
 photographs         runs the model          accounts, fusion,└──▶ web panel
 a leaf                                      decisions, storage
```

Both front ends read the same endpoints and receive the same live push, so the
phone and the panel always agree.

Each part has exactly one job:

- **ESP32-CAM** photographs a leaf on an interval and reads the DHT22 and soil
  probe wired to it.
- **Raspberry Pi** runs the ML team's leaf disease classifier (YOLO11n, tomato
  and pepper, on onnxruntime) and produces the diagnosis and a leaf risk score.
  The ML work lives here and nowhere else.
- **Server** holds the grower accounts, fuses that score with the sensor
  readings into a single stress score, decides whether to irrigate or ventilate,
  stores everything, and pushes it to the phone.
- **Phone and web panel** show what the greenhouse reported, disease names and
  next steps included. They compute nothing and invent nothing: with no data,
  or a photo too dark to read, they say so.

| Folder | What it is |
|---|---|
| `app/`, `src/` | The React Native (Expo) app the farmer uses |
| `server/` | The server: accounts, ingest, storage, live push. Runs on your own box |
| `greenpulse/greenpulse/` | The original Python pipeline and its research code |
| `web/` | The web panel, reading the same server data as the app |
| `leafnode/` | The greenhouse hardware: ESP32-CAM firmware, the Pi service, the model's weights |
| `GreenPulse 1/` | The ML team's package: training code, reports, models (datasets stay out of git) |

[leafnode/README.md](leafnode/README.md) covers the hardware and what the
model can and cannot tell you.

## Taking a photo on demand

The camera shoots on its own every five minutes. When the farmer wants a look
now, **Photograph the leaf now** on the app's dashboard (or **Take photo** on the
panel's overview) queues a request on the server. The Pi's agent picks it up,
has the ESP32 take the photo, scores it, and sends the photo, the risk score and
the sensor readings up through the same outbox as every scheduled frame. The
new reading shows up on both screens a few seconds later.

If the camera cannot help, the request ends with a reason instead of hanging:
no answer from the camera, a photo too dark to read, a node that is offline.

## Running the app

```bash
npm install
npx expo start
```

Scan the QR code with Expo Go. Point the app at a server by setting
`EXPO_PUBLIC_GREENPULSE_API` before starting, or by changing the address in
Settings, which is handy while testing against a laptop on the same wifi.

```bash
EXPO_PUBLIC_GREENPULSE_API=https://your-server npx expo start
```

In a release build, point the app at an `https://` address. Android blocks
plain http from standalone builds, so a LAN `http://` address works in Expo Go
for testing but not in a build you hand to a farmer. The Caddy setup in
`server/` gives you https with nothing extra to do.

Optional, to enable "Continue with Google": set `EXPO_PUBLIC_GOOGLE_CLIENT_ID`
to the same OAuth client id the server has in `GP_GOOGLE_CLIENT_ID`. Without it
the Google button is hidden rather than shown broken.

Checks:

```bash
npx tsc --noEmit                    # types
node scripts/check-api-contract.mjs # the app AND the panel still match the server
npx expo export --platform ios      # the bundle builds
```

## Running the web panel

```bash
cd web
npm install
npm run dev                                 # proxies /api to a local server
```

See [web/README.md](web/README.md). In production Caddy serves it from the same
origin as the API, so `docker compose up -d --build` ships both together.

## Running the server

See [server/README.md](server/README.md). Short version:

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload       # SQLite, no configuration needed
pytest                              # 97 tests
python tools/smoke_test.py          # the whole chain, end to end
python tools/seed_demo.py           # fill it with readings, for looking at the panel
```

Deploying to Contabo is `docker compose up -d --build` with a `.env`. Caddy
handles TLS on its own. On the shared VPS, where the host's Caddy already owns
80 and 443, it runs behind that one; see "When the box already runs a web
server" in [server/README.md](server/README.md).

## Connecting a greenhouse

1. Sign in on the phone, open Settings, tap **Pair a node**. A key appears once.
2. Put it in the Pi's `.env` as `LEAFNODE_UPSTREAM_TOKEN`, along with
   `LEAFNODE_UPSTREAM_URL=https://your-server/api/v1/ingest/capture`.
3. Run `bash pi/setup.sh` on the Pi again. Readings, with their leaf photos,
   appear on the dashboard as they arrive.

The same script also starts `pi/agent.py` (in the LeafNode folder), which lets
the farmer photograph a leaf from inside the app: it watches for those photos
and answers them through the same path. It only dials out, so nothing has to be
port forwarded.

## What the front ends will and will not show

A greenhouse that has never reported shows a waiting state, not a number. A
probe that is not wired reads "no sensor", not zero. A node that has gone quiet
is labelled quiet, with the age of the last reading. Every figure on screen came
from the greenhouse.

The panel's digital twin is the one place showing numbers that are not a
reading, and it is labelled a projection throughout. It does not score anything
itself: it asks the server, so it predicts the real engine rather than an
approximation that can drift from it.

## Where the score comes from

The node reports leaf risk on 0..100, higher meaning worse. The server combines
it with the sensors using the weights from the reference engine: leaf damage
0.40, soil moisture 0.30, temperature 0.15, light 0.15. Action starts at 50, the
farmer is alerted at 76. When a probe is missing its weight is dropped and the
rest are renormalised, rather than a missing reading being treated as perfect.

The full picture, including a caveat about how heat and light are weighted, is
in [server/README.md](server/README.md).
