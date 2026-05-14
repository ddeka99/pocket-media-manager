# Pocket Media Manager PC Helper

This helper runs on the Windows PC that stores your media. It scans your media
folder, chooses a weighted recommendation using your existing rules, serves the
chosen file over the local network, and accepts simple phone feedback.

Playback itself is delegated to Infuse or VLC. The helper is the recommendation
and streaming bridge, not a custom video player.

## How The Pieces Connect

1. Your phone calls `GET /next`.
2. The helper scans `MEDIA_ROOT`, loads `_mpv_prefs.json`, and picks a video.
3. The helper records play count and `last_played` immediately.
4. The helper creates a temporary stream token.
5. The phone opens the returned `infuse_url`, or opens `stream_url` manually in
   Infuse/VLC.
6. After watching, phone shortcuts call `/feedback/like`, `/feedback/dislike`,
   or `/feedback/pending`.

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
PREFS_FILE=./_mpv_prefs.json
SUPPORTED_EXTENSIONS=.mp4,.mkv,.mov,.avi,.webm
EXCLUDE_FOLDERS=
```

`PUBLIC_BASE_URL` must use the PC's LAN IP, not `localhost`, because the phone
needs to reach the PC.

Find the LAN IP from Windows:

```text
ipconfig
```

Look for the IPv4 address on the active Wi-Fi or Ethernet adapter.

## Run

```bash
./scripts/run-dev.sh
```

The default development server listens on:

```text
http://0.0.0.0:8787
```

Useful checks:

```text
http://localhost:8787/health
http://localhost:8787/next
http://localhost:8787/last
```

If the phone cannot reach `/health`, allow Python/Uvicorn through Windows
Firewall for private networks and confirm the phone is on the same Wi-Fi.

## Phone Shortcuts

Create a shortcut named `Next Recommended Video`:

1. Get contents of URL:

```text
http://<PC_LAN_IP>:8787/next
```

2. Get `infuse_url` from the JSON response.
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
```

Feedback applies to the last recommendation made by the running helper process.
If the helper restarts before feedback is sent, `/feedback/...` will not know
which item was last recommended.

## API

- `GET /health`
  Returns `{"ok": true}`.
- `GET /next`
  Picks and records a recommendation, then returns `stream_url`, `infuse_url`,
  and feedback URLs.
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
- `GET /last`
  Returns the last recommended file and its preference metadata.

## Recommendation Data

Preferences are stored in `_mpv_prefs.json` by default. The JSON shape matches
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
