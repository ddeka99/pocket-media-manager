# Pocket Media Manager PC Helper

This service indexes a Windows media folder, serves direct-play video files
over your local network, and stores playback plus feedback events in SQLite.

## Quick start

1. Create a virtual environment with a working Python installation.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

1. Run the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8765
```

1. Call `GET /pairing` to read the local API token.
2. Call `PUT /config` with the token and your media root path.
3. Call `POST /library/rescan` to build the library index.

## Notes

- `ffprobe` is optional. If it is on `PATH`, the helper will enrich duration
  and codec metadata.
- v1 only marks `.mp4`, `.m4v`, and `.mov` as iPhone direct-play compatible.
- Streaming uses FastAPI's file response path, which supports byte-range
  requests via Starlette.
