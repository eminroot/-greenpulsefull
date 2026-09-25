"""GreenPulse server.

    ESP32-CAM  --JPEG-->  Raspberry Pi  --score-->  this server  -->  phone

The node scores the leaf; this server fuses that score with the greenhouse
sensors, decides what to do, stores it, and pushes it to the farmer.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .db import init_db
from .routers import assistant, auth, captures, ingest, sites, stream, telemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("greenpulse")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info(
        "GreenPulse server ready (env=%s, db=%s)",
        settings.env,
        settings.database_url.split("://", 1)[0],
    )
    yield


app = FastAPI(
    title="GreenPulse",
    version="2.0.0",
    description="Greenhouse telemetry, leaf scoring and grower accounts.",
    lifespan=lifespan,
    # The interactive docs and the schema describe every endpoint and body.
    # Useful while building, not something to publish on a deployed box.
    docs_url=None if settings.is_production else "/docs",
    openapi_url=None if settings.is_production else "/openapi.json",
    redoc_url=None,
)

# No CORS middleware at all when nothing cross origin is allowed, which is the
# default: the panel is served from this same origin and the phone app is not a
# browser. "*" together with credentials is a misconfiguration, so it is refused
# in production by config.py rather than silently echoed back.
if settings.cors_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=settings.cors_list != ["*"],
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    # API responses are data, never a document. This stops a stored leaf photo
    # or a JSON body being rendered as a page in a victim's browser.
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    response.headers["X-Frame-Options"] = "DENY"
    # Answers are per account, so a shared cache must never keep one.
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    # Log the detail, tell the caller nothing about our internals.
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "server_error"})


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "service": "greenpulse-server",
        "version": app.version,
        "time": datetime.now(timezone.utc).isoformat(),
    }


app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(sites.router, prefix=API_PREFIX)
app.include_router(telemetry.router, prefix=API_PREFIX)
app.include_router(captures.router, prefix=API_PREFIX)
app.include_router(ingest.router, prefix=API_PREFIX)
app.include_router(assistant.router, prefix=API_PREFIX)
app.include_router(stream.router, prefix=API_PREFIX)
