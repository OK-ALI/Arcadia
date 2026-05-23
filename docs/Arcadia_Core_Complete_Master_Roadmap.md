# Arcadia Core — A Gaming Universe
## Master Roadmap (Final Consolidated Version)
**Platform:** Windows Desktop
**Status:** Planning Complete
**Version:** Final Discussion Snapshot

---

# Vision

Arcadia Core is not simply a game downloader.

Arcadia aims to become a local-first gaming ecosystem where users can:

- Discover games
- Download games
- Manage games
- Launch games
- Track playtime
- Manage saves
- Organize collections
- Record gaming history
- Preserve gaming memories

All inside one unified gaming universe.

---

# Product Roadmap

```text
v0.1 — Discover & Download      ✅ Shipped
v0.2 — Own & Play               🔜 Next
v0.3 — Polish & Personalize     📋 Planned
v1.0 — Gaming Universe          🌌 Vision
```

---

# v0.1 — Discover & Download ✅

## Gallery

- A-Z browsing
- Pagination
- Search
- Game metadata
- Artwork hydration
- Local artwork caching

## Compatibility System

- CPU checks
- GPU checks
- VRAM checks
- RAM checks
- Storage checks
- Compatibility badges

## News

- Gaming news feed
- Periodic refresh
- Cache fallback

## Download Manager

- Libtorrent integration
- Pause
- Resume
- Retry
- Queue management
- Progress tracking
- ETA tracking
- Speed tracking
- Seeder tracking
- Resume persistence

## Reliability

- Battery guard
- Tray mode
- Single instance protection
- Native folder picker
- Installer packaging
- GitHub release distribution

## Existing Safety

- Disk space validation

---

# v0.2 — Own & Play 🔜

## Offline-First Library

Library remains fully usable without internet.

Available offline:

- Launch games
- Playtime tracking
- Collections
- Journal
- Download history
- Save locations
- Cached artwork
- Library management

Only Gallery and News require internet.

---

## Automatic Library Enrollment

```text
Download Complete
↓
Add To Library
↓
Detect Executable
↓
Detect Save Locations
↓
Ready To Launch
```

No manual add required for Arcadia downloads.

Sources:

- Arcadia Download
- Start Menu Scan
- Folder Scan
- Manual Add

---

## Library Interface

### Visible Card Elements

- Artwork
- Game title
- Status
- Playtime
- Launch button
- More actions button

### More Actions Menu

```text
▶ Launch Game
📂 Open Install Folder
💾 Open Save Folder
📝 Game Journal
⭐ Favorite
📚 Add To Collection
🔄 Relink Executable
✔ Verify Installation
📋 Copy Install Path

────────────

🗑 Remove From Library
❌ Delete Game
```

### Remove From Library

Removes Arcadia metadata only.

Game files remain installed.

### Delete Game

Deletes installed game files while preserving:

- History
- Playtime
- Collections
- Journal

---

## Smart Executable Detection

Priority order:

1. Start Menu Scan
2. Folder Scan Heuristics
3. Manual Linking

Capabilities:

- Existing install detection
- New install detection
- Relinking moved games

---

## Existing Game Scanner

```text
Scan Installed Games
↓
Match Against Catalog
↓
Import To Library
```

---

# Dynamic Save Detection System

## Automatic Scan Locations

- Documents
- Documents/My Games
- Saved Games
- AppData/Local
- AppData/LocalLow
- AppData/Roaming
- ProgramData
- Steam userdata
- Installation directory

## Nested Folder Detection

Arcadia crawls matching directories using safe depth limits.

Example:

```text
Documents
└── My Games
    └── Resident Evil 4
        └── SaveData
            └── slot01.sav
```

Detected save folder:

```text
Resident Evil 4/SaveData
```

## Save Detection Signals

### Save File Types

```text
.sav
.save
.dat
.bin
.profile
.slot
.sgd
```

### Save Folder Names

```text
Save
Saves
SaveData
SaveGames
Profiles
UserData
```

## Confidence-Based Detection

Scores:

- Title match
- Alias match
- Save signatures
- Recent modification
- Folder naming

Highest-confidence path selected automatically.

## Multiple Save Locations

```text
💾 Save Locations >
   Save Files
   Config Files
   Screenshots
   Mods Folder
```

Selecting an item opens File Explorer directly.

---

# Download History

Tracks:

- Game name
- Download date
- Download size
- Status
- Folder location
- Library status

Actions:

- Open folder
- Re-download
- Add to library
- Remove history entry

---

# Playtime Tracking

Tracks:

- Total playtime
- Session count
- First played
- Last played
- Longest session

---

# Search, Sorting & Filtering

## Search

Search:

- Game title
- Collections
- Journal entries
- Status

## Sorting

```text
Custom Order
Recently Played
Recently Added

A-Z
Z-A

Most Played
Least Played

Largest Size
Smallest Size

Newest Install
Oldest Install

Favorites First
```

## Filters

```text
Installed
Playing
Completed
Favorites
Recent
Broken
Hidden
```

---

# Continue Playing Shelf

