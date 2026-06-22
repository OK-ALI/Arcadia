# Arcadia Core V0.3.3.4 Hotfix

Arcadia Core v0.3.3.4 is a focused Gallery specs, catalog performance, and UI
state hotfix. It keeps `v0.3.4` reserved for the next planned feature release.

## Fixes

- Changed visible Gallery specs hydration to progressive chunks instead of one
  large page-wide request.
- Fixed page-scoped specs hydration so changing Gallery pages does not leave the
  new page stuck behind an older in-flight request.
- Finalized missing requirements as `Specs Unavailable` when no source page,
  Steam, or PCGamingWiki match can be resolved confidently.
- Cached negative specs results so the same unavailable games do not repeatedly
  re-check on every navigation.
- Improved Compatible Specs Only hidden-count messaging.
- Fixed My Library launch/running button temporary state so hover-card actions
  do not briefly overlap while a game is launching.

## Notes

- This is a patch-only release.
- No new specs provider, source integration, or soundtrack feature is included.
- Low-confidence specs matches are still rejected to avoid misleading users.
- Users on `v0.3.3.1`, `v0.3.3.2`, or `v0.3.3.3` should be able to see this
  update inside Arcadia's App Settings update flow.

## Verification

- Python compile checks for backend modules and `app.py`.
- Frontend JavaScript syntax checks.
- API smoke checks for app version, Gallery, and visible requirements
  hydration.
- Verified unavailable specs return final non-pending metadata.
- PyInstaller and Inno Setup packaging.
