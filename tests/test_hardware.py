from saqr_engine.hardware.backends import choose_backend, probe_providers
from saqr_engine.hardware.detection import detect_hardware


def test_detects_real_machine():
    profile = detect_hardware()
    assert profile.cpu.logical_cores >= 1
    assert profile.system.ram_total_mb > 0
    assert profile.system.machine
    data = profile.to_dict()
    assert {"cpu", "gpus", "system"} <= set(data)


def test_cpu_probe_is_verified():
    profile = detect_hardware()
    probes = probe_providers(profile)
    cpu = next(p for p in probes if p.provider == "CPUExecutionProvider")
    assert cpu.verified is True
    assert cpu.offered is True


def test_backend_chain_always_ends_on_cpu():
    profile = detect_hardware()
    decision = choose_backend(profile, probe_providers(profile))
    assert decision.chain[-1] == "CPUExecutionProvider"
    assert decision.provider in decision.chain
    assert decision.tier in {"cpu", "gpu-high", "gpu-standard", "gpu-directml", "gpu-portable"}


def test_invalid_manual_provider_falls_back():
    profile = detect_hardware()
    decision = choose_backend(profile, probe_providers(profile), preferred="CUDAExecutionProvider")
    if decision.provider != "CUDAExecutionProvider":
        assert "unavailable" in decision.reason
    assert decision.manual is False


def test_duplicate_provider_names_are_not_trusted():
    profile = detect_hardware()
    probes = probe_providers(profile)
    names = [p.provider for p in probes]
    assert len(names) == len(set(names))
    assert all(p.reason for p in probes)
