# Arcadia Core V0.1.5 Stable

This release focuses on bug fixes and polish before larger roadmap work.

## Fixes

- Fixed per-download save folders for prepared torrent downloads.
- Changing the global default download folder no longer overrides a game/torrent
  folder chosen in the file-selection modal.
- Preserved the chosen save folder while torrent metadata is still loading.
- Improved browser-extension capture reliability for redirected files, MIME-type
  based downloads, final URLs, and late filename updates.
- Updated Arcadia application, installer, tray, favicon, and extension icons.
- Removed the visible app icon from the in-app sidebar UI and replaced missing
  game artwork fallback with a neutral placeholder.

## Notes

- Captured links still need to become real downloadable URLs before Arcadia can
  manage them.
- Some file hosts do not expose file size during probe; Arcadia may show unknown
  size until the transfer begins.
- Reload the unpacked browser extension after installing this release so the
  v1.1 extension service worker is active.
