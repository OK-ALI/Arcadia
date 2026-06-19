# Arcadia Core V0.3.3 Stable

Arcadia Core v0.3.3 is a maintainability and trust release. It adds in-app
GitHub release awareness, starts the backend package restructuring, improves
title/spec matching, and fixes a browser-extension issue where Edge/Chrome could
replay old browser download history after loading the unpacked extension.

## What's New

- Added an `Update Available` header pill backed by GitHub Releases.
- Added an App Updates modal with current version, latest version, release
  notes, download state, and install/restart actions.
- Added backend update APIs for version checks, update checks, installer
  download, and installer launch.
- Added structured backend feature packages for app updates, catalog logic,
  downloads, library, news sources, and system info.
- Added a shared title matcher with stronger cleanup, unique-token scoring,
  sequel-number guards, and conflict handling.
- Added a single resolved requirements pipeline so the UI shows one chosen specs
  source instead of multiple competing blocks.
- Improved Compatible Specs Only behavior through clearer resolved requirement
  metadata.
- Fixed extension startup/history replay by accepting `onChanged` and filename
  events only for current-session downloads first seen by `onCreated`.

## Notes

- Updates are user-confirmed only. Arcadia does not silently install updates.
- The installer is downloaded into Arcadia app data, then launched externally
  because Windows cannot replace the running executable in-place.
- Low-confidence specs/catalog matches are not applied automatically.
- Existing public API behavior remains compatible.

## Verification

- Python backend compile checks.
- Frontend and extension JavaScript syntax checks.
- Smoke tests for core APIs and new update endpoints.
- PyInstaller and Inno Setup packaging.

