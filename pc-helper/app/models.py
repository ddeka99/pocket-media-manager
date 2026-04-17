from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FeedbackType(str, Enum):
    liked = "liked"
    disliked = "disliked"
    save_for_later = "save_for_later"


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str = "pocket-media-manager-helper"
    api_version: str = "v1"
    media_root_configured: bool
    library_count: int


class PairingResponse(BaseModel):
    api_token: str


class AppConfigPayload(BaseModel):
    media_root: str


class AppConfigResponse(BaseModel):
    media_root: str | None
    api_token: str


class PlaybackProgressPayload(BaseModel):
    position_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    completed: bool = False


class PlaybackProgress(BaseModel):
    media_item_id: str
    position_seconds: float = 0
    duration_seconds: float | None = None
    completed: bool = False
    updated_at: datetime | None = None


class FeedbackPayload(BaseModel):
    feedback_type: FeedbackType


class FeedbackEvent(BaseModel):
    media_item_id: str
    feedback_type: FeedbackType
    created_at: datetime


class MediaItem(BaseModel):
    id: str
    title: str
    file_name: str
    relative_path: str
    folder: str
    size_bytes: int
    duration_seconds: float | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    width: int | None = None
    height: int | None = None
    container: str | None = None
    compatible_for_direct_play: bool = True
    incompatible_reason: str | None = None
    updated_at: datetime
    playback: PlaybackProgress | None = None
    feedback: list[FeedbackType] = Field(default_factory=list)


class MediaListResponse(BaseModel):
    items: list[MediaItem]


class StreamResponse(BaseModel):
    stream_url: str
    expires_in_seconds: int = 3600


class LibraryScanJob(BaseModel):
    id: int
    status: str
    scanned_files: int
    started_at: datetime
    completed_at: datetime | None = None
