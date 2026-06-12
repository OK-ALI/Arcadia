# Arcadia Core

**A Gaming Universe**

Arcadia Core is a Windows desktop gaming hub built with Python, Flask,
pywebview, HTML, CSS, and vanilla JavaScript. It focuses on fast game discovery,
live gaming news, local catalog caching, hardware compatibility checks, and a
built-in download experience powered by libtorrent plus direct-file capture.

## Download

The Windows installer is published from GitHub Releases when a packaged build is
available:

- Repository: https://github.com/OK-ALI/Arcadia
- Latest stable release: `v0.1.5`
- Installer filename: `ArcadiaCoreSetup.exe`

## Documentation

- [Arcadia Core Documentation](docs/Arcadia_Core_Documentation.md)

## Features

- Arcadia Core branding with the subtitle **A Gaming Universe**.
- Dark mode by default with a persistent light theme toggle.
- Expandable and resizable sidebar with collapsed icon mode.
- Games Gallery with A-Z browsing, pagination, progressive loading, and cached
  artwork.
- Gallery cards render quickly first, then hydrate artwork and specs in the
  background.
- Offline catalog support with cached game metadata and media.
- Live News tab with gaming articles, upcoming releases, and event links.
- Source links are shown as attribution, while Arcadia branding stays separate.
- Official game, publisher, and Steam links are shown only when confidence is
  strong enough.
- Dynamic Windows system detection for CPU, RAM, GPU list, and VRAM.
- Compatibility badges based on available game requirements:
  - Compatible
  - Min Specs
  - Below Specs
  - Unknown Specs
  - Checking Specs
- Compatible Specs Only filter hides pending and unknown entries.
- Built-in libtorrent download manager with selectable files, queue priority,
  pause/resume, retry, folder opening, magnet copy, live speed, seeders, ETA,
  and progress.
- FDM-style capture review for pasted, clipboard, browser-extension, and
  `arcadia://` download links before anything starts downloading.
- Direct HTTP/HTTPS file downloads with safe filename handling, pause/resume,
  exact-file delete protection, and progress tracking.
- HTTP `.torrent` links are inspected and converted into the normal torrent
  preparation flow when libtorrent can parse them.
- Browser extension ZIP is served by Arcadia and packaged with production
  builds for manual Chrome/Edge unpacked installation.
- Custom download folder selection through a native Windows folder picker.
- Prepared torrent downloads honor the per-download save folder selected in the
  file-selection modal, even when the global default download folder is
  different.
- Resume data is saved so downloads can continue from previous progress after
  relaunch when torrent state is available.
- Tray mode keeps Arcadia available in the background until **Quit Arcadia** is
  selected.
- Single-instance guard prevents multiple tray/background sessions.
- Tray status can show download progress and speed.
- Windows notification support for completed downloads.
- Battery safety guard pauses active downloads when a laptop battery drops below
  20 percent while unplugged.
- Confirmation dialogs protect remove and delete-files actions.
- Inno Setup packaging for a Windows installer.

## Screens And Sections

- Home
- Games Gallery
- News
- Wishlist & Queue
- Downloads
- Offline Catalog
- History
- Game details modal
- Prepare download modal

## Download Behavior

Arcadia Core does not apply an artificial speed cap by default. Real speed still
depends on seeders, trackers, ISP limits, disk speed, Wi-Fi quality, and system
conditions. Users can set custom download and upload limits from the Downloads
settings panel.

Captured links are never started blindly. Arcadia first probes supported
`http`, `https`, and `magnet` links, shows a review modal with file type, host,
size when available, resumable support, save folder, priority, and start mode,
then adds the task only after user confirmation.

Arcadia does not bypass captchas, timers, ad pages, or hidden download flows.
Those pages must still produce a real downloadable URL before Arcadia can handle
the file in-app.

## Browser Download Capture

The `arcadia-extension` folder contains the Arcadia Download Interceptor
extension for Chromium-based browsers. In production builds, Arcadia packages
this folder and serves it as:

```text
/api/app/download-extension
/api/app/download-extension/arcadia-extension.zip
```

The extension captures supported browser downloads, focuses Arcadia, and sends
the URL into the same review modal used by pasted and protocol links. The
extension checks download creation, later browser updates, MIME types, final
URLs, filenames, and known direct-download hosts so redirected files have more
than one chance to be captured. Store buttons are hidden until real Chrome/Edge
store listings exist; manual ZIP or unpacked installation is the supported path
for now.

## Source Attribution

Arcadia Core can use public game/source pages for catalog metadata, artwork,
download links, and source attribution. Source names may appear in details or
links, but they are not used as Arcadia Core branding.

## Privacy And Local Data

Runtime cache, download state, resume files, offline catalog files, and cached
artwork are stored locally under the app data folder. Capture and crash logs are
also written under the app data folder instead of beside the executable. These
files are excluded from the Git repository.

## Development

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the desktop app:

```powershell
.\.venv\Scripts\python.exe app.py
```

If the workspace folder is renamed, recreate the virtual environment. Windows
virtualenv launchers can embed paths from the original directory.

## Build

Build the PyInstaller distribution:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build-dist.ps1
```

Build the Inno Setup installer:

```powershell
& "C:\Program Files\Inno Setup 7\ISCC.exe" packaging\inno\Arcadia.iss
```

The installer output is:

```text
installer-output\ArcadiaCoreSetup.exe
```

The PyInstaller build should include the packaged browser extension at:

```text
dist\Arcadia\_internal\arcadia-extension\manifest.json
```

## Recommended Release Flow

1. Run frontend and backend checks.
2. Smoke test the capture endpoints, including `/api/torrent/probe-url`.
3. Build the PyInstaller distribution.
4. Verify `dist\Arcadia\_internal\arcadia-extension\manifest.json` exists.
5. Build the Inno Setup installer.
6. Create a GitHub release tag.
7. Upload `ArcadiaCoreSetup.exe` as the release asset.

## Notes

- This project targets Windows.
- The current workspace path used during development is:

```text
D:\Projects\Arcadia
```

- Inno Setup preview builds may warn that they are not intended for production
  installers. Use a stable Inno Setup release for public production releases.
