# Arcadia Core Documentation

**Project Name:** Arcadia Core  
**Subtitle:** A Gaming Universe  
**Platform:** Windows desktop  
**Repository:** https://github.com/OK-ALI/Arcadia  
**Installer Release:** https://github.com/OK-ALI/Arcadia/releases/tag/v0.3.3.1

## Project Overview

Arcadia Core is a Windows desktop gaming hub designed to bring game discovery,
catalog browsing, live gaming news, system compatibility checks, offline
metadata storage, and Arcadia Downloader into one polished application.
Downloads can come from prepared torrent metadata, direct HTTP/HTTPS files,
captured browser downloads, pasted links, clipboard detection, or the
`arcadia://` custom protocol.

The project was built as a full desktop product rather than a simple web page.
It combines a local Python backend with a desktop webview frontend, allowing the
app to feel modern while still having access to native Windows features such as
tray behavior, folder selection dialogs, system hardware scanning, and packaged
installer distribution.

## Purpose

The main goal of Arcadia Core is to create a convenient gaming command center
where users can:

- Browse a large games catalog.
- View game artwork, metadata, source links, and official links.
- Read live gaming news and upcoming release/event information.
- Check whether their Windows system meets available game requirements.
- Manage downloads from inside the app.
- Capture downloadable files into Arcadia without starting them blindly.
- Keep downloads running through tray mode until the app is explicitly quit.
- Build a local My Library view with installed-game status, executable links,
  launch controls, playtime tracking, and installed-folder size reporting.

The application is designed with performance, safety, and usability in mind:
large catalog operations are paginated, artwork/spec checks are hydrated in the
background, destructive download actions require confirmation, and battery-aware
download pausing protects laptop users.

## Current Roadmap Status

The current planning source of truth is
`docs/Arcadia_Core_Complete_Master_Roadmap.md`.

- `v0.1.x` shipped the Discover & Download foundation.
- `v0.1.5` shipped download path, capture, icon, and stale completed-download
  fixes.
- `v0.1.6` shipped the UI polish and packaging identity release.
- `v0.2.0` shipped the Own & Play MVP and is stable after user testing.
- `v0.2.1` shipped Smart Relink & Executable Detection.
- `v0.3.0` shipped the identity and polish release with Arcadia-branded naming,
  preset themes, theme-safe SVG interface icons, and cleaned My Library layout
  language.
- `v0.3.1` shipped the artwork reliability patch with stronger source-page
  artwork extraction, better Arcadia catalog title matching, and permanent My
  Library artwork caching.
- `v0.3.2` shipped the polish and trust release, focused on theme
  consistency, Compatible Specs Only coverage, collapsed sidebar download
  progress, My Library grid controls, stricter catalog matching, and browser
  extension capture reliability.
- `v0.3.3` shipped the maintainability and trust release, adding structured
  backend packages, in-app update checks, smarter title/spec matching, one
  resolved specs result, and an extension old-download replay fix.
- `v0.3.3.1` is the current hotfix release, keeping Gallery/Search artwork and
  specs cache results stable across page changes, detail opens, and app
  navigation.
- Later `v0.3.x` releases remain planned for optional soundtrack experience,
  collections, journal, save management, dashboards, and advanced filters.
- `v0.4.x` is planned for Discovery & Source Intelligence.
- `v0.5.x` is planned for Download Ecosystem & Production Hardening before
  `v1.0.x`.

## Technology Stack

### Backend

- Python
- Flask
- Requests
- BeautifulSoup
- libtorrent
- pystray
- pywebview bridge
- Windows CIM / WMIC hardware detection
- Browser-extension and custom-protocol capture support

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Font Awesome icons
- Responsive desktop-style UI
- v0.2.0 My Library / Own & Play UI with playable/backlog filters, launch
  buttons, running indicators, playtime display, and installed-size stats
- v0.2.2 My Library hover/focus card actions, full-artwork card presentation,
  Start Menu, Steam, Epic, local-only installed-game import review, and manual
  game-folder scanning
- v0.1.6 polished alignment, sidebar resizing, card grids, modals, responsive
  wrapping, focus states, and empty/loading states
- LocalStorage for persistent UI preferences

### Packaging

- PyInstaller for Windows app distribution
- Inno Setup for installer creation
- GitHub Releases for public installer delivery
- In-app update checks using GitHub Releases as the stable update source

## Application Architecture

Arcadia Core uses a local desktop architecture:

