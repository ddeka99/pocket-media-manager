from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from .auth import validate_token
from .config import AppPaths, RuntimeConfig
from .models import (
    AppConfigPayload,
    AppConfigResponse,
    FeedbackPayload,
    HealthResponse,
    LibraryScanJob,
    MediaItem,
    MediaListResponse,
    PairingResponse,
    PlaybackProgress,
    PlaybackProgressPayload,
    StreamResponse,
)
from .scanner import LibraryScanner
from .storage import Database


paths = AppPaths.build()
database = Database(paths.database_path)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        config = database.load_config()
    except Exception:
        config = RuntimeConfig.default()
        database.initialize(config)
    else:
        database.initialize(config)
    yield


app = FastAPI(title="Pocket Media Manager Helper", version="0.1.0", lifespan=lifespan)


def current_config() -> RuntimeConfig:
    return database.load_config()


def token_dependency(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> None:
    config = current_config()
    validate_token(config.api_token, authorization=authorization, token=token)


Authenticated = Annotated[None, Depends(token_dependency)]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    config = current_config()
    return HealthResponse(
        media_root_configured=bool(config.media_root),
        library_count=database.count_media_items(),
    )


@app.get("/pairing", response_model=PairingResponse)
def pairing() -> PairingResponse:
    return PairingResponse(api_token=current_config().api_token)


@app.get("/config", response_model=AppConfigResponse)
def get_config(_: Authenticated) -> AppConfigResponse:
    config = current_config()
    return AppConfigResponse(
        media_root=str(config.media_root) if config.media_root else None,
        api_token=config.api_token,
    )


@app.put("/config", response_model=AppConfigResponse)
def set_config(payload: AppConfigPayload, _: Authenticated) -> AppConfigResponse:
    media_root = Path(payload.media_root).expanduser().resolve()
    if not media_root.exists() or not media_root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configured media root must be an existing directory",
        )
    config = database.update_media_root(media_root)
    return AppConfigResponse(media_root=str(config.media_root), api_token=config.api_token)


@app.post("/library/rescan", response_model=LibraryScanJob)
def rescan_library(_: Authenticated) -> LibraryScanJob:
    config = current_config()
    if not config.media_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure a media root before scanning",
        )
    job_id = database.create_scan_job()
    scanner = LibraryScanner(database)
    scanned_files = scanner.scan(config.media_root)
    database.finish_scan_job(job_id, scanned_files)
    row = database.latest_scan_job()
    assert row is not None
    return LibraryScanJob.model_validate(dict(row))


@app.get("/library", response_model=MediaListResponse)
def list_library(_: Authenticated) -> MediaListResponse:
    return MediaListResponse(items=database.list_media_items())


@app.get("/library/{media_item_id}", response_model=MediaItem)
def get_media_item(media_item_id: str, _: Authenticated) -> MediaItem:
    item = database.get_media_item(media_item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return item


@app.post(
    "/library/{media_item_id}/progress",
    response_model=PlaybackProgress,
)
def save_progress(
    media_item_id: str,
    payload: PlaybackProgressPayload,
    _: Authenticated,
) -> PlaybackProgress:
    if not database.get_media_item(media_item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    return database.save_progress(
        media_item_id=media_item_id,
        position_seconds=payload.position_seconds,
        duration_seconds=payload.duration_seconds,
        completed=payload.completed,
    )


@app.post("/library/{media_item_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def add_feedback(media_item_id: str, payload: FeedbackPayload, _: Authenticated) -> None:
    if not database.get_media_item(media_item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    database.add_feedback(media_item_id, payload.feedback_type)


@app.post("/library/{media_item_id}/stream", response_model=StreamResponse)
def get_stream_url(media_item_id: str, request: Request, _: Authenticated) -> StreamResponse:
    if not database.get_media_item(media_item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found")
    token = current_config().api_token
    stream_url = str(request.base_url).rstrip("/") + f"/media/{media_item_id}/stream?token={token}"
    return StreamResponse(stream_url=stream_url)


@app.get("/media/{media_item_id}/stream")
def stream_media(media_item_id: str, token: str) -> FileResponse:
    validate_token(current_config().api_token, token=token)
    media_path = database.absolute_path_for_item(media_item_id)
    if not media_path or not media_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file missing")
    return FileResponse(path=media_path, filename=media_path.name)
