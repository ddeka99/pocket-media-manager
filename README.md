# Pocket Media Manager

Pocket Media Manager is a personal Windows PC to phone media recommender.

The current helper is intentionally small: it keeps your custom weighted
recommendation logic on the PC, serves the selected local media file over your
home Wi-Fi, and gives your phone a tiny browser page for launching and recording
feedback.

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

Then edit `pc-helper\.env` so `PUBLIC_BASE_URL` uses this PC's LAN IP address
and `PLAYER` names the phone player to open:

```text
PUBLIC_BASE_URL=http://192.168.1.50:8787
PLAYER=infuse
```

Use `PLAYER=vlc` to test VLC instead.

For everyday phone use, install the Windows startup task once from an elevated
PowerShell opened in `pc-helper`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-startup-task.ps1
```

After that, the helper starts automatically when Windows starts, before you sign
in. It runs without development reload mode, which is better for leaving it
available to your phone while the PC is awake.

When you edit `pc-helper\.env`, restart the scheduled task from an elevated
PowerShell so the running helper loads the new settings:

```powershell
Stop-ScheduledTask -TaskName "Pocket Media Manager PC Helper"
Start-ScheduledTask -TaskName "Pocket Media Manager PC Helper"
```

For active development, stop that always-on task and then run the development
server:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\remove-startup-task.ps1
```

```bash
./scripts/run-dev.sh
```

You can also run the normal no-reload server manually:

```bash
powershell -ExecutionPolicy Bypass -File .\scripts\run-server.ps1
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

Tap `Recommend` to open the configured player. Use `Recommend with Selections`
when you want to choose one or more top-level folders under `MEDIA_ROOT` for a
single recommendation. The home page also shows the folder names configured in
`EXCLUDE_FOLDERS`, so you can quickly confirm what is being skipped. When you
switch back to the browser, choose Like, Dislike, Pending, or Skip.

See `pc-helper/README.md` for the full setup and phone workflow.
