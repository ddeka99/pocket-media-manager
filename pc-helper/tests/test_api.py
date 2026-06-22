from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import state
from app.main import app, build_infuse_url, build_vlc_url


def configure_env(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    media_root = tmp_path / "media"
    media_root.mkdir()
    prefs_file = media_root / "_mpv_prefs.json"
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    monkeypatch.delenv("PREFS_FILE", raising=False)
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://192.168.1.50:8787")
    monkeypatch.setenv("SUPPORTED_EXTENSIONS", ".mp4,.mkv")
    monkeypatch.setenv("PLAYER", "infuse")
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


def test_home_links_app_icon(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert '<link rel="icon" type="image/png" sizes="128x128" href="/pocket-manager-icon.png">' in response.text
    assert '<link rel="apple-touch-icon" href="/pocket-manager-icon.png">' in response.text
    assert '<link rel="manifest" href="/manifest.webmanifest">' in response.text


def test_app_icon_and_manifest_are_available(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    icon_response = client.get("/pocket-manager-icon.png")
    favicon_response = client.get("/favicon.ico")
    manifest_response = client.get("/manifest.webmanifest")

    assert icon_response.status_code == 200
    assert icon_response.headers["content-type"] == "image/png"
    assert icon_response.content.startswith(b"\x89PNG")
    assert favicon_response.status_code == 200
    assert favicon_response.headers["content-type"] == "image/png"
    assert manifest_response.status_code == 200
    assert manifest_response.json()["icons"] == [
        {
            "src": "/pocket-manager-icon.png",
            "sizes": "128x128",
            "type": "image/png",
        }
    ]


def test_home_shows_recommend_and_reset(monkeypatch, tmp_path):
    configure_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Recommend" in response.text
    assert "Recommend with Selections" in response.text
    assert "Explore" in response.text
    assert "Scoreboard" in response.text
    assert "Address Other Feedback" in response.text
    assert "Reset Preferences" in response.text
    assert "Excluded folders" not in response.text


def test_scoreboard_lists_recommendable_files_by_score(monkeypatch, tmp_path):
    media_root, prefs_file = configure_env(monkeypatch, tmp_path)
    new_file = media_root / "new.mp4"
    enjoyed_file = media_root / "enjoyed.mp4"
    old_file = media_root / "old.mp4"
    recent_file = media_root / "recent.mp4"
    blocked_file = media_root / "blocked.mp4"
    for media_file in [new_file, enjoyed_file, old_file, recent_file, blocked_file]:
        media_file.write_bytes(b"fake media")
    prefs_file.write_text(
        json.dumps(
            {
                "files": {
                    str(enjoyed_file): {
                        "likes": 2,
                        "dislikes": 0,
                        "pending": 0,
                        "play_count": 1,
                        "last_played": "2026-01-01T00:00:00",
                        "last_feedback": "y",
                    },
                    str(old_file): {
                        "likes": 0,
                        "dislikes": 0,
                        "pending": 0,
                        "play_count": 1,
                        "last_played": "2024-01-01T00:00:00",
                        "last_feedback": None,
                    },
                    str(recent_file): {
                        "likes": 0,
                        "dislikes": 0,
                        "pending": 0,
                        "play_count": 1,
                        "last_played": "2026-01-01T00:00:00",
                        "last_feedback": None,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (media_root / "other_feedback.jsonl").write_text(
        json.dumps({"path": str(blocked_file), "type": "hold", "created_at": "2026-06-04T10:00:00"}) + "\n",
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.get("/scoreboard")

    assert response.status_code == 200
    assert '<a class="button secondary" href="/">Back</a>' in response.text
    assert "blocked.mp4" not in response.text
    assert response.text.index("new.mp4") < response.text.index("enjoyed.mp4")
    assert response.text.index("enjoyed.mp4") < response.text.index("old.mp4")
    assert response.text.index("old.mp4") < response.text.index("recent.mp4")
    assert "9.00" in response.text
    assert "3.50" in response.text


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
    assert "Something Else" in response.text


def test_other_feedback_is_hidden_when_record_already_exists(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "video.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app)
    client.post("/recommend", headers={"accept": "text/html"})
    (media_root / "other_feedback.jsonl").write_text(
        json.dumps({"path": str(media_file), "type": "fix", "created_at": "2026-06-04T10:00:00"}) + "\n",
        encoding="utf-8",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "Something Else feedback already exists for this file." in response.text
    assert "/feedback/other" not in response.text


def test_duplicate_other_feedback_post_is_rejected(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "video.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app)
    client.post("/recommend", headers={"accept": "text/html"})
    (media_root / "other_feedback.jsonl").write_text(
        json.dumps({"path": str(media_file), "type": "fix", "created_at": "2026-06-04T10:00:00"}) + "\n",
        encoding="utf-8",
    )

    response = client.post("/feedback/other")

    assert response.status_code == 409
    assert response.json()["detail"] == "Something Else feedback already exists for this file"


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
    movies = media_root / "Movies"
    nested = anime / "Series"
    nested.mkdir(parents=True)
    empty.mkdir()
    movies.mkdir()
    (media_root / "loose.mp4").write_bytes(b"fake media")
    (media_root / "notes.txt").write_text("not media", encoding="utf-8")
    (nested / "episode.mkv").write_bytes(b"fake media")
    (movies / "hidden.mp4").write_bytes(b"fake media")
    client = TestClient(app)

    response = client.get("/explore")

    assert response.status_code == 200
    assert "Explore" in response.text
    assert f"Browsing <em>{media_root}</em>" in response.text
    assert ">Home<" in response.text
    assert "loose.mp4" in response.text
    assert "Anime" in response.text
    assert "Movies" in response.text
    assert "notes.txt" not in response.text
    assert "Empty" not in response.text


def test_unresolved_something_else_blocks_recommendations_and_explore(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    blocked_folder = media_root / "Anime"
    available_folder = media_root / "Movies"
    blocked_folder.mkdir()
    available_folder.mkdir()
    blocked_file = blocked_folder / "blocked.mp4"
    available_file = available_folder / "available.mp4"
    blocked_file.write_bytes(b"fake blocked")
    available_file.write_bytes(b"fake available")
    (media_root / "other_feedback.jsonl").write_text(
        json.dumps({"path": str(blocked_file), "type": "remake", "created_at": "2026-06-11T10:00:00"}) + "\n",
        encoding="utf-8",
    )
    client = TestClient(app)

    explore_response = client.get("/explore")
    recommend_response = client.post("/recommend", headers={"accept": "text/html"})

    assert recommend_response.status_code == 200
    assert "available.mp4" in recommend_response.text
    assert "blocked.mp4" not in recommend_response.text
    assert explore_response.status_code == 200
    assert "Movies" in explore_response.text
    assert "Anime" not in explore_response.text
    assert "blocked.mp4" not in explore_response.text


def test_selected_recommend_ignores_files_with_unresolved_something_else(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    anime = media_root / "Anime"
    anime.mkdir()
    blocked_file = anime / "blocked.mp4"
    available_file = anime / "available.mp4"
    blocked_file.write_bytes(b"fake blocked")
    available_file.write_bytes(b"fake available")
    (media_root / "other_feedback.jsonl").write_text(
        json.dumps({"path": str(blocked_file), "type": "fix", "created_at": "2026-06-11T10:00:00"}) + "\n",
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.post(
        "/recommend/selected",
        data={"folders": "Anime"},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 200
    assert "available.mp4" in response.text
    assert "blocked.mp4" not in response.text


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


def test_something_else_requires_type_and_appends_feedback_file(monkeypatch, tmp_path):
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
    assert "Describe Change Required" in home_response.text
    assert "video.mp4" in home_response.text
    assert "Remake" in home_response.text
    assert "Fix" in home_response.text
    assert "Trim" in home_response.text
    assert "Hold" in home_response.text
    assert "/feedback/other/cancel" in home_response.text

    save_response = client.post(
        "/feedback/other/save",
        data={"feedback_type": "trim"},
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
            "type": "trim",
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


def test_something_else_cancel_returns_to_feedback_page(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app, follow_redirects=False)
    client.post("/recommend", headers={"accept": "text/html"})
    client.post("/feedback/other", headers={"accept": "text/html"})

    response = client.post(
        "/feedback/other/cancel",
        headers={"accept": "text/html"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    feedback_response = client.get("/")
    assert "Feedback" in feedback_response.text
    assert "Something Else" in feedback_response.text
    assert not (media_root / "other_feedback.jsonl").exists()


def test_something_else_rejects_invalid_type(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    (media_root / "video.mp4").write_bytes(b"fake media")
    client = TestClient(app)
    client.post("/recommend", headers={"accept": "text/html"})
    client.post("/feedback/other", headers={"accept": "text/html"})

    response = client.post("/feedback/other/save", data={"feedback_type": "unknown"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported other feedback type"
    assert not (media_root / "other_feedback.jsonl").exists()


def test_stale_other_feedback_save_does_not_append_duplicate(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    media_file = media_root / "video.mp4"
    media_file.write_bytes(b"fake media")
    client = TestClient(app)
    client.post("/recommend", headers={"accept": "text/html"})
    client.post("/feedback/other", headers={"accept": "text/html"})
    original_record = json.dumps(
        {"path": str(media_file), "type": "fix", "created_at": "2026-06-04T10:00:00"}
    )
    feedback_file = media_root / "other_feedback.jsonl"
    feedback_file.write_text(original_record + "\n", encoding="utf-8")

    response = client.post("/feedback/other/save", data={"feedback_type": "remake"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Something Else feedback already exists for this file"
    assert feedback_file.read_text(encoding="utf-8") == original_record + "\n"


def test_selected_something_else_returns_to_selection_after_save(monkeypatch, tmp_path):
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
        data={"feedback_type": "hold"},
        headers={"accept": "text/html"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/select"
    records = [
        json.loads(line)
        for line in (media_root / "other_feedback.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["path"] == str(media_file)
    assert records[0]["type"] == "hold"
    selection_response = client.get("/select")
    assert 'value="Anime" checked' not in selection_response.text
    assert 'value="Movies" checked' not in selection_response.text


def test_feedback_addressed_lists_paths_without_comments(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    first = media_root / "Anime" / "Steins Gate" / "Steins Gate Opening.mp4"
    second = media_root / "Anime" / "Attack On Titan" / "S1" / "e1.mp4"
    feedback_file = media_root / "other_feedback.jsonl"
    feedback_file.write_text(
        "\n".join(
            [
                json.dumps({"path": str(first), "type": "remake", "created_at": "2026-06-03T10:00:00"}),
                json.dumps({"path": str(second), "type": "trim", "created_at": "2026-06-03T10:01:00"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    client = TestClient(app)

    response = client.get("/feedback/addressed")

    assert response.status_code == 200
    assert "Address Other Feedback" in response.text
    assert "Remake" in response.text
    assert "Trim" in response.text
    assert '<span class="tag">Anime</span> <span class="file-name">Steins Gate Opening.mp4</span>' in response.text
    assert '<span class="tag">Anime</span> <span class="file-name">e1.mp4</span>' in response.text
    assert str(first.relative_to(media_root)) not in response.text
    assert str(second.relative_to(media_root)) not in response.text
    assert str(first) not in response.text
    assert str(second) not in response.text
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
                json.dumps({"path": str(first), "type": "remake", "created_at": "2026-06-03T10:00:00"}),
                json.dumps({"path": str(second), "type": "fix", "created_at": "2026-06-03T10:01:00"}),
                json.dumps({"path": str(third), "type": "hold", "created_at": "2026-06-03T10:02:00"}),
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
    original_text = json.dumps({"path": str(media_file), "type": "fix", "created_at": "2026-06-03T10:00:00"}) + "\n"
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
    assert '<button type="submit" form="selection-form">Recommend</button>' in response.text
    assert '<button class="secondary" type="submit" form="selection-cancel-form">Cancel</button>' in response.text
    assert 'data-select-folders="all">Select All</button>' in response.text
    assert 'data-select-folders="none">Deselect All</button>' in response.text
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


def test_stream_tokens_keep_only_latest_30(monkeypatch, tmp_path):
    media_root, _ = configure_env(monkeypatch, tmp_path)
    tokens = []
    media_files = []
    for index in range(31):
        media_file = media_root / f"video-{index}.mp4"
        media_file.write_bytes(b"fake media")
        media_files.append(media_file)
        tokens.append(state.create_stream_token(media_file))

    assert state.get_stream_path(tokens[0]) is None
    assert state.get_stream_path(tokens[1]) == media_files[1]
    assert state.get_stream_path(tokens[-1]) == media_files[-1]


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
