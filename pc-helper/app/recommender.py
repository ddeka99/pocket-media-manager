from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


UNSEEN_BONUS = 4.0
LIKE_BONUS = 1.0
PENDING_BONUS = 0.35
DISLIKE_PENALTY = 0.8
MIN_WEIGHT_FLOOR = 0.12
COOLDOWN_DAYS = 7
COOLDOWN_MULTIPLIER = 0.25

DEFAULT_META = {
    "likes": 0,
    "dislikes": 0,
    "pending": 0,
    "play_count": 0,
    "last_played": None,
    "last_feedback": None,
}

FEEDBACK_ALIASES = {
    "like": "y",
    "dislike": "n",
    "pending": "p",
    "y": "y",
    "n": "n",
    "p": "p",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def empty_prefs() -> dict[str, Any]:
    return {"files": {}}


def load_prefs(prefs_file: Path) -> dict[str, Any]:
    if not prefs_file.exists():
        prefs = empty_prefs()
        save_prefs(prefs, prefs_file)
        return prefs

    try:
        prefs = json.loads(prefs_file.read_text(encoding="utf-8"))
    except Exception:
        return empty_prefs()

    if not isinstance(prefs, dict):
        return empty_prefs()
    files = prefs.get("files")
    if not isinstance(files, dict):
        prefs["files"] = {}
    return prefs


def save_prefs(prefs: dict[str, Any], prefs_file: Path) -> None:
    prefs_file.parent.mkdir(parents=True, exist_ok=True)
    prefs_file.write_text(json.dumps(prefs, indent=2), encoding="utf-8")


def reset_prefs(prefs_file: Path) -> None:
    save_prefs(empty_prefs(), prefs_file)


def find_media_files(
    media_root: Path,
    supported_extensions: set[str],
    exclude_folders: set[str] | None = None,
) -> list[Path]:
    exclude_folders = exclude_folders or set()
    if not media_root.exists() or not media_root.is_dir():
        return []

    files: list[Path] = []
    for path in media_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in supported_extensions:
            continue
        if any(part in exclude_folders for part in path.parts):
            continue
        files.append(path)
    files.sort(key=lambda item: str(item).lower())
    return files


def list_top_level_media_folders(
    media_root: Path,
    supported_extensions: set[str],
    exclude_folders: set[str] | None = None,
) -> list[Path]:
    exclude_folders = exclude_folders or set()
    if not media_root.exists() or not media_root.is_dir():
        return []

    folders: list[Path] = []
    for path in media_root.iterdir():
        if not path.is_dir():
            continue
        if path.name in exclude_folders:
            continue
        if find_media_files(path, supported_extensions, exclude_folders):
            folders.append(path)
    folders.sort(key=lambda item: item.name.lower())
    return folders


def find_media_files_in_folders(
    folders: list[Path],
    supported_extensions: set[str],
    exclude_folders: set[str] | None = None,
) -> list[Path]:
    files: list[Path] = []
    for folder in folders:
        files.extend(find_media_files(folder, supported_extensions, exclude_folders))
    files.sort(key=lambda item: str(item).lower())
    return files


def ensure_entries(prefs: dict[str, Any], files: list[Path]) -> dict[str, Any]:
    prefs.setdefault("files", {})
    for file_path in files:
        key = str(file_path)
        existing = prefs["files"].setdefault(key, {})
        for field_name, default_value in DEFAULT_META.items():
            existing.setdefault(field_name, default_value)
    return prefs


def cooldown_factor(meta: dict[str, Any]) -> float:
    last_played = meta.get("last_played")
    if not last_played:
        return 1.0
    try:
        last_dt = datetime.fromisoformat(last_played)
    except (TypeError, ValueError):
        return 1.0

    if datetime.now() - last_dt < timedelta(days=COOLDOWN_DAYS):
        return COOLDOWN_MULTIPLIER
    return 1.0


def compute_weight(meta: dict[str, Any]) -> float:
    likes = meta.get("likes", 0)
    dislikes = meta.get("dislikes", 0)
    pending = meta.get("pending", 0)
    play_count = meta.get("play_count", 0)

    weight = 1.0
    if play_count == 0:
        weight += UNSEEN_BONUS

    preference = 1.0 + (LIKE_BONUS * likes) + (PENDING_BONUS * pending) - (DISLIKE_PENALTY * dislikes)
    preference = max(preference, MIN_WEIGHT_FLOOR)

    weight *= preference
    weight *= cooldown_factor(meta)
    return max(weight, MIN_WEIGHT_FLOOR)


def pick_weighted(files: list[Path], prefs: dict[str, Any]) -> Path:
    if not files:
        raise ValueError("No media files available")

    weights = []
    for file_path in files:
        meta = prefs["files"].get(str(file_path), {})
        weights.append(compute_weight(meta))
    return random.choices(files, weights=weights, k=1)[0]


def record_play(prefs: dict[str, Any], file_path: Path) -> None:
    key = str(file_path)
    meta = prefs["files"][key]
    meta["play_count"] = meta.get("play_count", 0) + 1
    meta["last_played"] = now_iso()


def apply_feedback(prefs: dict[str, Any], file_path: Path, feedback: str) -> str:
    normalized = FEEDBACK_ALIASES.get(feedback)
    if normalized is None:
        raise ValueError(f"Unsupported feedback: {feedback}")

    key = str(file_path)
    meta = prefs["files"][key]
    if normalized == "y":
        meta["likes"] = meta.get("likes", 0) + 1
    elif normalized == "n":
        meta["dislikes"] = meta.get("dislikes", 0) + 1
    elif normalized == "p":
        meta["pending"] = meta.get("pending", 0) + 1
    meta["last_feedback"] = normalized
    return normalized
