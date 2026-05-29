# SPDX-License-Identifier: Apache-2.0
"""Authentication data classes and token-cache interface.

JWT assertion build and real HTTP calls are implemented in M4 once the
service-account key schema (Q1-Q4) is confirmed.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class ServiceAccountKey:
    """Parsed service-account key.

    Exact field set is TBD (Q1); only ``client_id`` and ``private_key_pem``
    are assumed for now.
    """

    client_id: str
    private_key_pem: str


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
    """File-backed token cache (mode 0o600 enforcement implemented in M4)."""

    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir

    def load(self, profile: str) -> CachedToken | None:
        raise NotImplementedError("FileTokenCache is completed in M4")

    def save(self, profile: str, token: CachedToken) -> None:
        raise NotImplementedError("FileTokenCache is completed in M4")

    def clear(self, profile: str) -> None:
        raise NotImplementedError("FileTokenCache is completed in M4")


class TokenManager:
    """Manages token lifecycle: obtain, cache, refresh.

    JWT assertion construction and the actual auth HTTP call are implemented
    in M4.  The skeleton is provided here so the interface is stable for M2.
    """

    _SKEW_SECONDS: int = 60

    def __init__(
        self,
        key: ServiceAccountKey,
        cache: TokenCache,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._key = key
        self._cache = cache
        self._clock = clock
        self._lock = threading.Lock()
        self._profile: str = key.client_id

    def get_token(self) -> str:
        """Return a valid access token, refreshing if near expiry.

        Raises:
            NotImplementedError: Until M4 implements the JWT assertion flow.
        """
        raise NotImplementedError("JWT assertion flow implemented in M4")

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

    # M4 will add: _build_assertion(), _fetch_token()
