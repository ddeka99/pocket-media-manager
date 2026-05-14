from __future__ import annotations

import json
from datetime import datetime

from app import recommender


def test_load_prefs_creates_missing_file(tmp_path):
    prefs_file = tmp_path / "_mpv_prefs.json"

    prefs = recommender.load_prefs(prefs_file)

    assert prefs == {"files": {}}
    assert json.loads(prefs_file.read_text(encoding="utf-8")) == {"files": {}}


def test_load_prefs_recovers_from_corrupt_json(tmp_path):
    prefs_file = tmp_path / "_mpv_prefs.json"
    prefs_file.write_text("{bad json", encoding="utf-8")

    assert recommender.load_prefs(prefs_file) == {"files": {}}


def test_ensure_entries_preserves_existing_fields(tmp_path):
    media_file = tmp_path / "video.mp4"
    media_file.write_text("fake", encoding="utf-8")
    prefs = {
        "files": {
            str(media_file): {
                "likes": 2,
                "custom_note": "keep this",
            }
        }
    }

    recommender.ensure_entries(prefs, [media_file])

    meta = prefs["files"][str(media_file)]
    assert meta["likes"] == 2
    assert meta["custom_note"] == "keep this"
    assert meta["play_count"] == 0
    assert meta["last_feedback"] is None


def test_compute_weight_preserves_tuning_behavior():
    base = {**recommender.DEFAULT_META, "play_count": 1}
    unseen = {**recommender.DEFAULT_META, "play_count": 0}
    liked = {**base, "likes": 1}
    pending = {**base, "pending": 1}
    disliked = {**base, "dislikes": 100}
    recent = {**base, "last_played": datetime.now().isoformat(timespec="seconds")}

    assert recommender.compute_weight(unseen) > recommender.compute_weight(base)
    assert recommender.compute_weight(liked) > recommender.compute_weight(base)
    assert recommender.compute_weight(pending) > recommender.compute_weight(base)
    assert recommender.compute_weight(disliked) == recommender.MIN_WEIGHT_FLOOR
    assert recommender.compute_weight(recent) < recommender.compute_weight(base)


def test_pick_weighted_returns_available_file(tmp_path):
    files = [tmp_path / "one.mp4", tmp_path / "two.mp4"]
    for media_file in files:
        media_file.write_text("fake", encoding="utf-8")
    prefs = recommender.ensure_entries({"files": {}}, files)

    assert recommender.pick_weighted(files, prefs) in files


def test_record_play_and_feedback_use_existing_json_shape(tmp_path):
    media_file = tmp_path / "video.mp4"
    media_file.write_text("fake", encoding="utf-8")
    prefs = recommender.ensure_entries({"files": {}}, [media_file])

    recommender.record_play(prefs, media_file)
    recommender.apply_feedback(prefs, media_file, "like")

    meta = prefs["files"][str(media_file)]
    assert meta["play_count"] == 1
    assert meta["last_played"]
    assert meta["likes"] == 1
    assert meta["last_feedback"] == "y"
