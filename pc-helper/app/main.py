from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse

from .config import Settings, get_settings
from . import recommender
from . import state


app = FastAPI(title="Pocket Media Recommender Helper", version="0.1.0")


def build_infuse_url(stream_url: str, filename: str) -> str:
    query = urlencode({"url": stream_url, "filename": filename})
    return f"infuse://x-callback-url/play?{query}"


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _settings() -> Settings:
    return get_settings()


def _load_current_prefs(settings: Settings) -> dict[str, Any]:
    return recommender.load_prefs(settings.prefs_file)


def _stream_url(settings: Settings, token: str) -> str:
    return f"{settings.public_base_url}/stream/{token}"


def _feedback_urls(settings: Settings) -> dict[str, str]:
    return {
        "like": f"{settings.public_base_url}/feedback/like",
        "dislike": f"{settings.public_base_url}/feedback/dislike",
        "pending": f"{settings.public_base_url}/feedback/pending",
    }


def _select_next(settings: Settings) -> dict[str, str]:
    files = recommender.find_media_files(
        settings.media_root,
        settings.supported_extensions,
        settings.exclude_folders,
    )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No supported media files found under {settings.media_root}",
        )

    prefs = _load_current_prefs(settings)
    recommender.ensure_entries(prefs, files)
    selected = recommender.pick_weighted(files, prefs)
    recommender.record_play(prefs, selected)
    recommender.save_prefs(prefs, settings.prefs_file)

    state.set_last_recommended(selected)
    token = state.create_stream_token(selected)
    stream_url = _stream_url(settings, token)
    return {
        "file_name": selected.name,
        "path": str(selected),
        "stream_url": stream_url,
        "infuse_url": build_infuse_url(stream_url, selected.name),
    }


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/next", response_model=None)
def next_video(redirect: str | None = None) -> dict[str, Any] | RedirectResponse:
    settings = _settings()
    selected = _select_next(settings)
    if redirect == "infuse":
        return RedirectResponse(selected["infuse_url"])

    return {
        "file_name": selected["file_name"],
        "stream_url": selected["stream_url"],
        "infuse_url": selected["infuse_url"],
        "feedback": _feedback_urls(settings),
    }


@app.get("/stream/{token}")
def stream_media(token: str) -> FileResponse:
    settings = _settings()
    media_path = state.get_stream_path(token)
    if media_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown stream token")

    if not _is_under(media_path, settings.media_root):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media path is not allowed")

    if not media_path.exists() or not media_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file missing")

    return FileResponse(path=media_path, filename=media_path.name, media_type="application/octet-stream")


def _feedback_response(feedback: str) -> dict[str, Any]:
    settings = _settings()
    last_recommended = state.get_last_recommended()
    if last_recommended is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation has been made yet")

    prefs = _load_current_prefs(settings)
    recommender.ensure_entries(prefs, [last_recommended])
    recommender.apply_feedback(prefs, last_recommended, feedback)
    recommender.save_prefs(prefs, settings.prefs_file)
    return {"ok": True, "feedback": feedback, "file_name": last_recommended.name}


@app.post("/feedback/like")
def feedback_like() -> dict[str, Any]:
    return _feedback_response("like")


@app.post("/feedback/dislike")
def feedback_dislike() -> dict[str, Any]:
    return _feedback_response("dislike")


@app.post("/feedback/pending")
def feedback_pending() -> dict[str, Any]:
    return _feedback_response("pending")


@app.get("/last")
def last() -> dict[str, Any]:
    settings = _settings()
    last_recommended = state.get_last_recommended()
    if last_recommended is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation has been made yet")

    prefs = _load_current_prefs(settings)
    recommender.ensure_entries(prefs, [last_recommended])
    meta = prefs["files"][str(last_recommended)]
    return {
        "file_name": last_recommended.name,
        "path": str(last_recommended),
        "meta": meta,
    }
