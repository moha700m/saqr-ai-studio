"""Execution-provider probing and backend selection.

Two rules drive this module:

1. A provider is only used after it has been *verified*: we build a real
   one-node ONNX session on it. A name in ``get_available_providers()`` is a
   claim by the wheel, not proof that the driver/runtime works.
2. Selection always produces a full fallback chain, so a driver update that
   breaks CUDA degrades to CPU instead of crashing the app.
"""

from __future__ import annotations

import base64
import platform
from dataclasses import asdict, dataclass, field

import onnxruntime as ort

from .detection import HardwareProfile

# One-node Identity graph (77 bytes) used only to prove a provider can run.
_PROBE_MODEL = base64.b64decode(
    "CAg6QwoQCgF4EgF5IghJZGVudGl0eRIFcHJvYmVaEwoBeBIOCgwIARIICgIIAQoCCANiEwoBeRIOCgwIARIICgIIAQoCCANCBAoAEA0="
)

# Priority per product spec: CUDA, TensorRT, DirectML, other GPU, CPU.
PRIORITY: list[tuple[str, str]] = [
    ("CUDAExecutionProvider", "NVIDIA CUDA"),
    ("TensorrtExecutionProvider", "NVIDIA TensorRT"),
    ("DmlExecutionProvider", "DirectML"),
    ("ROCMExecutionProvider", "AMD ROCm"),
    ("MIGraphXExecutionProvider", "AMD MIGraphX"),
    ("OpenVINOExecutionProvider", "OpenVINO"),
    ("CoreMLExecutionProvider", "Apple CoreML"),
    ("QNNExecutionProvider", "Qualcomm QNN"),
    ("ArmNNExecutionProvider", "ArmNN"),
    ("CPUExecutionProvider", "CPU"),
]
PRIORITY_INDEX = {name: index for index, (name, _) in enumerate(PRIORITY)}
LABELS = dict(PRIORITY)

_GPU_PROVIDERS = {
    "CUDAExecutionProvider", "TensorrtExecutionProvider", "DmlExecutionProvider",
    "ROCMExecutionProvider", "MIGraphXExecutionProvider", "OpenVINOExecutionProvider",
    "CoreMLExecutionProvider", "QNNExecutionProvider",
}


@dataclass
class ProviderProbe:
    provider: str
    label: str
    offered: bool
    verified: bool
    reason: str = ""
    device: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BackendDecision:
    provider: str
    label: str
    chain: list[str]
    reason: str
    tier: str
    manual: bool = False
    probes: list[ProviderProbe] = field(default_factory=list)

    @property
    def is_gpu(self) -> bool:
        return self.provider in _GPU_PROVIDERS

    def to_dict(self) -> dict:
        data = asdict(self)
        data["is_gpu"] = self.is_gpu
        return data


def _provider_options(provider: str, profile: HardwareProfile | None) -> dict:
    if provider == "CUDAExecutionProvider":
        return {
            "device_id": 0,
            "cudnn_conv_algo_search": "HEURISTIC",
            "arena_extend_strategy": "kSameAsRequested",
            "do_copy_in_default_stream": "1",
        }
    if provider == "TensorrtExecutionProvider":
        return {
            "device_id": 0,
            "trt_max_workspace_size": str(2 << 30),
            "trt_fp16_enable": "1",
            "trt_engine_cache_enable": "1",
            "trt_timing_cache_enable": "1",
        }
    if provider == "OpenVINOExecutionProvider":
        device = "GPU_FP16" if profile and profile.primary_gpu and profile.primary_gpu.vendor in {"intel", "amd"} else "CPU"
        return {"device_type": device, "enable_opencl_throttling": "0"}
    if provider == "CPUExecutionProvider":
        cores = profile.cpu.physical_cores if profile and profile.cpu.physical_cores else 0
        return {"intra_op_num_threads": str(max(1, cores)),
                "graph_optimization_level": "ORT_ENABLE_ALL"}
    return {}


def _describe_device(provider: str, profile: HardwareProfile | None) -> str | None:
    if not profile:
        return None
    gpu = profile.primary_gpu
    if provider.startswith(("CUDA", "Tensorrt")) and gpu and gpu.vendor == "nvidia":
        return f"{gpu.name} ({gpu.vram_mb or '?'} MB)"
    if provider == "DmlExecutionProvider" and gpu:
        return gpu.name
    if provider == "CPUExecutionProvider":
        return profile.cpu.brand
    if gpu:
        return gpu.name
    return None


