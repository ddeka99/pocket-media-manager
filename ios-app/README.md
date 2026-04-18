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

## Personal Device Testing

1. Connect your iPhone to the MacBook and trust the computer on the device if prompted.
2. In Xcode, select the `PocketMediaManager` target, then open Signing & Capabilities.
3. Leave signing automatic, choose your Personal Team, and change the bundle identifier if Xcode says the default one is unavailable.
4. Pick your iPhone as the run destination and press Run.

The current plist allows plain HTTP for LAN testing so the app can talk to the Windows helper at `10.0.0.235:8765` during this personal-device phase.
