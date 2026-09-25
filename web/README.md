# GreenPulse web panel

The greenhouse control panel, in a browser. It reads exactly the same data as
the phone app, from the same server: sign in, see what the greenhouse is doing
right now, look through the leaf history, and ask what would happen under
different conditions.

It shares the mobile app's design language: the dark emerald canopy palette, the
leaf-and-pulse logo, the animated stress gauge, sensor cards, the autonomous
decision card and the trend chart.

## Running it

```bash
cd web
npm install
npm run dev      # http://localhost:5173
npm run build    # production build into dist/
```

`npm run dev` proxies `/api` and `/health` to a server on
`http://127.0.0.1:8000`. Point it somewhere else with `GREENPULSE_API`:

```bash
GREENPULSE_API=https://your-server npm run dev
```

In production the panel is served by Caddy from the same origin as the API (see
`server/deploy/Dockerfile.caddy`), so every request is relative, there is no CORS
to configure, and the panel can never end up pointing at a different server than
the one it is served from. `docker compose up -d --build` in `server/` builds and
ships it.

To enable "Continue with Google", set `VITE_GOOGLE_CLIENT_ID` to the same OAuth
client id the server holds in `GP_GOOGLE_CLIENT_ID`. Without it the button is
hidden rather than shown broken. Google returns an id_token, the panel hands it
to our server, and the server verifies it against Google's signing keys.

Sign in with the same account you use in the phone app.

## The five views

| | |
|---|---|
| **Overview** | Live stress score, the autonomous decision, the sensors and the trend |
| **Digital twin** | A what-if: move the inputs and see what the system would decide |
| **Sustainability** | Savings counted from the actions this greenhouse actually took |
| **Assistant** | Questions about the greenhouse, grounded in its live state |
| **Leaf gallery** | Every stored capture and its photo |

## What the panel will and will not show

A greenhouse that has never reported shows a waiting state, not a number. A
probe that is not wired reads "No sensor wired", not zero. A node that has gone
quiet is labelled, with the age of its last reading. Everything on screen came
from the greenhouse.

Two things follow from that, and are worth knowing:

**The digital twin does not do its own scoring.** Every change is sent to the
server and scored by the same engine that scores real readings, so the twin
predicts the actual system rather than an approximation that can drift from it.
A probe this greenhouse does not have is left out of the projection entirely,
exactly as the server leaves it out of a real reading.

**The twin does not control anything.** Its actuator tiles report what the
system would be doing at those values. The panel has no remote control over
greenhouse hardware, and does not pretend to.

## How it talks to the server

`src/api/client.ts` holds the session, attaches the token, and refreshes it when
the short-lived access token expires. It is the browser twin of the mobile app's
client, with the same endpoints and the same error codes.

Leaf photos are behind the same authentication as everything else, and an `<img>`
tag sends no `Authorization` header, so `AuthImage` fetches the bytes with the
token and hands the browser an object url. That also keeps the token out of URLs,
and so out of the reverse proxy's access log.

New readings arrive over a websocket (`/api/v1/sites/{id}/stream`). The
connection reconnects with backoff, and pulls a fresh snapshot on the way back
up in case readings were missed.

## Checks

```bash
npm run build                              # types + production build
node ../scripts/check-api-contract.mjs     # types still match the server's schema
```

The contract check reads the server's own OpenAPI schema and compares it against
`src/api/types.ts` here and in the phone app, so a field renamed on one side
cannot quietly ship.
