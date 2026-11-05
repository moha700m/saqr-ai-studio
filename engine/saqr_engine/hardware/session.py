"""ONNX Runtime session factory with a verified fallback ladder."""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import onnxruntime as ort

from .backends import BackendDecision, _provider_options
from .detection import HardwareProfile

log = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    path: str
    provider: str
    requested_chain: list[str]
    inputs: dict[str, list]
    outputs: dict[str, list]
    fell_back: bool


class ProviderError(RuntimeError):
    pass


def _shape(node_arg) -> list:
    """NodeArg from InferenceSession.get_inputs() exposes .shape directly."""
    dims = []
    for dim in getattr(node_arg, "shape", []) or []:
        dims.append(dim if isinstance(dim, int) and dim > 0 else "?")
    return dims


def create_session(
    model_path: str | Path,
    decision: BackendDecision | None = None,
    profile: HardwareProfile | None = None,
    providers: list[str] | None = None,
    trt_cache_dir: str | Path | None = None,
    session_options: ort.SessionOptions | None = None,
) -> tuple[ort.InferenceSession, SessionInfo]:
    """Create a session, walking the fallback chain until one provider works."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(path)

    chain = providers or (decision.chain if decision else ["CPUExecutionProvider"])
    opts = session_options or ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.log_severity_level = 3

    errors: list[str] = []
    for index, provider in enumerate(chain):
        provider_options = _provider_options(provider, profile)
        if provider == "TensorrtExecutionProvider" and trt_cache_dir:
            Path(trt_cache_dir).mkdir(parents=True, exist_ok=True)
            provider_options = {
                **provider_options,
                "trt_engine_cache_path": str(trt_cache_dir),
                "trt_timing_cache_path": str(trt_cache_dir),
            }
        try:
            session = ort.InferenceSession(str(path), sess_options=opts, providers=[(provider, provider_options)])
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{provider}: {type(exc).__name__}: {str(exc)[:200]}")
            log.warning("provider %s failed for %s", provider, path.name)
            continue
        actual = session.get_providers()[0]
        if actual != provider and provider != "CPUExecutionProvider":
            errors.append(f"{provider}: runtime fell back to {actual}")
            continue
        info = SessionInfo(
            path=str(path),
            provider=actual,
            requested_chain=chain,
            inputs={i.name: _shape(i) for i in session.get_inputs()},
            outputs={o.name: _shape(o) for o in session.get_outputs()},
            fell_back=index > 0 or actual != chain[0],
        )
        log.info("session %s ready on %s", path.name, actual)
        return session, info

    raise ProviderError("no execution provider could open the model. " + " | ".join(errors))


def available_provider_list() -> list[str]:
    with suppress(Exception):
        return ort.get_available_providers()
    return []
