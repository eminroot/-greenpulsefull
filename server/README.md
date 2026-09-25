# GreenPulse server

Runs on your own machine. Holds the grower accounts, takes readings from the
greenhouse hardware, and feeds the phone app.

```
                                                       ┌──▶ farmer's phone
ESP32-CAM ──JPEG──▶ Raspberry Pi ──score──▶ this server┤
                    (LeafNode,                (accounts,└──▶ web panel
                     the model)                fusion,
                                               storage)
```

The Pi scores the leaf. This server fuses that score with the greenhouse
sensors, decides whether to irrigate or ventilate, stores it, and pushes it to
every phone and panel with the dashboard open. Both front ends read the same
endpoints, so they always agree.

Nothing about the model runs here. The ML team's leaf disease classifier runs
on the Pi (`leafnode/pi/leaf_classifier.py`); this server receives its verdict,
disease name included, and passes it to both front ends.

## Running it locally

```bash
python -m venv .venv
.venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

It comes up on SQLite with no configuration, so there is nothing to install
first. Interactive API docs are at http://127.0.0.1:8000/docs.

```bash
pytest                          # 91 tests, the whole path
python tools/smoke_test.py      # starts a real server and walks it end to end
python tools/seed_demo.py       # fills it with readings, for looking at the panel
```

## Deploying to Contabo

```bash
git clone <this repo> && cd server
cp .env.example .env            # fill in DOMAIN, GP_SECRET_KEY, POSTGRES_PASSWORD
docker compose up -d --build
```

Point your domain's A record at the box first. Caddy gets the TLS certificate
on its own, so there is no certbot step and nothing to renew.

That one command also builds the web panel and serves it from the same origin as
the API, so the panel makes relative requests and there is no CORS to configure.
Open `https://your-domain` for the panel; the API lives under `/api/v1`.

Only ports 80 and 443 are published. Postgres and the API are reachable only
from inside the compose network.

Check it:

```bash
curl https://your-domain/health
python tools/smoke_test.py https://your-domain
```

### When the box already runs a web server

The shared Contabo VPS has its own Caddy on 80 and 443 for other sites, so
this stack's Caddy cannot have them. Put it behind that one instead:

```bash
# in server/.env
COMPOSE_FILE=docker-compose.yml:deploy/docker-compose.behind-proxy.yml
PANEL_PORT=8095
```

Then `docker compose up -d --build` publishes the panel and API on
`127.0.0.1:8095` only, and the host Caddy gets a block like
[deploy/host-caddy.example](deploy/host-caddy.example). The stack's Caddy trusts
the client address the host Caddy forwards, so the sign-in limits still count
per person rather than treating everybody as the proxy.

It runs this way today at `https://greenpulse.5.189.178.58.sslip.io`, from a
clone in `/opt/greenpulse`. The sslip.io name resolves to the IP inside it, so
it needs no DNS record; point a real subdomain at the box and swap the name in
the host Caddyfile when you have one. To ship a change:

```bash
cd /opt/greenpulse && git pull --ff-only
cd server && docker compose up -d --build
```

## Pairing a greenhouse node

1. In the app: Settings, then Greenhouse, then Pair a device. A token appears
   once. It is never shown again; pair the device again if it is lost.
2. On the Pi, in `pi/.env`:

   ```
   LEAFNODE_UPSTREAM_URL=https://your-domain/api/v1/ingest/capture
   LEAFNODE_UPSTREAM_TOKEN=gp_...
   LEAFNODE_SITE_ID=site-01
   ```
3. Run `bash setup.sh` in the Pi's `pi/` folder again. It restarts the
   service, starts the phone scan agent, and checks the token. By hand:

   ```bash
   curl -H "Authorization: Bearer gp_..." https://your-domain/api/v1/ingest/health
   ```

The Pi's existing SQLite outbox already survives outages: if the greenhouse
loses its connection, readings queue on disk and deliver when it returns. The
server treats a redelivered reading as a duplicate and stores it once, so the
queue drains cleanly instead of retrying forever.

The Pi sends each leaf photo inside the reading (`image_b64`), so the farmer
sees what the camera saw. A record the server refuses as malformed moves to the
Pi's `dead_letter` table instead of blocking the queue behind it.

To let the farmer scan a leaf from inside the app, the Pi also runs
`pi/agent.py` (LeafNode repo; `setup.sh` installs it as a service). It polls for
photos taken in the app, scores them through the local LeafNode service, and the
verdict goes up through the same outbox with the job id attached. If one verdict
arrives twice, the second copy still closes the scan. It only dials out, so the
Pi needs no port forwarding.

## The API

Everything is under `/api/v1`.

**Grower**, bearer access token:

