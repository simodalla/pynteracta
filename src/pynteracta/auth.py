# SPDX-License-Identifier: Apache-2.0
"""Authentication: service-account key parsing, JWT assertion, token cache."""

from __future__ import annotations

import base64
import hashlib
import json
import stat
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

import jwt
import structlog
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from pynteracta.exceptions import AuthenticationError
from pynteracta.models.facade.auth import (
    CreateAccessTokenByServiceAccountRequestDTO,
    GoogleOAuth2AccessTokenResponse,
    ServiceAccountTokenResponse,
)
from pynteracta.transport import HttpTransport

_log = structlog.get_logger("pynteracta.auth")

_AUTH_PATH = "core/auth/create-access-token-by-service-account"
_GOOGLE_AUTH_PATH = "core/auth/create-access-token-by-google-oauth2-access-token-credentials"
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

    Expected schema (per official vendor docs):

    .. code-block:: json

        {
            "type": "service_account",
            "private_key_id": 42,
            "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
            "client_id": 1001
        }

    Raises:
        AuthenticationError: If the file is unreadable, not valid JSON, ``type`` is not
            ``"service_account"``, or required fields are missing.
    """
    try:
        raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AuthenticationError(f"Cannot read service account key: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuthenticationError(f"Invalid JSON in service account key: {path}") from exc

    key_type = raw.get("type")
    if key_type != "service_account":
        raise AuthenticationError(
            f"Service account key {path}: expected type 'service_account', got {key_type!r}"
        )

    private_key_id = raw.get("private_key_id")
    private_key = raw.get("private_key")
    client_id = raw.get("client_id")

    missing = [
        name
        for name, value in (
            ("private_key_id", private_key_id),
            ("private_key", private_key),
            ("client_id", client_id),
        )
        if value is None
    ]
    if missing:
        raise AuthenticationError(
            f"Service account key {path} is missing required field(s): {', '.join(missing)}"
        )

    return ServiceAccountKey(
        client_id=int(client_id),  # type: ignore[arg-type]
        private_key_id=int(private_key_id),  # type: ignore[arg-type]
        private_key_pem=str(private_key),
    )


@dataclass(frozen=True)
class ServiceAccountKey:
    """Parsed service-account key (vendor schema)."""

    client_id: int
    private_key_id: int
    private_key_pem: str


@dataclass(frozen=True)
class GoogleOAuth2Credentials:
    """Credentials for the Google-OAuth2 authentication method.

    Supply **exactly one** of:

    - ``token``: a static Google OAuth2 access token (min scope ``profile``), or
    - ``token_provider``: a callable returning a fresh Google access token on demand.

    The library never runs a Google browser/PKCE flow; obtaining the Google access token is
    the caller's responsibility (see ``docs/authentication.md``).  The Google identity must
    already be linked to an Interacta user.
    """

    token: str | None = None
    token_provider: Callable[[], str] | None = None

    def __post_init__(self) -> None:
        if (self.token is None) == (self.token_provider is None):
            raise AuthenticationError(
                "GoogleOAuth2Credentials requires exactly one of 'token' or 'token_provider'"
            )

    def get_google_token(self) -> str:
        """Return the current Google access token (static value or provider result)."""
        if self.token_provider is not None:
            return self.token_provider()
        assert self.token is not None  # guaranteed by __post_init__
        return self.token


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


def build_cache_key(api_base: str, identity: str) -> str:
    """Namespace a token-cache key by tenant so two tenants never share a file.

    The credential alone does not identify a tenant: Interacta ``client_id`` values are
    vendor-assigned small integers, and a certification tenant is often a clone of production,
    so two profiles pointing at different hosts can carry the same id. Hashing the API base into
    the key keeps their cache files distinct, and a production bearer token can no longer be
    replayed against a staging host.
    """
    digest = hashlib.sha256(api_base.encode("utf-8")).hexdigest()[:16]
    return f"{digest}-{identity}"


class FileTokenCache:
    """File-backed token cache with POSIX ``0o600`` / ``0o700`` enforcement."""

    def __init__(self, cache_dir: Path, api_base: str | None = None) -> None:
        _maybe_warn_windows()
        self._dir = cache_dir
        self._api_base = api_base
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
        stored_base = data.get("api_base")
        if self._api_base is not None and stored_base is not None and stored_base != self._api_base:
            # A file written for another tenant. Discard rather than hand its token to this host.
            # A file written by <= 0.9.2 carries no "api_base" and is accepted (see D-v0.9.3-5).
            _log.warning(
                "auth.token_cache_tenant_mismatch",
                path=str(path),
                expected=self._api_base,
                stored=stored_base,
            )
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
        payload: dict[str, Any] = {
            "access_token": token.access_token,
            "expires_at": _iso(token.expires_at),
            "obtained_at": _iso(token.obtained_at),
        }
        if self._api_base is not None:
            payload["api_base"] = self._api_base
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if sys.platform != "win32":
            path.chmod(_FILE_MODE)
            _check_posix_mode(path, _FILE_MODE, label="token cache file")

    def clear(self, profile: str) -> None:
        path = self._path_for(profile)
        if path.exists():
            path.unlink()


@runtime_checkable
class TokenProvider(Protocol):
    """Common surface for token managers consumed by :class:`HttpTransport`."""

    def get_token(self) -> str: ...

    def invalidate(self) -> None: ...


class TokenManager:
    """Manages token lifecycle: obtain, cache, refresh."""

    AUDIENCE = "injenia/portal-authenticator"
    ALGORITHM = "RS512"
    ASSERTION_TTL_SECONDS = 300
    _MAX_TTL_SECONDS = 600
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
        self._profile: str = build_cache_key(transport.base_url, str(key.client_id))

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
        iat = int(now.timestamp())
        exp = iat + self.ASSERTION_TTL_SECONDS
        if exp - iat > self._MAX_TTL_SECONDS:
            raise AuthenticationError(
                f"Assertion TTL {exp - iat}s exceeds vendor cap of {self._MAX_TTL_SECONDS}s"
            )
        claims = {
            "jti": uuid4().hex,
            "aud": self.AUDIENCE,
            "iss": self._key.client_id,
            "iat": iat,
            "exp": exp,
        }
        # Build a compact JWT manually so that numeric iss and kid are preserved as JSON
        # numbers (PyJWT rejects non-string iss via its payload validator).
        try:
            return _encode_rs512(
                header={"alg": "RS512", "typ": "JWT", "kid": self._key.private_key_id},
                payload=claims,
                pem=self._key.private_key_pem,
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


class GoogleOAuth2TokenManager:
    """Obtains an Interacta access token by exchanging a Google OAuth2 access token.

    Mirrors :class:`TokenManager`'s public surface (:meth:`get_token` / :meth:`invalidate`)
    so it is interchangeable as a :class:`HttpTransport` token provider/invalidator.  The
    Interacta access token is cached and refreshed exactly like the service-account flow; the
    cache key is the profile name (the Google flow has no ``client_id``).
    """

    _SKEW_SECONDS: int = TokenManager._SKEW_SECONDS

    def __init__(
        self,
        credentials: GoogleOAuth2Credentials,
        cache: TokenCache,
        transport: HttpTransport,
        *,
        cache_key: str,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._credentials = credentials
        self._cache = cache
        self._transport = transport
        self._clock = clock
        self._lock = threading.Lock()
        self._profile = build_cache_key(transport.base_url, cache_key)

    def get_token(self) -> str:
        """Return a valid Interacta access token, refreshing if near expiry."""
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

    def _needs_refresh(self, token: CachedToken) -> bool:
        now = self._clock()
        delta = (token.expires_at - now).total_seconds()
        return delta < self._SKEW_SECONDS

    def _fetch_token(self) -> CachedToken:
        google_token = self._credentials.get_google_token()
        response = self._transport.request(
            "POST",
            _GOOGLE_AUTH_PATH,
            json={"googleOAuth2Token": google_token},
        )
        parsed = GoogleOAuth2AccessTokenResponse.from_dict(response.json())
        access_token = parsed.access_token
        if not access_token:
            raise AuthenticationError("Google OAuth2 auth response missing accessToken")
        obtained_at = self._clock()
        expires_at = _decode_token_expiry(access_token)
        return CachedToken(
            access_token=access_token,
            expires_at=expires_at,
            obtained_at=obtained_at,
        )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _encode_rs512(header: dict[str, Any], payload: dict[str, Any], pem: str) -> str:
    """Produce a compact RS512 JWT preserving numeric claim values verbatim."""
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    private_key: RSAPrivateKey = serialization.load_pem_private_key(pem.encode(), password=None)  # type: ignore[assignment]
    signature = private_key.sign(signing_input, asym_padding.PKCS1v15(), hashes.SHA512())
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


def _decode_token_expiry(access_token: str) -> datetime:
    """Extract ``exp`` from the access-token JWT (no ``expiresIn`` in API response)."""
    try:
        payload = jwt.decode(
            access_token,
            options={"verify_signature": False},
            algorithms=["RS256", "RS512", "HS256", "ES256"],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Cannot decode access token expiry") from exc
    exp = payload.get("exp")
    if exp is None:
        raise AuthenticationError("Access token missing exp claim")
    return datetime.fromtimestamp(int(exp), tz=UTC)


def _assertion_ttl() -> timedelta:
    return timedelta(seconds=TokenManager.ASSERTION_TTL_SECONDS)
