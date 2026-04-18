# pocket-media-manager

Pocket Media Manager is a personal media streaming and tracking app for a
single-user iPhone + Windows setup.

The main idea is simple:

- keep the actual media files on the Windows PC
- use the phone as a lightweight remote browser and player
- keep watch progress and simple feedback on the PC so future recommendation
  work has useful behavior data to build on

This means the PC acts as the source of truth and the iPhone acts as the
portable client.

## Why It Is Built This Way

This project is intentionally not trying to be a full Plex-style ecosystem.
The first version is optimized for one person, one PC, one phone, and a home
Wi-Fi network.

That leads to a few deliberate choices:

- no cloud sync
- no multi-user accounts
- no transcoding in v1
- no external metadata service in v1
- no heavy media-server feature set

Instead, the system focuses on a small reliable loop:

1. point the helper at a Windows folder
2. scan and index the video files
3. browse and play them on the iPhone
4. save progress and feedback
5. use that stored history later for recommendation work

## End-To-End Flow

From a user point of view, the current experience looks like this:

1. Start the PC helper on Windows.
2. The helper exposes a local HTTP API on the home network.
3. The iPhone app connects to that helper using a LAN URL and pairing token.
4. The app loads the indexed library from the helper.
5. When you open an item and press Play, the app requests a stream URL.
6. The helper serves the underlying file directly.
7. While you watch, the app periodically reports playback position.
8. When you reopen the item later, the saved position is used as the resume
   point.

That is why your playback test worked after refreshing and reopening the file:
the resume point was stored by the backend and then returned again when the app
reloaded that item.

## How The Logic Is Split

### Windows helper

The helper is responsible for:

- remembering which folder is the library root
- scanning the filesystem
- extracting media metadata
- deciding whether a file is direct-play compatible in v1
- storing watch progress and feedback in SQLite
- serving streamable files over HTTP

### iPhone app

The app is responsible for:

- collecting the helper URL and token
- showing the indexed library
- asking the helper for a stream URL
- playing the video
- sending progress and feedback back to the helper

The phone does not own the media library. It is effectively a remote client for
the PC helper.

## Core Data Model

The backend stores a few important categories of data:

- `media_items`
  The indexed video library, including title, path, codec, duration, container,
  and whether the item is considered direct-play compatible for iPhone.
- `playback_state`
  The latest saved resume position per media item.
- `playback_events`
  The event history of playback updates over time.
- `feedback_events`
  Simple signals such as liked, disliked, and save-for-later.
- `scan_jobs`
  A small history of library scans.

This split matters because recommendations usually need event history, not just
the latest state. That is why playback is stored both as current state and as
append-only events.

## Repo layout

- `pc-helper/`: FastAPI + SQLite helper service that indexes local video files and streams them over your LAN.
- `ios-app/`: SwiftUI client scaffold for connecting to the helper, browsing the library, and playing compatible videos.

## Current Status

- Windows helper: runnable, tested, and scanning your configured media library.
- iPhone client: checked-in Xcode project under `ios-app/`, with the current LAN helper URL/token preloaded for personal-device testing, a compact library-first flow, and a landscape playback screen built on Apple's standard AVKit player UI.

## Current v1 Boundaries

The current system works, but it is intentionally narrow:

- video-first, not a general media platform
- best effort direct play for iPhone-compatible files
- unsupported containers are indexed but marked incompatible
- metadata comes from local file structure and `ffprobe`
- recommendation logic has not been built yet

That means v1 is already useful as a personal mobile playback tool, while still
laying down the behavior data needed for the later recommendation phase.
