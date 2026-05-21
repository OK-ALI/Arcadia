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

& "$Root\.venv\Scripts\python.exe" -m PyInstaller "$Root\Arcadia.spec" --noconfirm --clean

$Required = @(
    "$Root\dist\Arcadia\Arcadia.exe",
    "$Root\dist\Arcadia\_internal\libtorrent\__init__.cp312-win_amd64.pyd",
    "$Root\dist\Arcadia\_internal\libtorrent\libcrypto-1_1-x64.dll",
    "$Root\dist\Arcadia\_internal\libtorrent\libssl-1_1-x64.dll",
    "$Root\dist\Arcadia\_internal\webview\lib\Microsoft.Web.WebView2.Core.dll"
)

foreach ($Path in $Required) {
    if (!(Test-Path -LiteralPath $Path)) {
        throw "Missing required bundle file: $Path"
    }
}

Write-Host "Arcadia build ready: $Root\dist\Arcadia"
