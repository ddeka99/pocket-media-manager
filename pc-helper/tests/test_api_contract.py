from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app, database
from app.config import RuntimeConfig


def test_health_and_pairing_endpoints(tmp_path: Path) -> None:
    database.database_path = tmp_path / "api.db"
    database.initialize(RuntimeConfig(media_root=None, api_token="abc123"))

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    pairing = client.get("/pairing")
    assert pairing.status_code == 200
    assert pairing.json()["api_token"] == "abc123"
