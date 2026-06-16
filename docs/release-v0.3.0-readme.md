# Arcadia Core V0.3.0 Stable

Arcadia Core v0.3.0 is a UI identity and polish release. It keeps the v0.2.x
Own & Play and downloader behavior stable while improving product language,
interface icons, preset themes, and My Library arrangement.

## Highlights

- Renamed user-facing downloader language to **Arcadia Downloader**.
- Renamed **Download inside App** to **Download with Arcadia**.
- Renamed **Needs Link** to **Needs Launch File**.
- Renamed **Relink Executable** to **Change Launch File**.
- Renamed **Source Size** to **Download Size**.
- Added theme-safe SVG interface icons from `assets/icons`.
- Added preset themes:
  - Arcadia Dark
  - Arcadia Light
  - Neon Red
  - Electric Blue
- Added a theme picker menu with persisted theme selection.
- Added subtle theme-specific gaming background treatments so each preset feels
  distinct without using heavy image assets.
- Polished My Library action grouping and tightened card sizing.
- Kept Remove from My Library inside game details with confirmation.
- Replaced the desktop/tray/taskbar/installer icon with the new light Arcadia
  app icon.
- Hardened uninstall behavior so Arcadia closes from the tray before removal
  and asks before deleting local app data.
- Added icon attribution documentation for the user-provided SVG assets.

## Notes

- No downloader API changes.
- No scraper changes.
- No database migration.
- Missing interface icons continue to use the existing Font Awesome fallback.
- Local app data under `%LOCALAPPDATA%\Arcadia Core` is preserved unless the
  user confirms removal during uninstall.
- Soundtrack mode, collections, journal, saves, and dashboard personalization
  remain planned for later v0.3.x releases.
