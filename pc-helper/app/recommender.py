from __future__ import annotations

import json
import os
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


UNSEEN_BONUS = 8.0
LIKE_BONUS = 1.25
PENDING_BONUS = 0.35
DISLIKE_PENALTY = 1.75
MIN_WEIGHT_FLOOR = 0.12
RECENCY_TIE_BREAKER_MIN_MULTIPLIER = 0.9

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


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as temp_file:
            temp_file.write(text)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def save_prefs(prefs: dict[str, Any], prefs_file: Path) -> None:
    write_text_atomic(prefs_file, json.dumps(prefs, indent=2))


def reset_prefs(prefs_file: Path) -> None:
    save_prefs(empty_prefs(), prefs_file)


def find_media_files(
    media_root: Path,
    supported_extensions: set[str],
) -> list[Path]:
    if not media_root.exists() or not media_root.is_dir():
        return []

    files: list[Path] = []
    for path in media_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in supported_extensions:
            continue
        files.append(path)
    files.sort(key=lambda item: str(item).lower())
    return files


def list_top_level_media_folders(
    media_root: Path,
    supported_extensions: set[str],
) -> list[Path]:
    if not media_root.exists() or not media_root.is_dir():
        return []

    folders: list[Path] = []
    for path in media_root.iterdir():
        if not path.is_dir():
            continue
        if find_media_files(path, supported_extensions):
            folders.append(path)
    folders.sort(key=lambda item: item.name.lower())
    return folders


def find_media_files_in_folders(
    folders: list[Path],
    supported_extensions: set[str],
) -> list[Path]:
    files: list[Path] = []
    for folder in folders:
        files.extend(find_media_files(folder, supported_extensions))
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


def last_played_sort_value(meta: dict[str, Any]) -> datetime:
    last_played = meta.get("last_played")
    if not last_played:
        return datetime.min
    try:
        return datetime.fromisoformat(last_played)
    except (TypeError, ValueError):
        return datetime.min


def date_added_sort_value(file_path: Path) -> datetime:
    try:
        return datetime.fromtimestamp(file_path.stat().st_ctime)
    except OSError:
        return datetime.max


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
    return max(weight, MIN_WEIGHT_FLOOR)


def score_media_files(files: list[Path], prefs: dict[str, Any]) -> list[tuple[Path, float]]:
    scored = []
    for file_path in files:
        meta = prefs["files"].get(str(file_path), {})
        score = compute_weight(meta)
        last_played = meta.get("last_played")
        if last_played:
            tie_bucket = 1
            tie_value = last_played_sort_value(meta)
        else:
            tie_bucket = 0
            tie_value = date_added_sort_value(file_path)
        scored.append((file_path, score, tie_bucket, tie_value))

    scored.sort(key=lambda item: (-item[1], item[2], item[3], str(item[0]).lower()))
    return [(file_path, score) for file_path, score, _tie_bucket, _tie_value in scored]


def apply_recency_tie_breakers(
    files: list[Path],
    prefs: dict[str, Any],
    weights: list[float],
) -> list[float]:
    groups: dict[float, list[int]] = {}
    for index, weight in enumerate(weights):
        groups.setdefault(weight, []).append(index)

    adjusted = list(weights)
    for indices in groups.values():
        if len(indices) <= 1:
            continue

        recencies = {
            last_played_sort_value(prefs["files"].get(str(files[index]), {}))
            for index in indices
        }
        if len(recencies) <= 1:
            continue

        sorted_recencies = sorted(recencies)
        recency_rank = {
            recency: rank
            for rank, recency in enumerate(sorted_recencies)
        }
        max_rank = len(sorted_recencies) - 1
        for index in indices:
            meta = prefs["files"].get(str(files[index]), {})
            rank = recency_rank[last_played_sort_value(meta)]
            multiplier = 1.0 - ((1.0 - RECENCY_TIE_BREAKER_MIN_MULTIPLIER) * (rank / max_rank))
            adjusted[index] = max(weights[index] * multiplier, MIN_WEIGHT_FLOOR)

    return adjusted


def pick_weighted(files: list[Path], prefs: dict[str, Any]) -> Path:
    if not files:
        raise ValueError("No media files available")

    weights = []
    for file_path in files:
        meta = prefs["files"].get(str(file_path), {})
        weights.append(compute_weight(meta))
    adjusted_weights = apply_recency_tie_breakers(files, prefs, weights)
    return random.choices(files, weights=adjusted_weights, k=1)[0]


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
