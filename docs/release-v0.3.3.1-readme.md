# Arcadia Core V0.3.3.1 Hotfix

Arcadia Core v0.3.3.1 is a focused stability hotfix for Gallery/Search artwork
and Compatible Specs hydration after the v0.3.3 release.

## Fixes

- Fixed Gallery/Search cards repeatedly returning to loading artwork after page
  changes or navigation.
- Fixed specs that stayed on `Checking Specs` even after details had already
  resolved the game as compatible or unavailable.
- Added durable per-game card metadata caching for resolved artwork and specs.
- Opening game details now backfills the shared card cache, so Gallery/Search
  reuse the resolved artwork/spec state.
- `Specs Unavailable` is now treated as a finished state instead of being
  converted back into a pending specs check.
- Hardened the JSON cache with a process lock so parallel artwork/spec workers
  do not overwrite each other or corrupt `cache.json`.
- Updated in-app version comparison so four-part hotfix versions like
  `v0.3.3.1` are detected correctly.

## Notes

- This is a patch-only release. No new v0.3.4 feature work is included.
- Existing Gallery, Search, Latest Repacks, details, and update APIs remain
  compatible.
- `v0.3.4` remains reserved for the next planned v0.3.x feature release.

## Verification

- Python compile checks for all backend modules and `app.py`.
- Smoke tests for Gallery, visible artwork hydration, requirements hydration,
  Latest Repacks, and Search.
- Targeted regression check confirming a game card keeps resolved artwork/spec
  status after details backfill.
