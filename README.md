# Arcadia Core

**A Gaming Universe**

Arcadia Core is a desktop gaming hub built with Python Flask, pywebview, HTML,
CSS, and vanilla JavaScript. It brings together game discovery, offline catalog
storage, hardware compatibility checks, live gaming news, official game links,
and a built-in libtorrent download manager.

## Highlights

- Games Gallery with local artwork fallback from the Arcadia icon.
- Offline catalog with cached artwork, source metadata, and storage stats.
- Live News tab with trusted gaming news, official updates, upcoming games, and events.
- Official game/publisher links when they can be resolved with confidence.
- RAM and GPU-aware compatibility badges.
- Built-in downloads with libtorrent, selectable files, speed limits, live speed, ETA, peers, and seeders.
- High-speed defaults with no artificial download cap unless the user sets one.

## Source Attribution

The app can use public source pages for catalog/download metadata. Source names
may appear as attribution inside details or links, but Arcadia Core branding is
independent.

## Development

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

If the workspace folder is renamed, recreate the virtual environment. Windows
virtualenv launchers often embed paths from the original directory.

## Build

```powershell
.\venv\Scripts\pyinstaller.exe Arcadia.spec
```

The expected workspace path after rename is:

```text
D:\Projects\Arcadia
```

