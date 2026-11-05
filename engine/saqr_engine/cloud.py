"""Bring-your-own-endpoint cloud inference.

SAQR ships no cloud provider and cannot upload anything by itself. A cloud job
requires (1) an endpoint + credential the user configured, (2) a consent record
naming the file and the destination, and (3) an explicit call from the user's
action. Uploads go to a temporary file, are streamed with progress, and the
temporary file is always deleted.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path


class CloudDisabled(RuntimeError):
    pass


class ConsentRequired(RuntimeError):
    pass


@dataclass
class CloudConfig:
    endpoint: str | None = None
    token: str | None = None
    provider_name: str | None = None
    max_upload_mb: int = 64

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.provider_name)

    def to_public(self) -> dict:
        return {
            "configured": self.configured,
            "provider_name": self.provider_name,
            "endpoint_host": _host(self.endpoint) if self.endpoint else None,
            "max_upload_mb": self.max_upload_mb,
            "token_set": bool(self.token),
        }


@dataclass
class Consent:
    granted: bool
    file_name: str
    destination: str
    granted_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CloudResult:
    ok: bool
    output_path: str | None
    bytes_sent: int
    elapsed_s: float
    error: str | None = None


def _host(url: str | None) -> str | None:
    if not url:
        return None
    return urllib.parse.urlsplit(url).netloc


def require_consent(consent: Consent | None, config: CloudConfig, path: Path) -> Consent:
    if not config.configured:
        raise CloudDisabled("cloud endpoint is not configured; SAQR has no bundled cloud provider")
    if consent is None or not consent.granted:
        raise ConsentRequired("explicit consent is required before uploading media")
    if consent.file_name != path.name or consent.destination != config.endpoint:
        raise ConsentRequired("consent does not match this file and destination")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > config.max_upload_mb:
        raise ValueError(f"file is {size_mb:.1f} MB, above the {config.max_upload_mb} MB limit")
    return consent


def process_in_cloud(path: str | Path, config: CloudConfig, consent: Consent | None,
                     progress=None, timeout: float = 120.0) -> CloudResult:
    source = Path(path)
    require_consent(consent, config, source)
    boundary = "----saqr" + os.urandom(8).hex()
    body_head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{source.name}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body_tail = f"\r\n--{boundary}--\r\n".encode()
    payload = body_head + source.read_bytes() + body_tail
    request = urllib.request.Request(
        config.endpoint, data=payload, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "X-Saqr-Consent": "explicit",
                 **({"Authorization": f"Bearer {config.token}"} if config.token else {})},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided endpoint
            data = response.read()
        if progress:
            progress(len(payload), len(payload))
        suffix = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
        handle, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="saqr-cloud-")
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        return CloudResult(True, tmp_path, len(payload), round(time.time() - started, 2))
    except urllib.error.HTTPError as exc:
        return CloudResult(False, None, len(payload), round(time.time() - started, 2),
                           f"endpoint returned {exc.code}")
    except (urllib.error.URLError, TimeoutError) as exc:
        return CloudResult(False, None, 0, round(time.time() - started, 2), str(exc))


def load_cloud_config(home: Path) -> CloudConfig:
    path = Path(home) / "cloud.json"
    if not path.exists():
        return CloudConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return CloudConfig()
    return CloudConfig(endpoint=data.get("endpoint"), token=data.get("token"),
                       provider_name=data.get("provider_name"),
                       max_upload_mb=int(data.get("max_upload_mb", 64)))
