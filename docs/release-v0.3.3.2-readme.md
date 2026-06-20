# Arcadia Core V0.3.3.2 Hotfix

Arcadia Core v0.3.3.2 is a focused updater and App Settings menu hotfix. It
keeps `v0.3.4` reserved for the next planned feature release.

## Fixes

- Improved in-app update checks so Arcadia selects the highest stable GitHub
  release by parsed version instead of relying only on GitHub's latest-release
  endpoint.
- Kept support for four-part hotfix versions such as `v0.3.3.1` and
  `v0.3.3.2`.
- Forced a fresh update check on app startup so a just-published release is not
  hidden by the short local update-check cache.
- Kept the top-right control as an App Settings button instead of changing it
  into a theme-only icon.
- Added an update dot to the App Settings button when a newer Arcadia release is
  available.
- Added pop in/out motion and a blurred glass effect to the App Settings menu.

## Important Update Note

Arcadia Core v0.3.3 itself cannot detect `v0.3.3.1` or `v0.3.3.2` from inside
the app because its updater only understood three-part versions. Users on
`v0.3.3` should install this hotfix manually once from GitHub Releases.

After this hotfix line is installed, future four-part hotfix releases can be
detected normally by Arcadia's in-app updater.

## Verification

- Python compile checks for updater, backend routes, config, and app entry.
- Frontend JavaScript syntax checks.
- In-app update version selection checks.
- PyInstaller and Inno Setup packaging.
