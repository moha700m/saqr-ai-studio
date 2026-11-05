"""Command line surface: diagnostics, model management, serving, benchmarking."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from .config import Settings
from .hardware.backends import choose_backend, probe_providers
from .hardware.detection import detect_hardware
from .models.manager import ModelError, ModelManager
from .version import __version__


def _print_profile(profile) -> None:
    print(f"CPU   : {profile.cpu.brand}")
    print(f"        {profile.cpu.physical_cores} cores / {profile.cpu.logical_cores} threads, "
          f"ISA: {', '.join(profile.cpu.isa) or 'unknown'} ({profile.cpu.isa_source})")
    if profile.gpus:
        for gpu in profile.gpus:
            print(f"GPU   : {gpu.name}  vendor={gpu.vendor}  vram={gpu.vram_mb or '?'} MB  "
                  f"driver={gpu.driver or '?'}  [{gpu.source}]")
    else:
        print("GPU   : none detected")
    print(f"RAM   : {profile.system.ram_total_mb} MB total / {profile.system.ram_available_mb} MB free")
    print(f"Disk  : {profile.system.disk_free_gb} GB free")
    print(f"OS    : {profile.system.os_name} {profile.system.os_release} ({profile.system.machine})")
    print(f"Python: {profile.system.python}")


def cmd_doctor(args) -> int:
    settings = Settings.load()
    profile = detect_hardware()
    probes = probe_providers(profile, verify_tensorrt=args.verify_trt)
    decision = choose_backend(profile, probes, preferred=settings.preferred_provider)
    if args.json:
        print(json.dumps({"hardware": profile.to_dict(), "decision": decision.to_dict(),
                          "summary": profile.summary()}, indent=2))
        return 0
    print(f"SAQR AI Studio {__version__} — hardware diagnostics\n")
    _print_profile(profile)
    print("\nProviders (verified = a real session opened):")
    for probe in probes:
        mark = "OK " if probe.verified else "-- "
        print(f"  {mark}{probe.provider:<32} {probe.reason[:70]}")
    print(f"\nSelected backend : {decision.provider} ({decision.label})")
    print(f"Fallback chain   : {' -> '.join(decision.chain)}")
    print(f"Reason           : {decision.reason}")
    print(f"Performance tier : {decision.tier}")
    if profile.notes:
        print("Notes            : " + "; ".join(profile.notes))
    manager = ModelManager(settings)
    print("\nModels:")
    for row in manager.catalog():
        state = "installed" if row["installed"] else ("downloadable" if row["downloadable"] else "manual")
        print(f"  {row['name']:<38} {row['license_id']:<22} {state}")
    print(f"\nData directory   : {settings.home}")
    return 0


def cmd_models(args) -> int:
    settings = Settings.load()
    manager = ModelManager(settings)
    if args.action == "list":
        for row in manager.catalog():
            print(f"{row['id']:<18} {row['kind']:<9} {row['license_id']:<24} "
                  f"commercial={str(row['commercial_use']):<5} installed={row['installed']} "
                  f"downloadable={row['downloadable']}")
        return 0
    if args.action == "download":
        def progress(done: int, total: int) -> None:
            pct = f"{done * 100 // total:3d}%" if total else f"{done // 1024} KB"
            print(f"\r  {pct}", end="", flush=True)
        record = manager.download(args.model_id, progress=progress)
        print(f"\ninstalled {record.filename} ({record.sha256[:16]}…)")
        return 0
    if args.action == "import":
        path = args.path or args.model_id
        if not path:
            print("error: import needs a path", file=sys.stderr)
            return 2
        record = manager.install_file(path, kind=args.kind, model_id=args.model_id_override,
                                      accept_license=args.accept_license)
        print(f"installed {record.id} -> {record.path}\nsha256 {record.sha256}")
        return 0
    if args.action == "remove":
        print("removed" if manager.remove(args.model_id) else "not installed")
        return 0
    if args.action == "verify":
        print(json.dumps(manager.verify(args.model_id), indent=2))
        return 0
    return 1


def cmd_serve(args) -> int:
    import uvicorn

    from .api.auth import BridgeAuth
    from .api.server import create_app

    settings = Settings.load()
    settings.api_port = args.port
    auth = BridgeAuth(allowed_origins=settings.allowed_origins)
    app = create_app(settings=settings, auth=auth)
    print(f"SAQR bridge on http://{settings.api_host}:{settings.api_port}")
    if args.pair:
        code = auth.issue_code()
        print(f"Pairing code: {code['code']}  (valid {code['expires_in']}s)")
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, log_level="warning")
    return 0


def cmd_pair(args) -> int:
    """Issue a pairing code in-process; useful for scripts and the desktop app."""
    from .api.auth import BridgeAuth

    settings = Settings.load()
    auth = BridgeAuth(allowed_origins=settings.allowed_origins)
    print(json.dumps(auth.issue_code()))
    return 0


def cmd_benchmark(args) -> int:
    import cv2
    import numpy as np

    from .face.pipeline import FaceEngine

    settings = Settings.load()
    profile = detect_hardware()
    decision = choose_backend(profile, probe_providers(profile), preferred=settings.preferred_provider)
    engine = FaceEngine(settings, decision=decision, profile=profile)
    try:
        engine.load_models(want_swap=args.swap, want_enhance=False)
    except Exception as exc:  # noqa: BLE001
        print(f"engine unavailable: {exc}")
        return 2
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"cannot read {args.image}")
            return 2
        frame = cv2.resize(frame, (args.width, args.height))
        if args.source:
            engine.set_source(args.source)
    else:
        frame = np.random.default_rng(7).integers(0, 255, (args.height, args.width, 3), dtype=np.uint8)
    times = []
    faces = 0
    for _ in range(args.frames):
        start = time.perf_counter()
        result = engine.process(frame.copy(), swap=args.swap)
        times.append((time.perf_counter() - start) * 1000)
        faces = len(result.faces)
    times_sorted = sorted(times)
    p50 = statistics.median(times)
    p95 = times_sorted[int(len(times_sorted) * 0.95) - 1]
    report = {
        "version": __version__,
        "provider": decision.provider,
        "frames": args.frames,
        "resolution": f"{args.width}x{args.height}",
        "faces_detected": faces,
        "swap": args.swap,
        "can_swap": engine.can_swap,
        "mean_ms": round(statistics.fmean(times), 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "fps_mean": round(1000 / statistics.fmean(times), 2),
        "fps_p95_slow": round(1000 / p95, 2),
        "hardware": profile.summary(),
    }
    print(json.dumps(report, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


def cmd_process(args) -> int:
    from .face.pipeline import FaceEngine
    from .hardware.backends import choose_backend, probe_providers
    from .media.image import process_image
    from .media.video import process_video

    settings = Settings.load()
    profile = detect_hardware()
    decision = choose_backend(profile, probe_providers(profile), preferred=settings.preferred_provider)
    engine = FaceEngine(settings, decision=decision, profile=profile)
    engine.load_models(want_swap=True, want_enhance=settings.face_enhance)
    if args.source:
        engine.set_source(args.source)
    if args.kind == "image":
        result = process_image(args.input, args.output, engine)
    else:
        def progress(done, total):
            if total:
                print(f"\r  {done}/{total} frames", end="", flush=True)
        result = process_video(args.input, args.output, engine, progress=progress)
        print()
    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="saqr", description="SAQR AI Studio engine CLI")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="detect hardware and choose a backend")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--verify-trt", action="store_true", help="also build a TensorRT test engine")
    doctor.set_defaults(func=cmd_doctor)

    models = sub.add_parser("models", help="manage ONNX models")
    models.add_argument("action", choices=["list", "download", "import", "remove", "verify"])
    models.add_argument("model_id", nargs="?", default="")
    models.add_argument("--path", default="")
    models.add_argument("--kind", choices=["detector", "swapper", "enhancer"])
    models.add_argument("--id", dest="model_id_override", default=None)
    models.add_argument("--accept-license", action="store_true")
    models.set_defaults(func=cmd_models)

    serve = sub.add_parser("serve", help="run the local web bridge")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--pair", action="store_true", help="print a pairing code on start")
    serve.set_defaults(func=cmd_serve)

    pair = sub.add_parser("pair-code", help="issue a one-time pairing code")
    pair.set_defaults(func=cmd_pair)

    bench = sub.add_parser("benchmark", help="measure real latency/fps")
    bench.add_argument("--frames", type=int, default=30)
    bench.add_argument("--width", type=int, default=640)
    bench.add_argument("--height", type=int, default=480)
    bench.add_argument("--image", default=None)
    bench.add_argument("--source", default=None)
    bench.add_argument("--swap", action="store_true")
    bench.add_argument("--out", default=None)
    bench.set_defaults(func=cmd_benchmark)

    process = sub.add_parser("process", help="process an image or a video")
    process.add_argument("kind", choices=["image", "video"])
    process.add_argument("input")
    process.add_argument("output")
    process.add_argument("--source", default=None)
    process.set_defaults(func=cmd_process)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ModelError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
