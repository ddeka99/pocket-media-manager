# Pocket Media Manager iOS App

This folder contains a SwiftUI client scaffold that matches the PC helper contract.

## What It Does

- Manual connection to the PC helper with a server URL and pairing token
- Library loading over the helper HTTP API
- Detail screen with metadata and feedback controls
- Native playback through `AVPlayer` and `VideoPlayer`
- Periodic playback progress sync back to the helper

## Main flow

1. Enter the PC helper base URL and pairing token.
2. Load the indexed library from `GET /library`.
3. Open a media item and request a playback URL from `POST /library/{id}/stream`.
4. Play with the native iPhone player.
5. Send progress and feedback back to the helper.

## Inputs From The PC Helper

- Base URL such as `http://<windows-pc-ip>:8765`
- Pairing token from `GET /pairing`
- Indexed media returned by the helper after a rescan

## When To Start On MacBook

Move to the MacBook/Xcode phase after `pc-helper/scripts/lan-check.ps1`
prints a reachable Wi-Fi URL and pairing token for the helper.

## Opening in Xcode

Create a new iOS App project in Xcode named `PocketMediaManager`, then replace the generated source files with the contents of `PocketMediaManager/` and use `Info.plist` from this folder.

This repository was scaffolded from Windows, so an `.xcodeproj` was not generated locally here.
