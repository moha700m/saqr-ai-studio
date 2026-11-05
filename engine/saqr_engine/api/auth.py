"""Pairing-code authentication for the local desktop/web bridge.

Threat model: a web page in the user's browser tries to talk to 127.0.0.1.
The bridge therefore requires (a) a one-time code that only the desktop app can
display, (b) an Origin allowlist checked before any handler runs, and (c) a
bearer token that is stored hashed and expires.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass, field


class AuthError(RuntimeError):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


@dataclass
class Session:
    token_hash: str
    client: str
    origin: str | None
    created_at: float
    expires_at: float
    scopes: tuple[str, ...] = ("engine:read", "engine:frame", "engine:source")

    def to_public(self) -> dict:
        return {"client": self.client, "created_at": int(self.created_at),
                "expires_at": int(self.expires_at), "scopes": list(self.scopes)}


@dataclass
class PairingCode:
    code: str
    created_at: float
    expires_at: float
    used: bool = False


@dataclass
class RateLimiter:
    limit: int = 6
    window_s: float = 60.0
    _hits: dict[str, list[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self, key: str) -> None:
        now = time.time()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self.window_s]
            if len(hits) >= self.limit:
                raise AuthError("too many pairing attempts; wait a minute", status=429)
            hits.append(now)
            self._hits[key] = hits


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class BridgeAuth:
    def __init__(self, pairing_ttl: float = 180.0, session_ttl: float = 12 * 3600.0,
                 allowed_origins: list[str] | None = None):
        self.pairing_ttl = pairing_ttl
        self.session_ttl = session_ttl
        self.allowed_origins = allowed_origins or []
        self._codes: dict[str, PairingCode] = {}
        self._sessions: dict[str, Session] = {}
        self._limiter = RateLimiter()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ pairing
    def issue_code(self) -> dict:
        code = f"{secrets.randbelow(1_000_000):06d}"
        now = time.time()
        with self._lock:
            self._codes = {k: v for k, v in self._codes.items() if v.expires_at > now and not v.used}
            self._codes[code] = PairingCode(code=code, created_at=now, expires_at=now + self.pairing_ttl)
        return {"code": code, "expires_in": int(self.pairing_ttl)}

    def redeem(self, code: str, client: str, origin: str | None, ip: str = "local") -> dict:
        self._limiter.check(ip)
        now = time.time()
        with self._lock:
            record = self._codes.get(code.strip())
            if record is None or record.used or record.expires_at < now:
                raise AuthError("invalid or expired pairing code")
            record.used = True
            token = secrets.token_urlsafe(32)
            session = Session(
                token_hash=_hash(token), client=(client or "web")[:64], origin=origin,
                created_at=now, expires_at=now + self.session_ttl,
            )
            self._sessions[session.token_hash] = session
            self._codes.pop(code, None)
        return {"token": token, "token_type": "Bearer", "expires_in": int(self.session_ttl),
                "scopes": list(session.scopes)}

    # ------------------------------------------------------------------ sessions
    def validate(self, token: str | None) -> Session:
        if not token:
            raise AuthError("missing bearer token")
        session = self._sessions.get(_hash(token))
        if session is None:
            raise AuthError("unknown token")
        if session.expires_at < time.time():
            self._sessions.pop(session.token_hash, None)
            raise AuthError("session expired")
        return session

    def revoke(self, token: str) -> bool:
        return self._sessions.pop(_hash(token), None) is not None

    def revoke_all(self) -> int:
        count = len(self._sessions)
        self._sessions.clear()
        return count

    def session_count(self) -> int:
        now = time.time()
        with self._lock:
            self._sessions = {k: v for k, v in self._sessions.items() if v.expires_at > now}
            return len(self._sessions)

    def origin_allowed(self, origin: str | None) -> bool:
        if origin is None:
            return True  # same-origin / non-browser clients
        return origin.rstrip("/") in {o.rstrip("/") for o in self.allowed_origins}

    @staticmethod
    def constant_time_equals(a: str, b: str) -> bool:
        return hmac.compare_digest(a, b)