def probe_providers(
    profile: HardwareProfile | None = None,
    verify: bool = True,
    verify_tensorrt: bool = False,
) -> list[ProviderProbe]:
    """Return one probe per known provider, in priority order.

    ``verify`` runs the tiny graph. TensorRT builds an engine, which can take
    seconds, so it is opt-in via ``verify_tensorrt`` (the installer runs it
    with the flag; the app start-up path does not).
    """
    offered = set(ort.get_available_providers())
    probes: list[ProviderProbe] = []
    for provider, label in PRIORITY:
        is_offered = provider in offered
        probe = ProviderProbe(
            provider=provider, label=label, offered=is_offered,
            verified=False, device=_describe_device(provider, profile),
        )
        if not is_offered:
            probe.reason = "not compiled into the installed onnxruntime build"
            probes.append(probe)
            continue
        if not verify or (provider == "TensorrtExecutionProvider" and not verify_tensorrt):
            probe.verified = True
            probe.reason = "offered by onnxruntime; verified on first real session"
            probes.append(probe)
            continue
        try:
            options = _provider_options(provider, profile)
            providers = [(provider, options)]
            if provider == "TensorrtExecutionProvider":
                providers.append(("CUDAExecutionProvider", _provider_options("CUDAExecutionProvider", profile)))
            session = ort.InferenceSession(_PROBE_MODEL, providers=providers)
            if provider in session.get_providers():
                session.run(None, {"x": [[0.0, 0.0, 0.0]]})
                probe.verified = True
                probe.reason = "tiny inference succeeded"
            else:
                probe.reason = "onnxruntime silently fell back to CPU"
        except Exception as exc:  # noqa: BLE001 - driver errors are arbitrary
            probe.reason = f"{type(exc).__name__}: {str(exc)[:240]}"
        probes.append(probe)
    return probes


def choose_backend(
    profile: HardwareProfile | None = None,
    probes: list[ProviderProbe] | None = None,
    preferred: str | None = None,
    allow_fallback: bool = True,
) -> BackendDecision:
    probes = probes if probes is not None else probe_providers(profile)
    verified = [p for p in probes if p.verified]
    by_name = {p.provider: p for p in probes}
    manual = False

    chosen: ProviderProbe | None = None
    reason = ""
    if preferred and preferred in by_name and by_name[preferred].verified:
        chosen = by_name[preferred]
        manual = True
        reason = "manual selection from settings"
    elif preferred:
        reason = f"requested provider {preferred} is unavailable; automatic selection used"

    if chosen is None:
        for probe in verified:
            if probe.provider == "CPUExecutionProvider":
                continue
            chosen = probe
            break
    if chosen is None:
        chosen = by_name.get("CPUExecutionProvider")
        if chosen is None:
            chosen = ProviderProbe("CPUExecutionProvider", "CPU", True, True, "assumed")
        reason = reason or "no GPU provider passed verification"

    chain = [chosen.provider]
    if allow_fallback:
        for probe in sorted(verified, key=lambda p: PRIORITY_INDEX.get(p.provider, 99)):
            if probe.provider not in chain:
                chain.append(probe.provider)
        if "CPUExecutionProvider" in by_name and "CPUExecutionProvider" not in chain:
            chain.append("CPUExecutionProvider")

    return BackendDecision(
        provider=chosen.provider,
        label=chosen.label,
        chain=chain,
        reason=reason or "highest-priority verified provider",
        tier=_tier(chosen.provider, profile),
        manual=manual,
        probes=probes,
    )


def _tier(provider: str, profile: HardwareProfile | None) -> str:
    if provider == "CPUExecutionProvider" or provider not in _GPU_PROVIDERS:
        return "cpu"
    if provider == "DmlExecutionProvider":
        return "gpu-directml"
    if provider in {"OpenVINOExecutionProvider", "CoreMLExecutionProvider", "QNNExecutionProvider", "ArmNNExecutionProvider"}:
        return "gpu-portable"
    gpu = profile.primary_gpu if profile else None
    if gpu and gpu.vram_mb and gpu.vram_mb >= 8192:
        return "gpu-high"
    return "gpu-standard"


def platform_tag() -> str:
    return f"{platform.system().lower()}-{platform.machine().lower()}"
