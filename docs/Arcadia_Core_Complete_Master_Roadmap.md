# Arcadia Core - A Gaming Universe
## Master Roadmap

**Platform:** Windows Desktop  
**Status:** Current as of v0.3.3.4
**Latest Stable:** v0.3.3.4

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
v0.2.3 - Start Menu Shortcut + Hover Fixes   Shipped and stable
v0.3.0 - UI Identity, Naming, Icons & Themes Shipped and stable
v0.3.1 - Reliable Catalog Artwork & Matching Shipped and stable
v0.3.2 - Theme Polish, Specs Coverage & Reliability Shipped and stable
v0.3.3 - Structured Backend, Updates & Specs Trust Shipped and stable
v0.3.3.1 - Gallery Artwork & Specs Cache Hotfix Shipped and stable
v0.3.3.2 - Updater & App Settings Menu Hotfix Shipped and stable
v0.3.3.3 - Visible Gallery Artwork + Updater Modal Hotfix Shipped and stable
v0.3.3.4 - Gallery Specs + Launch Button Hotfix Current
v0.3.x - Personalize & Library Depth         Planned
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
- Needs Launch File.
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
- Games with multiple candidates become Needs Launch File.
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
- Download with Arcadia is disabled for games already installed and linked.

## Backend Structure

v0.2.0 introduced modular Own & Play services:

- Library service for installed state, metadata merging, and enrollment.
- Executable detector for safe folder scanning and candidate scoring.
- Game launcher for process launching, running state, and playtime callbacks.

---

# v0.2.1 - Smart Relink & Executable Detection

Status: shipped.

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
- Import uncertain matches as Needs Launch File.
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
- Reveal Launch, Open Folder, Change Launch File, and Mark Backlog as a
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

Status: v0.3.3.4 current; later v0.3.x releases planned.

Goal: make Arcadia feel more professional, coherent, and alive before deeper
source intelligence and downloader hardening work.

Planned split:

```text
v0.3.0 - UI Identity, Naming, Icons & Preset Themes
v0.3.1 - Reliable Catalog Artwork & Library Matching
v0.3.2 - Theme Polish, Specs Coverage & Reliability
v0.3.3 - Structured Backend, Updates & Specs Trust
v0.3.3.1 - Gallery Artwork & Specs Cache Hotfix
v0.3.3.2 - Updater & App Settings Menu Hotfix
v0.3.3.3 - Visible Gallery Artwork + Updater Modal Hotfix
v0.3.3.4 - Gallery Specs + Launch Button Hotfix
v0.3.4 - Optional Soundtrack Experience
v0.3.5 - Collections & Journal Foundation
v0.3.6 - Save Management & Personal Dashboard
```

## v0.3.0 UI Identity, Naming, Icons And Preset Themes

- Rename technical or generic labels into Arcadia-branded product language.
- Use `Arcadia Downloader` instead of `Built-in Downloader`.
- Use `Download with Arcadia` instead of `Download inside App`.
- Use `Needs Launch File` instead of `Needs Link`.
- Use `Change Launch File` instead of `Relink Executable`.
- Use `Download Size` instead of `Source Size`.
- Add theme-safe SVG interface icons from `assets/icons`.
- Keep Font Awesome as fallback for icons that are not yet available as SVG.
- Add icon attribution documentation for user-provided Flaticon assets.
- Group My Library actions into primary import actions and maintenance actions.
- Keep remove-from-library inside game details with confirmation only.
- Ship preset themes:
  - Arcadia Dark.
  - Arcadia Light.
  - Neon Red.
  - Electric Blue.
- Add subtle CSS-only gaming background treatments for each preset.
- Persist selected theme locally.
- Ensure icons adapt across all preset themes with CSS mask/currentColor
  rendering.

## v0.3.1 Reliable Catalog Artwork And Library Matching

- Improve source-page image extraction for OpenGraph/Twitter images, lazy-loaded
  WordPress images, linked image targets, and content images.
