from __future__ import annotations

import json
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
    monkeypatch.setenv("EXCLUDE_FOLDERS", "")
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
    assert "Explore" in response.text
    assert "Feedback Addressed" in response.text
    assert "Reset Preferences" in response.text
    assert "Excluded folders" in response.text
    assert "No excluded folders configured." in response.text


def test_home_lists_configured_excluded_folders(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    monkeypatch.setenv("EXCLUDE_FOLDERS", "Trailers,Behind the Scenes")
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Excluded folders" in response.text
    assert "<li>Behind the Scenes</li>" in response.text
    assert "<li>Trailers</li>" in response.text


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
    assert "/feedback/other" in response.text


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


def test_explore_lists_supported_files_and_media_folders(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    empty = media_root / "Empty"
    excluded = media_root / "Excluded"
    nested = anime / "Series"
    nested.mkdir(parents=True)
    empty.mkdir()
    excluded.mkdir()
    (media_root / "loose.mp4").write_bytes(b"fake media")
    (media_root / "notes.txt").write_text("not media", encoding="utf-8")
    (nested / "episode.mkv").write_bytes(b"fake media")
    (excluded / "hidden.mp4").write_bytes(b"fake media")
    monkeypatch.setenv("EXCLUDE_FOLDERS", "Excluded")
    client = TestClient(app)

    response = client.get("/explore")

    assert response.status_code == 200
    assert "Explore" in response.text
    assert f"Browsing <em>{media_root}</em>" in response.text
    assert ">Home<" in response.text
    assert "loose.mp4" in response.text
    assert "Anime" in response.text
    assert "notes.txt" not in response.text
    assert "Empty" not in response.text
    assert "Excluded" not in response.text


def test_explore_can_navigate_into_folder_and_back(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    anime.mkdir()
    (anime / "episode.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.get("/explore", params={"path": "Anime"})

    assert response.status_code == 200
    assert "Browsing <em>Anime</em>" in response.text
    assert "episode.mp4" in response.text
    assert ">Back<" in response.text
    assert ">Home<" in response.text
    assert 'href="/explore"' in response.text


def test_explore_play_records_file_and_shows_feedback(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    anime.mkdir()
    media_file = anime / "episode.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app)

    response = client.post("/explore/play", data={"path": str(media_file.relative_to(media_root))})

    assert response.status_code == 200
    assert "Feedback" in response.text
    assert "episode.mp4" in response.text
    assert "infuse://x-callback-url/play?" in response.text
    prefs = json.loads(prefs_file.read_text(encoding="utf-8"))
    assert prefs["files"][str(media_file)]["play_count"] == 1


def test_explore_rejects_unsupported_or_outside_paths(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "notes.txt").write_text("not media", encoding="utf-8")
    outside_file = tmp_path / "outside.mp4"
    outside_file.write_bytes(b"fake media")
    client = TestClient(app)

    unsupported = client.post("/explore/play", data={"path": "notes.txt"})
    outside = client.get("/explore", params={"path": ".."})

    assert unsupported.status_code == 404
    assert outside.status_code == 404


def test_selected_feedback_redirects_back_to_prechecked_selection(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    movies = media_root / "Movies"
    anime.mkdir()
    movies.mkdir()
    (anime / "episode.mp4").write_bytes(b"fake anime")
    (movies / "movie.mp4").write_bytes(b"fake movie")
    client = TestClient(app, follow_redirects=False)
    client.post(
        "/recommend/selected",
        data={"folders": "Anime"},
        headers={"accept": "text/html"},
    )

    response = client.post("/feedback/like", headers={"accept": "text/html"})

    assert response.status_code == 303
    assert response.headers["location"] == "/select"
    assert '"likes": 1' in prefs_file.read_text(encoding="utf-8")

    selection_response = client.get("/select")
    assert selection_response.status_code == 200
    assert 'value="Anime" checked' in selection_response.text
    assert 'value="Movies" checked' not in selection_response.text


def test_selection_cancel_clears_saved_folders_and_returns_home(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    anime.mkdir()
    (anime / "episode.mp4").write_bytes(b"fake anime")
    client = TestClient(app, follow_redirects=False)
    client.post(
        "/recommend/selected",
        data={"folders": "Anime"},
        headers={"accept": "text/html"},
    )

    response = client.post("/select/cancel", headers={"accept": "text/html"})

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    selection_response = client.get("/select")
    assert 'value="Anime" checked' not in selection_response.text


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


def test_other_feedback_requires_save_and_appends_comment_file(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "video.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)
    client.post("/recommend", headers={"accept": "text/html"})

    other_response = client.post("/feedback/other", headers={"accept": "text/html"})

    assert other_response.status_code == 303
    assert other_response.headers["location"] == "/feedback/other"

    home_response = client.get("/")
    assert home_response.status_code == 200
    assert "Other Feedback" in home_response.text
    assert "video.mp4" in home_response.text

    save_response = client.post(
        "/feedback/other/save",
        data={"comment": "Boring, could have been 5 minutes"},
        headers={"accept": "text/html"},
    )

    assert save_response.status_code == 303
    assert save_response.headers["location"] == "/"
    records = [
        json.loads(line)
        for line in (media_root / "other_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records == [
        {
            "path": str(media_file),
            "comment": "Boring, could have been 5 minutes",
            "created_at": records[0]["created_at"],
        }
    ]
    assert records[0]["created_at"]
    prefs_text = prefs_file.read_text(encoding="utf-8")
    assert '"likes": 0' in prefs_text
    assert '"dislikes": 0' in prefs_text
    assert '"pending": 0' in prefs_text
    assert '"play_count": 1' in prefs_text
    assert '"last_feedback": null' in prefs_text


def test_other_feedback_allows_empty_comment(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "video.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)
    client.post("/recommend", headers={"accept": "text/html"})
    client.post("/feedback/other", headers={"accept": "text/html"})

    response = client.post(
        "/feedback/other/save",
        data={"comment": ""},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 303
    records = [
        json.loads(line)
        for line in (media_root / "other_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["path"] == str(media_file)
    assert records[0]["comment"] == ""
    assert records[0]["created_at"]


def test_other_feedback_rejects_long_or_multiline_comment(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app)
    client.post("/recommend", headers={"accept": "text/html"})
    client.post("/feedback/other", headers={"accept": "text/html"})

    long_response = client.post("/feedback/other/save", data={"comment": "x" * 201})
    newline_response = client.post("/feedback/other/save", data={"comment": "line one\nline two"})

    assert long_response.status_code == 400
    assert long_response.json()["detail"] == "Comment must be 200 characters or fewer."
    assert newline_response.status_code == 400
    assert newline_response.json()["detail"] == "Comment must be a single line."
    assert not (media_root / "other_feedback.jsonl").exists()


def test_selected_other_feedback_returns_to_selection_after_save(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    movies = media_root / "Movies"
    anime.mkdir()
    movies.mkdir()
    media_file = anime / "episode.mp4"
    media_file.write_bytes(b"fake anime")
    (movies / "movie.mp4").write_bytes(b"fake movie")
    client = TestClient(app, follow_redirects=False)
    client.post(
        "/recommend/selected",
        data={"folders": "Anime"},
        headers={"accept": "text/html"},
    )
    client.post("/feedback/other", headers={"accept": "text/html"})

    response = client.post(
        "/feedback/other/save",
        data={"comment": "wrong category"},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/select"
    records = [
        json.loads(line)
        for line in (media_root / "other_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["path"] == str(media_file)
    assert records[0]["comment"] == "wrong category"
    selection_response = client.get("/select")
    assert 'value="Anime" checked' in selection_response.text
    assert 'value="Movies" checked' not in selection_response.text


def test_feedback_addressed_lists_paths_without_comments(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    first = media_root / "Anime" / "Steins Gate.mp4"
    second = media_root / "Anime" / "Attack On Titan" / "S1" / "e1.mp4"
    feedback_file = media_root / "other_feedback.jsonl"
    feedback_file.write_text(
        "\n".join(
            [
                json.dumps({"path": str(first), "comment": "boring", "created_at": "2026-06-03T10:00:00"}),
                json.dumps({"path": str(second), "comment": "", "created_at": "2026-06-03T10:01:00"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.get("/feedback/addressed")

    assert response.status_code == 200
    assert "Feedback Addressed" in response.text
    assert str(first.relative_to(media_root)) in response.text
    assert str(second.relative_to(media_root)) in response.text
    assert str(first) not in response.text
    assert str(second) not in response.text
    assert "boring" not in response.text
    assert 'name="line_numbers" value="0"' in response.text
    assert 'name="line_numbers" value="1"' in response.text


def test_feedback_addressed_save_removes_checked_records(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    first = media_root / "Anime" / "Steins Gate.mp4"
    second = media_root / "Anime" / "Attack On Titan" / "S1" / "e1.mp4"
    third = media_root / "Anime" / "Attack On Titan" / "S1" / "e2.mp4"
    feedback_file = media_root / "other_feedback.jsonl"
    feedback_file.write_text(
        "\n".join(
            [
                json.dumps({"path": str(first), "comment": "one", "created_at": "2026-06-03T10:00:00"}),
                json.dumps({"path": str(second), "comment": "two", "created_at": "2026-06-03T10:01:00"}),
                json.dumps({"path": str(third), "comment": "three", "created_at": "2026-06-03T10:02:00"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    client = TestClient(app, follow_redirects=False)

    response = client.post("/feedback/addressed", data={"line_numbers": ["0", "1"]})

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    remaining = [json.loads(line) for line in feedback_file.read_text(encoding="utf-8").splitlines()]
    assert [record["path"] for record in remaining] == [str(third)]


def test_feedback_addressed_cancel_does_not_modify_records(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "Anime" / "Steins Gate.mp4"
    original_text = json.dumps({"path": str(media_file), "comment": "keep", "created_at": "2026-06-03T10:00:00"}) + "\n"
    feedback_file = media_root / "other_feedback.jsonl"
    feedback_file.write_text(original_text, encoding="utf-8")
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert feedback_file.read_text(encoding="utf-8") == original_text


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
    assert f"Folders in <em>{media_root}</em>:" in response.text
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
