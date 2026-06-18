# Arcadia Core V0.3.1 Stable

Arcadia Core v0.3.1 is a focused artwork reliability patch. It improves how
Arcadia finds artwork from catalog source pages and how My Library matches
installed/local/platform games back to Arcadia catalog entries.

## Highlights

- Improved source-page artwork extraction for OpenGraph/Twitter images,
  lazy-loaded WordPress images, linked images, and content images.
- Added stronger filtering for logos, placeholders, transparent loaders, and
  non-game images.
- Missing visible Gallery, Search, and Latest cards now request targeted
  artwork repair from source pages.
- Opening game details backfills missing cached catalog artwork when a cover is
  found.
- Improved Arcadia catalog title matching for installed/local/platform games by
  ignoring edition, platform, trademark, version, DLC, and repack text.
- My Library artwork matched from Arcadia catalog is cached in Arcadia app data
  and survives restart/offline use.
- Imported Steam games now use public Steam app metadata for genres, companies,
  languages, release date, requirements, and Steam page when Arcadia catalog
  metadata is missing.
- Imported Epic/local games can fall back to Arcadia title search when the A-Z
  catalog cache is empty or partial.
- My Library details now use platform-aware labels, showing installed size and
  library source for Steam/Epic/local games instead of irrelevant repack size
  fields.
- Gallery/Search/Latest artwork repair is now throttled so cards render quickly
  first and missing artwork fills in progressively.
- The native Windows title bar now syncs with Arcadia's active theme where
  supported by Windows DWM.
- Manual artwork overrides remain protected.
- Game details now show clearer artwork sources such as Manual, Steam, Epic,
  Arcadia Catalog, and Placeholder.

## Notes

- No new scraper source was added.
- No SteamGridDB or API-key artwork provider was added.
- No database migration file is required; existing My Library entries upgrade
  lazily when artwork refresh runs.
- Gallery artwork remains progressive so cards can render quickly first.