1. The desktop launcher starts a Flask backend server locally.
2. pywebview opens the frontend inside a native desktop window.
3. The frontend communicates with the backend through local HTTP API routes.
4. pywebview exposes selected native capabilities to JavaScript, such as folder
   selection dialogs.
5. A Windows tray controller keeps the app available in the background.
6. A single-instance guard prevents duplicate background/tray sessions.
7. Optional browser and protocol integrations pass captured links back into the
   local Arcadia API for review before download tasks are created.

This structure keeps the UI flexible while still allowing native desktop
behavior where it matters.

The backend is being organized into feature packages so new work does not keep
growing large top-level files:

- `backend/app_update` for GitHub release checks and installer flow.
- `backend/catalog` for source catalog logic, title matching, and requirements
  resolution.
- `backend/downloads` for downloader and capture code as it migrates.
- `backend/library` for My Library, artwork, launch, and import code as it
  migrates.
- `backend/news_sources` for news aggregation.
- `backend/system_info` for PC specs and compatibility helpers.

## Main Features

## Games Gallery

The Games Gallery provides an A-Z catalog experience with pagination and
background hydration.

Key behavior:

- Page-based loading for better speed and stability.
- Default page size of 24 games.
- A-Z and numeric browsing filters.
- Cards render first with available metadata.
- Artwork loads progressively in the background.
- Requirements are fetched for visible games instead of processing the entire
  catalog at once.
- Cached artwork is reused to avoid slow repeated loading.

This approach improves the user experience because the app becomes usable
quickly while heavier metadata tasks continue in the background.

## Artwork Handling

Arcadia Core avoids using source-site branding as game artwork. The artwork
priority is:

1. Cached game thumbnail.
2. Game thumbnail.
3. Cached game cover.
4. Game cover.
5. Screenshot.
6. Arcadia Core fallback icon.

Artwork is cached locally when available so future sessions can load the gallery
more quickly.

For My Library imports, Arcadia also resolves platform and local artwork:

- Steam imports use the local Steam app ID and public Steam CDN artwork.
- Epic imports use local Epic manifest metadata for a best-effort public artwork
  lookup.
- Matched Arcadia catalog entries can reuse existing cached Arcadia artwork.
- Catalog artwork matching uses cleaned title and slug comparison so local
  imports can match entries with edition/version text differences.
- Local-only games can use manual artwork selected from game details.
- Manual artwork is copied into Arcadia app data so cards remain stable even if
  the original image is moved.
- Game details show the current artwork source: Steam, Epic, Arcadia Catalog,
  Manual, or Placeholder.

## My Library Removal

Games can be removed from My Library from the game details modal with
confirmation. This removes the Arcadia library entry only. Installed game
folders, executables, and downloaded files are not deleted by this action.

## Game Details

Game detail views can show:

- Title and metadata.
- Game artwork and screenshots.
- Source attribution.
- Official game/publisher links when confidently available.
- Steam page links when confidently matched.
- Hardware compatibility panel.
- Storage warning when local disk space appears insufficient.
- Download preparation controls.

## Hardware Detection

Arcadia Core detects system hardware dynamically on each Windows machine.

Detected data includes:

- CPU name.
- Installed and usable RAM.
- Primary GPU.
- GPU list.
- VRAM when Windows exposes it.
- Local drive free space.

The backend prefers PowerShell CIM queries and falls back to WMIC-style detection
where needed. This makes the app more portable across different Windows systems.

## Compatibility System

Arcadia Core uses real available requirements when possible. It does not mark a
game as compatible based only on guesses.

Badge states:

- **Compatible:** System appears to meet recommended or target specs.
- **Min Specs:** System appears to meet minimum requirements but may be below
  recommended level.
- **Below Specs:** System appears below a known minimum requirement.
- **Checking Specs:** Requirements are still being fetched for the visible page.
- **Specs Unavailable:** Requirements could not be found or
  compared accurately after available sources were checked.

The current filter relies on one resolved requirement source selected by the
backend. It keeps Checking Specs results visible while hydration runs, then hides
final Below Specs and Specs Unavailable results once Arcadia has exhausted
trusted requirement sources.

## News System

The News page provides a live-updating gaming news area with cached results.

News content includes:

- General gaming news.
- PC gaming news.
- Hardware news.
- Release information.
- Official publisher/platform updates.
- Upcoming games.
- Upcoming gaming events.

News refreshes periodically and remains usable through cached content if a
network refresh fails.

## Download Manager

