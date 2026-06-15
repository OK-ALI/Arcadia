# Arcadia Core V0.2.0 Stable

This release introduces the first **Own & Play** milestone for Arcadia Core.
Offline Catalog has evolved into **My Library**, so saved and completed Arcadia
downloads can become launchable local games instead of only cached catalog
entries.

## V0.2.0 Highlights

- Renamed Offline Catalog to My Library across navigation, headers, cards,
  empty states, and documentation.
- Added installed-game state for saved games:
  - Backlog
  - Installed
  - Needs Link
  - Missing
- Added executable linking and relinking for installed folders.
- Added executable detection that scans selected install folders and filters out
  uninstallers, redistributables, setup files, crash reporters, helpers, and
  unrelated launchers.
- Added launch controls for linked games.
- Added running-state detection with a spinner on Launch buttons while Arcadia
  is tracking a launched game process.
- Added launch count, last played time, and playtime tracking.
- Updated playtime display so short test sessions show seconds instead of
  appearing as `Not played`.
- Added installed-folder disk usage reporting through the `Installed Size`
  library stat.
- Added automatic My Library enrollment when an Arcadia download completes with
  a catalog slug.
- Added My Library filters for Playable, Installed, Needs Link, Backlog, and
  All.
- Added library-aware Gallery/Search/Wishlist/Latest cards so installed games
  show their local state outside the library view.
- Disabled `Download inside App` for games that are already installed and
  linked.
- Improved My Library layout so complete cards and their action buttons appear
  before the grid scrolls.
- Improved collapsed sidebar alignment and running-button spacing.
- Kept existing `/api/offline/*` storage behavior compatible with earlier saved
  games.

## Technical Changes

- Added modular backend services:
  - `backend/library_service.py`
  - `backend/executable_detector.py`
  - `backend/game_launcher.py`
- Kept `backend/offline_library.py` focused on durable storage, cached media,
  import/export, stats, and legacy compatibility.
- Added new My Library APIs:
  - `GET /api/offline/game/<slug>`
  - `POST /api/offline/link/<slug>`
  - `POST /api/offline/launch/<slug>`
  - `POST /api/offline/open-folder/<slug>`
- Extended offline library records with install/play fields while preserving
  notes, tags, favorite state, saved metadata, and cached artwork.
- Added a live session registry for launched game processes so the frontend can
  show `Running` while the watched executable is active.

## Version History Included

### V0.1.6 Stable

- Full UI polishing release.
- Improved alignment, spacing, responsive behavior, modals, cards, toolbars,
  empty states, loading states, and focus states.
- Refined the resizable/collapsible sidebar and Windows AppUserModelID/icon
  packaging identity.
- Cleaned remaining mojibake and corrupted CSS comments.

### V0.1.5 Stable

- Fixed per-download save folder behavior for torrent/game downloads.
- Fixed completed downloads that could get stuck after late libtorrent protocol
  errors.
- Improved browser-extension capture reliability for redirected and MIME-based
  downloads.
- Updated Arcadia app, installer, tray, favicon, and extension icons.

### Earlier V0.1.x Foundation

- Built the core Arcadia desktop shell with Flask, pywebview, local APIs, and a
  Windows installer path.
- Added Games Gallery, latest repacks, game details, compatibility checks,
  live news, wishlist/queue, downloads, extension capture, clipboard capture,
  and `arcadia://` link handoff.
- Added built-in torrent/direct-download management with pause, resume,
  priority, folder opening, safe delete behavior, and tray support.

## Notes

- v0.2.0 does not add DODI, Crackwatcher, Steam import, soundtrack mode, save
  detection, collections, journal, or delete-installed-game features.
- Playtime is tracked from the linked executable that Arcadia launches. If the
  linked executable only opens another launcher and exits quickly, playtime can
  be undercounted. Relink to the real game executable when possible.
- Arcadia does not delete installed game folders in this MVP.
