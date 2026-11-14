"""Which pages may call the server from the browser: the laptop's dev server and the deployed site, nothing else."""

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings


@pytest.fixture
def client():
    with TestClient(create_app(Settings(warmup=False))) as c:
        yield c


def preflight(client, origin):
    return client.options(
        "/api/copilot/transcribe",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "https://interplanetary-survival-guide-marti-red.vercel.app",
        "https://interplanetary-survival-guide-git-main-makkis-projects-ca792676.vercel.app",
    ],
)
def test_the_app_is_allowed(client, origin):
    r = preflight(client, origin)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", ["https://evil.example", "https://someone-else.vercel.app", "http://interplanetary-survival-guide-x.vercel.app"])
def test_other_sites_are_refused(client, origin):
    r = preflight(client, origin)
    assert "access-control-allow-origin" not in r.headers
