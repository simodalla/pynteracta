# SPDX-License-Identifier: Apache-2.0
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pynteracta.auth import (
    CachedToken,
    FileTokenCache,
    MemoryTokenCache,
    ServiceAccountKey,
    TokenCache,
    TokenManager,
)

_EXPIRY_SHORT = 30
_EXPIRY_LONG = 3600


def _token(*, seconds_until_expiry: float = _EXPIRY_LONG) -> CachedToken:
    now = datetime.now(tz=UTC)
    return CachedToken(
        access_token="tok",
        expires_at=now + timedelta(seconds=seconds_until_expiry),
        obtained_at=now,
    )


class TestServiceAccountKey:
    def test_frozen(self) -> None:
        key = ServiceAccountKey(client_id="cid", private_key_pem="pem")
        with pytest.raises(AttributeError):
            key.client_id = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        key = ServiceAccountKey(client_id="cid", private_key_pem="pem")
        assert key.client_id == "cid"
        assert key.private_key_pem == "pem"


class TestMemoryTokenCache:
    def test_round_trip(self) -> None:
        cache = MemoryTokenCache()
        t = _token()
        cache.save("dev", t)
        assert cache.load("dev") is t

    def test_load_missing(self) -> None:
        assert MemoryTokenCache().load("missing") is None

    def test_clear(self) -> None:
        cache = MemoryTokenCache()
        cache.save("dev", _token())
        cache.clear("dev")
        assert cache.load("dev") is None

    def test_clear_nonexistent_is_safe(self) -> None:
        MemoryTokenCache().clear("nope")

    def test_satisfies_protocol(self) -> None:
        assert isinstance(MemoryTokenCache(), TokenCache)


class TestFileTokenCacheStub:
    _CACHE_DIR = Path("/tmp")

    def test_load_raises(self) -> None:
        fc = FileTokenCache(self._CACHE_DIR)
        with pytest.raises(NotImplementedError):
            fc.load("dev")

    def test_save_raises(self) -> None:
        fc = FileTokenCache(self._CACHE_DIR)
        with pytest.raises(NotImplementedError):
            fc.save("dev", _token())

    def test_clear_raises(self) -> None:
        fc = FileTokenCache(self._CACHE_DIR)
        with pytest.raises(NotImplementedError):
            fc.clear("dev")


class TestTokenManager:
    def _make(self) -> TokenManager:
        key = ServiceAccountKey(client_id="cid", private_key_pem="pem")
        cache = MemoryTokenCache()
        return TokenManager(key=key, cache=cache)

    def test_get_token_raises_not_implemented(self) -> None:
        tm = self._make()
        with pytest.raises(NotImplementedError):
            tm.get_token()

    def test_invalidate_clears_cache(self) -> None:
        key = ServiceAccountKey(client_id="cid", private_key_pem="pem")
        cache = MemoryTokenCache()
        cache.save("cid", _token())
        tm = TokenManager(key=key, cache=cache)
        tm.invalidate()
        assert cache.load("cid") is None

    def test_needs_refresh_when_near_expiry(self) -> None:
        key = ServiceAccountKey(client_id="cid", private_key_pem="pem")
        cache = MemoryTokenCache()
        tm = TokenManager(key=key, cache=cache)
        near_expiry = _token(seconds_until_expiry=_EXPIRY_SHORT)
        assert tm._needs_refresh(near_expiry) is True

    def test_no_refresh_when_valid(self) -> None:
        key = ServiceAccountKey(client_id="cid", private_key_pem="pem")
        cache = MemoryTokenCache()
        tm = TokenManager(key=key, cache=cache)
        valid = _token(seconds_until_expiry=_EXPIRY_LONG)
        assert tm._needs_refresh(valid) is False
