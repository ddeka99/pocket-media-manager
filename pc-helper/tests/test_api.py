from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import state
from app.main import app, build_infuse_url


def configure_env(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    media_root = tmp_path / "media"
    media_root.mkdir()
    prefs_file = tmp_path / "_mpv_prefs.json"
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    monkeypatch.setenv("PREFS_FILE", str(prefs_file))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://192.168.1.50:8787")
    monkeypatch.setenv("SUPPORTED_EXTENSIONS", ".mp4,.mkv")
    monkeypatch.delenv("EXCLUDE_FOLDERS", raising=False)
    state.clear_state()
    return media_root, prefs_file


def test_build_infuse_url_encodes_special_characters():
    infuse_url = build_infuse_url(
        "http://192.168.1.50:8787/stream/token with spaces",
        "A file [sample] 'quote'.mp4",
    )

    assert infuse_url.startswith("infuse://x-callback-url/play?")
    assert "token+with+spaces" in infuse_url
    assert "A+file+%5Bsample%5D+%27quote%27.mp4" in infuse_url


def test_health_returns_ok(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_next_last_and_feedback_update_prefs(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "Example Video.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app)

    next_response = client.get("/next")
    assert next_response.status_code == 200
    payload = next_response.json()
    assert payload["file_name"] == "Example Video.mp4"
    assert payload["stream_url"].startswith("http://192.168.1.50:8787/stream/")
    assert payload["infuse_url"].startswith("infuse://x-callback-url/play?")
    assert payload["feedback"]["like"] == "http://192.168.1.50:8787/feedback/like"

    last_response = client.get("/last")
    assert last_response.status_code == 200
    assert last_response.json()["meta"]["play_count"] == 1

    feedback_response = client.post("/feedback/like")
    assert feedback_response.status_code == 200
    assert feedback_response.json() == {
        "ok": True,
        "feedback": "like",
        "file_name": "Example Video.mp4",
    }

    prefs_text = prefs_file.read_text(encoding="utf-8")
    assert '"likes": 1' in prefs_text
    assert '"last_feedback": "y"' in prefs_text


def test_next_redirects_to_infuse(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)

    response = client.get("/next?redirect=infuse")

    assert response.status_code in {302, 307}
    assert response.headers["location"].startswith("infuse://x-callback-url/play?")


def test_next_returns_404_when_no_media_exists(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/next")

    assert response.status_code == 404
    assert "No supported media files" in response.json()["detail"]


def test_unknown_stream_token_returns_404(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/stream/not-a-token")

    assert response.status_code == 404


def test_stream_serves_token_file(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "video.mp4"
    media_file.write_bytes(b"0123456789")
    token = state.create_stream_token(media_file)
    client = TestClient(app)

    response = client.get(f"/stream/{token}", headers={"Range": "bytes=0-3"})

    assert response.status_code in {200, 206}
    assert response.content


def test_stream_rejects_token_path_outside_media_root(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    outside_file = tmp_path / "outside.mp4"
    outside_file.write_bytes(b"outside")
    token = state.create_stream_token(outside_file)
    client = TestClient(app)

    response = client.get(f"/stream/{token}")

    assert response.status_code == 404


def test_stream_returns_404_when_file_was_deleted(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    missing_file = media_root / "deleted.mp4"
    missing_file.write_bytes(b"soon gone")
    token = state.create_stream_token(missing_file)
    missing_file.unlink()
    client = TestClient(app)

    response = client.get(f"/stream/{token}")

    assert response.status_code == 404
