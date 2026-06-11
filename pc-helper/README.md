# Pocket Media Manager PC Helper

This helper runs on the Windows PC that stores your media. It scans your media
folder, chooses a weighted recommendation using your existing rules, serves the
chosen file over the local network, and accepts simple phone feedback.

Playback itself is delegated to Infuse or VLC. The helper is the recommendation
and streaming bridge, not a custom video player.

## How The Pieces Connect

1. Your phone opens the helper home page and taps `Recommend`.
2. The helper scans `MEDIA_ROOT`, loads `_mpv_prefs.json`, and picks a video.
3. The helper records play count and `last_played` immediately.
4. The helper creates a temporary stream token.
5. The phone opens the configured player while the browser stays on a feedback
   page.
6. After watching, you switch back to the browser and choose Like, Dislike,
   Pending, Skip, or Other.

Plex can stay installed for normal library playback, but this workflow does not
depend on Plex. It exists to preserve your custom recommendation behavior.

## Setup

From Git Bash:

```bash
cd C:\Dev\pocket-media-manager\pc-helper
./scripts/bootstrap.sh
```

The bootstrap script creates `.venv`, installs dependencies, and creates `.env`
from `.env.example` if needed.

Edit `.env`:

```text
MEDIA_ROOT=E:\Hobby Disk
PUBLIC_BASE_URL=http://192.168.1.50:8787
SERVER_HOST=0.0.0.0
SERVER_PORT=8787
PLAYER=infuse
SUPPORTED_EXTENSIONS=.mp4,.mkv,.mov,.avi,.webm
EXCLUDE_FOLDERS=
```

`PUBLIC_BASE_URL` must use the PC's LAN IP, not `localhost`, because the phone
needs to reach the PC.

`PLAYER` controls which app the `Recommend` button opens. Supported values are
`infuse` and `vlc`. Infuse is the default because it has already worked cleanly
in this setup. Set `PLAYER=vlc` to try VLC with the same recommendation and
feedback flow.

The helper stores recommendation preferences in `MEDIA_ROOT\_mpv_prefs.json`.
If that file does not exist, it is created the first time preferences are saved.

Find the LAN IP from Windows:

```text
ipconfig
```

Look for the IPv4 address on the active Wi-Fi or Ethernet adapter.

## Everyday Windows Startup

For normal phone use, run the helper as a Windows scheduled task instead of
keeping a development terminal open. This starts the server when Windows boots,
before you sign in, and keeps it available while the PC is awake.

From an elevated PowerShell in `pc-helper`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-startup-task.ps1
```

The task runs `scripts\run-server.ps1`, which starts Uvicorn without
development reload mode. The scheduled task runs as Windows `SYSTEM`, so it does
not depend on your account being signed in. It reads `SERVER_HOST` and
`SERVER_PORT` from `.env`, defaulting to:

```text
http://0.0.0.0:8787
```

Logs are appended to:

```text
pc-helper\.tmp\server.log
```

If you edit `.env` after the startup task is installed, restart the task from an
elevated PowerShell so the running helper loads the new settings:

```powershell
Stop-ScheduledTask -TaskName "Pocket Media Manager PC Helper"
Start-ScheduledTask -TaskName "Pocket Media Manager PC Helper"
```

If you want to stop the always-on helper before development work, remove the
scheduled task from an elevated PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\remove-startup-task.ps1
```

Install it again with `install-startup-task.ps1` when you want to return to the
always-on phone workflow.

