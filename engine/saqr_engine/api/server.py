"""Local-only FastAPI bridge.

Security posture:
* binds 127.0.0.1 (never 0.0.0.0 unless the operator explicitly overrides)
* every state-changing call needs a bearer token from a one-time pairing code
* Origin allowlist is enforced before handlers, not only by CORS
* request bodies are size-capped and media is decoded defensively
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from ..config import Settings
from ..hardware.backends import choose_backend, probe_providers
from ..hardware.detection import detect_hardware
from ..models.manager import ModelError, ModelManager
from ..version import __version__
from .auth import AuthError, BridgeAuth

log = logging.getLogger(__name__)
MAX_BODY = 12 * 1024 * 1024


class PairRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)
    client: str = Field(default="web", max_length=64)


class SourceRequest(BaseModel):
    image: str
    name: str = "source"


class FrameRequest(BaseModel):
    image: str
    swap: bool = True
    strength: float = Field(default=1.0, ge=0.0, le=1.0)


class AcceptLicenseRequest(BaseModel):
    accepted_by: str = Field(default="operator", max_length=80)


class MapRequest(BaseModel):
    track_id: int
    source_name: str | None = None


def _decode_base64_image(data: str) -> np.ndarray:
    if "," in data[:64] and data.strip().startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="image is not valid base64") from exc
    if len(raw) > MAX_BODY:
        raise HTTPException(status_code=413, detail="image too large")
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="cannot decode image")
    return image


def _encode_jpeg(image: np.ndarray, quality: int = 92) -> str:
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise HTTPException(status_code=500, detail="jpeg encode failed")
    return base64.b64encode(buffer.tobytes()).decode()


def create_app(
    settings: Settings | None = None,
    auth: BridgeAuth | None = None,
    engine_factory: Callable | None = None,
) -> FastAPI:
    settings = settings or Settings.load()
    origins = list(getattr(settings, "allowed_origins", []) or [])
    auth = auth or BridgeAuth(allowed_origins=origins)
    app = FastAPI(title="SAQR AI Studio Bridge", version=__version__, docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.auth = auth
    app.state.engine = None
    app.state.engine_error = None
    app.state.lock = threading.Lock()
    app.state.started = time.time()
    app.state.engine_factory = engine_factory
    app.state.sources = {}

    if origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=origins, allow_credentials=False,
            allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"],
            max_age=600,
        )

    @app.middleware("http")
    async def guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if not auth.origin_allowed(origin):
            return JSONResponse({"detail": "origin not allowed"}, status_code=403)
        client_host = request.client.host if request.client else ""
        if client_host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            return JSONResponse({"detail": "bridge is local-only"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    def require_token(authorization: str | None = Header(default=None)):
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
        try:
            return auth.validate(token)
        except AuthError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from exc

    def get_engine(load: bool = True):
        if app.state.engine is None and load:
            with app.state.lock:
                if app.state.engine is None:
                    try:
                        from ..face.pipeline import FaceEngine

                        engine = app.state.engine_factory() if app.state.engine_factory else FaceEngine(settings)
                        engine.load_models(want_swap=True, want_enhance=True)
                        app.state.engine = engine
                    except Exception as exc:  # noqa: BLE001
                        app.state.engine_error = str(exc)
                        log.warning("engine unavailable: %s", exc)
                        raise HTTPException(status_code=503, detail=f"engine unavailable: {exc}") from exc
        return app.state.engine

    # ------------------------------------------------------------------ public
    @app.get("/api/health")
    def health():
        return {
            "ok": True, "app": "SAQR AI Studio", "version": __version__,
            "uptime_s": round(time.time() - app.state.started, 1),
            "paired_sessions": auth.session_count(), "engine_ready": app.state.engine is not None,
        }

    @app.post("/api/pair")
    def pair(body: PairRequest, request: Request):
        try:
            result = auth.redeem(body.code, body.client, request.headers.get("origin"),
                                 ip=request.client.host if request.client else "local")
        except AuthError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
        return result

    # ------------------------------------------------------------------ engine
    @app.get("/api/session")
    def session_info(session=Depends(require_token)):
        return session.to_public()

    @app.post("/api/session/revoke")
    def revoke(authorization: str | None = Header(default=None)):
        if authorization and authorization.lower().startswith("bearer "):
            auth.revoke(authorization.split(" ", 1)[1].strip())
        return {"revoked": True}

    @app.get("/api/hardware")
    def hardware(_=Depends(require_token)):
        profile = detect_hardware()
        probes = probe_providers(profile)
        decision = choose_backend(profile, probes, preferred=settings.preferred_provider,
                                  allow_fallback=settings.allow_fallback)
        return {"profile": profile.to_dict(), "decision": decision.to_dict(), "summary": profile.summary()}

    @app.get("/api/models")
    def models(_=Depends(require_token)):
        manager = ModelManager(settings)
        return {"catalog": manager.catalog(), "installed": manager.list()}

    @app.post("/api/models/{model_id}/accept")
    def accept(model_id: str, body: AcceptLicenseRequest, _=Depends(require_token)):
        manager = ModelManager(settings)
        manager.accept_license(model_id, body.accepted_by)
        return {"accepted": model_id}

    @app.get("/api/engine/status")
    def engine_status(_=Depends(require_token)):
        engine = get_engine(load=False)
        if engine is None:
            return {"loaded": False, "error": app.state.engine_error}
        return {"loaded": True, "status": engine.status()}

    @app.post("/api/source")
    def set_source(body: SourceRequest, _=Depends(require_token)):
        image = _decode_base64_image(body.image)
        engine = get_engine()
        try:
            source = engine.set_source_from_array(image, name=body.name)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        app.state.sources[source.name] = source
        thumbnail = base64.b64encode(cv2.imencode(".jpg", source.thumbnail)[1].tobytes()).decode()
        return {"name": source.name, "thumbnail": thumbnail,
                "sources": [{"name": s.name, "primary": s is engine.source} for s in app.state.sources.values()]}

    @app.get("/api/sources")
    def list_sources(_=Depends(require_token)):
        engine = get_engine(load=False)
        rows = []
        for name, source in app.state.sources.items():
            thumbnail = base64.b64encode(cv2.imencode(".jpg", source.thumbnail)[1].tobytes()).decode()
            rows.append({"name": name, "thumbnail": thumbnail,
                         "primary": bool(engine and engine.source is source)})
        return {"sources": rows}

    @app.post("/api/map")
    def map_face(body: MapRequest, _=Depends(require_token)):
        engine = get_engine()
        source = app.state.sources.get(body.source_name) if body.source_name else None
        engine.map_face(body.track_id, source)
        return {"track_id": body.track_id, "source": body.source_name}

    @app.post("/api/frame")
    def process_frame(body: FrameRequest, _=Depends(require_token)):
        image = _decode_base64_image(body.image)
        engine = get_engine()
        from ..face.swapper import SwapOptions

        result = engine.process(image, swap=body.swap,
                                options=SwapOptions(strength=body.strength,
                                                    keep_mouth=settings.mouth_mask))
        return {
            "image": _encode_jpeg(result.frame, 90),
            "metrics": result.metrics,
            "faces": [f.to_dict() for f in result.faces],
            "swapped_faces": result.swapped_faces,
            "error": result.error,
        }

    # ------------------------------------------------------------------ diagnostics
    @app.get("/api/diagnostics")
    def diagnostics(_=Depends(require_token)):
        engine = app.state.engine
        return {
            "version": __version__,
            "provider": engine.decision.provider if engine and engine.decision else None,
            "sessions": {k: v.__dict__ for k, v in (engine.sessions.items() if engine else [])},
            "load_errors": engine.load_errors if engine else [],
            "models": [m.to_dict() for m in ModelManager(settings).list()],
            "engine_error": app.state.engine_error,
        }

    @app.exception_handler(AuthError)
    async def auth_error_handler(_request: Request, exc: AuthError):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    @app.exception_handler(ModelError)
    async def model_error_handler(_request: Request, exc: ModelError):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    dist = Path(__file__).resolve().parents[3] / "web" / "dist"
    if dist.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            candidate = dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app
