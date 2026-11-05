"""Install, verify, list and remove ONNX models.

Downloaded files are verified against the catalogue SHA-256 before they are
moved into place. Imports from disk are hashed and recorded, so the same file
is never silently swapped later.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from ..config import Settings
from .manifest import CATALOG, ModelSpec, find_spec

log = logging.getLogger(__name__)
ProgressFn = Callable[[int, int], None]


class ModelError(RuntimeError):
    pass


@dataclass
class InstalledModel:
    id: str
    filename: str
    kind: str
    path: str
    sha256: str
    license_id: str
    commercial_use: bool
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


class ModelManager:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self.root = self.settings.models_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_file = self.root / "installed.json"
        self.acceptance_file = self.root / "license_acceptance.json"
        self._index: dict[str, dict] = self._read_json(self.index_file)

    # ------------------------------------------------------------------ state
    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_index(self) -> None:
        tmp = self.index_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._index, indent=2), encoding="utf-8")
        tmp.replace(self.index_file)

    def accept_license(self, model_id: str, accepted_by: str) -> None:
        record = self._read_json(self.acceptance_file)
        record[model_id] = {"accepted_by": accepted_by, "accepted": True}
        self.acceptance_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def license_accepted(self, model_id: str) -> bool:
        return bool(self._read_json(self.acceptance_file).get(model_id, {}).get("accepted"))

    # ------------------------------------------------------------------ queries
    def catalog(self) -> list[dict]:
        installed = {item["id"]: item for item in self.list()}
        rows = []
        for spec in CATALOG:
            row = spec.to_dict()
            row["installed"] = spec.id in installed
            row["license_accepted"] = self.license_accepted(spec.id)
            rows.append(row)
        return rows

    def list(self) -> list[dict]:
        existing = []
        for model_id, record in list(self._index.items()):
            path = Path(record.get("path", ""))
            if not path.exists():
                self._index.pop(model_id, None)
                continue
            existing.append(record)
        self._write_index()
        return existing

    def resolve(self, kind: str) -> InstalledModel | None:
        for record in self.list():
            if record.get("kind") == kind:
                return InstalledModel(**record)
        return None

    def require(self, kind: str) -> InstalledModel:
        model = self.resolve(kind)
        if model is None:
            raise ModelError(
                f"no {kind} model installed. Run `saqr models install` or import a local .onnx file."
            )
        return model

    # ------------------------------------------------------------------ install
    def install_file(self, source: str | Path, kind: str | None = None,
                     model_id: str | None = None, accept_license: bool = False) -> InstalledModel:
        src = Path(source).expanduser()
        if not src.exists() or src.suffix.lower() != ".onnx":
            raise ModelError(f"not an .onnx file: {src}")
        spec = find_spec(model_id or src.name) or find_spec(kind or "")
        if spec is None:
            raise ModelError("unknown model. Pass --id with a catalogue id, or --kind for a custom model.")
        if kind and spec.kind != kind:
            raise ModelError(f"{spec.id} is a {spec.kind} model, not {kind}")
        if spec.requires_acceptance and not (accept_license or self.license_accepted(spec.id)):
            raise ModelError(
                f"{spec.name} is licensed as '{spec.license_name}'. Re-run with "
                "--accept-license after reading docs/MODEL_LICENSES.md."
            )

        digest = sha256_file(src)
        if spec.sha256 and digest != spec.sha256:
            raise ModelError(f"checksum mismatch for {spec.name}: {digest} != {spec.sha256}")

        self._validate_graph(src, spec)
        target = self.root / spec.filename
        if src.resolve() != target.resolve():
            shutil.copy2(src, target)
        record = InstalledModel(
            id=spec.id, filename=spec.filename, kind=spec.kind, path=str(target),
            sha256=digest, license_id=spec.license_id, commercial_use=spec.commercial_use,
            source="import",
        )
        self._index[spec.id] = record.to_dict()
        self._write_index()
        return record

    def download(self, model_id: str, progress: ProgressFn | None = None) -> InstalledModel:
        spec = find_spec(model_id)
        if spec is None:
            raise ModelError(f"unknown model id: {model_id}")
        if not spec.downloadable:
            raise ModelError(
                f"{spec.name} cannot be downloaded automatically (license: {spec.license_name}). "
                "Obtain it yourself and use `saqr models import`."
            )
        if spec.requires_acceptance and not self.license_accepted(spec.id):
            raise ModelError("license acceptance required before download")

        target = self.root / spec.filename
        with tempfile.NamedTemporaryFile(delete=False, suffix=".part", dir=self.root) as tmp:
            tmp_path = Path(tmp.name)
            try:
                with urllib.request.urlopen(spec.download_url, timeout=60) as response:  # noqa: S310 - fixed https URL from catalogue
                    total = int(response.headers.get("Content-Length") or 0)
                    done = 0
                    while True:
                        block = response.read(1 << 16)
                        if not block:
                            break
                        tmp.write(block)
                        done += len(block)
                        if progress:
                            progress(done, total)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
        digest = sha256_file(tmp_path)
        if spec.sha256 and digest != spec.sha256:
            tmp_path.unlink(missing_ok=True)
            raise ModelError(f"downloaded file failed checksum: {digest}")
        tmp_path.replace(target)
        record = InstalledModel(
            id=spec.id, filename=spec.filename, kind=spec.kind, path=str(target), sha256=digest,
            license_id=spec.license_id, commercial_use=spec.commercial_use, source="download",
        )
        self._index[spec.id] = record.to_dict()
        self._write_index()
        return record

    def remove(self, model_id: str, delete_file: bool = True) -> bool:
        record = self._index.pop(model_id, None)
        if record is None:
            return False
        if delete_file:
            Path(record["path"]).unlink(missing_ok=True)
        self._write_index()
        return True

    def verify(self, model_id: str) -> dict:
        record = self._index.get(model_id)
        if not record:
            raise ModelError(f"{model_id} is not installed")
        path = Path(record["path"])
        actual = sha256_file(path) if path.exists() else ""
        return {
            "id": model_id,
            "exists": path.exists(),
            "expected": record.get("sha256"),
            "actual": actual,
            "ok": bool(actual) and actual == record.get("sha256"),
        }

    # ------------------------------------------------------------------ graph check
    @staticmethod
    def _validate_graph(path: Path, spec: ModelSpec) -> None:
        """Reject a file that is not a usable ONNX graph before it reaches the UI."""
        import onnxruntime as ort

        try:
            session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        except Exception as exc:  # noqa: BLE001
            raise ModelError(f"onnxruntime cannot open {path.name}: {str(exc)[:200]}") from exc
        if not session.get_inputs():
            raise ModelError(f"{path.name} has no inputs")
        if spec.kind == "swapper":
            names = {i.name for i in session.get_inputs()}
            if not {"source", "target"} <= names:
                raise ModelError(
                    f"{path.name} does not look like an inswapper-style graph "
                    f"(inputs: {sorted(names)}; expected 'source' and 'target')"
                )
        if spec.kind == "detector" and spec.input_size:
            shape = session.get_inputs()[0].shape
            if len(shape) != 4:
                raise ModelError(f"{path.name} is not an image detector (input shape {shape})")
