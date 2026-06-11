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
OTHER_FEEDBACK_FILE_NAME = "other_feedback.jsonl"
OTHER_FEEDBACK_MAX_COMMENT_LENGTH = 200
APP_ICON_PATH = Path(__file__).resolve().parents[1] / "pocket-manager-icon.png"


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <link rel="icon" type="image/png" sizes="128x128" href="/pocket-manager-icon.png">
  <link rel="apple-touch-icon" href="/pocket-manager-icon.png">
  <link rel="manifest" href="/manifest.webmanifest">
  <meta name="application-name" content="Pocket Media Manager">
  <meta name="apple-mobile-web-app-title" content="Pocket Media Manager">
  <meta name="theme-color" content="#f7f7f4">
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
    input[type="text"] {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #bcbcb5;
      border-radius: 6px;
      padding: .85rem 1rem;
      background: white;
      color: #181818;
      font: inherit;
    }}
    .stack {{ display: grid; gap: .7rem; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: .7rem;
      padding: .3rem 0;
      background: #f7f7f4;
    }}
    .toolbar.single {{ grid-template-columns: 1fr; }}
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
        "other": f"{settings.public_base_url}/feedback/other",
    }


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and "application/json" not in accept


def _current_feedback_page() -> HTMLResponse | None:
    last_recommended = state.get_last_recommended()
    if not state.is_awaiting_feedback() or last_recommended is None:
        return None
    settings = _settings()
    if _has_other_feedback_for_file(settings, last_recommended):
        state.set_awaiting_other_feedback(False)
        return _feedback_page(last_recommended.name, other_available=False)
    if state.is_awaiting_other_feedback():
        return _other_feedback_page(last_recommended.name)
    return _feedback_page(
        last_recommended.name,
        other_available=not _has_other_feedback_for_file(settings, last_recommended),
    )


def _home_page(settings: Settings) -> HTMLResponse:
    feedback_page = _current_feedback_page()
    if feedback_page is not None:
        return feedback_page

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
  <form method="get" action="/explore">
    <button class="secondary" type="submit">Explore</button>
  </form>
  <form method="get" action="/feedback/addressed">
    <button class="secondary" type="submit">Feedback Addressed</button>
  </form>
  <form method="get" action="/reset">
    <button class="secondary" type="submit">Reset Preferences</button>
  </form>
</div>""",
    )


def _selection_page(
    settings: Settings,
    error: str | None = None,
    selected_folder_names: list[str] | None = None,
) -> HTMLResponse:
    feedback_page = _current_feedback_page()
    if feedback_page is not None:
        return feedback_page

    folders = recommender.list_top_level_media_folders(
        settings.media_root,
        settings.supported_extensions,
    )
    if not folders:
        return _page(
            "Select Folders",
            """<h1>Recommend with Selections</h1>
<p>No top-level folders with supported media were found.</p>
<form method="post" action="/select/cancel">
  <button class="secondary" type="submit">Cancel</button>
</form>""",
        )

    error_html = f'<p style="color:#9d2020;">{escape(error)}</p>' if error else ""
    selected_names = set(selected_folder_names if selected_folder_names is not None else state.get_selected_folder_names())
    folder_controls = "\n".join(
        f"""<label class="check">
  <input type="checkbox" name="folders" value="{escape(folder.name, quote=True)}"{' checked' if folder.name in selected_names else ''}>
  <span>{escape(folder.name)}</span>
</label>"""
        for folder in folders
    )
    media_root_label = escape(str(settings.media_root))
    return _page(
        "Select Folders",
        f"""<h1>Recommend with Selections</h1>
{error_html}
<div class="toolbar">
  <button type="submit" form="selection-form">Recommend</button>
  <button class="secondary" type="submit" form="selection-cancel-form">Cancel</button>
  <button class="secondary" type="button" data-select-folders="all">Select All</button>
  <button class="secondary" type="button" data-select-folders="none">Deselect All</button>
</div>
<form id="selection-form" method="post" action="/recommend/selected" class="stack">
  <p>Folders in <em>{media_root_label}</em>:</p>
  <div class="stack">
    {folder_controls}
  </div>
</form>
<form id="selection-cancel-form" method="post" action="/select/cancel"></form>
<script>
  document.querySelectorAll("[data-select-folders]").forEach(function (button) {{
    button.addEventListener("click", function () {{
      var checked = button.dataset.selectFolders === "all";
      document.querySelectorAll('input[name="folders"]').forEach(function (checkbox) {{
        checkbox.checked = checked;
      }});
    }});
  }});
