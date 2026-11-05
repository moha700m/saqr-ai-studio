param(
  [Parameter(Mandatory = $true)][string]$AppDir,
  [string]$InstallDetector = "1"
)
$ErrorActionPreference = "Continue"
$exe = Join-Path $AppDir "SaqrAIStudio.exe"
$logDir = Join-Path $env:LOCALAPPDATA "SaqrAIStudio\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$report = Join-Path $logDir "install-diagnostics.json"

Write-Host "SAQR: detecting hardware..."
& $exe doctor --json *> $report
if ($LASTEXITCODE -ne 0) {
  Write-Warning "diagnostics returned $LASTEXITCODE; see $report"
}

if ($InstallDetector -eq "1") {
  Write-Host "SAQR: installing YuNet detector (checksum verified)..."
  & $exe models download yunet-2023mar
  if ($LASTEXITCODE -ne 0) { Write-Warning "YuNet download failed; install it later from the Models page." }
}

# Never install CUDA/TensorRT or camera drivers silently.
Write-Host "SAQR: setup complete. GPU runtimes are only installed on demand."
