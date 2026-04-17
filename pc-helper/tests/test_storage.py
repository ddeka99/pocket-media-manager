from __future__ import annotations

from pathlib import Path

from app.config import RuntimeConfig
from app.storage import Database


def test_database_persists_config_and_progress(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    database.initialize(RuntimeConfig(media_root=tmp_path, api_token="secret-token"))

    database.replace_media_index(
        [
            {
                "id": "media-1",
                "title": "Sample",
                "file_name": "sample.mp4",
                "relative_path": "sample.mp4",
                "absolute_path": str(tmp_path / "sample.mp4"),
                "folder": "",
                "size_bytes": 10,
                "duration_seconds": 120.0,
                "video_codec": "h264",
                "audio_codec": "aac",
                "width": 1920,
                "height": 1080,
                "container": "mp4",
                "compatible_for_direct_play": 1,
                "incompatible_reason": None,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ]
    )

    progress = database.save_progress("media-1", 30.0, 120.0, False)
    assert progress.position_seconds == 30.0

    items = database.list_media_items()
    assert len(items) == 1
    assert items[0].playback is not None
    assert items[0].playback.position_seconds == 30.0


def test_database_updates_media_root(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    database.initialize(RuntimeConfig(media_root=None, api_token="secret-token"))
    updated = database.update_media_root(tmp_path / "media")
    assert updated.media_root == tmp_path / "media"
