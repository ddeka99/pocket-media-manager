# pocket-media-manager

Personal media streaming and recommendation playground for a single-user iPhone + Windows setup.

## Repo layout

- `pc-helper/`: FastAPI + SQLite helper service that indexes local video files and streams them over your LAN.
- `ios-app/`: SwiftUI client scaffold for connecting to the helper, browsing the library, and playing compatible videos.

## Current Status

- Windows helper: runnable, tested, and scanning your configured media library.
- iPhone client: checked-in Xcode project under `ios-app/`, with the current LAN helper URL/token preloaded for personal-device testing.
