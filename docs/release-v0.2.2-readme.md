# Arcadia Core V0.2.2 Stable

This release completes the next Own & Play hardening pass for My Library.
Arcadia can now import installed games from common local sources, present cleaner
hover-action library cards, hydrate artwork for platform/local games, and remove
individual library entries without touching installed files.

## V0.2.2 Highlights

- Added installed-game import review for Start Menu shortcuts, Steam libraries,
  Epic manifests, and user-selected game folders.
- Added Steam and Epic filters in My Library.
- Preserved platform labels so imported Steam/Epic/local games do not appear as
  repack entries.
- Added hover/focus card actions for Launch, Open Folder, Relink, Mark Backlog,
  and Remove from My Library.
- Added a subtle blur/dim hover treatment behind library card actions.
- Improved My Library card alignment, compact action overlay spacing, and
  full-artwork presentation.
- Added platform/local artwork hydration:
  - Steam public CDN artwork by app ID.
  - Best-effort Epic artwork from local manifest metadata and public catalog
    lookups.
  - Arcadia catalog artwork matching using cleaned title and slug comparison.
  - Manual Change Artwork and Reset Artwork controls per game.
- Added per-game library removal. This removes only the Arcadia My Library
  entry; installed folders, executables, and downloaded files stay on disk.
- Improved catalog artwork matching so local games can match Arcadia entries
  even when edition, version, build, DLC, or repack text differs.
- Added `DELETE /api/offline/game/<slug>` for library-entry removal.
- Added `/api/offline/artwork/*` endpoints for refresh, manual assignment, and
  reset.

## V0.2.1 Included

- Improved executable relinking for installed games.
- Added exact `.exe` picker support when folder scanning is not enough.
- Improved executable candidate scoring and filtering.
- Added per-game installed size display.
- Improved playtime display for short sessions.
- Improved running-state behavior on Launch buttons.

## Version History Included

### V0.2.0 Stable

- Introduced My Library / Own & Play MVP.
- Added installed-game state, executable linking, launch controls, launch count,
  last played time, and playtime tracking.
- Added automatic My Library enrollment for completed Arcadia downloads with a
  catalog slug.
- Added Playable, Installed, Needs Link, Backlog, and All filters.
- Disabled `Download inside App` for already installed linked games.

### V0.1.6 Stable

- Full UI polishing release.
- Improved alignment, spacing, responsive behavior, modals, cards, toolbars,
  empty states, loading states, focus states, and sidebar resizing.
- Included Windows AppUserModelID/icon packaging identity fixes.

### V0.1.5 Stable

- Fixed per-download save folder behavior.
- Fixed completed downloads that could remain stuck after late libtorrent
  protocol errors.
- Improved extension capture reliability.
- Updated app, installer, tray, favicon, and extension icons.

### Earlier V0.1.x Foundation

- Built the Arcadia desktop shell with Flask, pywebview, local APIs, and Windows
  installer packaging.
- Added Games Gallery, Latest Repacks, game details, compatibility checks, live
  news, wishlist/queue, downloads, browser-extension capture, clipboard capture,
  and `arcadia://` handoff.
- Added torrent/direct-download management with pause, resume, priority, folder
  opening, safe delete behavior, and tray support.

## Notes

- v0.2.2 still never deletes installed game folders from My Library actions.
- Epic artwork is best-effort because some Epic manifests/public records do not
  expose usable cover art. Manual artwork remains the reliable fallback.
- Start Menu and folder imports always require user review before games are
  added.
- Steam/Epic/local imports are matched conservatively to avoid applying the
  wrong artwork.
