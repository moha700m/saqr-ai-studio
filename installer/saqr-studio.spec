# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SAQR AI Studio (Windows/Linux/macOS).

Models are deliberately NOT bundled: inswapper is non-commercial and YuNet is
downloaded by the installer with a verified checksum.
"""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent          # noqa: F821 - provided by PyInstaller
WEB_DIST = ROOT / "web" / "dist"

datas, binaries, hiddenimports = collect_all("saqr_engine")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += ["onnxruntime", "cv2", "fastapi", "pydantic", "psutil"]
hiddenimports += ["saqr_desktop", "saqr_desktop.app", "saqr_desktop.main_window",
                  "saqr_desktop.pages", "saqr_desktop.runtime", "saqr_desktop.widgets"]

if WEB_DIST.exists():
    datas.append((str(WEB_DIST), "web/dist"))

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT / "engine"), str(ROOT / "desktop")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "torch", "tensorflow"],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="SaqrAIStudio", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=True,  # CLI needs stdout; the launcher hides it for the GUI
    icon=None,
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name="SaqrAIStudio",
)
