# Arcadia Core Documentation

**Project Name:** Arcadia Core  
**Subtitle:** A Gaming Universe  
**Platform:** Windows desktop  
**Repository:** https://github.com/OK-ALI/Arcadia  
**Installer Release:** https://github.com/OK-ALI/Arcadia/releases/tag/v0.1.0

## Project Overview

Arcadia Core is a Windows desktop gaming hub designed to bring game discovery,
catalog browsing, live gaming news, system compatibility checks, offline
metadata storage, and built-in download management into one polished application.

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
- Keep downloads running through tray mode until the app is explicitly quit.

The application is designed with performance, safety, and usability in mind:
large catalog operations are paginated, artwork/spec checks are hydrated in the
background, destructive download actions require confirmation, and battery-aware
download pausing protects laptop users.

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

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Font Awesome icons
- Responsive desktop-style UI
- LocalStorage for persistent UI preferences

### Packaging

- PyInstaller for Windows app distribution
- Inno Setup for installer creation
- GitHub Releases for public installer delivery

## Application Architecture

Arcadia Core uses a local desktop architecture:

1. The desktop launcher starts a Flask backend server locally.
2. pywebview opens the frontend inside a native desktop window.
3. The frontend communicates with the backend through local HTTP API routes.
4. pywebview exposes selected native capabilities to JavaScript, such as folder
   selection dialogs.
5. A Windows tray controller keeps the app available in the background.
6. A single-instance guard prevents duplicate background/tray sessions.

This structure keeps the UI flexible while still allowing native desktop
behavior where it matters.

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
- **Unknown Specs:** Requirements could not be compared accurately.
- **Checking Specs:** Requirements are still being fetched for the visible page.

The Compatible Specs Only filter hides unknown and pending results so users only
see games with real passing compatibility results.

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

Arcadia Core includes a built-in download manager using libtorrent.

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
- Persist resume data for relaunch continuity when torrent state is available.
- Custom default download folder.
- Native Windows folder picker.

The app avoids artificial speed caps by default. Actual speed depends on seeders,
trackers, ISP conditions, disk speed, and network quality.

## Download Safety

Arcadia Core includes several safety measures:

- Remove from queue requires confirmation.
- Delete files requires a stronger confirmation because local files are removed.
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
- Charcoal-dark default theme.
- Polished light theme.
- Expandable sidebar.
- Resizable sidebar.
- Tooltip-friendly collapsed navigation.
- Responsive downloader controls.
- Styled confirmation dialogs.
- Persistent theme and sidebar preferences.

The dark theme remains the default, while light mode is available for users who
prefer a cleaner high-contrast workspace.

## Data And Caching

Arcadia Core stores runtime data locally, including:

- Catalog cache.
- News cache.
- Download state.
- Torrent resume data.
- Offline library metadata.
- Cached artwork.

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
- `/api/torrent/prepare`
- `/api/torrent/confirm`
- `/api/torrent/control`
- `/api/app/focus`

These APIs separate frontend presentation from backend tasks such as scraping,
hardware detection, cache management, and download control.

## Packaging And Release

Arcadia Core is packaged in two stages:

1. PyInstaller builds a portable Windows distribution folder.
2. Inno Setup builds a user-facing Windows installer named
   `ArcadiaCoreSetup.exe`.

The installer is uploaded to GitHub Releases so users can download the app
without cloning the source code.

## Engineering Challenges Solved

The project addresses several real desktop-app challenges:

- Migrating branding and workspace naming cleanly.
- Replacing an external downloader dependency with an in-process libtorrent
  engine.
- Preventing duplicate background sessions.
- Preserving download resume data across app restarts.
- Keeping a very large gallery responsive.
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
