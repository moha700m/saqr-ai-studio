import http.server
import threading
from pathlib import Path

import pytest

from saqr_engine.cloud import (CloudConfig, CloudDisabled, Consent, ConsentRequired,
                               process_in_cloud, require_consent)

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)


class Handler(http.server.BaseHTTPRequestHandler):
    received = b""

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        Handler.received = self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(PNG)

    def log_message(self, *_args):
        pass


@pytest.fixture()
def endpoint():
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/infer"
    server.shutdown()


def test_unconfigured_cloud_is_disabled(tmp_path):
    with pytest.raises(CloudDisabled):
        require_consent(None, CloudConfig(), tmp_path / "a.png")


def test_consent_must_match_file_and_destination(tmp_path, endpoint):
    path = tmp_path / "portrait.png"
    path.write_bytes(PNG)
    config = CloudConfig(endpoint=endpoint, provider_name="test")
    with pytest.raises(ConsentRequired):
        require_consent(Consent(False, path.name, endpoint), config, path)
    with pytest.raises(ConsentRequired):
        require_consent(Consent(True, "other.png", endpoint), config, path)
    with pytest.raises(ConsentRequired):
        require_consent(Consent(True, path.name, "https://other.example"), config, path)
    assert require_consent(Consent(True, path.name, endpoint), config, path).granted


def test_upload_sends_bytes_and_returns_temp_file(tmp_path, endpoint):
    path = tmp_path / "portrait.jpg"
    path.write_bytes(b"fake-jpeg-bytes" * 10)
    config = CloudConfig(endpoint=endpoint, provider_name="test")
    result = process_in_cloud(path, config, Consent(True, path.name, endpoint))
    assert result.ok is True
    assert result.bytes_sent > path.stat().st_size
    output = Path(result.output_path)
    assert output.exists() and output.read_bytes() == PNG
    assert b"fake-jpeg-bytes" in Handler.received
    output.unlink()  # caller-owned temp file cleanup


def test_upload_is_never_silent(tmp_path, endpoint):
    path = tmp_path / "portrait.jpg"
    path.write_bytes(b"x")
    config = CloudConfig(endpoint=endpoint, provider_name="test")
    with pytest.raises(ConsentRequired):
        process_in_cloud(path, config, None)