</script>""",
    )


def _feedback_page(file_name: str, player_url: str | None = None, other_available: bool = True) -> HTMLResponse:
    escaped_name = escape(file_name)
    opener = ""
    fallback = ""
    other_control = (
        '<form method="post" action="/feedback/other"><button class="secondary" type="submit">Other</button></form>'
        if other_available
        else "<p>Other feedback already exists for this file. Mark it addressed before adding another Other note.</p>"
    )
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
  {other_control}
</div>""",
    )


def _other_feedback_page(file_name: str, error: str | None = None, comment: str = "") -> HTMLResponse:
    escaped_name = escape(file_name)
    escaped_comment = escape(comment, quote=True)
    error_html = f'<p style="color:#9d2020;">{escape(error)}</p>' if error else ""
    return _page(
        "Other Feedback",
        f"""<h1>Other Feedback</h1>
<p>{escaped_name}</p>
{error_html}
<form method="post" action="/feedback/other/save" class="stack">
  <input type="text" name="comment" maxlength="{OTHER_FEEDBACK_MAX_COMMENT_LENGTH}" value="{escaped_comment}" autocomplete="off">
  <button type="submit">Save</button>
</form>""",
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
    state.set_awaiting_other_feedback(False)
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
    state.clear_selected_folder_names()
    files = recommender.find_media_files(
        settings.media_root,
        settings.supported_extensions,
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
        )
    }
    return [eligible[name] for name in folder_names if name in eligible]


def _relative_to_media_root(settings: Settings, path: Path) -> str:
    try:
        return str(path.relative_to(settings.media_root))
    except ValueError:
        return str(path)


def _explore_url(settings: Settings, folder_path: Path) -> str:
    relative_path = _relative_to_media_root(settings, folder_path)
    if relative_path == ".":
        return "/explore"
    return f"/explore?{urlencode({'path': relative_path})}"


def _explore_target(settings: Settings, relative_path: str | None) -> Path:
    if not relative_path:
        return settings.media_root
    target = (settings.media_root / relative_path).resolve()
    if not _is_under(target, settings.media_root):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Explore path is not allowed")
    return target


def _folder_has_supported_media(settings: Settings, folder_path: Path) -> bool:
    return bool(
        recommender.find_media_files(
            folder_path,
            settings.supported_extensions,
        )
    )


def _explore_page(settings: Settings, relative_path: str | None = None) -> HTMLResponse:
    feedback_page = _current_feedback_page()
    if feedback_page is not None:
        return feedback_page

    current = _explore_target(settings, relative_path)
    if not current.exists() or not current.is_dir():
        return _page(
            "Explore",
            """<h1>Explore</h1>
<p>The selected folder was not found.</p>
<a class="button secondary" href="/">Cancel</a>""",
        )

    folders = []
    files = []
    for child in sorted(current.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir():
            if _folder_has_supported_media(settings, child):
                folders.append(child)
        elif child.is_file() and child.suffix.lower() in settings.supported_extensions:
            files.append(child)

    folder_links = "\n".join(
        f'<a class="button secondary" href="{escape(_explore_url(settings, folder), quote=True)}">{escape(folder.name)}</a>'
        for folder in folders
    )
    file_controls = "\n".join(
        f"""<form method="post" action="/explore/play">
  <input type="hidden" name="path" value="{escape(_relative_to_media_root(settings, file_path), quote=True)}">
  <button class="secondary" type="submit">{escape(file_path.name)}</button>
</form>"""
        for file_path in files
    )
    parent_link = ""
    if current.resolve() != settings.media_root.resolve():
        parent_link = f'<a class="button secondary" href="{escape(_explore_url(settings, current.parent), quote=True)}">Back</a>'
    toolbar_class = "toolbar" if parent_link else "toolbar single"
    toolbar = f"""<div class="{toolbar_class}">
  {parent_link}
  <a class="button secondary" href="/">Home</a>
</div>"""

    current_label = str(settings.media_root) if current.resolve() == settings.media_root.resolve() else _relative_to_media_root(settings, current)
    empty_message = "<p>No supported media files found here.</p>" if not folders and not files else ""
    return _page(
        "Explore",
        f"""<h1>Explore</h1>
{toolbar}
<p>Browsing <em>{escape(current_label)}</em></p>
<div class="stack">
  {folder_links}
  {file_controls}
  {empty_message}
</div>""",
    )


def _select_explored_file(settings: Settings, relative_path: str) -> dict[str, str]:
    selected = _explore_target(settings, relative_path)
    if not selected.exists() or not selected.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file missing")
    if selected.suffix.lower() not in settings.supported_extensions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported media file")

    state.clear_selected_folder_names()
    return _select_from_files(settings, [selected])


def _return_path_after_feedback() -> str:
    return "/select" if state.get_selected_folder_names() else "/"


def _validate_other_comment(comment: str) -> str:
    if "\n" in comment or "\r" in comment:
        raise ValueError("Comment must be a single line.")
    if len(comment) > OTHER_FEEDBACK_MAX_COMMENT_LENGTH:
        raise ValueError("Comment must be 200 characters or fewer.")
    return comment


def _append_other_feedback(settings: Settings, file_path: Path, comment: str) -> None:
    output_path = settings.media_root / OTHER_FEEDBACK_FILE_NAME
    record = {
        "path": str(file_path),
        "comment": comment,
        "created_at": recommender.now_iso(),
    }
    line = f"{json.dumps(record, ensure_ascii=False)}\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8", newline="") as output_file:
        output_file.write(line)


