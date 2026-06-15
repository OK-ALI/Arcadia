# Arcadia Core - A Gaming Universe
## Master Roadmap

**Platform:** Windows Desktop  
**Status:** Current as of v0.2.2 Stable  
**Latest Stable:** v0.2.2  

---

# Vision

Arcadia Core is not simply a game downloader.

Arcadia aims to become a local-first gaming ecosystem where users can:

- Discover games.
- Download games.
- Manage games.
- Launch games.
- Track playtime.
- Manage installed game folders.
- Manage saves.
- Organize collections.
- Record gaming history.
- Preserve gaming memories.

All inside one unified gaming universe.

---

# Product Roadmap

```text
v0.1.x - Discover & Download                 Shipped
v0.1.5 - Download Capture Bug Fixes          Shipped
v0.1.6 - UI Polish                           Shipped
v0.2.0 - Own & Play MVP                      Shipped and stable
v0.2.1 - Smart Relink & Executable Detection Shipped
v0.2.2 - Start Menu Import + Hover Library Cards Shipped and stable
v0.3.x - Identity, Polish & Personalize      Planned
v0.4.x - Discovery & Source Intelligence     Planned
v0.5.x - Download Ecosystem & Hardening      Planned
v1.0.0 - Gaming Universe                     Vision
```

---

# v0.1.x - Discover & Download

Status: shipped.

## Gallery

- A-Z browsing.
- Pagination.
- Search.
- Game metadata.
- Artwork hydration.
- Local artwork caching.
- Game details.

## Compatibility System

- CPU checks.
- GPU checks.
- VRAM checks.
- RAM checks.
- Storage checks.
- Compatibility badges.
- Compatible Specs Only filtering.

## News

- Gaming news feed.
- Upcoming release and event links.
- Periodic refresh.
- Cache fallback.

## Download Manager

- Libtorrent integration.
- Direct HTTP/HTTPS file downloads.
- Browser extension capture.
- Clipboard and paste capture.
- `arcadia://` protocol handoff.
- Pause, resume, retry, and queue priority.
- Progress, ETA, speed, and seeder tracking.
- Resume persistence.
- Safe remove and delete-files actions.

## Reliability

- Battery guard.
- Tray mode.
- Single-instance protection.
- Native folder picker.
- Installer packaging.
- GitHub release distribution.

---

# v0.1.5 - Download Capture Bug Fixes

Status: shipped.

- Fixed per-download save folder behavior for prepared torrent downloads.
- Fixed completed downloads that could get stuck after late libtorrent protocol
  errors.
- Improved browser-extension capture reliability for redirected files, MIME
  types, final URLs, and late filename updates.
- Updated Arcadia app, installer, tray, favicon, and extension icons.
- Removed the visible app icon from the in-app sidebar UI.

---

# v0.1.6 - UI Polish

Status: shipped.

- Refined buttons, icon buttons, inputs, toggles, badges, cards, empty states,
  loading states, toasts, modals, and focus states.
- Improved alignment, spacing, gutters, page sections, card grids, and toolbar
  behavior.
- Improved responsive behavior across desktop, laptop, and narrow layouts.
- Polished the resizable and collapsible sidebar.
- Improved game cards, details modals, prepare download, capture review, search
  history, and download rows.
- Cleaned visible mojibake and corrupted CSS comments.
- Included the Windows AppUserModelID/taskbar icon identity fix.

---

# v0.2.0 - Own & Play MVP

Status: shipped and user-tested stable.

## My Library

Offline Catalog became My Library.

Library entries now support:

- Backlog.
- Installed.
- Needs Link.
- Missing.
- Cached artwork.
- Saved metadata.
- Notes, tags, and favorite state preservation.

## Installed Game State

- Completed Arcadia downloads with a catalog slug can auto-enroll into My
  Library.
- Completed download folders are recorded as install folders.
- Install folders are scanned for likely launchable `.exe` files.
- Games with clear executable matches become launchable.
- Games with multiple candidates become Needs Link.
- Missing folders or executables are marked Missing.

## Launch And Playtime

- My Library cards include Launch controls.
- Linked games can launch from Arcadia.
- Arcadia records launch count, last played time, and playtime.
- Running games show a spinner and Running state while Arcadia is tracking the
  launched process.
- Short play sessions display seconds instead of appearing as Not Played.

## Library Stats And Layout

- My Library shows saved games, installed count, playtime, installed folder
  size, and backlog count.
- Installed Size measures real linked install folders, not source/repack size.
- Cards show complete artwork, metadata, playtime, last played, and action
  controls before the grid scrolls.
