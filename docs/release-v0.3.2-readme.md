# Arcadia Core V0.3.2 Stable

Arcadia Core v0.3.2 is a polish and trust release. It keeps the v0.3.1 artwork
work intact while improving theme quality, My Library layout control,
Compatible Specs Only behavior, collapsed downloader status, and browser
extension capture reliability.

## Highlights

- Replaced the older Neon Red and Electric Blue presets with Ember and Abyss.
- Added accent color, background intensity, and reduced-motion preferences.
- Kept the native Windows title bar synced with Arcadia themes.
- Added a collapsed sidebar download badge for percent, active count, or
  metadata-only states.
- Replaced My Library grid presets with Auto plus a manual card-size slider.
- Tightened My Library card sizing and hover action alignment.
- Improved Compatible Specs Only with clearer Checking Specs, Compatible, Min
  Specs, Below Specs, and Specs Unavailable states.
- Added a conservative PCGamingWiki requirements fallback after source-page and
  Steam checks.
- Raised automatic catalog match thresholds to avoid wrong artwork/spec
  metadata on similarly named games.
- Improved the browser extension handoff with richer metadata and local retry
  behavior before `arcadia://` fallback.

## Notes

- Existing `theme-neon-red` and `theme-electric-blue` saved preferences migrate
  to Ember and Abyss automatically.
- Low-confidence external specs and catalog matches are not applied
  automatically.
- Soundtrack mode, collections, journal, saves, and deeper dashboard
  personalization remain planned for later v0.3.x releases.

## Install

Run `ArcadiaCoreSetup.exe`. The ZIP contains the same installer plus this
README.
