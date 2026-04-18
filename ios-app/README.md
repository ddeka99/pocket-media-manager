# Pocket Media Manager iOS App

This folder contains a SwiftUI client scaffold that matches the PC helper contract.

## What It Does

- Manual connection to the PC helper with a server URL and pairing token
- Library loading over the helper HTTP API
- Detail screen with metadata and feedback controls
- Native playback through `AVPlayer` and `VideoPlayer`
- Periodic playback progress sync back to the helper

The iPhone app is intentionally thin. It does not manage the library itself.
Its job is to present what the PC helper already knows and to send user actions
back to that helper.

## Main flow

1. Enter the PC helper base URL and pairing token.
2. Load the indexed library from `GET /library`.
3. Open a media item and request a playback URL from `POST /library/{id}/stream`.
4. Play with the native iPhone player.
5. Send progress and feedback back to the helper.

## Functional View Of The App

From the user perspective, the app has three functional areas:

- connection/settings
  Store the helper URL and token.
- library browsing
  Show the indexed items returned by the helper.
- item playback
  Request a stream URL, play the file, and report progress.

The UI itself is deliberately simple. The important part is the loop between:

- library item
- play
- resume
- feedback

That is the core behavior the app currently needs to support.

## Inputs From The PC Helper

- Base URL such as `http://<windows-pc-ip>:8765`
- Pairing token from `GET /pairing`
- Indexed media returned by the helper after a rescan

## How It Talks To The Backend

The app mostly revolves around these helper calls:

- `GET /library`
  load the library list
- `GET /library/summary`
  load lightweight helper status
- `POST /library/{id}/stream`
  get the playback URL
- `POST /library/{id}/progress`
  save resume state
- `POST /library/{id}/feedback`
  save simple preference events

## Important Code Paths

- `Services/APIClient.swift`
  wraps the helper HTTP API
- `Services/AppConfigurationStore.swift`
  stores the helper URL/token locally on the device
- `Views/RootView.swift`
  decides whether the app shows connection setup or the main tabs
- `Views/LibraryView.swift`
  shows the indexed media list
- `Views/MediaDetailView.swift`
  shows a single item and starts playback
- `ViewModels/PlayerViewModel.swift`
  manages the player and periodic progress sync

## Opening in Xcode

Open `ios-app/PocketMediaManager.xcodeproj` in Xcode.

The project is now checked in and points at:

- app sources in `ios-app/PocketMediaManager/`
- app plist in `ios-app/Info.plist`
- bootstrap LAN connection defaults in `ios-app/PocketMediaManager/Resources/BootstrapConfiguration.plist`

## Current Bootstrap Helper Settings

The first launch on a fresh install preloads:

- Helper URL: `http://10.0.0.235:8765`
- Pairing token: `rqc37qS44rS61TwSpdDwcytmQV8F-Wuz`

If the Windows PC IP or token changes later, either edit those values in the app's Settings tab or update `BootstrapConfiguration.plist` before reinstalling.

## Notes

- The app expects the helper to be reachable on the same home network.
- The current setup allows plain HTTP for local LAN testing.
- The app is intentionally light on UI complexity; most of the real behavior
  lives in the helper and its stored data.
