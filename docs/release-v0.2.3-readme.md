# Arcadia Core V0.2.3 Stable

This is a focused patch release for My Library import and card-action polish
after v0.2.2.

## V0.2.3 Fixes

- Removed the `Remove from My Library` action from the card hover overlay to
  prevent cramped/overlapping hover controls.
- Kept `Remove from Library` in game details with confirmation.
- Restored the My Library hover overlay to four actions:
  - Launch
  - Open Folder
  - Relink
  - Mark Backlog
- Improved Start Menu import for game/repack shortcuts whose `.lnk` target is
  stale or missing.
- Added fallback to shortcut `IconLocation` when it points to a real local
  `.exe`, so shortcuts like `FitGirl-Launcher.exe` entries can still resolve to
  the real nested game executable.
- Continued filtering uninstall/support shortcuts.

## Version History Included

### V0.2.2 Stable

- Added installed-game import review for Start Menu, Steam, Epic, and selected
  game folders.
- Added hover/focus My Library cards, platform/local artwork hydration, manual
  artwork controls, and per-game library removal.
- Added Steam/Epic filters and platform/local labels.

### V0.2.1 Stable

- Improved executable relinking, exact `.exe` picker support, installed size
  display, short-session playtime display, and Launch running states.

### V0.2.0 Stable

- Introduced My Library / Own & Play MVP with installed-game state, executable
  linking, launch controls, playtime, and automatic enrollment for completed
  Arcadia downloads.

### V0.1.x Foundation

- Added the Arcadia desktop shell, Games Gallery, latest repacks, game details,
  compatibility checks, live news, wishlist, downloads, browser-extension
  capture, clipboard capture, `arcadia://` handoff, installer packaging, and UI
  polishing.

## Notes

- v0.2.3 does not add manual catalog matching.
- Removing a game from My Library still never deletes installed game files.
- Start Menu imports still require user review before adding or updating games.
