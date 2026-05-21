# Arcadia Core Packaging Notes

Arcadia uses a two-stage Windows packaging flow:

1. PyInstaller creates the self-contained app folder at `dist\Arcadia`.
2. Advanced Installer packages that folder into an MSI/EXE installer.

This keeps Python/native dependency collection under PyInstaller, while Advanced Installer handles installer UX, shortcuts, upgrades, signing, prerequisites, and optional auto-update flows.

## Build The App Folder

From `D:\Projects\Arcadia`:

```powershell
.\packaging\build-dist.ps1
```

The distributable source folder is:

```text
D:\Projects\Arcadia\dist\Arcadia
```

Important native runtime files that must exist after build:

```text
dist\Arcadia\_internal\libtorrent\__init__.cp312-win_amd64.pyd
dist\Arcadia\_internal\libtorrent\libcrypto-1_1-x64.dll
dist\Arcadia\_internal\libtorrent\libssl-1_1-x64.dll
dist\Arcadia\_internal\webview\lib\Microsoft.Web.WebView2.Core.dll
```

## Advanced Installer Project Setup

Create a new Advanced Installer project using one of these project types:

- MSI/EXE installer for normal desktop distribution.
- MSIX only if you specifically want Microsoft Store-style packaging and have tested WebView2/tray behavior there.

Recommended settings:

- Product name: `Arcadia Core`
- Publisher: your publisher/company name
- Install folder: `[ProgramFilesFolder]\Arcadia Core`
- Application folder content: add everything inside `dist\Arcadia`, preserving subfolders.
- Main executable: `Arcadia.exe`
- Shortcut: Start Menu shortcut to `Arcadia.exe`
- Optional desktop shortcut: user choice.
- Icon: `frontend\favicon.ico`
- Prerequisite: Microsoft Edge WebView2 Runtime, Evergreen Bootstrapper or Evergreen Standalone.
- Install scope: per-machine if using Program Files, per-user if you want no admin prompts.
- Upgrades: enable major upgrades and keep a stable Upgrade Code.
- Digital signing: sign the installer and `Arcadia.exe` when you have a certificate.

Runtime user data is stored outside Program Files at:

```text
%LOCALAPPDATA%\Arcadia Core
```

Do not remove that folder on uninstall unless you deliberately add an optional “remove user data” flow.

## Advanced Installer CLI

If Advanced Installer is installed and you have an `.aip` project, you can build it from command line with:

```powershell
$ai = "C:\Program Files (x86)\Caphyon\Advanced Installer 23.6\bin\x86\AdvancedInstaller.com"
& $ai /build "D:\Projects\Arcadia\packaging\advanced-installer\Arcadia.aip"
```

Adjust the Advanced Installer version/path to your machine.

## Why Advanced Installer Here

Advanced Installer is better than Inno Setup when you want MSI/MSIX, GUI project editing, built-in prerequisites, signing workflows, CI/CD integration, updater support, and enterprise deployment features. Inno Setup is still fine for a lightweight scripted EXE installer.