- Gallery, Search, Wishlist, and Latest cards can display library state.
- Download inside App is disabled for games already installed and linked.

## Backend Structure

v0.2.0 introduced modular Own & Play services:

- Library service for installed state, metadata merging, and enrollment.
- Executable detector for safe folder scanning and candidate scoring.
- Game launcher for process launching, running state, and playtime callbacks.

---

# v0.2.1 - Smart Relink & Executable Detection

Status: implemented / in testing.

Goal: make manual linking accurate and trustworthy for games already in My
Library.

## Exact Executable Picker

- Add an exact `.exe` picker when folder scan is not enough.
- Let the user choose the real game executable directly.
- Validate that the selected executable is inside the chosen install folder.
- Keep the folder picker as the first linking path, but expose exact selection
  as a clear fallback.

## Smarter Candidate Scoring

Improve executable detection so it:

- Prefers file names similar to the game title or slug.
- Prefers root folders or likely game binary folders.
- Prefers larger real game executables over tiny helpers.
- Down-ranks launchers, helpers, tools, crash reporters, and secondary apps.
- Excludes setup, uninstall, redistributable, DirectX, VC, support, and repair
  executables.
- Uses Start Menu shortcut targets as a helper signal for games already being
  linked.

## Candidate Review UI

- Show the recommended executable first.
- Show confidence, file name, relative path, size, and reason.
- Make uncertain matches visually different from strong matches.
- Keep the user in control when multiple candidates exist.

## Playtime Reliability

- Explain when playtime may be undercounted because the selected executable is
  only a launcher that exits quickly.
- Encourage relinking to the real game executable when Arcadia detects a very
  short launcher-style session.
- Keep playtime based on the process Arcadia actually launches.

## Per-Game Installed Size

- Show each installed game's folder size on its library card or details panel.
- Reuse the installed-folder measurement already used for total Installed Size.
- Avoid double-counting shared folders in summary stats.

## My Library Polish

- Polish card action alignment, running button state, filters, and responsive
  behavior.
- Refresh installed/running/link state consistently across My Library, Gallery,
  Search, Wishlist, Latest, and Details.

## Packaging Cleanup

- Keep the build script compatible with the working Python 3.11 build path.
- Avoid brittle checks tied to only one Python minor version.
- Document the Inno Setup preview warning and prefer a stable Inno release for
  public production packaging.

---

# v0.2.2 - Installed Game Import + Hover Library Cards

Status: in progress.

Goal: find already-installed games from the user's PC through Start Menu
shortcuts, Steam/Epic library manifests, or user-selected install folders, then
offer to import them into My Library while polishing cards so actions appear on
hover instead of permanently occupying card space.

## Start Menu Scan

- Scan user and common Start Menu shortcut folders.
- Read `.lnk` shortcut targets.
- Resolve executable target, working directory, icon path, and shortcut name
  when available.
- Ignore shortcuts that do not point to launchable executables.

## Filtering

Filter out:

- Non-game apps.
- Uninstallers.
- Setup/installers.
- Repair tools.
- Redistributables.
- System shortcuts.
- Browser/web shortcuts.
- Vendor utilities that are not games.

## Matching

- Match shortcut names and executable targets against Arcadia catalog titles and
  slugs.
- Prefer strong title/slug matches.
- Use executable path and folder names as supporting evidence.
- Avoid duplicate imports for games already in My Library.

## Review Before Import

- Show a Start Menu import review modal before adding anything.
- Import strong matches as Installed.
- Import uncertain matches as Needs Link.
- Allow the user to reject individual matches.
- Never auto-import without user confirmation.

## Manual Folder Scan

- Let users choose a game folder or parent games directory when Start Menu
  shortcuts do not find enough games.
- Scan the selected folder and first-level child folders for likely game
  executables.
- Match folder names and executable names against known Arcadia catalog/library
  titles and slugs.
- Allow unmatched local-only installed games to enter My Library with minimal
  metadata when a launchable executable can be found.
- Use the same review modal and confirmation rules as Start Menu import.

## Platform Library Scan

- Read Steam library manifests from configured Steam library folders.
- Read Epic Games launcher manifests from the local Epic manifest directory.
- Import strong executable matches as Installed and uncertain ones as Needs
  Link.
- Label platform games by their source, such as Steam Library or Epic Games,
  instead of showing repack/source-site labels.
- Add My Library filters for Steam and Epic imports.
- Keep all platform imports behind the review modal; never auto-import.

