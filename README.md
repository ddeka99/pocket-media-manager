# Pocket Media Manager

Pocket Media Manager is a personal Windows PC to phone media recommender.

The current v1 helper is intentionally small: it keeps your custom weighted
recommendation logic on the PC, serves the selected local media file over your
home Wi-Fi, and gives your phone a tiny browser page for launching Infuse and
recording feedback.

The project does not replace Plex as a full media library. It exists because
Plex can play files well, but it does not know your custom recommendation
preferences such as unseen boosts, soft dislike penalties, pending items, and
recent-play cooldowns.

## What Is In This Repo

- `pc-helper/`
  FastAPI helper that scans a Windows media folder, picks a recommendation,
  streams the selected file, and records like/dislike/pending feedback.
- `import random.py`
  The original local PC script used as the source reference for the v1
  recommendation rules. It is not imported directly by the helper.

## Quick Start

Open Git Bash in `pc-helper/` and run:

```bash
./scripts/bootstrap.sh
```

Then edit `pc-helper\.env` so `PUBLIC_BASE_URL` uses this PC's LAN IP address,
for example:

```text
PUBLIC_BASE_URL=http://192.168.1.50:8787
```

Run the helper:

```bash
./scripts/run-dev.sh
```

Test locally:

```text
http://localhost:8787/
http://localhost:8787/health
```

Test from your phone on the same Wi-Fi:

```text
http://<PC_LAN_IP>:8787/
```

Tap `Recommend` to open Infuse. When you switch back to the browser, choose
Like, Dislike, Pending, or Skip.

See `pc-helper/README.md` for the full setup and phone workflow.
