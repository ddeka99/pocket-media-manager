from __future__ import annotations

from pathlib import Path
from typing import Any
from html import escape
import json
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request, status
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
    form {{ margin: 0; }}
    .stack {{ display: grid; gap: .7rem; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }}
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


def _home_page() -> HTMLResponse:
    last_recommended = state.get_last_recommended()
    if state.is_awaiting_feedback() and last_recommended is not None:
        return _feedback_page(last_recommended.name)

    return _page(
        "Pocket Media Manager",
        """<h1>Pocket Media Manager</h1>
<div class="stack">
  <form method="post" action="/recommend">
    <button type="submit">Recommend</button>
  </form>
  <form method="get" action="/reset">
    <button class="secondary" type="submit">Reset Preferences</button>
  </form>
</div>""",
    )


def _feedback_page(file_name: str, infuse_url: str | None = None) -> HTMLResponse:
    escaped_name = escape(file_name)
    opener = ""
    fallback = ""
    if infuse_url:
        escaped_url = escape(infuse_url, quote=True)
        script_url = json.dumps(infuse_url)
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
    state.set_awaiting_feedback(True)
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


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return _home_page()


@app.post("/recommend", response_class=HTMLResponse)
def recommend_from_browser() -> HTMLResponse:
    settings = _settings()
    selected = _select_next(settings)
    return _feedback_page(selected["file_name"], selected["infuse_url"])


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
