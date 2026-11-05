"""Cross-platform hardware inspection.

The goal is that a non-technical user never has to look up their CPU or GPU.
Every field is optional and is filled only from a source that actually answered;
nothing is inferred from the marketing name of the machine.

Sources used per platform:
  Windows : CIM/WMI via PowerShell, nvidia-smi, registry VRAM key
  Linux   : /proc/cpuinfo, /proc/meminfo, nvidia-smi, rocm-smi, sysfs, lspci
  macOS   : sysctl, system_profiler -json
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

import psutil


# --------------------------------------------------------------------------- models
@dataclass
class CPUInfo:
    brand: str = "unknown"
    vendor: str = "unknown"
    architecture: str = platform.machine()
    physical_cores: int = 0
    logical_cores: int = 0
    base_mhz: float | None = None
    max_mhz: float | None = None
    isa: list[str] = field(default_factory=list)
    isa_source: str = "unavailable"

    @property
    def has_avx2(self) -> bool:
        return "avx2" in self.isa


@dataclass
class GPUInfo:
    name: str
    vendor: str
    vram_mb: int | None = None
    driver: str | None = None
    compute_capability: str | None = None
    source: str = "unknown"
    integrated: bool | None = None


@dataclass
class SystemInfo:
    os_name: str = platform.system()
    os_release: str = ""
    os_version: str = ""
    machine: str = platform.machine()
    is_64bit: bool = platform.machine().endswith("64") or platform.machine() in {"arm64", "aarch64"}
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    disk_free_gb: float = 0.0
    python: str = platform.python_version()


@dataclass
class HardwareProfile:
    cpu: CPUInfo
    system: SystemInfo
    gpus: list[GPUInfo] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def primary_gpu(self) -> GPUInfo | None:
        dedicated = [g for g in self.gpus if g.integrated is False]
        return (dedicated or self.gpus or [None])[0]

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        gpu = ", ".join(f"{g.name} ({g.vendor}, {g.vram_mb or '?'} MB)" for g in self.gpus) or "none detected"
        return (
            f"CPU: {self.cpu.brand} | {self.cpu.physical_cores}C/{self.cpu.logical_cores}T | "
            f"AVX2={'yes' if self.cpu.has_avx2 else 'no/unknown'}\n"
            f"GPU: {gpu}\n"
            f"RAM: {self.system.ram_total_mb} MB | free disk: {self.system.disk_free_gb} GB\n"
            f"OS: {self.system.os_name} {self.system.os_release} ({self.system.machine})"
        )


# --------------------------------------------------------------------------- helpers
def _run(cmd: list[str], timeout: float = 6.0) -> str:
    """Run a diagnostic command; empty string when it is missing or fails."""
    if not shutil.which(cmd[0]):
        return ""
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system() == "Windows" else 0,
        )
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _powershell_json(script: str) -> list[dict]:
    if platform.system() != "Windows":
        return []
    raw = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout=15)
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    return data if isinstance(data, list) else [data]


def _vendor_from_name(name: str) -> str:
    low = name.lower()
    if "nvidia" in low or "geforce" in low or "quadro" in low or "rtx" in low or "tesla" in low:
        return "nvidia"
    if "amd" in low or "radeon" in low or "ati " in low:
        return "amd"
    if "intel" in low or "iris" in low or "arc " in low or "uhd graphics" in low:
        return "intel"
    if "apple" in low:
        return "apple"
    return "other"


def _isa_from_flags(flags: Iterable[str]) -> list[str]:
    flags = set(flags)
    wanted = [("sse4_2", "SSE4.2"), ("avx", "AVX"), ("avx2", "AVX2"), ("avx512f", "AVX-512"),
              ("fma", "FMA"), ("f16c", "F16C"), ("amx_tile", "AMX"), ("neon", "NEON")]
    return [label for flag, label in wanted if flag in flags]


# --------------------------------------------------------------------------- CPU
def detect_cpu() -> CPUInfo:
    info = CPUInfo(
        physical_cores=psutil.cpu_count(logical=False) or 0,
        logical_cores=psutil.cpu_count(logical=True) or 0,
    )
    freq = None
    freq_fn = getattr(psutil, "cpu_freq", None)  # not exposed on every platform/version
    if callable(freq_fn):
        try:
            freq = freq_fn()
        except (NotImplementedError, OSError):
            freq = None
    if freq:
        info.base_mhz = round(freq.min or 0, 1) or None
        info.max_mhz = round(freq.max or 0, 1) or None

    system = platform.system()
    if system == "Linux" and Path("/proc/cpuinfo").exists():
        text = Path("/proc/cpuinfo").read_text(errors="ignore")
        match = re.search(r"^model name\s*:\s*(.+)$", text, re.MULTILINE)
        if match:
            info.brand = match.group(1).strip()
        vendor = re.search(r"^vendor_id\s*:\s*(.+)$", text, re.MULTILINE)
        info.vendor = (vendor.group(1).strip().lower() if vendor else "unknown")
        flags_match = re.search(r"^flags\s*:\s*(.+)$", text, re.MULTILINE)
        if flags_match:
            info.isa = _isa_from_flags(flags_match.group(1).split())
            info.isa_source = "/proc/cpuinfo"
        if info.brand == "unknown":
            # aarch64 /proc/cpuinfo has no "model name"; lscpu names the SoC.
            match = re.search(r"^Model name\s*:\s*(.+)$", _run(["lscpu"]), re.MULTILINE)
            if match:
                info.brand = match.group(1).strip()
            cpuinfo = text.lower()
            if "asimd" in cpuinfo or "neon" in cpuinfo:
                info.isa = ["NEON"]
                info.isa_source = "/proc/cpuinfo (asimd)"
    elif system == "Darwin":
        info.brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"]).strip() or "Apple Silicon"
        info.vendor = "apple"
        features = _run(["sysctl", "-n", "machdep.cpu.features"]).lower().split()
        if features:
            info.isa = _isa_from_flags(features)
            info.isa_source = "sysctl"
        if "arm64" in info.architecture:
            info.isa = ["NEON"] + [v for v in info.isa if v != "NEON"]
            info.isa_source = "arm64 baseline"
    elif system == "Windows":
        rows = _powershell_json(
            "Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,"
            "NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | ConvertTo-Json"
        )
        if rows:
            row = rows[0]
            info.brand = (row.get("Name") or "unknown").strip()
            info.vendor = (row.get("Manufacturer") or "unknown").strip().lower()
            info.physical_cores = int(row.get("NumberOfCores") or info.physical_cores)
            info.logical_cores = int(row.get("NumberOfLogicalProcessors") or info.logical_cores)
            if row.get("MaxClockSpeed"):
                info.max_mhz = float(row["MaxClockSpeed"])
        # WMI does not expose AVX; do not guess. ORT will pick the kernel it can run.
        info.isa_source = "unavailable (WMI exposes no ISA flags)"
    elif system == "Linux":
        # ARM boards usually have no "model name" line; lscpu is the reliable source.
        raw = _run(["lscpu"])
        match = re.search(r"^Model name\s*:\s*(.+)$", raw, re.MULTILINE)
        if match:
            info.brand = match.group(1).strip()
        if "aarch64" in info.architecture or "arm" in info.architecture:
            cpuinfo = Path("/proc/cpuinfo").read_text(errors="ignore").lower()
            info.isa = ["NEON"] if "asimd" in cpuinfo or "neon" in cpuinfo else []
            info.isa_source = "/proc/cpuinfo (asimd)"
    else:
        info.brand = platform.processor() or "unknown"

    if not info.brand or info.brand == "unknown":
        info.brand = platform.processor() or f"{info.architecture} CPU"
    return info


# --------------------------------------------------------------------------- GPU
def _nvidia_gpus() -> list[GPUInfo]:
    raw = _run([
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version,compute_cap",
        "--format=csv,noheader,nounits",
    ])
    gpus: list[GPUInfo] = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3 or not parts[0]:
            continue
        vram = int(float(parts[1])) if parts[1].replace(".", "", 1).isdigit() else None
        gpus.append(GPUInfo(
            name=parts[0], vendor="nvidia", vram_mb=vram, driver=parts[2],
            compute_capability=parts[3] if len(parts) > 3 else None, source="nvidia-smi",
            integrated=False,
        ))
    return gpus


def _linux_gpus() -> list[GPUInfo]:
    gpus: list[GPUInfo] = []
    drm = Path("/sys/class/drm")
    if drm.exists():
        for card in sorted(drm.glob("card[0-9]*")):
            if "-" in card.name:
                continue  # connectors, not cards
            device = card / "device"
            name_file = device / "product_name"
            vendor_file = device / "vendor"
            vram_file = device / "mem_info_vram_total"
            if not vendor_file.exists():
                continue
            vendor_id = vendor_file.read_text(errors="ignore").strip().lower()
            vendor = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}.get(vendor_id, "other")
            name = name_file.read_text(errors="ignore").strip() if name_file.exists() else ""
            if not name:
                pci = _run(["lspci", "-mm", "-s", device.resolve().name.split("/")[-1]])
                name = pci.replace('"', "").strip() or f"{vendor} GPU"
            vram_mb = None
            if vram_file.exists():
                try:
                    vram_mb = int(vram_file.read_text().strip()) // (1024 * 1024)
                except ValueError:
                    vram_mb = None
            gpus.append(GPUInfo(name=name, vendor=vendor, vram_mb=vram_mb, source="sysfs", integrated=False))
    if not any(g.vendor == "amd" for g in gpus):
        raw = _run(["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--json"])
        try:
            data = json.loads(raw) if raw.strip() else {}
        except ValueError:
            data = {}
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            name = entry.get("Card series") or entry.get("Card SKU") or key
            gpus.append(GPUInfo(name=str(name), vendor="amd", source="rocm-smi", integrated=False))
    return gpus


def _windows_gpus() -> list[GPUInfo]:
    rows = _powershell_json(
        "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,"
        "AdapterCompatibility,VideoProcessor | ConvertTo-Json"
    )
    gpus: list[GPUInfo] = []
    for row in rows:
        name = (row.get("Name") or "unknown").strip()
        vram = row.get("AdapterRAM")
        vram_mb = int(vram) // (1024 * 1024) if isinstance(vram, int) and vram > 0 else None
        if vram_mb and vram_mb >= 4095:
            # Win32_VideoController.AdapterRAM is uint32 and saturates at 4 GB.
            vram_mb = _windows_registry_vram_mb() or vram_mb
        gpus.append(GPUInfo(
            name=name, vendor=_vendor_from_name(name), vram_mb=vram_mb,
            driver=str(row.get("DriverVersion") or "") or None,
            source="wmi", integrated=_vendor_from_name(name) == "intel" and "arc" not in name.lower(),
        ))
    return gpus


def _windows_registry_vram_mb() -> int | None:
    rows = _powershell_json(
        "Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\"
        "{4d36e968-e325-11ce-bfc1-08002be10318}\\0*' -ErrorAction SilentlyContinue | "
        "Where-Object { $_.'HardwareInformation.qwMemorySize' } | "
        "Select-Object -First 1 -ExpandProperty 'HardwareInformation.qwMemorySize'"
    )
    if rows and isinstance(rows[0], dict):
        try:
            return int(rows[0].get("value", 0)) // (1024 * 1024) or None
        except (TypeError, ValueError):
            return None
    return None


def _mac_gpus() -> list[GPUInfo]:
    raw = _run(["system_profiler", "SPDisplaysDataType", "-json"], timeout=20)
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return []
    gpus: list[GPUInfo] = []
    for item in data.get("SPDisplaysDataType", []):
        name = item.get("sppci_model") or item.get("_name") or "GPU"
        vram = item.get("spdisplays_vram") or item.get("spdisplays_vram_shared")
        vram_mb = None
        if isinstance(vram, str):
            match = re.search(r"(\d+)\s*(MB|GB)", vram)
            if match:
                vram_mb = int(match.group(1)) * (1024 if match.group(2) == "GB" else 1)
        gpus.append(GPUInfo(
            name=name, vendor=_vendor_from_name(name), vram_mb=vram_mb,
            source="system_profiler", integrated="apple" in name.lower() or "integrated" in str(item).lower(),
        ))
    return gpus


def detect_gpus() -> tuple[list[GPUInfo], list[str]]:
    notes: list[str] = []
    gpus = _nvidia_gpus()
    system = platform.system()
    if system == "Linux":
        others = _linux_gpus()
    elif system == "Windows":
        others = _windows_gpus()
    elif system == "Darwin":
        others = _mac_gpus()
    else:
        others = []
    known = {g.name.lower() for g in gpus}
    for gpu in others:
        if gpu.name.lower() not in known and "microsoft basic display" not in gpu.name.lower():
            gpus.append(gpu)
    if not gpus:
        notes.append("No GPU was detected. The CPU backend will be used.")
    if system == "Linux" and any(g.vendor == "nvidia" for g in gpus) and not shutil.which("nvidia-smi"):
        notes.append("NVIDIA hardware present but nvidia-smi is missing; VRAM/driver unknown.")
    return gpus, notes


# --------------------------------------------------------------------------- system
def detect_system() -> SystemInfo:
    vm = psutil.virtual_memory()
    info = SystemInfo(
        os_name=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        machine=platform.machine(),
        is_64bit=platform.machine().endswith("64") or platform.machine() in {"arm64", "aarch64"},
        ram_total_mb=int(vm.total // (1024 * 1024)),
        ram_available_mb=int(vm.available // (1024 * 1024)),
        python=platform.python_version(),
    )
    try:
        info.disk_free_gb = round(shutil.disk_usage(Path.home()).free / (1024 ** 3), 1)
    except OSError:
        info.disk_free_gb = 0.0
    if platform.system() == "Windows":
        rows = _powershell_json("Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version | ConvertTo-Json")
        if rows:
            info.os_name = str(rows[0].get("Caption") or "Windows").strip()
            info.os_release = str(rows[0].get("Version") or info.os_release)
    elif platform.system() == "Linux" and Path("/etc/os-release").exists():
        for line in Path("/etc/os-release").read_text(errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                info.os_name = line.split("=", 1)[1].strip().strip('"')
    return info


def detect_hardware() -> HardwareProfile:
    gpus, notes = detect_gpus()
    return HardwareProfile(cpu=detect_cpu(), system=detect_system(), gpus=gpus, notes=notes)
