# Windows installer

The installer is built on Windows (or on `windows-latest` in CI) because PyInstaller
cannot cross-compile a working frozen bundle.

```
# prerequisites: Python 3.12 x64, Node 20+, Inno Setup 6
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
# -> installer/Output/SAQR-AI-Setup.exe
```

What the installer does:

1. Detects 64-bit Windows and refuses 32-bit installs.
2. Copies the frozen app (engine + desktop + built web UI).
3. Runs `SaqrAIStudio.exe doctor --json` and stores the hardware report in
   `%LOCALAPPDATA%\SaqrAIStudio\logs\install-diagnostics.json`.
4. Optionally downloads YuNet and verifies its SHA-256 before installation.
5. Creates Start Menu + desktop shortcuts and an uninstall entry.
6. Never installs CUDA/TensorRT, camera drivers, or Python. Missing GPU runtimes are
   reported in the diagnostics page, not installed silently.

Code signing is not configured. Add your certificate to `SignTool` in Inno Setup to
avoid SmartScreen warnings. Unsigned builds still run.