- Repair missing visible Gallery/Search/Latest artwork by hydrating source pages
  and updating the cached catalog entry.
- Improve title matching for installed/local/platform games by ignoring edition,
  platform, trademark, repack, version, and DLC noise.
- Cache matched My Library artwork under Arcadia app data so it survives restart
  and offline use.
- Keep manual artwork overrides protected and show clearer artwork source labels
  such as Manual, Steam, Epic, Arcadia Catalog, and Placeholder.

## v0.3.2 Theme Polish, Specs Coverage And Reliability

Status: shipped and stable.

Goal: make the current interface and trust systems feel more dependable before
adding new personalization features.

### Compatible Specs Only

- Improved the requirements resolver pipeline:
  - Source page specs first.
  - Steam requirements second.
  - PCGamingWiki no-key fallback third.
- Cache resolved requirements per game slug/title so Gallery and Search do not
  repeatedly refetch the same specs.
- Apply external requirements only after strict title matching.
- Store requirement metadata:
  - `requirements_source`.
  - `requirements_confidence`.
  - `requirements_checked_at`.
  - `requirements_status`.
- Replaced vague Unknown Specs behavior with clearer states:
  - Checking Specs.
  - Compatible.
  - Min Specs.
  - Below Specs.
  - Specs Unavailable.
- When Compatible Specs Only is enabled, keep Checking Specs games visible
  temporarily, then hide only final Below Specs and Specs Unavailable results.
- Show a small notice or count when games are hidden because specs are
  unavailable.

### Sidebar Download Progress

- Keep download percentage visible when the sidebar is collapsed.
- Replace the previously hidden collapsed badge with a compact icon overlay:
  - Percent for known-size downloads.
  - Active count for unknown-size downloads.
  - `M` or similar metadata indicator for metadata-only states.
- Preserve full status text in the nav tooltip.
- Ensure the badge does not overlap the Downloads icon or active sidebar state.

### My Library Grid

- Make My Library card sizing visually align with Games Gallery card rhythm.
- Replace the preset-only grid dropdown with:
  - Auto mode.
  - Manual card-size slider.
- Persist the slider value in local storage.
- In Auto mode, use responsive gallery-like tracks.
- In manual mode, map slider values to card width and artwork height while
  preserving complete rows and grid-only vertical scrolling.

### Stricter Catalog Matching

- Raise automatic Arcadia catalog match confidence for library metadata and
  artwork.
- Require stronger title token overlap for short titles and sequel-heavy
  franchises.
- Keep exact cleaned-title and exact slug matches fast.
- Store match score and reason as today.
- Avoid applying catalog artwork or metadata when confidence is below the
  stricter threshold.
- Preserve Steam, Epic, and local metadata when no confident Arcadia catalog
  match exists.

### Theme Refresh And Accessibility Polish

- Keep Arcadia Dark as the default identity theme.
- Keep Arcadia Light as a polished supported theme.
- Replace Neon Red with Ember:
  - Graphite base.
  - Warm ember/red-orange accents.
  - Less neon glow, more premium gaming hardware feel.
- Replace Electric Blue with Abyss:
  - Deep black/navy base.
  - Cyan and steel-blue accents.
  - Cooler sci-fi mood without making the whole UI blue.
- Add simple theme customization controls:
  - Accent color selector.
  - Background intensity: Off, Subtle, Immersive.
  - Motion preference: Normal or Reduced.
- Keep layout identical across themes; themes change color, depth, background
  treatment, and accents only.
- Polish native Windows title bar theme sync fallback behavior.
- Audit buttons, inputs, cards, modals, menus, badges, disabled states, focus
  rings, hover states, and scrollbars across all themes.
- Keep contrast readable in light mode and accent themes.
- Respect reduced-motion preferences for hover/card transitions where practical.

### Extension Reliability

