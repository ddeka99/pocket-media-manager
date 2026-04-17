from __future__ import annotations

import hashlib
from pathlib import Path

from .media import compatibility_for_ios, derive_title, extract_media_metadata, looks_like_video
from .storage import Database, utcnow_iso


def stable_media_id(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()


class LibraryScanner:
    def __init__(self, database: Database) -> None:
        self.database = database

    def scan(self, media_root: Path) -> int:
        records: list[dict[str, object]] = []
        for file_path in sorted(media_root.rglob("*")):
            if not file_path.is_file() or not looks_like_video(file_path):
                continue
            relative_path = file_path.relative_to(media_root).as_posix()
            compatible, reason = compatibility_for_ios(file_path)
            metadata = extract_media_metadata(file_path)
            records.append(
                {
                    "id": stable_media_id(relative_path),
                    "title": derive_title(file_path),
                    "file_name": file_path.name,
                    "relative_path": relative_path,
                    "absolute_path": str(file_path.resolve()),
                    "folder": file_path.parent.relative_to(media_root).as_posix()
                    if file_path.parent != media_root
                    else "",
                    "size_bytes": file_path.stat().st_size,
                    "duration_seconds": metadata["duration_seconds"],
                    "video_codec": metadata["video_codec"],
                    "audio_codec": metadata["audio_codec"],
                    "width": metadata["width"],
                    "height": metadata["height"],
                    "container": metadata["container"],
                    "compatible_for_direct_play": int(compatible),
                    "incompatible_reason": reason,
                    "updated_at": utcnow_iso(),
                }
            )

        self.database.replace_media_index(records)
        return len(records)
