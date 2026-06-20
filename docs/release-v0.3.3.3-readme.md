# Arcadia Core V0.3.3.3 Hotfix

Arcadia Core v0.3.3.3 is a focused Gallery/Search artwork hydration and
in-app updater polish hotfix. It keeps `v0.3.4` reserved for the next planned
feature release.

## Fixes

- Fixed visible Gallery artwork hydration stopping after the first 8 cards on a
  24-game page.
- Updated the frontend visible-artwork pass to request the full visible page
  instead of a small first batch.
- Updated the backend visible-artwork endpoint to accept full visible page
  batches instead of clipping requests too aggressively.
- Increased visible artwork worker concurrency modestly so full-page hydration
  completes faster without forcing a catalog-wide artwork crawl.
- Preserved the permanent artwork cache behavior from `v0.3.3.1`, so resolved
  artwork should still survive page changes and app navigation.
- Improved the App Updates modal release-notes layout so headings, bullets, and
  status text render cleanly instead of looking like raw markdown.
- Fixed stale downloaded-installer state so `Download Update` and
  `Install & Restart` stay disabled when Arcadia is already up to date.

## Notes

- This is a patch-only release.
- Specs matching changes from the previous hotfix line are unchanged.
- Users on `v0.3.3.1` or `v0.3.3.2` should be able to see this update inside
  Arcadia's App Settings update flow.

## Verification

- Python compile checks for backend modules and `app.py`.
- Frontend JavaScript syntax checks.
- API smoke checks for app version, Gallery, and visible artwork hydration.
- Verified the visible artwork endpoint accepts 24 slugs in one request.
- Verified no-update updater state clears stale installer paths and disables
  install actions.
- PyInstaller and Inno Setup packaging.
