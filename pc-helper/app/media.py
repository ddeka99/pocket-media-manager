from __future__ import annotations

import json
import mimetypes
import subprocess
from pathlib import Path


VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}

IOS_DIRECT_PLAY_EXTENSIONS = {".mp4", ".m4v", ".mov"}


def looks_like_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def guess_media_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def derive_title(path: Path) -> str:
    name = path.stem.replace("_", " ").replace(".", " ")
    return " ".join(part for part in name.split() if part)


def compatibility_for_ios(path: Path) -> tuple[bool, str | None]:
    ext = path.suffix.lower()
    if ext in IOS_DIRECT_PLAY_EXTENSIONS:
        return True, None
    return False, f"{ext} is not marked for direct iPhone playback in v1"


def extract_media_metadata(path: Path) -> dict[str, object]:
    metadata: dict[str, object] = {
        "duration_seconds": None,
        "video_codec": None,
        "audio_codec": None,
        "width": None,
        "height": None,
        "container": path.suffix.lower().lstrip(".") or None,
    }
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-print_format",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return metadata

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return metadata

    format_data = parsed.get("format", {})
    streams = parsed.get("streams", [])
    duration_value = format_data.get("duration")
    if duration_value is not None:
        try:
            metadata["duration_seconds"] = float(duration_value)
        except (TypeError, ValueError):
            metadata["duration_seconds"] = None

    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type == "video":
            metadata["video_codec"] = stream.get("codec_name")
            metadata["width"] = stream.get("width")
            metadata["height"] = stream.get("height")
        elif codec_type == "audio" and not metadata["audio_codec"]:
            metadata["audio_codec"] = stream.get("codec_name")
    return metadata