- Keep the existing extension project.
- Improve repeated-download capture by tracking IDs and URLs separately.
- Capture final URL, original URL, filename, MIME type, and referrer where
  available.
- Prefer final URL when present, but keep the original URL as fallback metadata.
- Improve local Arcadia handoff retry behavior before using `arcadia://`.
- Keep unsupported captcha/timer/ad pages as fallback links only.
- Keep permissions minimal:
  - `downloads`.
  - `tabs`.
  - local Arcadia host permission.

## v0.3.3 Structured Backend, Updates And Specs Trust

Status: shipped and stable.

Goal: improve maintainability and trust before larger personalization features.
This release starts the backend package split, adds GitHub release awareness,
centralizes title/spec matching, and fixes old browser download replay from the
extension.

### Backend Structure

- Add feature packages under `backend/`:
  - `app_update`.
  - `catalog`.
  - `downloads`.
  - `library`.
  - `news_sources`.
  - `system_info`.
- Keep `server.py` as route wiring.
- Use compatibility imports while older modules migrate gradually.
- Keep new v0.3.3 logic in the appropriate package instead of adding more
  weight to top-level backend files.

### Update Source

- Use GitHub Releases as the public update source.
- Check the latest stable release from `OK-ALI/Arcadia`.
- Compare the installed app version against the latest release tag.
- Ignore drafts and prereleases unless a future setting explicitly enables
  preview channels.
- Cache the last update check result locally to avoid repeated network calls.

### Header Update Indicator

- Add an `Update Available` pill in the top-right header near the theme/settings
  controls only when a newer stable version exists.
- Keep the header quiet when Arcadia is current.
- Use a compact download/update icon so it does not crowd the search bar or
  Compatible Specs Only toggle.
- Show a tooltip with the latest version and release date.

### Update Modal

Clicking the update pill opens a focused update modal showing:

- Current installed version.
- Latest available version.
- Release title.
- Release notes summary.
- Asset size when available.
- Buttons:
  - Check Again.
  - Download Update.
  - Install & Restart.
  - Later.

### Settings App Updates Section

- Add an App Updates area for manual control from the top controls menu.
- Show:
  - Current version.
  - Latest checked version.
  - Last checked time.
  - Update channel, stable-only for v0.3.3.
- Add controls:
  - Check Again.
  - Download Update.
  - Install & Restart.

### Download And Install Flow

- Download `ArcadiaCoreSetup.exe` from the latest GitHub release asset.
- Save the installer into Arcadia app data.
- Verify the downloaded file exists and has a reasonable size before launching.
- Ask for confirmation before starting the installer.
- Launch the installer and let it handle replacing the installed app.
- Keep a fallback link to the GitHub release if download or launch fails.

### Safety And UX

- Never install silently in v0.3.3.
- Never auto-download without user action.
- Do not interrupt active downloads without warning.
- If downloads are active, tell the user to pause/finish them before updating.
- Keep release notes short inside Arcadia, with a link to the full GitHub
  release.
- Handle offline mode gracefully with a small `Could not check updates` message
  only when the user manually asks.

### Smarter Title And Specs Matching

- Add a shared title matcher for specs, artwork, catalog, Steam, Epic, and local
  library matching.
- Normalize trademarks, edition labels, DLC/bonus text, repack/source labels,
  platform labels, punctuation, and version/build text.
- Use guarded token scoring so unique title words help confidence while common
  franchise words are weak.
- Protect sequel numbers, so `TEKKEN 8` cannot match `TEKKEN 7`.
- Treat close candidate conflicts as uncertain instead of applying specs or
  artwork automatically.
- Resolve requirements in one backend pipeline and return only one final specs
  result to the UI.
- Use source page requirements first, then Steam, then PCGamingWiki when title
  confidence is strong enough.

### Extension Replay Fix

- Record extension startup time and current-session download IDs.
- Ignore browser download records that started before extension load.
- Ignore completed, interrupted, cancelled, or history-restored records.
- Allow `onChanged` and filename capture only for download IDs first seen by
  `onCreated` in the current extension session.
