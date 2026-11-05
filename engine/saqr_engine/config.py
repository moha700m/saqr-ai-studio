"""Runtime configuration and paths.

Everything resolves relative to ``SAQR_HOME`` (default: a per-user directory),
so a packaged install and a source checkout behave identically. Tests override
``SAQR_HOME`` to a tmp dir instead of touching the real profile.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def default_home() -> Path:
    override = os.environ.get("SAQR_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", str(Path.home()))
        return Path(base) / "SaqrAIStudio"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SaqrAIStudio"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "saqr-ai-studio"


@dataclass
class Settings:
    """Mutable-at-runtime settings; persisted as JSON by :meth:`save`."""

    home: Path = field(default_factory=default_home)
    # Local-first defaults. Cloud processing is opt-in by design (see PRIVACY.md).
    cloud_enabled: bool = False
    auto_start_camera: bool = False
    save_processed_media: bool = False
    telemetry: bool = False
    preferred_provider: str | None = None
    allow_fallback: bool = True
    swap_strength: float = 1.0
    mouth_mask: bool = True
    face_enhance: bool = False
    enhancement_blend: float = 0.6
    max_capture_queue: int = 2
    api_host: str = "127.0.0.1"
    api_port: int = 8765
    allowed_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "https://localhost",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ])

    @property
    def models_dir(self) -> Path:
        return self.home / "models"

    @property
    def cache_dir(self) -> Path:
        return self.home / "cache"

    @property
    def media_dir(self) -> Path:
        return self.home / "media"

    @property
    def logs_dir(self) -> Path:
        return self.home / "logs"

    @property
    def settings_file(self) -> Path:
        return self.home / "settings.json"

    def ensure_dirs(self) -> None:
        for path in (self.home, self.models_dir, self.cache_dir, self.media_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict:
        return {
            "cloud_enabled": self.cloud_enabled,
            "auto_start_camera": self.auto_start_camera,
            "save_processed_media": self.save_processed_media,
            "telemetry": self.telemetry,
            "preferred_provider": self.preferred_provider,
            "allow_fallback": self.allow_fallback,
            "swap_strength": self.swap_strength,
            "mouth_mask": self.mouth_mask,
            "face_enhance": self.face_enhance,
            "enhancement_blend": self.enhancement_blend,
            "max_capture_queue": self.max_capture_queue,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "allowed_origins": self.allowed_origins,
        }

    def save(self) -> None:
        import json

        self.ensure_dirs()
        tmp = self.settings_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(self.settings_file)

    @classmethod
    def load(cls, home: Path | None = None) -> "Settings":
        import json

        settings = cls(home=home or default_home())
        if settings.settings_file.exists():
            try:
                data = json.loads(settings.settings_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            for key, value in data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
        settings.ensure_dirs()
        return settings