You can also run the normal no-reload server manually:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-server.ps1
```

## Development Run

Use the development server when changing the app code:

```bash
./scripts/run-dev.sh
```

This starts Uvicorn with reload enabled, which is useful while editing code but
is not the preferred mode for daily phone playback.

Useful checks:

```text
http://localhost:8787/
http://localhost:8787/health
http://localhost:8787/next
http://localhost:8787/last
```

If the phone cannot reach `/health`, allow Python/Uvicorn through Windows
Firewall for private networks and confirm the phone is on the same Wi-Fi. If the
boot task starts but recommendations find no media, confirm that `MEDIA_ROOT` is
a local drive available before sign-in; mapped network drives usually belong to a
signed-in user session and are not visible to `SYSTEM`.

## Phone Browser Flow

The main phone workflow is the helper home page:

```text
http://<PC_LAN_IP>:8787/
```

The home page shows the current `EXCLUDE_FOLDERS` setting below the action
buttons. These names are skipped by normal recommendations and do not appear as
top-level choices in `Recommend with Selections`.

Tap `Recommend`. The helper selects a video, records the play, opens Infuse or
VLC depending on `PLAYER`, and leaves the browser on a feedback page.

Tap `Explore` when you want to browse `MEDIA_ROOT` manually. Explore shows
folders that contain supported media somewhere below them and shows only files
with extensions from `SUPPORTED_EXTENSIONS`. It also respects
`EXCLUDE_FOLDERS`. Choosing a file records play metadata, opens the configured
player, and then uses the same feedback flow as recommendations. The top of
Explore shows the full `MEDIA_ROOT` path at the root and relative folder names
inside subfolders. Use the sticky `Home` button to leave Explore; subfolders
also show a sticky `Back` button.

Tap `Recommend with Selections` when you want to limit one recommendation to
specific top-level folders under `MEDIA_ROOT`. The selection page shows the
configured media root at the top, then only shows top-level folders that contain
at least one supported media file. Files are found recursively inside those
selected folders. For example, selecting `Anime` can still recommend files under
`Anime\Attack on Titan`, while `Attack on Titan` itself is not shown as a
checkbox.

After feedback for a selected recommendation, the browser returns to the
selection page with the same folders still checked. This lets you keep asking
for recommendations from the same subset. Use `Cancel` on the selection page to
clear that saved selection and return to the home page.

When you switch back to the browser, choose:

- `Like`
  Boosts that file in future recommendations.
- `Dislike`
  Softly penalizes that file without banning it.
- `Pending`
  Marks it as something to revisit and gives it a smaller boost than Like.
- `Skip`
  Records no preference feedback. The play count and cooldown from the
  recommendation are still already recorded.
- `Other`
  Opens a required save step for an optional one-line comment. Saving writes an
  entry to `other_feedback.jsonl` under `MEDIA_ROOT` without changing
  like/dislike/pending counts. If the same file already has an unresolved Other
  feedback entry, the Other button is withheld until that entry is marked
  addressed.

After feedback is completed, the browser returns to the home page and
`Recommend` is available again. If the recommendation came from selected
folders, it returns to the selection page with those folders still checked.

For `Other`, the comment may be empty, but it must be one line and at most 200
characters including spaces. Each saved entry is appended to:

```text
MEDIA_ROOT\other_feedback.jsonl
```

Entries use JSON Lines: one JSON object per line.

```json
{"path":"E:\\Hobby Disk\\Anime\\Steins Gate.mp4","comment":"Boring, could have been 5 minutes","created_at":"2026-06-03T10:00:00"}
```

If the comment is empty, `comment` is stored as an empty string:

```json
{"path":"E:\\Hobby Disk\\Anime\\Steins Gate.mp4","comment":"","created_at":"2026-06-03T10:00:00"}
```

Use `Feedback Addressed` on the home page after reviewing Other feedback. It
shows each saved item with a checkbox and displays only the path below
`MEDIA_ROOT`, such as `Anime\Steins Gate.mp4`. Comments are not shown there.
Checking items and saving removes those entries from `other_feedback.jsonl`.
Cancel returns home without changing the file. Once an entry is removed here,
that file can receive a new Other feedback note again.

The home page also has `Reset Preferences`. It opens a confirmation page before
clearing `MEDIA_ROOT\_mpv_prefs.json` back to an empty preference database.

## Optional Phone Shortcuts

You can still use Shortcuts if you want. Create a shortcut named
`Next Recommended Video`:

1. Get contents of URL:

```text
http://<PC_LAN_IP>:8787/next
```

2. Get `player_url` from the JSON response.
3. Open URL.

If you want the shortest possible shortcut, open this URL directly:

```text
http://<PC_LAN_IP>:8787/next?redirect=infuse
```

Create feedback shortcuts:

```text
POST http://<PC_LAN_IP>:8787/feedback/like
POST http://<PC_LAN_IP>:8787/feedback/dislike
POST http://<PC_LAN_IP>:8787/feedback/pending
POST http://<PC_LAN_IP>:8787/feedback/skip
POST http://<PC_LAN_IP>:8787/feedback/other
POST http://<PC_LAN_IP>:8787/feedback/other/save
```

Feedback applies to the last recommendation made by the running helper process.
If the helper restarts before feedback is sent, `/feedback/...` will not know
which item was last recommended.

## API

- `GET /health`
  Returns `{"ok": true}`.
- `GET /`
  Returns the minimal browser control page.
- `POST /recommend`
  Browser action that selects a recommendation, opens the configured player,
  and shows feedback buttons.
- `GET /explore`
  Shows a manual browser rooted at `MEDIA_ROOT`.
- `GET /explore?path=...`
  Shows a subfolder under `MEDIA_ROOT`.
- `POST /explore/play`
  Plays a selected supported media file from Explore, records play metadata, and
  shows feedback buttons.
- `GET /next`
  Picks and records a recommendation, then returns `stream_url`, `infuse_url`,
  configured `player`, `player_url`, and feedback URLs.
- `GET /next?redirect=infuse`
  Picks and records a recommendation, then redirects straight to Infuse.
- `GET /stream/{token}`
  Streams a token-mapped file. Unknown tokens, missing files, and paths outside
  `MEDIA_ROOT` return 404.
- `POST /feedback/like`
  Adds one like to the last recommended file.
- `POST /feedback/dislike`
  Adds one dislike to the last recommended file.
- `POST /feedback/pending`
  Adds one pending/save-for-later mark to the last recommended file.
- `POST /feedback/skip`
  Clears the feedback step without changing preference counts.
- `POST /feedback/other`
  Starts the required Other feedback comment step. Returns a conflict if the
  current file already has an unresolved Other feedback entry.
- `GET /feedback/other`
  Shows the Other feedback comment page, unless the current file already has an
  unresolved Other feedback entry.
- `POST /feedback/other/save`
  Saves an optional `comment` form field to `MEDIA_ROOT\other_feedback.jsonl` and
  clears the feedback step without changing preference counts. The comment must
  be one line and at most 200 characters. Duplicate unresolved Other feedback
  for the same file is rejected.
- `GET /feedback/addressed`
  Shows saved Other feedback records by relative media path, without comments.
- `POST /feedback/addressed`
  Removes the checked Other feedback records and returns to the home page.
- `GET /reset`
  Shows a confirmation page for resetting preferences.
- `POST /reset`
  Clears `_mpv_prefs.json` and resets in-memory recommendation state.
- `GET /last`
  Returns the last recommended file and its preference metadata.

## Recommendation Data

Preferences are stored in `MEDIA_ROOT\_mpv_prefs.json`. The JSON shape matches
the original PC script:

```json
{
  "files": {
    "E:\\Hobby Disk\\Example\\video.mp4": {
      "likes": 0,
      "dislikes": 0,
      "pending": 0,
      "play_count": 0,
      "last_played": null,
      "last_feedback": null
    }
  }
}
```

If the preference file is missing, the helper creates it. If it is corrupted,
the helper recovers with an empty in-memory preference set and writes a clean
file the next time preferences are saved.

`Other` feedback is stored separately in `other_feedback.jsonl` under
`MEDIA_ROOT`. Each line has `path`, `comment`, and `created_at`. It does not
affect recommendation weights. The helper appends new records when Other
feedback is saved and rewrites the file when addressed records are removed.

## Safety Notes

This server is for your private home network only. Do not expose it to the
public internet.

The helper does not accept arbitrary file paths from the phone. It only streams
files selected by the recommendation engine, behind opaque stream tokens, and
it verifies streamed files are under `MEDIA_ROOT`.

## Testing

Run:

```bash
./scripts/test.sh
```

The tests use temporary media folders and preference files, so they do not
modify your real media library or your real `_mpv_prefs.json`.
