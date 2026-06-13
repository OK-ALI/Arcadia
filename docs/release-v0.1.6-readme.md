# Arcadia Core V0.1.6 Stable

This release focuses on UI polish and packaging identity before larger v0.2
feature work.

## Improvements

- Refined the shared UI system for buttons, icon buttons, inputs, toggles,
  badges, cards, empty states, loading states, modals, toasts, and focus rings.
- Improved page alignment, spacing, gutters, section headers, toolbars,
  pagination, and card grids across the existing Arcadia screens.
- Improved responsive behavior for desktop, laptop, and narrow layouts so
  grids, modals, download rows, and toolbar actions wrap more cleanly.
- Polished the resizable sidebar, including collapsed mode, resize affordance,
  menu alignment, footer actions, and system panel text handling.
- Improved game card hierarchy, compatibility badge handling, title wrapping,
  card footers, and artwork/loading presentation.
- Improved game details, capture review, prepare download, extension
  instructions, search history, and download-row presentation without changing
  downloader behavior.
- Removed remaining visible mojibake from frontend UI files and cleaned
  corrupted CSS comments.
- Included the Windows AppUserModelID packaging fix so rebuilt shortcuts and
  taskbar identity can use the Arcadia icon more reliably.

## Notes

- v0.1.6 does not add new scrapers, Steam integration, soundtrack mode, or
  downloader behavior changes.
- If the taskbar still shows an old icon after reinstalling, unpin the old
  shortcut and pin Arcadia again from the refreshed Start Menu shortcut.
- Visual browser QA may still need a manual pass on the installed build because
  Windows can cache webview/taskbar presentation outside the source tree.
