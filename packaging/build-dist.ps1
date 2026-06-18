param(
    [switch]$CleanOnly
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($CleanOnly) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Root\build", "$Root\dist"
    return
}

$PythonCandidates = @(
    "$Root\.venv\Scripts\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "python"
)

$Python = $null
foreach ($Candidate in $PythonCandidates) {
    try {
        & $Candidate -c "import PyInstaller" *> $null
        if ($LASTEXITCODE -eq 0) {
            $Python = $Candidate
            break
        }
    } catch {
        continue
    }
}

if (-not $Python) {
    throw "No Python environment with PyInstaller is available. Install requirements.txt first."
}

& $Python -m PyInstaller "$Root\Arcadia.spec" --noconfirm --clean

$ExtensionSource = "$Root\arcadia-extension"
$ExtensionTarget = "$Root\dist\Arcadia\arcadia-extension"
if (Test-Path -LiteralPath $ExtensionSource) {
    if (Test-Path -LiteralPath $ExtensionTarget) {
        Remove-Item -Recurse -Force $ExtensionTarget
    }
    Copy-Item -Recurse -Force $ExtensionSource $ExtensionTarget
}

$Required = @(
    "$Root\dist\Arcadia\Arcadia.exe",
    "$Root\dist\Arcadia\arcadia-extension\manifest.json",
    "$Root\dist\Arcadia\_internal\libtorrent\libcrypto-1_1-x64.dll",
    "$Root\dist\Arcadia\_internal\libtorrent\libssl-1_1-x64.dll",
    "$Root\dist\Arcadia\_internal\webview\lib\Microsoft.Web.WebView2.Core.dll"
)

foreach ($Path in $Required) {
    if (!(Test-Path -LiteralPath $Path)) {
        throw "Missing required bundle file: $Path"
    }
}

$LibtorrentPyd = Get-ChildItem -Path "$Root\dist\Arcadia\_internal\libtorrent" -Filter "__init__.cp*-win_amd64.pyd" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $LibtorrentPyd) {
    throw "Missing required libtorrent Python extension."
}

Write-Host "Arcadia build ready: $Root\dist\Arcadia"
