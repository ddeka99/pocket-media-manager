from __future__ import annotations

from pathlib import Path
from typing import Any
from html import escape
import json
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from .config import Settings, get_settings
from . import recommender
from . import state


app = FastAPI(title="Pocket Media Recommender Helper", version="0.1.0")


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f7f7f4;
      color: #181818;
    }}
    main {{
      width: min(26rem, calc(100vw - 2rem));
      display: grid;
      gap: 1rem;
    }}
    h1 {{ font-size: 1.45rem; margin: 0; }}
    p {{ margin: 0; line-height: 1.4; color: #555; }}
    ul {{ margin: 0; padding-left: 1.2rem; color: #555; }}
    li {{ line-height: 1.4; }}
    form {{ margin: 0; }}
    .stack {{ display: grid; gap: .7rem; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }}
    .status {{
      border-top: 1px solid #d8d8d2;
      padding-top: 1rem;
      display: grid;
      gap: .45rem;
    }}
    .label {{
      color: #181818;
      font-weight: 650;
    }}
    button, a.button {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #181818;
      border-radius: 6px;
      padding: .9rem 1rem;
      background: #181818;
      color: white;
      font: inherit;
      text-align: center;
      text-decoration: none;
      cursor: pointer;
    }}
    button.secondary, a.secondary {{ background: white; color: #181818; }}
    button.danger {{ border-color: #9d2020; background: #9d2020; }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>"""
    )


def build_infuse_url(stream_url: str, filename: str) -> str:
    query = urlencode({"url": stream_url, "filename": filename})
    return f"infuse://x-callback-url/play?{query}"


def build_vlc_url(stream_url: str) -> str:
    query = urlencode({"url": stream_url})
    return f"vlc-x-callback://x-callback-url/stream?{query}"


def build_player_url(settings: Settings, stream_url: str, filename: str) -> str:
    if settings.player == "vlc":
        return build_vlc_url(stream_url)
    return build_infuse_url(stream_url, filename)


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


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def _excluded_folders_html(settings: Settings) -> str:
    folders = sorted(settings.exclude_folders, key=str.lower)
    if not folders:
        return '<p>No excluded folders configured.</p>'

    items = "\n".join(f"<li>{escape(folder)}</li>" for folder in folders)
    return f"<ul>{items}</ul>"


def _home_page(settings: Settings) -> HTMLResponse:
    last_recommended = state.get_last_recommended()
    if state.is_awaiting_feedback() and last_recommended is not None:
        return _feedback_page(last_recommended.name)

    excluded_folders = _excluded_folders_html(settings)
    return _page(
        "Pocket Media Manager",
        f"""<h1>Pocket Media Manager</h1>
<div class="stack">
  <form method="post" action="/recommend">
    <button type="submit">Recommend</button>
  </form>
  <form method="get" action="/select">
    <button class="secondary" type="submit">Recommend with Selections</button>
  </form>
  <form method="get" action="/reset">
    <button class="secondary" type="submit">Reset Preferences</button>
  </form>
</div>
<section class="status">
  <p class="label">Excluded folders</p>
  {excluded_folders}
</section>""",
    )


def _selection_page(settings: Settings, error: str | None = None) -> HTMLResponse:
    folders = recommender.list_top_level_media_folders(
        settings.media_root,
        settings.supported_extensions,
        settings.exclude_folders,
    )
    if not folders:
        return _page(
            "Select Folders",
            """<h1>Recommend with Selections</h1>
<p>No top-level folders with supported media were found.</p>
<a class="button secondary" href="/">Back</a>""",
        )

    error_html = f'<p style="color:#9d2020;">{escape(error)}</p>' if error else ""
    folder_controls = "\n".join(
        f"""<label class="check">
  <input type="checkbox" name="folders" value="{escape(folder.name, quote=True)}">
  <span>{escape(folder.name)}</span>
</label>"""
        for folder in folders
    )
    media_root_label = escape(str(settings.media_root))
    return _page(
        "Select Folders",
        f"""<h1>Recommend with Selections</h1>
{error_html}
<form method="post" action="/recommend/selected" class="stack">
  <p>Folders in <em>{media_root_label}</em>:</p>
  <div class="stack">
    {folder_controls}
  </div>
  <button type="submit">Recommend</button>
</form>
<a class="button secondary" href="/">Cancel</a>""",
    )


def _feedback_page(file_name: str, player_url: str | None = None) -> HTMLResponse:
    escaped_name = escape(file_name)
    opener = ""
    fallback = ""
    if player_url:
        escaped_url = escape(player_url, quote=True)
        script_url = json.dumps(player_url)
        opener = f"""<script>
  setTimeout(function () {{
    window.location.href = {script_url};
  }}, 100);
</script>"""
        fallback = f'<a class="button secondary" href="{escaped_url}">Open Player</a>'

    return _page(
        "Feedback",
        f"""{opener}
<h1>Feedback</h1>
<p>{escaped_name}</p>
<div class="stack">
  {fallback}
  <div class="row">
    <form method="post" action="/feedback/like"><button type="submit">Like</button></form>
    <form method="post" action="/feedback/dislike"><button type="submit">Dislike</button></form>
  </div>
  <div class="row">
    <form method="post" action="/feedback/pending"><button type="submit">Pending</button></form>
    <form method="post" action="/feedback/skip"><button class="secondary" type="submit">Skip</button></form>
  </div>
</div>""",
    )


def _select_from_files(settings: Settings, files: list[Path]) -> dict[str, str]:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No supported media files found",
        )

    prefs = _load_current_prefs(settings)
    recommender.ensure_entries(prefs, files)
    selected = recommender.pick_weighted(files, prefs)
    recommender.record_play(prefs, selected)
    recommender.save_prefs(prefs, settings.prefs_file)

    state.set_last_recommended(selected)
    state.set_awaiting_feedback(True)
    token = state.create_stream_token(selected)
    stream_url = _stream_url(settings, token)
    infuse_url = build_infuse_url(stream_url, selected.name)
    player_url = build_player_url(settings, stream_url, selected.name)
    return {
        "file_name": selected.name,
        "path": str(selected),
        "stream_url": stream_url,
        "infuse_url": infuse_url,
        "player": settings.player,
        "player_url": player_url,
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
    return _select_from_files(settings, files)


def _selected_folder_paths(settings: Settings, folder_names: list[str]) -> list[Path]:
    eligible = {
        folder.name: folder
        for folder in recommender.list_top_level_media_folders(
            settings.media_root,
            settings.supported_extensions,
            settings.exclude_folders,
        )
    }
    return [eligible[name] for name in folder_names if name in eligible]


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return _home_page(_settings())


@app.post("/recommend", response_class=HTMLResponse)
def recommend_from_browser() -> HTMLResponse:
    settings = _settings()
    selected = _select_next(settings)
    return _feedback_page(selected["file_name"], selected["player_url"])


@app.get("/select", response_class=HTMLResponse)
def select_folders() -> HTMLResponse:
    return _selection_page(_settings())


@app.post("/recommend/selected", response_class=HTMLResponse)
def recommend_from_selected_folders(folders: list[str] = Form(default=[])) -> HTMLResponse:
    settings = _settings()
    if not folders:
        return _selection_page(settings, "Select at least one folder.")

    selected_folders = _selected_folder_paths(settings, folders)
    if not selected_folders:
        return _selection_page(settings, "Select at least one available folder.")

    files = recommender.find_media_files_in_folders(
        selected_folders,
        settings.supported_extensions,
        settings.exclude_folders,
    )
    if not files:
        return _selection_page(settings, "No supported media files were found in the selected folders.")

    selected = _select_from_files(settings, files)
    return _feedback_page(selected["file_name"], selected["player_url"])


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
        "player": selected["player"],
        "player_url": selected["player_url"],
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


def _feedback_response(feedback: str, request: Request) -> dict[str, Any] | RedirectResponse:
    settings = _settings()
    last_recommended = state.get_last_recommended()
    if last_recommended is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation has been made yet")

    if feedback != "skip":
        prefs = _load_current_prefs(settings)
        recommender.ensure_entries(prefs, [last_recommended])
        recommender.apply_feedback(prefs, last_recommended, feedback)
        recommender.save_prefs(prefs, settings.prefs_file)
    state.set_awaiting_feedback(False)

    if _wants_html(request):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return {"ok": True, "feedback": feedback, "file_name": last_recommended.name}


@app.post("/feedback/like", response_model=None)
def feedback_like(request: Request) -> dict[str, Any] | RedirectResponse:
    return _feedback_response("like", request)


@app.post("/feedback/dislike", response_model=None)
def feedback_dislike(request: Request) -> dict[str, Any] | RedirectResponse:
    return _feedback_response("dislike", request)


@app.post("/feedback/pending", response_model=None)
def feedback_pending(request: Request) -> dict[str, Any] | RedirectResponse:
    return _feedback_response("pending", request)


@app.post("/feedback/skip", response_model=None)
def feedback_skip(request: Request) -> dict[str, Any] | RedirectResponse:
    return _feedback_response("skip", request)


@app.get("/reset", response_class=HTMLResponse)
def reset_confirm() -> HTMLResponse:
    return _page(
        "Reset Preferences",
        """<h1>Reset Preferences?</h1>
<p>This clears the recommendation preference file and starts fresh.</p>
<div class="stack">
  <form method="post" action="/reset">
    <button class="danger" type="submit">Reset Preferences</button>
  </form>
  <a class="button secondary" href="/">Cancel</a>
</div>""",
    )


@app.post("/reset", response_model=None)
def reset_preferences(request: Request) -> dict[str, bool] | RedirectResponse:
    settings = _settings()
    recommender.reset_prefs(settings.prefs_file)
    state.clear_state()
    if _wants_html(request):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return {"ok": True}


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