- Preserve repeated capture for fresh user downloads.

## v0.3.3.1 Gallery Artwork And Specs Cache Hotfix

Status: shipped and stable.

Goal: keep progressive Gallery/Search artwork and specs hydration from
restarting or reverting when users change pages, open details, or navigate
between app sections.

- Store resolved card artwork and specs in a durable per-game metadata cache.
- Merge cached card metadata into Gallery, Search, and Latest Repacks responses.
- Backfill card metadata when game details resolves artwork or requirements.
- Treat `Specs Unavailable` as a final cached state instead of returning it to
  `Checking Specs`.
- Add cache write locking so parallel artwork/spec hydration workers do not
  overwrite each other.
- Support four-part hotfix versions such as `v0.3.3.1` in the in-app updater.

## v0.3.3.2 Updater And App Settings Menu Hotfix

Status: shipped and stable.

Goal: make Arcadia's update controls clearer and make future hotfix detection
more reliable without using the reserved `v0.3.4` feature slot.

- Select the highest stable GitHub release by parsed version instead of relying
  only on GitHub's latest-release endpoint.
- Keep support for four-part hotfix versions such as `v0.3.3.1` and
  `v0.3.3.2`.
- Force one fresh update check on app startup so a newly published release is
  not hidden by the short local update-check cache.
- Keep the top-right button as an App Settings control instead of a theme-only
  icon.
- Show an update dot on the App Settings button when a newer version is
  available.
- Add pop in/out motion and a blurred glass treatment to the App Settings menu.

## v0.3.3.3 Visible Gallery Artwork + Updater Modal Hotfix

Status: shipped and stable.

Goal: make visible-page artwork hydration cover the full Gallery/Search page
instead of stopping after the first small batch, and make the App Updates modal
clearer and safer after the app is already current.

- Hydrate up to 24 visible Gallery cards in one pass, matching the current page
  size.
- Allow the backend visible-artwork endpoint to accept full visible page batches
  instead of clipping requests to 12.
- Increase visible artwork worker concurrency modestly so full-page hydration
  finishes faster without starting a full catalog-wide artwork crawl.
- Keep the existing permanent artwork cache behavior from `v0.3.3.1`.
- Render update release notes as structured headings, paragraphs, and bullet
  lists instead of raw markdown text.
- Clear stale downloaded-installer state when no newer release is available, so
  `Download Update` and `Install & Restart` stay disabled when Arcadia is
  already up to date.

## v0.3.3.4 Gallery Specs And Launch Button Hotfix

Status: current stable hotfix.

Goal: make visible Gallery specs checks finish reliably without slowing the
whole page, and fix a short-lived My Library running-button overlap.

- Hydrate pending visible specs progressively in small page-scoped chunks.
- Let new Gallery pages start their own specs checks even if an older page
  request is still finishing.
- Return and cache final `Specs Unavailable` results when no confident source,
  Steam, or PCGamingWiki requirements can be resolved.
- Keep strict title matching so low-confidence specs are not applied just to
  clear a checking badge.
- Show clearer Compatible Specs Only hidden-count messaging.
- Keep Launch, Opening, and Running button markup stable so hover-card actions
  do not overlap or resize during launch.

## Naming And Product Language

- Continue auditing buttons, empty states, toasts, modal titles, settings labels,
  and docs for wording that feels temporary, developer-focused, or unclear.
- Use consistent terms for:
  - My Library.
  - Backlog.
  - Installed.
  - Needs Launch File.
  - Arcadia Downloader.
  - Capture Review.
  - Prepare Download.
- Keep source names as attribution only, not as Arcadia feature names.

## Theme System

- Keep charcoal dark as the default Arcadia identity.
- Keep light mode as a polished supported theme.
- Refine theme presets after the base UI is stable.
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