Arcadia Core includes Arcadia Downloader, which uses libtorrent for torrent work
and a direct HTTP/HTTPS worker for normal downloadable files.

Download features:

- Select files before adding a torrent to the download queue.
- Set priority and queue order.
- Pause and resume downloads.
- Retry failed downloads.
- Open download folders.
- Copy magnet links.
- Show live progress percentage.
- Show completed size, total size, download speed, upload speed, seeders, and
  ETA.
- Remove or clear completed rows even if libtorrent reports a late stale source
  URL/protocol error after the files are already complete.
- Persist resume data for relaunch continuity when torrent state is available.
- Custom default download folder.
- Native Windows folder picker.
- Per-download save folder selection in the torrent file-selection modal,
  independent from the global default download folder.
- Add direct HTTP/HTTPS file URLs after review.
- Add HTTP `.torrent` URLs into the normal torrent preparation flow when they
  can be parsed by libtorrent.
- Add captured links as paused or start them immediately after confirmation.

The app avoids artificial speed caps by default. Actual speed depends on seeders,
trackers, ISP conditions, disk speed, and network quality.

## Download Capture Flow

Arcadia uses an FDM-style review step for captured links. Supported capture
entry points include:

- Manual paste in the Downloads tab.
- Clipboard detection for direct downloadable URLs.
- Browser extension handoff.
- `arcadia://add-url?url=...` protocol handoff.

The flow is:

```text
Captured URL
-> Validate scheme and size
-> Probe metadata
-> Show review modal
-> User chooses folder, priority, and start mode
-> Arcadia creates the confirmed task
```

The review modal can show:

- Link type: magnet, torrent file, or direct file.
- Filename.
- Host.
- File size when available.
- Content type.
- Whether resume support appears available.
- Warnings when a URL looks like a webpage instead of a direct file.

Captured links never start downloading until the user confirms them.

## Browser Extension

The `arcadia-extension` folder contains the Arcadia Download Interceptor
extension for Chromium-based browsers.

Production behavior:

- PyInstaller packages the extension into the app distribution.
- Arcadia serves the extension ZIP from `/api/app/download-extension`.
- The extension uses browser download creation, update, MIME-type, filename, and
  final-URL signals to capture supported downloadable URLs.
- While Arcadia is running, the extension focuses the app and passes the URL to
  the review modal.
- If Arcadia is not reachable, the extension falls back to the registered
  `arcadia://` protocol.

Manual ZIP or unpacked installation is the supported browser integration path
until official Chrome/Edge store listings exist.

## Download Safety

Arcadia Core includes several safety measures:

- Remove from queue requires confirmation.
- Delete files requires a stronger confirmation because local files are removed.
- Direct HTTP filenames are sanitized before writing to disk.
- Direct HTTP deletes remove only the exact recorded downloaded file.
- Captured URLs are limited to `http`, `https`, and `magnet` schemes.
- Unsupported or malformed captured links are rejected before task creation.
- Battery guard pauses downloads when an unplugged laptop drops below 20 percent.
- Closing the window hides the app to tray instead of accidentally terminating
  background work.
- Quit Arcadia fully exits the app from the tray menu.
- Single-instance guard prevents duplicate tray sessions after relaunch.

## Tray Behavior

When the app window is closed, Arcadia Core can continue running in the system
tray. The tray menu can show download status such as progress and speed, and it
allows the user to reopen or fully quit Arcadia.

This makes the downloader feel like a proper desktop utility instead of a web
page that disappears when the window closes.

## User Interface

The UI is designed around a gaming hub identity:

- Arcadia red/orange accent colors.
- Arcadia Dark default theme.
- Arcadia Light theme.
- Current themes:
  - Arcadia Dark.
  - Arcadia Light.
  - Ember, replacing Neon Red with a warmer graphite/red-orange gaming style.
  - Abyss, replacing Electric Blue with a deeper black/navy/cyan sci-fi style.
- Theme customization controls:
  - Accent color selector.
  - Background intensity controls.
  - Normal or reduced motion preference.
- Subtle CSS-only gaming background treatments per preset theme.
- Expandable sidebar.
- Resizable sidebar.
- Tooltip-friendly collapsed navigation.
- Responsive downloader controls.
- My Library cards with installed, backlog, missing, and link-needed states.
- My Library cards reveal Launch, Open Folder, Relink, and Backlog actions on
  hover/focus instead of showing permanent action toggles.
- Start Menu import scans Windows shortcuts, resolves executable targets,
  filters non-game utilities, and asks for review before importing matches.
