# Build SAQR AI Studio and the Inno Setup installer on Windows.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "== Python environment =="
if (-not (Test-Path "$root\.venv")) { py -3.12 -m venv "$root\.venv" }
& "$root\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$root\.venv\Scripts\pip.exe" install -e "$root\engine[desktop,dev]" pyinstaller

Write-Host "== Web UI =="
Push-Location "$root\web"
npm ci
npm run build
Pop-Location

Write-Host "== Freeze =="
& "$root\.venv\Scripts\pyinstaller.exe" --noconfirm --clean --distpath "$root\dist" --workpath "$root\build" "$root\installer\saqr-studio.spec"

Write-Host "== Installer =="
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "Inno Setup 6 not found. Install it from jrsoftware.org." }
& $iscc "$root\installer\saqr-studio.iss"

Write-Host "Done: $root\installer\Output\SAQR-AI-Setup.exe"
