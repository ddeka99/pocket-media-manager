# Pocket Media Manager iOS App

This folder contains a SwiftUI client scaffold that matches the PC helper contract.

## Current scope

- Manual connection to the PC helper with a server URL and pairing token
- Library loading over the helper HTTP API
- Detail screen with metadata and feedback controls
- Native playback through `AVPlayer` and `VideoPlayer`
- Periodic playback progress sync back to the helper

## Opening in Xcode

Create a new iOS App project in Xcode named `PocketMediaManager`, then replace the generated source files with the contents of `PocketMediaManager/` and use `Info.plist` from this folder.

This repository was scaffolded from Windows, so an `.xcodeproj` was not generated locally here.