- Manual folder import lets users choose a game folder or parent games
  directory when Start Menu shortcuts do not expose the installed game.
- Steam and Epic imports read local launcher manifests and show detected games
  in the same confirmation modal before adding them to My Library.
- Imported Steam/Epic games are labeled by platform source and can be filtered
  separately in My Library.
- Styled confirmation dialogs.
- Persistent theme and sidebar preferences.

Arcadia Dark remains the default. All preset and customized themes use the same
layout and theme-safe icon masks, so interface icons remain visible across dark,
light, and accented themes. Theme backgrounds are intentionally lightweight CSS
layers, not large image assets, to keep the desktop app responsive.

## Data And Caching

Arcadia Core stores runtime data locally, including:

- Catalog cache.
- News cache.
- Download state.
- Torrent resume data.
- Captured direct-download task state.
- Temporary parsed torrent files.
- Offline library metadata.
- Executable links, launch count, last played timestamps, and playtime metadata.
- Cached artwork.
- Capture/download crash logs.

These runtime files are intentionally excluded from Git so the repository stays
focused on source code, assets, and packaging configuration.

## API Areas

Important backend API areas include:

- `/api/system/specs`
- `/api/library`
- `/api/library/index`
- `/api/library/artwork`
- `/api/library/requirements`
- `/api/news`
- `/api/torrent/status`
- `/api/torrent/settings`
- `/api/torrent/probe-url`
- `/api/torrent/add-url`
- `/api/torrent/prepare`
- `/api/torrent/confirm`
- `/api/torrent/control`
- `/api/offline/library`
- `/api/offline/game/<slug>`
- `/api/offline/link/<slug>`
- `/api/offline/launch/<slug>`
- `/api/offline/open-folder/<slug>`
- `/api/app/focus`
- `/api/app/download-extension`

These APIs separate frontend presentation from backend tasks such as scraping,
hardware detection, cache management, and download control.

## Packaging And Release

Arcadia Core is packaged in two stages:

1. PyInstaller builds a portable Windows distribution folder.
2. Inno Setup builds a user-facing Windows installer named
   `ArcadiaCoreSetup.exe`.

The installer is uploaded to GitHub Releases so users can download the app
without cloning the source code.

Production packaging also includes the browser extension. After a PyInstaller
build, the extension should exist at:

```text
dist\Arcadia\_internal\arcadia-extension\manifest.json
```

The Inno Setup installer copies the full `dist\Arcadia` folder, including the
packaged extension and frontend assets.

Uninstall behavior:

- The uninstaller stops a running Arcadia tray process before file removal.
- Installed files and leftover files under the Arcadia install directory are
  removed.
- Local user data under `%LOCALAPPDATA%\Arcadia Core` is preserved by default.
  The uninstaller prompts before removing settings, download state, resume
  data, My Library metadata, cached artwork, and logs.
- Downloaded games outside Arcadia's app data folder are never removed by the
  uninstaller.

## Engineering Challenges Solved

The project addresses several real desktop-app challenges:

- Migrating branding and workspace naming cleanly.
- Replacing an external downloader dependency with an in-process libtorrent
  engine.
- Preventing duplicate background sessions.
- Preserving download resume data across app restarts.
- Routing browser, clipboard, paste, and protocol captures through one review
  flow.
- Packaging the browser extension with the installed app.
- Keeping a very large gallery responsive.
- Evolving saved offline metadata into a launchable local game library.
- Avoiding false compatibility labels when requirements are unknown.
- Handling dynamic hardware detection across different Windows systems.
- Caching artwork without blocking the first render.
- Packaging Python, frontend assets, native dependencies, and icons into a
  Windows installer.

## Portfolio Summary

Arcadia Core demonstrates full-stack desktop application development:

- Backend API design.
- Frontend UI engineering.
- Native Windows integration.
- System hardware detection.
- Background task handling.
- Local caching strategy.
- Download manager implementation.
- Download capture and review workflow.
- Packaging and release workflow.
- GitHub repository and release publishing.

It is suitable as a portfolio project because it shows both product thinking and
engineering execution: the app has a clear user-facing purpose, practical
desktop features, polished UI behavior, and a complete build/release path.

## Future Improvements

Possible future improvements include:

- More official source mappings for publishers and games.
- Better Steam requirement matching for edge-case titles.
- Optional screenshots in the README.
- A dedicated settings page.
- Import/export for offline library data.
- More granular download scheduling controls.
- Signed installer builds.
- Automated CI checks and release packaging.