```text
Continue Playing

Tekken 8
Played 15 Minutes Ago

Resident Evil 4
Played Yesterday
```

Automatically generated from recent activity.

---

# Library Health Monitoring

States:

```text
Installed
Missing
Moved
Broken
```

Features:

- Validation
- Relinking
- Recovery actions

---

# Safety & Reliability Layer

## Protected Folder Detection

Prevent deletion of:

- Windows folders
- Program Files
- User profile roots
- Desktop root
- Documents root
- Downloads root

Unsafe operations blocked automatically.

---

## Installation Validation

Before launch:

- Verify executable exists
- Verify path exists
- Verify folder accessibility

Broken games automatically flagged.

---

## Hash Verification

Support:

- SHA256
- MD5
- CRC32

Detect:

- Corruption
- Incomplete downloads

---

## Save Safety

- Save verification
- Backup before restore
- Backup before import
- Backup rotation

---

## Crash Recovery

Restore:

- Active downloads
- Window state
- Filters
- Current page

After unexpected shutdown.

---

## Undo Actions

Temporary undo for:

- Remove from Library
- Remove from Collection
- Remove Favorite

---

## Visual Safety Indicators

```text
Green  = Safe
Yellow = Warning
Red    = Destructive
```

Consistent application-wide.

---

# v0.3 — Polish & Personalize 📋

## Collections

Examples:

```text
Favorites
Currently Playing
Completed
Backlog
Co-op Games
Horror Collection
Must Replay
```

Features:

- Custom collections
- Collection statistics
- Collection filtering

---

## Game Journal

Per-game timeline.

Examples:

```text
Reached Gold Rank
Need to finish Chapter 7
Try Dexterity Build
Playing Friday Night
```

Features:

- Timeline view
- Search
- Timestamps

---

## Statistics Dashboard

Tracks:

- Total hours played
- Most played games
- Weekly activity
- Monthly activity
- Storage usage
- Average session
- Completed games

---

## Advanced Filters

- Genre
- Year
- Developer
- Publisher
- Compatibility
- Playtime range
- Storage size

---

## Save Management

- Backup save
- Restore save
- Export save
- Import save

---

# UI Polish Philosophy

Do NOT redesign Arcadia.

Improve:

- Clarity
- Consistency
- Alignment
- Accessibility
- Discoverability

Keep:

- Existing workflows
- Existing navigation
- Existing identity

---

## Layout Improvements

- Better spacing
- Better alignment
- Consistent margins
- Cleaner hierarchy
- Better information grouping

---

## Visual Improvements

- Improved game cards
- Better typography
- Better iconography
- Better status badges
- Better color hierarchy
- Unified button system
- Refined red/black theme

---

## Hero Shelf

Large featured section:

- Last played game
- Last activity
- Total playtime
- Quick launch

---

## Continue Playing Redesign

Larger featured cards.

Console-inspired experience.

---

## Recently Added Shelf

Highlights newly added games.

---

## Game Card Evolution

- Better artwork presentation
- Cleaner metadata
- Better hover states
- Improved launch visibility
- Playing Now indicators

---

## Game Details Redesign

Sections:

- Overview
- Playtime
- Save Locations
- Journal
- Collections
- History
- Statistics

---

## Sidebar Improvements

- Icons + labels
- Better spacing
- Better discoverability
- Cleaner navigation

---

## User Experience Improvements

- Better empty states
- Skeleton loading
- Toast notifications
- Smart tooltips
- Context-aware menus
- Right-click support
- Keyboard shortcuts
- First-run onboarding

---

## Accessibility

- Larger UI mode
- Better keyboard navigation
- Improved focus states
- Better contrast options

---

## Micro Interactions

- Card hover elevation
- Smooth menu transitions
- Button feedback
- Collection expansion animation

---

## Database Protection

- Automatic backups
- Backup before updates
- Backup before migrations

---

## Recovery Mode

If corruption occurs:

- Detect backup
- Restore backup
- Recovery wizard

---

## Soft Delete System

Recently removed entries recoverable before permanent deletion.

---

## Library Export & Import

Export:

- Library
- Collections
- Journal
- Playtime
- Save locations
- Settings

Portable backup package.

Restore entire Arcadia setup on another machine.

---

# v1.0 — Gaming Universe 🌌

Unified gaming ecosystem.

## Integrations

- Steam
- Epic Games
- GOG
- Ubisoft Connect
- EA App
- Battle.net
- Arcadia Downloads
- Manual Installations

## Unified Systems

- Unified Library
- Unified Launcher
- Unified Playtime Tracking
- Unified Save Management

---

# Storage Architecture

## Database

SQLite

Stores:

- Library
- Playtime
- Journal
- Collections
- History
- Save paths
- Settings

## Cache

- Artwork
- News
- Catalog

## Downloads

User-defined location.

## Backups

- Database backups
- Save backups
- Export packages

---

# Final Product Identity

Arcadia Core is a local-first gaming platform focused on:

- Discovery
- Ownership
- Organization
- Preservation
- Personalization

One Library.
One Launcher.
One Gaming Universe.
