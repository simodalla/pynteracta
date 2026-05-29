# SPDX-License-Identifier: Apache-2.0
"""Authentication: service-account key parsing, JWT assertion, token cache."""

from __future__ import annotations

import json
import stat
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import jwt
import structlog

from pynteracta.exceptions import AuthenticationError
from pynteracta.models.facade.auth import (
    CreateAccessTokenByServiceAccountRequestDTO,
    ServiceAccountTokenResponse,
)
from pynteracta.transport import HttpTransport

_log = structlog.get_logger("pynteracta.auth")

_AUTH_PATH = "core/auth/create-access-token-by-service-account"
_ASSERTION_TTL = timedelta(minutes=5)
_FILE_MODE = 0o600
_DIR_MODE = 0o700
_WINDOWS_WARNED = False


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _maybe_warn_windows() -> None:
    global _WINDOWS_WARNED  # noqa: PLW0603
    if sys.platform == "win32" and not _WINDOWS_WARNED:
        _log.warning(
            "token_cache.windows_permissions",
            message=(
                "POSIX file modes are not enforced on Windows; token cache protection "
                "relies on NTFS ACLs. Prefer token_cache='memory' for stronger isolation."
            ),
        )
        _WINDOWS_WARNED = True


def _check_posix_mode(path: Path, expected: int, *, label: str) -> None:
    if sys.platform == "win32":
        return
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != expected:
        msg = (
            f"Refusing to use {label} {path}: permissions are {oct(mode)}, expected {oct(expected)}"
        )
        raise AuthenticationError(msg)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_service_account_key(path: Path) -> ServiceAccountKey:
    """Parse a service-account key JSON file into :class:`ServiceAccountKey`.

    Supported field names (Q1 — first match wins per role):

    * ``client_id``: ``clientId``, ``email``, ``client_id``
    * ``private_key_pem``: ``privateKey``, ``private_key``
    * ``token_audience``: ``tokenAudience``, ``token_audience``, ``audience``
    * ``kid``: ``kid`` (optional)

    Raises:
        AuthenticationError: If the file is unreadable or required fields are missing.
    """
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AuthenticationError(f"Cannot read service account key: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuthenticationError(f"Invalid JSON in service account key: {path}") from exc

    client_id = raw.get("clientId") or raw.get("email") or raw.get("client_id")
    private_key = raw.get("privateKey") or raw.get("private_key")
    token_audience = raw.get("tokenAudience") or raw.get("token_audience") or raw.get("audience")
    kid = raw.get("kid")

    missing = [
        name
        for name, value in (
            ("clientId/email", client_id),
            ("privateKey", private_key),
            ("tokenAudience", token_audience),
        )
        if not value
    ]
    if missing:
        raise AuthenticationError(
            f"Service account key {path} is missing required field(s): {', '.join(missing)}"
        )

    return ServiceAccountKey(
        client_id=str(client_id),
        private_key_pem=str(private_key),
        token_audience=str(token_audience),
        kid=str(kid) if kid is not None else None,
    )


@dataclass(frozen=True)
class ServiceAccountKey:
    """Parsed service-account key (Q1 schema)."""

    client_id: str
    private_key_pem: str
    token_audience: str
    kid: str | None = None


@dataclass
class CachedToken:
    """A cached access token with its validity window."""

    access_token: str
    expires_at: datetime
    obtained_at: datetime


@runtime_checkable
class TokenCache(Protocol):
    """Pluggable token-cache backend."""

    def load(self, profile: str) -> CachedToken | None: ...

    def save(self, profile: str, token: CachedToken) -> None: ...

    def clear(self, profile: str) -> None: ...


class MemoryTokenCache:
    """In-process token cache (not persisted across restarts)."""

    def __init__(self) -> None:
        self._store: dict[str, CachedToken] = {}

    def load(self, profile: str) -> CachedToken | None:
        return self._store.get(profile)

    def save(self, profile: str, token: CachedToken) -> None:
        self._store[profile] = token

    def clear(self, profile: str) -> None:
        self._store.pop(profile, None)


class FileTokenCache:
    """File-backed token cache with POSIX ``0o600`` / ``0o700`` enforcement."""

    def __init__(self, cache_dir: Path) -> None:
        _maybe_warn_windows()
        self._dir = cache_dir
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        if sys.platform != "win32":
            self._dir.chmod(_DIR_MODE)
            _check_posix_mode(self._dir, _DIR_MODE, label="cache directory")

    def _path_for(self, profile: str) -> Path:
        safe = profile.replace("/", "_").replace("\\", "_")
        return self._dir / f"{safe}.token.json"

    def load(self, profile: str) -> CachedToken | None:
        path = self._path_for(profile)
        if not path.exists():
            return None
        _check_posix_mode(path, _FILE_MODE, label="token cache file")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _log.warning("auth.token_cache_corrupt", path=str(path), error=str(exc))
            return None
        try:
            return CachedToken(
                access_token=str(data["access_token"]),
                expires_at=_parse_iso(str(data["expires_at"])),
                obtained_at=_parse_iso(str(data["obtained_at"])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            _log.warning("auth.token_cache_corrupt", path=str(path), error=str(exc))
            return None

    def save(self, profile: str, token: CachedToken) -> None:
        self._ensure_dir()
        path = self._path_for(profile)
        payload = {
            "access_token": token.access_token,
            "expires_at": _iso(token.expires_at),
            "obtained_at": _iso(token.obtained_at),
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if sys.platform != "win32":
            path.chmod(_FILE_MODE)
            _check_posix_mode(path, _FILE_MODE, label="token cache file")

    def clear(self, profile: str) -> None:
        path = self._path_for(profile)
        if path.exists():
            path.unlink()


class TokenManager:
    """Manages token lifecycle: obtain, cache, refresh."""

    _SKEW_SECONDS: int = 60

    def __init__(
        self,
        key: ServiceAccountKey,
        cache: TokenCache,
        transport: HttpTransport,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._key = key
        self._cache = cache
        self._transport = transport
        self._clock = clock
        self._lock = threading.Lock()
        self._profile: str = key.client_id

    def get_token(self) -> str:
        """Return a valid access token, refreshing if near expiry."""
        with self._lock:
            cached = self._cache.load(self._profile)
            if cached is not None and not self._needs_refresh(cached):
                _log.debug("auth.token_cache_loaded", profile=self._profile)
                return cached.access_token

            refreshed = cached is not None
            token = self._fetch_token()
            self._cache.save(self._profile, token)
            if refreshed:
                _log.info("auth.token_refreshed", expires_at=_iso(token.expires_at))
            else:
                _log.info("auth.token_obtained", expires_at=_iso(token.expires_at))
            return token.access_token

    def invalidate(self) -> None:
        """Discard any cached token for the current profile."""
        with self._lock:
            self._cache.clear(self._profile)

    @property
    def _cached(self) -> CachedToken | None:
        return self._cache.load(self._profile)

    def _needs_refresh(self, token: CachedToken) -> bool:
        now = self._clock()
        delta = (token.expires_at - now).total_seconds()
        return delta < self._SKEW_SECONDS

    def _build_assertion(self) -> str:
        now = self._clock()
        claims = {
            "iss": self._key.client_id,
            "sub": self._key.client_id,
            "aud": self._key.token_audience,
            "iat": int(now.timestamp()),
            "exp": int((now + _ASSERTION_TTL).timestamp()),
        }
        headers: dict[str, str] = {}
        if self._key.kid is not None:
            headers["kid"] = self._key.kid
        try:
            return jwt.encode(
                claims,
                self._key.private_key_pem,
                algorithm="RS256",
                headers=headers or None,
            )
        except Exception as exc:
            raise AuthenticationError("Failed to build JWT assertion") from exc

    def _fetch_token(self) -> CachedToken:
        assertion = self._build_assertion()
        req = CreateAccessTokenByServiceAccountRequestDTO(jwtAssertion=assertion)
        response = self._transport.request(
            "POST",
            _AUTH_PATH,
            json=req.model_dump(mode="json", exclude_none=True),
        )
        body = response.json()
        parsed = ServiceAccountTokenResponse.from_dict(body)
        access_token = parsed.access_token
        if not access_token:
            raise AuthenticationError("Auth response missing accessToken")
        obtained_at = self._clock()
        expires_at = _decode_token_expiry(access_token)
        return CachedToken(
            access_token=access_token,
            expires_at=expires_at,
            obtained_at=obtained_at,
        )


def _decode_token_expiry(access_token: str) -> datetime:
    """Extract ``exp`` from the access-token JWT (Q3 — no ``expiresIn`` in API response)."""
    try:
        payload = jwt.decode(
            access_token,
            options={"verify_signature": False},
            algorithms=["RS256", "HS256", "ES256"],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Cannot decode access token expiry") from exc
    exp = payload.get("exp")
    if exp is None:
        raise AuthenticationError("Access token missing exp claim")
    return datetime.fromtimestamp(int(exp), tz=UTC)