def _load_other_feedback_entries(settings: Settings) -> list[dict[str, Any]]:
    feedback_path = settings.media_root / OTHER_FEEDBACK_FILE_NAME
    if not feedback_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(feedback_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        file_path = record.get("path")
        if not isinstance(file_path, str) or not file_path:
            continue
        entries.append(
            {
                "line_number": line_number,
                "path": file_path,
            }
        )
    return entries


def _has_other_feedback_for_file(settings: Settings, file_path: Path) -> bool:
    target = str(file_path)
    return any(entry["path"] == target for entry in _load_other_feedback_entries(settings))


def _feedback_page_for_selection(settings: Settings, selected: dict[str, str]) -> HTMLResponse:
    selected_path = Path(selected["path"])
    return _feedback_page(
        selected["file_name"],
        selected["player_url"],
        other_available=not _has_other_feedback_for_file(settings, selected_path),
    )


def _remove_other_feedback_entries(settings: Settings, line_numbers: set[int]) -> None:
    feedback_path = settings.media_root / OTHER_FEEDBACK_FILE_NAME
    if not feedback_path.exists() or not line_numbers:
        return

    kept_lines = [
        line
        for line_number, line in enumerate(feedback_path.read_text(encoding="utf-8").splitlines())
        if line_number not in line_numbers
    ]
    trailing_text = "".join(f"{line}\n" for line in kept_lines)
    feedback_path.write_text(trailing_text, encoding="utf-8")


def _feedback_display_path(settings: Settings, file_path: str) -> str:
    try:
        return str(Path(file_path).relative_to(settings.media_root))
    except ValueError:
        return file_path


def _feedback_addressed_page(settings: Settings) -> HTMLResponse:
    entries = _load_other_feedback_entries(settings)
    if not entries:
        return _page(
            "Feedback Addressed",
            """<h1>Feedback Addressed</h1>
<p>No other feedback records found.</p>
<a class="button secondary" href="/">Cancel</a>""",
        )

    controls = "\n".join(
        f"""<label class="check">
  <input type="checkbox" name="line_numbers" value="{entry["line_number"]}">
  <span>{escape(_feedback_display_path(settings, entry["path"]))}</span>
</label>"""
        for entry in entries
    )
    return _page(
        "Feedback Addressed",
        f"""<h1>Feedback Addressed</h1>
<form method="post" action="/feedback/addressed" class="stack">
  <div class="stack">
    {controls}
  </div>
  <button type="submit">Save</button>
</form>
<a class="button secondary" href="/">Cancel</a>""",
    )


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/pocket-manager-icon.png")
def app_icon() -> FileResponse:
    if not APP_ICON_PATH.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App icon missing")
    return FileResponse(path=APP_ICON_PATH, media_type="image/png")


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    if not APP_ICON_PATH.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App icon missing")
    return FileResponse(path=APP_ICON_PATH, media_type="image/png")


@app.get("/manifest.webmanifest")
def web_manifest() -> dict[str, Any]:
    return {
        "name": "Pocket Media Manager",
        "short_name": "Pocket Media",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f7f7f4",
        "theme_color": "#f7f7f4",
        "icons": [
            {
                "src": "/pocket-manager-icon.png",
                "sizes": "128x128",
                "type": "image/png",
            }
        ],
    }


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return _home_page(_settings())


@app.get("/feedback/addressed", response_class=HTMLResponse)
def feedback_addressed() -> HTMLResponse:
    feedback_page = _current_feedback_page()
    if feedback_page is not None:
        return feedback_page
    return _feedback_addressed_page(_settings())


@app.post("/feedback/addressed", response_model=None)
def save_feedback_addressed(line_numbers: list[int] = Form(default=[])) -> RedirectResponse:
    if state.is_awaiting_feedback():
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    _remove_other_feedback_entries(_settings(), set(line_numbers))
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/recommend", response_class=HTMLResponse)
def recommend_from_browser() -> HTMLResponse:
    settings = _settings()
    selected = _select_next(settings)
    return _feedback_page_for_selection(settings, selected)


@app.get("/explore", response_class=HTMLResponse)
def explore(path: str | None = None) -> HTMLResponse:
    return _explore_page(_settings(), path)


@app.post("/explore/play", response_class=HTMLResponse)
def play_explored_file(path: str = Form(...)) -> HTMLResponse:
    settings = _settings()
    selected = _select_explored_file(settings, path)
    return _feedback_page_for_selection(settings, selected)


@app.get("/select", response_class=HTMLResponse)
def select_folders() -> HTMLResponse:
    return _selection_page(_settings())


@app.post("/select/cancel", response_model=None)
def cancel_selected_folders() -> RedirectResponse:
    if state.is_awaiting_feedback():
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    state.clear_selected_folder_names()
    state.set_awaiting_feedback(False)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/recommend/selected", response_class=HTMLResponse)
def recommend_from_selected_folders(folders: list[str] = Form(default=[])) -> HTMLResponse:
    settings = _settings()
    if not folders:
        return _selection_page(settings, "Select at least one folder.", folders)

    selected_folders = _selected_folder_paths(settings, folders)
    if not selected_folders:
        return _selection_page(settings, "Select at least one available folder.", folders)

    files = recommender.find_media_files_in_folders(
        selected_folders,
        settings.supported_extensions,
    )
    if not files:
        return _selection_page(
            settings,
            "No supported media files were found in the selected folders.",
            [folder.name for folder in selected_folders],
        )

    state.set_selected_folder_names([folder.name for folder in selected_folders])
    selected = _select_from_files(settings, files)
    return _feedback_page_for_selection(settings, selected)


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
    if state.is_awaiting_other_feedback():
        if _wants_html(request):
            return RedirectResponse("/feedback/other", status_code=status.HTTP_303_SEE_OTHER)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Other feedback must be saved first")

    if feedback != "skip":
        prefs = _load_current_prefs(settings)
        recommender.ensure_entries(prefs, [last_recommended])
        recommender.apply_feedback(prefs, last_recommended, feedback)
        recommender.save_prefs(prefs, settings.prefs_file)
    state.set_awaiting_other_feedback(False)
    state.set_awaiting_feedback(False)

    if _wants_html(request):
        return RedirectResponse(_return_path_after_feedback(), status_code=status.HTTP_303_SEE_OTHER)
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


@app.post("/feedback/other", response_model=None)
def feedback_other(request: Request) -> dict[str, Any] | RedirectResponse | HTMLResponse:
    settings = _settings()
    last_recommended = state.get_last_recommended()
    if last_recommended is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation has been made yet")
    if not state.is_awaiting_feedback():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No feedback is currently pending")
    if _has_other_feedback_for_file(settings, last_recommended):
        if _wants_html(request):
            return _feedback_page(last_recommended.name, other_available=False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Other feedback already exists for this file")

    state.set_awaiting_other_feedback(True)
    if _wants_html(request):
        return RedirectResponse("/feedback/other", status_code=status.HTTP_303_SEE_OTHER)
    return {"ok": True, "feedback": "other", "file_name": last_recommended.name}


@app.get("/feedback/other", response_class=HTMLResponse)
def other_feedback_form() -> HTMLResponse:
    settings = _settings()
    last_recommended = state.get_last_recommended()
    if last_recommended is None or not state.is_awaiting_feedback():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation has been made yet")
    if _has_other_feedback_for_file(settings, last_recommended):
        return _feedback_page(last_recommended.name, other_available=False)
    state.set_awaiting_other_feedback(True)
    return _other_feedback_page(last_recommended.name)


@app.post("/feedback/other/save", response_model=None)
def save_other_feedback(request: Request, comment: str = Form(default="")) -> dict[str, Any] | RedirectResponse | HTMLResponse:
    settings = _settings()
    last_recommended = state.get_last_recommended()
    if last_recommended is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No recommendation has been made yet")
    if not state.is_awaiting_feedback() or not state.is_awaiting_other_feedback():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No other feedback is currently pending")
    if _has_other_feedback_for_file(settings, last_recommended):
        state.set_awaiting_other_feedback(False)
        if _wants_html(request):
            return _feedback_page(last_recommended.name, other_available=False)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Other feedback already exists for this file")

    try:
        validated_comment = _validate_other_comment(comment)
    except ValueError as error:
        if _wants_html(request):
            return _other_feedback_page(last_recommended.name, str(error), comment)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    _append_other_feedback(settings, last_recommended, validated_comment)
    state.set_awaiting_other_feedback(False)
    state.set_awaiting_feedback(False)

    if _wants_html(request):
        return RedirectResponse(_return_path_after_feedback(), status_code=status.HTTP_303_SEE_OTHER)
    return {"ok": True, "feedback": "other", "file_name": last_recommended.name}


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
