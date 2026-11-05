"""Detect OBS Virtual Camera (and similar) without installing or loading drivers.

We only report what the OS already exposes. Installing a virtual camera driver
is the user's explicit action in OBS; SAQR never does it silently.
"""

from __future__ import annotations

import platform
import shutil
from dataclasses import asdict, dataclass


@dataclass
class VirtualCameraStatus:
    available: bool
    device_name: str | None = None
    obs_installed: bool = False
    obs_path: str | None = None
    instructions: str = (
        "Install OBS Studio, click 'Start Virtual Camera' in OBS, then select "
        "'OBS Virtual Camera' as the camera in apps that support it. On Windows 11 "
        "the camera may appear as 'OBS Virtual Camera' after the OBS driver is installed."
    )

    def to_dict(self) -> dict:
        return asdict(self)


def detect_virtual_camera(devices: list | None = None) -> VirtualCameraStatus:
    names: list[str] = []
    if devices:
        names = [getattr(d, "name", "") for d in devices]
    else:
        from .stream import enumerate_cameras

        names = [c.name for c in enumerate_cameras(probe=False)]

    obs_path = shutil.which("obs64.exe") or shutil.which("obs") or shutil.which("obs-studio")
    obs_installed = bool(obs_path)
    if platform.system() == "Windows" and not obs_path:
        from pathlib import Path

        candidate = Path(r"C:\Program Files\obs-studio\bin\64bit\obs64.exe")
        if candidate.exists():
            obs_installed, obs_path = True, str(candidate)

    match = next((n for n in names if "obs" in n.lower() or "virtual" in n.lower()), None)
    return VirtualCameraStatus(available=match is not None, device_name=match,
                               obs_installed=obs_installed, obs_path=obs_path)