## Hover Library Cards

- Remove permanent card action buttons from the normal card body.
- Reveal Launch, Open Folder, Relink Executable, and Mark Backlog as a
  hover/focus overlay.
- Keep keyboard access with focus-visible states and button labels.
- Keep touch layouts usable by exposing actions when hover is unavailable.
- Preserve click-on-card behavior for opening game details.

## Full Artwork Cards

- My Library cards show full artwork with contain-fit presentation.
- Use a soft dark/blurred backdrop for artwork that does not match the card
  aspect ratio.
- Keep card tracks fixed so complete cards appear in rows and only the grid
  scrolls vertically.
- Leave Gallery and Search card artwork behavior unchanged unless shared CSS is
  directly affected.

## Platform And Local Artwork

- Hydrate Steam imports from public Steam CDN artwork using local app IDs.
- Try Epic public/catalog artwork from local Epic manifest metadata when
  available.
- Cache resolved platform artwork into Arcadia offline media.
- Add manual Change Artwork and Reset Artwork controls in game details.
- Keep manual artwork copied into Arcadia app data so original user files are
  not referenced directly.

---

# v0.3.x - Identity, Polish & Personalize

Status: planned after Own & Play linking/import is reliable.

Goal: make Arcadia feel more professional, coherent, and alive before deeper
source intelligence and downloader hardening work.

Planned split:

```text
v0.3.0 - Product Naming & UI Language
v0.3.1 - Theme System Expansion
v0.3.2 - Optional Soundtrack Experience
v0.3.3 - Collections & Journal Foundation
v0.3.4 - Save Management & Personal Dashboard
```

## Naming And Product Language

- Rename technical or generic labels into Arcadia-branded product language.
- Use `Arcadia Downloader` instead of `Built-in Downloader`.
- Use consistent terms for:
  - My Library.
  - Backlog.
  - Installed.
  - Needs Link.
  - Arcadia Downloader.
  - Capture Review.
  - Prepare Download.
- Audit buttons, empty states, toasts, modal titles, settings labels, and docs
  for wording that feels temporary, developer-focused, or unclear.
- Keep source names as attribution only, not as Arcadia feature names.

## Theme System

- Keep charcoal dark as the default Arcadia identity.
- Keep light mode as a polished supported theme.
- Add more theme presets after the base UI is stable:
  - Arcadia Dark.
  - Arcadia Light.
  - Neon Red.
  - Console Green.
  - Midnight Blue.
- Persist selected theme locally.
- Keep accessibility contrast acceptable for every theme.
- Avoid one-note palettes where every element becomes the same color.

## Gaming Soundtrack Experience

- Add an optional soundtrack mode that can make Arcadia feel like a gaming hub.
- Keep soundtrack mode off by default.
- Use only user-provided local audio files or clearly permitted bundled audio.
- Add simple controls:
  - Play/pause.
  - Next/previous.
  - Volume.
  - Mute.
  - Enable/disable on startup.
- Store soundtrack settings locally.
- Do not stream copyrighted commercial game music from unofficial sources.
- Do not block app use if audio files are missing.

## Collections

Examples:

- Favorites.
- Currently Playing.
- Completed.
- Backlog.
- Co-op Games.
- Horror Collection.
- Must Replay.

Features:

- Custom collections.
- Collection statistics.
- Collection filtering.

## Game Journal

Per-game timeline for player notes.

Examples:

- Reached Gold Rank.
- Need to finish Chapter 7.
- Try Dexterity Build.
- Playing Friday Night.

Features:

- Timeline view.
- Search.
- Timestamps.

## Save Management

- Save detection.
- Save backup.
- Save restore.
- Save export.
- Save import.
- Backup before restore/import.
- Backup rotation.

## Statistics Dashboard

- Total hours played.
- Most played games.
- Weekly activity.
- Monthly activity.
- Storage usage.
- Average session.
- Completed games.

## Advanced Filters

- Genre.
- Year.
- Developer.
- Publisher.
- Compatibility.
- Playtime range.
- Storage size.
- Installed state.

## User Experience

- Continue Playing shelf.
- Recently Added shelf.
- Better game details sections.
- Context-aware menus.
- Right-click support.
- Keyboard shortcuts.
- First-run onboarding.
- Better accessibility and larger UI options.

---

# v0.4.x - Discovery & Source Intelligence

Status: planned after My Library personalization foundations are in place.

Goal: make Arcadia better at explaining what games are available, where metadata
comes from, and what status a game is in without weakening the all-in-one app
experience.

## Metadata Enrichment

