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

## Testing

Run the backend tests with:

```powershell
.\scripts\test.ps1
```

## Notes

- If `python` or `py` still resolves to a Windows Store stub in this shell,
  disable the App Execution Aliases for Python or restart the terminal after
  installation.
- `ffprobe` is optional. If it is on `PATH`, the helper will enrich duration
  and codec metadata.
- v1 only marks `.mp4`, `.m4v`, and `.mov` as iPhone direct-play compatible.
- Streaming uses FastAPI's file response path, which supports byte-range
  requests via Starlette.
