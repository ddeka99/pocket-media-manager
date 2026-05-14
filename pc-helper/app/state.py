from __future__ import annotations

import secrets
from pathlib import Path


LAST_RECOMMENDED_PATH: Path | None = None
STREAM_TOKENS: dict[str, Path] = {}


def set_last_recommended(file_path: Path) -> None:
    global LAST_RECOMMENDED_PATH
    LAST_RECOMMENDED_PATH = file_path


def get_last_recommended() -> Path | None:
    return LAST_RECOMMENDED_PATH


def create_stream_token(file_path: Path) -> str:
    token = secrets.token_urlsafe(16)
    STREAM_TOKENS[token] = file_path
    return token


def get_stream_path(token: str) -> Path | None:
    return STREAM_TOKENS.get(token)


def clear_state() -> None:
    global LAST_RECOMMENDED_PATH
    LAST_RECOMMENDED_PATH = None
    STREAM_TOKENS.clear()
