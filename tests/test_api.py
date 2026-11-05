import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from saqr_engine.api.auth import BridgeAuth
from saqr_engine.api.server import create_app

ORIGIN = {"Origin": "http://localhost:5173"}


@pytest.fixture()
def bridge(settings):
    auth = BridgeAuth(allowed_origins=["http://localhost:5173"], pairing_ttl=60)
    app = create_app(settings=settings, auth=auth)
    return TestClient(app), auth


def _pair(client, auth):
    code = auth.issue_code()["code"]
    response = client.post("/api/pair", json={"code": code, "client": "pytest"}, headers=ORIGIN)
    assert response.status_code == 200, response.text
    return response.json()["token"]


def test_health_is_public(bridge):
    client, _ = bridge
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["app"] == "SAQR AI Studio"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_protected_routes_need_token(bridge):
    client, _ = bridge
    assert client.get("/api/hardware").status_code == 401
    assert client.get("/api/models").status_code == 401


def test_pairing_flow(bridge):
    client, auth = bridge
    token = _pair(client, auth)
    headers = {**ORIGIN, "Authorization": f"Bearer {token}"}
    assert client.get("/api/session", headers=headers).status_code == 200
    data = client.get("/api/hardware", headers=headers).json()
    assert data["profile"]["cpu"]["logical_cores"] >= 1
    assert data["decision"]["chain"][-1] == "CPUExecutionProvider"
    catalog = client.get("/api/models", headers=headers).json()
    assert any(row["id"] == "yunet-2023mar" for row in catalog["catalog"])


def test_wrong_code_rejected(bridge):
    client, _ = bridge
    response = client.post("/api/pair", json={"code": "000000", "client": "x"}, headers=ORIGIN)
    assert response.status_code == 401


def test_code_is_one_time(bridge):
    client, auth = bridge
    code = auth.issue_code()["code"]
    assert client.post("/api/pair", json={"code": code}, headers=ORIGIN).status_code == 200
    assert client.post("/api/pair", json={"code": code}, headers=ORIGIN).status_code == 401


def test_pairing_rate_limited(bridge):
    client, _ = bridge
    statuses = [client.post("/api/pair", json={"code": "999999"}, headers=ORIGIN).status_code
                for _ in range(8)]
    assert statuses[-1] == 429
    assert statuses[0] == 401


def test_foreign_origin_blocked(bridge):
    client, _ = bridge
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_token_required_for_frame(bridge):
    client, auth = bridge
    response = client.post("/api/frame", json={"image": "AAAA"}, headers=ORIGIN)
    assert response.status_code == 401


def test_frame_rejects_non_image(bridge):
    client, auth = bridge
    token = _pair(client, auth)
    headers = {**ORIGIN, "Authorization": f"Bearer {token}"}
    response = client.post("/api/frame", json={"image": base64.b64encode(b"nope").decode()},
                           headers=headers)
    assert response.status_code == 400


def test_frame_returns_503_without_models(bridge):
    client, auth = bridge
    token = _pair(client, auth)
    headers = {**ORIGIN, "Authorization": f"Bearer {token}"}
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    import cv2

    payload = base64.b64encode(cv2.imencode(".jpg", image)[1].tobytes()).decode()
    response = client.post("/api/frame", json={"image": payload}, headers=headers)
    assert response.status_code == 503
    assert "engine unavailable" in response.json()["detail"]


def test_session_can_be_revoked(bridge):
    client, auth = bridge
    token = _pair(client, auth)
    headers = {**ORIGIN, "Authorization": f"Bearer {token}"}
    assert client.post("/api/session/revoke", headers=headers).status_code == 200
    assert client.get("/api/session", headers=headers).status_code == 401
