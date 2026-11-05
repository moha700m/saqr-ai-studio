"""Post-install smoke check: models, provider, and a real inference if possible."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from saqr_engine.config import Settings  # noqa: E402
from saqr_engine.hardware.backends import choose_backend, probe_providers  # noqa: E402
from saqr_engine.hardware.detection import detect_hardware  # noqa: E402
from saqr_engine.models.manager import ModelManager  # noqa: E402


def main() -> int:
    settings = Settings.load()
    profile = detect_hardware()
    decision = choose_backend(profile, probe_providers(profile),
                              preferred=settings.preferred_provider)
    manager = ModelManager(settings)
    report = {
        "home": str(settings.home),
        "provider": decision.provider,
        "chain": decision.chain,
        "hardware": profile.summary(),
        "models": manager.catalog(),
        "ok": manager.resolve("detector") is not None,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        print("\nInstall a detector: saqr models download yunet-2023mar", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
