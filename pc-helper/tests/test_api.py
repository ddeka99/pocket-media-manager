from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import state
from app.main import app, build_infuse_url, build_vlc_url


def configure_env(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    media_root = tmp_path / "media"
    media_root.mkdir()
    prefs_file = tmp_path / "_mpv_prefs.json"
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    monkeypatch.setenv("PREFS_FILE", str(prefs_file))
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://192.168.1.50:8787")
    monkeypatch.setenv("SUPPORTED_EXTENSIONS", ".mp4,.mkv")
    monkeypatch.setenv("PLAYER", "infuse")
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


def test_build_vlc_url_encodes_stream_url():
    vlc_url = build_vlc_url("http://192.168.1.50:8787/stream/token with spaces")

    assert vlc_url == "vlc-x-callback://x-callback-url/stream?url=http%3A%2F%2F192.168.1.50%3A8787%2Fstream%2Ftoken+with+spaces"


def test_health_returns_ok(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_home_shows_recommend_and_reset(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Recommend" in response.text
    assert "Recommend with Selections" in response.text
    assert "Reset Preferences" in response.text


def test_browser_recommend_returns_feedback_page_with_infuse_opener(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "Browser Video.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.post("/recommend", headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "Feedback" in response.text
    assert "Browser Video.mp4" in response.text
    assert "infuse://x-callback-url/play?" in response.text
    assert "/feedback/like" in response.text
    assert "/feedback/skip" in response.text


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
    assert payload["player"] == "infuse"
    assert payload["player_url"] == payload["infuse_url"]
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


def test_browser_feedback_redirects_home(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)
    client.post("/recommend", headers={"accept": "text/html"})

    response = client.post("/feedback/dislike", headers={"accept": "text/html"})

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert '"dislikes": 1' in prefs_file.read_text(encoding="utf-8")


def test_skip_feedback_does_not_change_preference_counts(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app)
    client.post("/recommend", headers={"accept": "text/html"})

    response = client.post("/feedback/skip")

    assert response.status_code == 200
    assert response.json()["feedback"] == "skip"
    prefs_text = prefs_file.read_text(encoding="utf-8")
    assert '"likes": 0' in prefs_text
    assert '"dislikes": 0' in prefs_text
    assert '"pending": 0' in prefs_text
    assert '"play_count": 1' in prefs_text
    assert '"last_feedback": null' in prefs_text


def test_next_redirects_to_infuse(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)

    response = client.get("/next?redirect=infuse")

    assert response.status_code in {302, 307}
    assert response.headers["location"].startswith("infuse://x-callback-url/play?")


def test_vlc_player_setting_returns_vlc_player_url(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    monkeypatch.setenv("PLAYER", "vlc")
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.get("/next")

    assert response.status_code == 200
    payload = response.json()
    assert payload["player"] == "vlc"
    assert payload["infuse_url"].startswith("infuse://x-callback-url/play?")
    assert payload["player_url"].startswith("vlc-x-callback://x-callback-url/stream?")


def test_browser_recommend_uses_vlc_when_configured(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    monkeypatch.setenv("PLAYER", "vlc")
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.post("/recommend", headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "vlc-x-callback://x-callback-url/stream?" in response.text


def test_selection_page_lists_only_top_level_folders_with_media(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    nested = anime / "Attack on Titan"
    empty = media_root / "Empty"
    nested.mkdir(parents=True)
    empty.mkdir()
    (nested / "episode.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.get("/select")

    assert response.status_code == 200
    assert "Anime" in response.text
    assert "Attack on Titan" not in response.text
    assert "Empty" not in response.text


def test_selected_recommend_requires_at_least_one_folder(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    folder = media_root / "Anime"
    folder.mkdir()
    (folder / "episode.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.post("/recommend/selected", data={}, headers={"accept": "text/html"})

    assert response.status_code == 200
    assert "Select at least one folder." in response.text


def test_selected_recommend_scopes_pick_to_selected_folders(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    movies = media_root / "Movies"
    anime.mkdir()
    movies.mkdir()
    (anime / "episode.mp4").write_bytes(b"fake anime")
    (movies / "movie.mp4").write_bytes(b"fake movie")
    client = TestClient(app)

    response = client.post(
        "/recommend/selected",
        data={"folders": "Anime"},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 200
    assert "episode.mp4" in response.text
    assert "movie.mp4" not in response.text


def test_selected_recommend_ignores_invalid_folder_names(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    folder = media_root / "Anime"
    folder.mkdir()
    (folder / "episode.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.post(
        "/recommend/selected",
        data={"folders": ".."},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 200
    assert "Select at least one available folder." in response.text


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


def test_reset_preferences_clears_prefs_and_state(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)
    client.post("/recommend", headers={"accept": "text/html"})
    client.post("/feedback/like")

    response = client.post("/reset", headers={"accept": "text/html"})

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert prefs_file.read_text(encoding="utf-8") == '{\n  "files": {}\n}'
    assert client.get("/last").status_code == 404


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
