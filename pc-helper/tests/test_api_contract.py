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


def test_library_summary_endpoint(tmp_path: Path) -> None:
    database.database_path = tmp_path / "api.db"
    database.initialize(RuntimeConfig(media_root=tmp_path, api_token="abc123"))
    database.replace_media_index(
        [
            {
                "id": "media-1",
                "title": "Direct",
                "file_name": "direct.mp4",
                "relative_path": "direct.mp4",
                "absolute_path": str(tmp_path / "direct.mp4"),
                "folder": "",
                "size_bytes": 100,
                "duration_seconds": 60.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1280,
                "height": 720,
                "container": "mp4",
                "compatible_for_direct_play": 1,
                "incompatible_reason": None,
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": "media-2",
                "title": "Needs transcode",
                "file_name": "other.mkv",
                "relative_path": "Shows/other.mkv",
                "absolute_path": str(tmp_path / "Shows" / "other.mkv"),
                "folder": "Shows",
                "size_bytes": 200,
                "duration_seconds": 120.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1920,
                "height": 1080,
                "container": "mkv",
                "compatible_for_direct_play": 0,
                "incompatible_reason": ".mkv is not marked for direct iPhone playback in v1",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        ]
    )
    job_id = database.create_scan_job()
    database.finish_scan_job(job_id, scanned_files=2)

    client = TestClient(app)
    response = client.get(
        "/library/summary",
        headers={"Authorization": "Bearer abc123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 2
    assert payload["direct_play_items"] == 1
    assert payload["incompatible_items"] == 1
    assert payload["media_root"] == str(tmp_path)


def test_stream_endpoint_accepts_query_token(tmp_path: Path) -> None:
    database.database_path = tmp_path / "api.db"
    database.initialize(RuntimeConfig(media_root=tmp_path, api_token="abc123"))

    media_path = tmp_path / "direct.mp4"
    media_path.write_bytes(b"fake media bytes")
    database.replace_media_index(
        [
            {
                "id": "media-1",
                "title": "Direct",
                "file_name": "direct.mp4",
                "relative_path": "direct.mp4",
                "absolute_path": str(media_path),
                "folder": "",
                "size_bytes": media_path.stat().st_size,
                "duration_seconds": 60.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1280,
                "height": 720,
                "container": "mp4",
                "compatible_for_direct_play": 1,
                "incompatible_reason": None,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )

    client = TestClient(app)
    response = client.get("/media/media-1/stream?token=abc123")

    assert response.status_code == 200
    assert response.content == b"fake media bytes"
