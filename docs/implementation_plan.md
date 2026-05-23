# Implementation Plan - URI Protocol Handler, Extension & ZIP Download Fixes

This plan outlines the changes to resolve the browser extension block, allow the extension to launch Arcadia when closed, handle dynamic app install directories, fix the extension ZIP download failure, and ensure that captured downloads navigate to the downloader view and display a confirmation dialog.

## Proposed Changes

### Chrome/Edge Extension

#### [MODIFY] [manifest.json](file:///d:/Projects/Arcadia/arcadia-extension/manifest.json)
- Add `host_permissions` for `http://127.0.0.1:5000/*` to allow the background service worker to fetch/POST download details to the local Flask server without being blocked by Chrome's security policies.

#### [MODIFY] [background.js](file:///d:/Projects/Arcadia/arcadia-extension/background.js)
- Update `sendToArcadia(url)` to catch fetch errors (which occur if the Flask server is offline).
- If the local API is offline, trigger the custom protocol `arcadia://add-url?url=<url>` by navigating the current active tab to it, prompting Windows to launch the Arcadia application.

---

### Backend Server

#### [MODIFY] [server.py](file:///d:/Projects/Arcadia/backend/server.py)
- Update project path resolution in the extension zip/folder routes to use a dynamic root check. If `sys.frozen` is true, resolve the base directory relative to `sys.executable` instead of `__file__`. This allows the extension buttons to function properly regardless of where the app is installed.
- Update `/api/app/focus` to accept an optional `url` parameter in its JSON payload and pass it to the single-instance focus callback.
- Add `/api/app/open-external-url` POST endpoint to open a URL in the user's default system browser using `webbrowser.open()`.

---

### Desktop App Client

#### [MODIFY] [app.py](file:///d:/Projects/Arcadia/app.py)
- Implement `register_custom_protocol()` to write the custom protocol association to `HKEY_CURRENT_USER\Software\Classes\arcadia` on startup. Resolves python scripts or compiled `.exe` files dynamically.
- Update the focus callback signature of `TrayController.show_window` and `set_focus_callback` to accept an optional `url` and pass it to the handler.
- Update `focus_existing_instance(url)` to forward the protocol arguments to the running process before exiting the secondary process.
- Parse command-line args in `main()` for the custom protocol prefix, and handle startup link queuing if it's a cold boot.

#### [MODIFY] [index.html](file:///d:/Projects/Arcadia/frontend/index.html)
- Add `data-url` attributes and wire up class/id selectors so the JavaScript layer can capture ZIP download, Chrome Store, and Edge Store clicks, opening them in the external default system browser.

#### [MODIFY] [app.js](file:///d:/Projects/Arcadia/frontend/js/app.js)
- Bind click events for ZIP download, Chrome Store, and Edge Store buttons to call `/api/app/open-external-url`.
- Implement `window.onCapturedLinkDetected(url)`:
  - Immediately navigates the app view to the **Downloads** view using `switchView('downloads')`.
  - Displays a clean confirmation dialog: **"Captured Browser Download"** with the target URL.
  - If confirmed, calls `API.addDownloadUrl(url)` to add the direct download or show the file selection modal.
- Hook the focus handler in `app.py` to trigger `window.onCapturedLinkDetected(url)`.

---

## Verification Plan

### Automated Tests
- Syntax compile checks on `app.py` and `server.py`.

### Manual Verification
1. **Extension ZIP Download Verification**:
   - Open Arcadia. Click **Download ZIP**.
   - Verify that your system's default browser launches and downloads `arcadia-extension.zip`.
   - Click **Edge Store** / **Chrome Store**. Verify they open in your system browser.
2. **Extension Fetch Verification**:
   - Reload the extension in Edge/Chrome.
   - Click a direct download link while Arcadia is running. Verify that it cancels the browser download, focuses Arcadia, navigates to the Downloads view, and shows the Captured Download modal.
3. **App Closed Invocation**:
   - Close Arcadia entirely.
   - Click a direct download link.
   - Verify that the browser prompts to open Arcadia, launches it, navigates to the Downloads view, and shows the Captured Download modal.
4. **App Already Running URI Forwarding**:
   - Keep Arcadia running in the background.
   - In a terminal, run `.venv\Scripts\python.exe app.py "arcadia://add-url?url=https://datanodes.to/download/test.zip"`.
   - Verify that the running window restores focus, navigates to the Downloads view, and shows the Captured Download modal.
5. **Dynamic Path Verification**:
   - Verify clicking "Load Local (Developer)" opens Explorer to the extension directory.