- Improve official game, publisher, and Steam page matching.
- Add clearer confidence labels for official links.
- Prefer real game artwork and screenshots over source-site branding.
- Improve requirements/spec scraping fallbacks when source pages are incomplete.
- Track when game metadata was last refreshed.

## Release And Status Intelligence

- Add clearer game lifecycle signals:
  - Released.
  - Upcoming.
  - Recently updated.
  - Installed.
  - In backlog.
  - Missing executable.
- Add an Upcoming and Recently Updated experience that is separate from My
  Library.
- Keep cracked/pending/source-status integrations as optional research items
  until a reliable and safe source policy is agreed.

## Search And Discovery Improvements

- Add richer search sorting:
  - Relevance.
  - Release date.
  - Size.
  - Installed state.
  - Compatibility.
  - Recently added.
- Add filter chips for source, status, compatibility, installed state, and
  backlog state.
- Improve empty states so users know whether results are missing because of
  filters, offline mode, or incomplete catalog hydration.

## Recommendations

- Add local-first recommendations from:
  - Wishlist.
  - Backlog.
  - Installed games.
  - Genres and tags.
  - Compatibility.
- Avoid cloud accounts or personal data upload.
- Keep recommendations explainable, not opaque.

## Source Policy

- Keep source names as attribution only.
- Do not use third-party source branding as Arcadia branding.
- Do not bypass captchas, timers, ad pages, or hidden-download flows.
- Only add source integrations that can support Arcadia's in-app flow or provide
  useful catalog/status value without misleading users.

---

# v0.5.x - Download Ecosystem & Production Hardening

Status: planned as the final pre-v1 maturity phase.

Goal: make Arcadia's downloader, capture system, packaging, and data safety
stable enough to support a v1.0 release.

## Download Manager Maturity

- Improve unknown-size download handling and user messaging.
- Improve direct-file resume behavior and failure recovery.
- Add download history as a durable user-facing view.
- Add queue profiles:
  - Balanced.
  - Max speed.
  - Quiet/background.
  - Battery safe.
- Add clearer retry reasons and error recovery actions.

## Browser Capture Maturity

- Re-test extension capture against common redirect and final-URL flows.
- Improve late filename, MIME type, and content-disposition handling.
- Keep extension capture review mandatory before starting downloads.
- Add extension diagnostics so users can see whether Arcadia, the extension, and
  browser permissions are connected.

## Data Safety

- Add automatic backups for My Library data before migrations.
- Add export/import for:
  - Library.
  - Playtime.
  - Collections.
  - Journal.
  - Settings.
  - Download history.
- Add recovery mode for corrupted local data.
- Add soft-delete or undo for non-destructive library actions.

## Packaging And Release Hardening

- Replace preview Inno Setup with a stable production installer build.
- Make release builds repeatable from one script:
  - Checks.
  - PyInstaller build.
  - Extension verification.
  - Inno installer.
  - ZIP packaging.
  - Release notes asset.
- Ensure installer, shortcuts, taskbar, tray, and app window use consistent
  Arcadia identity.
- Keep Defender false-positive risk low by avoiding suspicious packaging tricks,
  documenting build inputs, and keeping unsigned-build expectations clear.

## v1 Readiness Checklist

- Browse, search, and gallery are fast enough for normal use.
- Downloads can start, pause, resume, fail, retry, remove, and delete safely.
- My Library can import, link, launch, track, and recover games reliably.
- Local data can be backed up, restored, and migrated.
- Installer and releases are repeatable.
- Documentation reflects the real app behavior.

---

# v1.0.0 - Gaming Universe

Status: vision.

v1.0 should only happen after the full core loop is dependable:

```text
Browse -> Download/Capture -> Install/Link -> Launch -> Track -> Manage
```

## Unified Systems

- Unified library.
- Unified launcher.
- Unified playtime tracking.
- Unified save management.
- Unified download history.
- Unified personalization.

## Possible Integrations

- Steam.
- Epic Games.
- GOG.
- Ubisoft Connect.
- EA App.
- Battle.net.
- Arcadia downloads.
- Manual installations.

## Storage Architecture Direction

Current storage remains JSON-based for the v0.2 MVP line. A future v1-class
upgrade may move durable library data into SQLite when collections, journal,
history, saves, and import/export become larger.

---

# Final Product Identity

Arcadia Core is a local-first gaming platform focused on:

- Discovery.
- Ownership.
- Organization.
- Preservation.
- Personalization.

One Library.  
One Launcher.  
One Gaming Universe.
