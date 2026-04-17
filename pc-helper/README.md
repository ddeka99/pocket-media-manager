# Pocket Media Manager PC Helper

This service indexes a Windows media folder, serves direct-play video files
over your local network, and stores playback plus feedback events in SQLite.

## Quick start

1. Open PowerShell in `pc-helper/`.
2. Bootstrap the local environment:

```powershell
.\scripts\bootstrap.ps1
```

3. Run the API:

```powershell
.\scripts\run-dev.ps1
```

4. Call `GET /pairing` to read the local API token.
5. Call `PUT /config` with the token and your media root path.
6. Call `POST /library/rescan` to build the library index.

## Main flow

1. `GET /pairing`
   Read the local token used by the iPhone app and admin scripts.
2. `PUT /config`
   Store the Windows media root that should be scanned.
3. `POST /library/rescan`
   Walk the media root, extract metadata, and update the SQLite index.
4. `GET /library`
   Return the full media list used by the iPhone app.
5. `POST /library/{id}/stream`
   Return a stream URL for playback.
6. `POST /library/{id}/progress` and `POST /library/{id}/feedback`
   Save watch progress and simple preference signals.

## Small operator commands

With the helper already running:

```powershell
.\scripts\admin.ps1
```

Rescan and print a short summary:

```powershell
.\scripts\admin.ps1 -Rescan
```

Check the Wi-Fi URL and pairing token that the iPhone app should use:

```powershell
.\scripts\lan-check.ps1
```

## Testing

Run the backend tests with:

```powershell
.\scripts\test.ps1
```

## Notes

- The helper keeps its local state in `pc-helper/data/library.db`.
- Important code paths:
  - `app/main.py`: HTTP routes
  - `app/scanner.py`: folder walk and indexing
  - `app/media.py`: title/compatibility/ffprobe metadata extraction
  - `app/storage.py`: SQLite reads and writes
- For your current Windows session, the helper is reachable on the local Wi-Fi at
  `http://10.0.0.235:8765` while that IPv4 address remains the same.
- If `python` or `py` still resolves to a Windows Store stub in this shell,
  disable the App Execution Aliases for Python or restart the terminal after
  installation.
- `ffprobe` is optional. If it is on `PATH`, the helper will enrich duration
  and codec metadata.
- v1 only marks `.mp4`, `.m4v`, and `.mov` as iPhone direct-play compatible.
- Streaming uses FastAPI's file response path, which supports byte-range
  requests via Starlette.
