# pocket-media-manager

Personal media streaming and recommendation playground for a single-user iPhone + Windows setup.

## Repo layout

- `pc-helper/`: FastAPI + SQLite helper service that indexes local video files and streams them over your LAN.
- `ios-app/`: SwiftUI client scaffold for connecting to the helper, browsing the library, and playing compatible videos.
