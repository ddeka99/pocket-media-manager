from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _default_data_dir() -> Path:
    env_value = os.getenv("PMM_DATA_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "data"


@dataclass(slots=True)
class AppPaths:
    data_dir: Path
    database_path: Path
    config_path: Path

    @classmethod
    def build(cls) -> "AppPaths":
        data_dir = _default_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            data_dir=data_dir,
            database_path=data_dir / "library.db",
            config_path=data_dir / "config.env",
        )


@dataclass(slots=True)
class RuntimeConfig:
    media_root: Path | None
    api_token: str

    @classmethod
    def default(cls) -> "RuntimeConfig":
        return cls(media_root=None, api_token=secrets.token_urlsafe(24))
