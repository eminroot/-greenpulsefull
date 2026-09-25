"""Test fixtures.

Environment is set before the app is imported, because configuration is read
once at import time. Each run gets a throwaway SQLite file and data directory,
so tests never touch a real deployment.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="greenpulse-test-")

os.environ["GP_ENV"] = "test"
os.environ["GP_SECRET_KEY"] = "test-secret-not-for-production-padded-to-32-bytes"
os.environ["GP_DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ["GP_DATA_DIR"] = f"{_TMP}/data"
os.environ["GP_DEVICE_ONLINE_SECONDS"] = "900"
# The suite signs a lot of accounts in and out from one address. Limiter
# behaviour is covered on its own in test_security.py with tight limits.
os.environ["GP_SIGNUP_RATE_LIMIT"] = "1000"
os.environ["GP_LOGIN_RATE_LIMIT"] = "1000"
os.environ["GP_ASSISTANT_RATE_LIMIT"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="session")
def grower(client) -> dict:
    """A registered account with its default greenhouse."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "grower@example.com",
            "password": "greenhouse1",
            "name": "Test Grower",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()

    sites = client.get(
        "/api/v1/sites",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    ).json()
    assert sites, "registration should create a default greenhouse"

    return {
        "access": body["access_token"],
        "refresh": body["refresh_token"],
        "user": body["user"],
        "site": sites[0],
    }


@pytest.fixture(scope="session")
def auth(grower) -> dict:
    return {"Authorization": f"Bearer {grower['access']}"}


@pytest.fixture(scope="session")
def node(client, grower, auth) -> dict:
    """A paired Raspberry Pi with its upload token."""
    res = client.post(
        f"/api/v1/sites/{grower['site']['id']}/devices",
        json={"name": "Greenhouse Pi", "kind": "pi"},
        headers=auth,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return {"token": body["token"], "headers": {"Authorization": f"Bearer {body['token']}"}}
