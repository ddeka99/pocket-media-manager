from __future__ import annotations

import secrets
from pathlib import Path


LAST_RECOMMENDED_PATH: Path | None = None
STREAM_TOKENS: dict[str, Path] = {}
AWAITING_FEEDBACK = False
SELECTED_FOLDER_NAMES: list[str] = []


def set_last_recommended(file_path: Path) -> None:
    global LAST_RECOMMENDED_PATH
    LAST_RECOMMENDED_PATH = file_path


def set_awaiting_feedback(value: bool) -> None:
    global AWAITING_FEEDBACK
    AWAITING_FEEDBACK = value


def is_awaiting_feedback() -> bool:
    return AWAITING_FEEDBACK


def get_last_recommended() -> Path | None:
    return LAST_RECOMMENDED_PATH


def set_selected_folder_names(folder_names: list[str]) -> None:
    global SELECTED_FOLDER_NAMES
    SELECTED_FOLDER_NAMES = list(folder_names)


def get_selected_folder_names() -> list[str]:
    return list(SELECTED_FOLDER_NAMES)


def clear_selected_folder_names() -> None:
    SELECTED_FOLDER_NAMES.clear()


def create_stream_token(file_path: Path) -> str:
    token = secrets.token_urlsafe(16)
    STREAM_TOKENS[token] = file_path
    return token


def get_stream_path(token: str) -> Path | None:
    return STREAM_TOKENS.get(token)


def clear_state() -> None:
    global LAST_RECOMMENDED_PATH, AWAITING_FEEDBACK
    LAST_RECOMMENDED_PATH = None
    AWAITING_FEEDBACK = False
    clear_selected_folder_names()
    STREAM_TOKENS.clear()
