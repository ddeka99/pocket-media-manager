# Pocket Media Manager PC Helper

This service indexes a Windows media folder, serves direct-play video files
over your local network, and stores playback plus feedback events in SQLite.

## What The Helper Is Doing

The helper is the backend brain of the project.

Functionally, it has four jobs:

1. remember where the media library lives on the PC
2. scan that folder and build an indexed library
3. serve playable files over HTTP to the iPhone app
4. store user behavior such as resume position and simple feedback

The helper is intentionally stateful. It is not just a passthrough file server.
It keeps a local database so the phone can behave like a media app rather than
just a remote file browser.

## Quick start

1. Open Git Bash in `pc-helper/`.
2. Bootstrap the local environment:

```bash
bash ./scripts/bootstrap.sh
```

3. Run the API:

```bash
bash ./scripts/run-dev.sh
```

4. Call `GET /pairing` to read the local API token.
5. Call `PUT /config` with the token and your media root path.
6. Call `POST /library/rescan` to build the library index.

## What A User Actually Experiences

When the helper is running, the real user journey is:

1. the app connects with a helper URL and token
2. the app asks for the indexed library
3. the user opens an item
4. the app asks the helper for a stream URL
5. the helper serves the actual file
6. the app periodically saves progress
7. the helper stores that progress and returns it later as the resume point

So from the user side, the helper mainly shows up as:

- a library that loads
- a video that starts playing
- a video that resumes where it was left off
- a system that remembers simple reactions

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

## Route-Level Meaning

These are the most important endpoints in plain language:

- `GET /health`
  Quick status check. Used to confirm the helper is alive and how many library
  items are currently indexed.
- `GET /pairing`
  Returns the local API token. The phone uses that token in later requests.
- `PUT /config`
  Tells the helper which Windows folder should be treated as the media root.
- `POST /library/rescan`
  Rebuilds the library index by walking the media root.
- `GET /library`
  Returns the full browsable media list.
- `GET /library/summary`
  Returns short operational information such as item counts and top folders.
- `POST /library/{id}/stream`
  Creates the direct playback URL used by the app.
- `POST /library/{id}/progress`
  Saves the latest watch position.
- `POST /library/{id}/feedback`
  Saves simple feedback events.

## Small operator commands

With the helper already running:

```bash
bash ./scripts/admin.sh
```

Rescan and print a short summary:

```bash
bash ./scripts/admin.sh --rescan
```

Check the Wi-Fi URL and pairing token that the iPhone app should use:

```bash
bash ./scripts/lan-check.sh
```

## Testing

Run the backend tests with:

```bash
bash ./scripts/test.sh
```

## Underlying Logic

### Scanning

During a rescan, the helper:

1. walks the configured media root recursively
2. keeps only files that look like supported video containers
3. derives a stable media ID from the relative path
4. extracts local metadata with `ffprobe` when available
5. marks items as compatible or incompatible for direct iPhone playback
6. updates the SQLite index

Files that are not video-like are ignored. Files such as `.mkv` can still be
indexed, but they are marked incompatible for v1 direct playback.

### Playback

When the user presses Play:

1. the app requests `/library/{id}/stream`
2. the helper returns a signed-ish local stream URL containing the token
3. the app uses the native iPhone player against that URL
4. the helper serves the file directly

### Resume

While the user is watching, the app periodically sends playback position to
`/library/{id}/progress`.

The helper stores that in two ways:

- `playback_state`
  latest known position for quick resume
- `playback_events`
  history of progress updates over time

That is why resume feels immediate while still preserving a behavior trail for
future analytics or recommendations.

### Feedback

Feedback is intentionally simple in v1:

- liked
- disliked
- save for later

These are stored as events rather than a complicated preference model. That
keeps the current experience lightweight while still producing useful data for a
later recommendation layer.

## Data You Can Inspect

The main SQLite database is:

- `pc-helper/data/library.db`

The most useful tables are:

- `media_items`
- `playback_state`
- `playback_events`
- `feedback_events`
- `scan_jobs`

Personal scratch SQL files can live in:

- `pc-helper/scratch/`

That folder is ignored by git so you can experiment freely.

## Important Code Paths

- Git Bash is now the preferred Windows shell for the helper workflow.
- `app/main.py`
  Defines the HTTP API and glues requests to the scanner and database.
- `app/scanner.py`
  Walks the filesystem and converts files into indexed media records.
- `app/media.py`
  Derives titles, checks compatibility, and calls `ffprobe`.
- `app/storage.py`
  Owns SQLite reads and writes.
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