| | |
|---|---|
| `POST /auth/register`, `/auth/login`, `/auth/google` | sign in, returns an access + refresh pair |
| `POST /auth/refresh`, `/auth/logout` | rotating refresh tokens |
| `GET`/`PATCH`/`DELETE /auth/me`, `POST /auth/me/password` | the account |
| `GET`/`POST /sites`, `GET`/`DELETE /sites/{id}` | greenhouses |
| `GET`/`POST /sites/{id}/devices`, `DELETE /devices/{id}` | pairing |
| `GET /sites/{id}/live` | what the dashboard renders |
| `GET /sites/{id}/captures` | history |
| `GET /sites/{id}/series?metric=&hours=` | trend charts |
| `GET /sites/{id}/sustainability` | savings, counted from real actions |
| `POST /score/preview` | what would the system do with these numbers? Stores nothing |
| `POST /sites/{id}/scans` | a leaf photo taken in the app |
| `POST /sites/{id}/camera/capture` | ask the greenhouse camera for a photo now (a second tap returns the same request) |
| `GET /scans/{job_id}` | how that scan or camera request is getting on |
| `GET`/`DELETE /captures/{id}`, `GET /captures/{id}/image` | one reading |
| `POST /sites/{id}/stream/ticket`, then `WS /sites/{id}/stream?ticket=` | live push (one minute, single use ticket) |

**Node**, bearer device token:

| | |
|---|---|
| `GET /ingest/health` | check the token and URL |
| `POST /ingest/capture` | a scored leaf, exactly the record `pi/uploader.py` sends |
| `POST /ingest/capture/{capture_id}/image` | attach the JPEG |
| `GET /ingest/jobs?kinds=photo,camera` | long poll for work: a phone photo to score, or a photo to take. `kinds` defaults to `photo`, so an older agent is never handed a camera job |
| `GET /ingest/jobs/{id}/image` | download that phone photo |
| `POST /ingest/jobs/fail` | could not do it; `error` is a code the app explains (`unreadable:too_dark`, `camera_unreachable`, ...) |

## How a reading is scored

The node reports `risk_score` on 0..100, higher meaning worse. The server
combines it with the greenhouse sensors using the same weights as the reference
engine: leaf damage 0.40, soil moisture 0.30, temperature 0.15, light 0.15.
Autonomous action starts at 50, the farmer is alerted at 76.

**Missing probes are not faked.** If no light sensor is wired, light drops out
of the sum and the remaining weights are renormalised, rather than the score
pretending the light is perfect. Which inputs were real is recorded on every
reading in `signals`, and the app shows an absent probe as absent.

**A photo the node could not read is not a healthy leaf.** At night, or with
nothing in frame, the Pi sends the sensors without a leaf score. The leaf drops
out of the sum the same way a missing probe does, so the greenhouse stays
scored (and watered) through the night. `risk_score` is null on that reading,
and `/live` adds `last_leaf_capture` so the dashboard keeps showing the last
leaf that could be read.

One consequence worth knowing: temperature and light carry 0.15 each, so on
their own they cannot push the score past the action threshold of 50. A hot but
otherwise healthy canopy is reported as heat stress and watched, not vented.
That is inherited from the reference engine and left as it was; if you want heat
alone to open the vents, raise `WEIGHT_THERMAL` or lower `ACTION_THRESHOLD` in
`app/engine/`. A test pins the current behaviour so a change is deliberate.

## The leaf diagnosis

The Pi's classifier sends its full verdict in the record's `extra.diagnosis`:
crop, a disease code (`late_blight`, `healthy`, ...), the confidence and the
runners-up, or `status: "unreadable"` with a reason (`too_dark`, `overexposed`,
`no_leaf`, `too_small`). `app/engine/diagnosis.py` parses it back, field by
field, and every capture carries it as `diagnosis`. Codes only: the app and
the panel own the wording in each language.

A confident disease (0.65 and up, the ML team's own line) asks for a human look
even when the stress score is low. The leaf is 40% of the score, so in a
greenhouse with perfect sensors a certain late blight scores 38 and would
otherwise never reach the farmer. It becomes `ALERT_AGRONOMIST` with the farmer
notified, or, if the sensors already called for irrigation or ventilation, that
action stands and the farmer is told about the leaf as well. A diagnosis never
switches an actuator on: the ML team cleared the model for advice only.

Below 0.65 the finding is shown as "not sure yet" and alerts no one.

## The what-if endpoint

`POST /score/preview` runs the same engine, weights and thresholds as a real
reading and stores nothing. The panel's digital twin uses it, so what the twin
shows is what the greenhouse would actually do rather than a second copy of the
scoring that can drift from this one. A test asserts the two agree.

## Notes on how it is built

- Passwords are hashed with argon2. Access tokens are short lived JWTs; refresh
  tokens are opaque, stored only as hashes, and rotate on every use, so a stolen
  one stops working as soon as the real phone refreshes.
- Device tokens are random and stored as a sha256. A leaked node token can only
  write to the greenhouse it was paired with, because the token decides which
  site a reading lands in, not the `site_id` in the body.
- One greenhouse's data is invisible to every other account; a site belonging to
  someone else answers 404, not 403, so ids cannot be probed.
- Leaf images are files under `GP_DATA_DIR`, named from ids the server
  generated, so a crafted filename cannot escape the directory.
- `create_all` builds the schema at startup. There is no production data yet, so
  that keeps deployment to one command. Add Alembic before the first schema
  change once a real greenhouse is running. The last change without it
  (2026-09-25) made `captures.risk_score` nullable; a database created before
  then should be dropped and recreated.
- The live fan out in `app/events.py` is in process, which is why the container
  runs a single worker. To run more, move it to Redis pub/sub; nothing outside
  that file needs to change.
