# SPDX-License-Identifier: Apache-2.0
"""Unit tests for authentication and token caching."""

from __future__ import annotations

import base64
import json
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest
import respx
from httpx import Response

from pynteracta.auth import (
    CachedToken,
    FileTokenCache,
    GoogleOAuth2Credentials,
    GoogleOAuth2TokenManager,
    MemoryTokenCache,
    ServiceAccountKey,
    TokenCache,
    TokenManager,
    TokenProvider,
    _decode_token_expiry,
    build_cache_key,
    load_service_account_key,
)
from pynteracta.exceptions import AuthenticationError
from pynteracta.models.facade.auth import GoogleOAuth2AccessTokenResponse
from pynteracta.transport import HttpTransport

_EXPECTED_FILE_MODE = 0o600
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
_SA_KEY_PATH = _FIXTURES / "sa_key.json"
_BASE = "https://api.example.com/portal/api/external/v2"
_AUTH_PATH = "/core/auth/create-access-token-by-service-account"
_AUTH_URL = f"{_BASE}{_AUTH_PATH}"
# Google exchange endpoint is under /portal/api/core/... (no /external/v2/ prefix).
_GOOGLE_BASE = "https://api.example.com/portal/api"


def _mock_transport(base_url: str) -> MagicMock:
    """A mocked transport that still exposes the ``base_url`` the cache key is derived from."""
    transport = MagicMock(spec=HttpTransport)
    transport.base_url = base_url
    return transport


def _google_cache_key(base_url: str = _GOOGLE_BASE) -> str:
    """The tenant-scoped key a GoogleOAuth2TokenManager derives from ``_GOOGLE_CACHE_KEY``."""
    return build_cache_key(base_url, _GOOGLE_CACHE_KEY)


def _sa_cache_key(key: ServiceAccountKey, base_url: str = _BASE) -> str:
    """The tenant-scoped cache key a TokenManager derives for this key (see build_cache_key)."""
    return build_cache_key(base_url, str(key.client_id))


_GOOGLE_AUTH_PATH = "/core/auth/create-access-token-by-google-oauth2-access-token-credentials"
_GOOGLE_AUTH_URL = f"{_GOOGLE_BASE}{_GOOGLE_AUTH_PATH}"
_GOOGLE_CACHE_KEY = "default"
"""The raw cache_key callers pass; the manager namespaces it by tenant."""
_EXPIRY_SHORT = 30
_EXPIRY_LONG = 3600
_FIXTURE_CLIENT_ID = 1001
_FIXTURE_KEY_ID = 42


def _token(*, seconds_until_expiry: float = _EXPIRY_LONG) -> CachedToken:
    now = datetime.now(tz=UTC)
    return CachedToken(
        access_token="tok",
        expires_at=now + timedelta(seconds=seconds_until_expiry),
        obtained_at=now,
    )


def _make_access_jwt(*, exp: int | None = None) -> str:
    if exp is None:
        exp = int((datetime.now(tz=UTC) + timedelta(hours=1)).timestamp())
    return jwt.encode({"sub": "user", "exp": exp}, "secret", algorithm="HS256")


def _jwt_header(token: str) -> dict[str, Any]:
    """Decode JWT header without PyJWT validation (allows numeric kid/iss)."""
    part = token.split(".", maxsplit=1)[0]
    padded = part + "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _jwt_payload(token: str) -> dict[str, Any]:
    """Decode JWT payload without verification."""
    part = token.split(".", maxsplit=2)[1]
    padded = part + "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _load_fixture_key() -> ServiceAccountKey:
    return load_service_account_key(_SA_KEY_PATH)


def _make_token_manager(
    *,
    cache: MemoryTokenCache | FileTokenCache | None = None,
    transport: HttpTransport | None = None,
    key: ServiceAccountKey | None = None,
    clock: MagicMock | None = None,
) -> TokenManager:
    return TokenManager(
        key=key or _load_fixture_key(),
        cache=cache or MemoryTokenCache(),
        transport=transport or _mock_transport(_BASE),
        clock=clock or (lambda: datetime.now(tz=UTC)),
    )


class TestLoadServiceAccountKey:
    def test_loads_fixture(self) -> None:
        key = load_service_account_key(_SA_KEY_PATH)
        assert key.client_id == _FIXTURE_CLIENT_ID
        assert key.private_key_id == _FIXTURE_KEY_ID
        assert "BEGIN PRIVATE KEY" in key.private_key_pem

    def test_wrong_type_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(
            json.dumps(
                {"type": "user_account", "private_key_id": 1, "private_key": "pem", "client_id": 2}
            )
        )
        with pytest.raises(AuthenticationError, match="service_account"):
            load_service_account_key(path)

    def test_missing_type_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"private_key_id": 1, "private_key": "pem", "client_id": 2}))
        with pytest.raises(AuthenticationError, match="service_account"):
            load_service_account_key(path)

    def test_missing_field_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"type": "service_account", "client_id": 1}))
        with pytest.raises(AuthenticationError, match="missing required field"):
            load_service_account_key(path)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not json")
        with pytest.raises(AuthenticationError, match="Invalid JSON"):
            load_service_account_key(path)


class TestServiceAccountKey:
    def test_frozen(self) -> None:
        key = ServiceAccountKey(
            client_id=1,
            private_key_id=2,
            private_key_pem="pem",
        )
        with pytest.raises(AttributeError):
            key.client_id = 99  # type: ignore[misc]


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


class TestFileTokenCache:
    def test_round_trip(self, tmp_path: Path) -> None:
        cache = FileTokenCache(tmp_path)
        t = _token()
        cache.save("dev", t)
        loaded = cache.load("dev")
        assert loaded is not None
        assert loaded.access_token == t.access_token
        assert loaded.expires_at == t.expires_at
        assert loaded.obtained_at == t.obtained_at

    def test_save_creates_mode_0600(self, tmp_path: Path) -> None:
        cache = FileTokenCache(tmp_path)
        cache.save("dev", _token())
        path = tmp_path / "dev.token.json"
        assert path.exists()
        if hasattr(stat, "S_IMODE"):
            assert stat.S_IMODE(path.stat().st_mode) == _EXPECTED_FILE_MODE

    def test_refuses_overly_permissive_file(self, tmp_path: Path) -> None:
        cache = FileTokenCache(tmp_path)
        cache.save("dev", _token())
        path = tmp_path / "dev.token.json"
        path.chmod(0o644)
        with pytest.raises(AuthenticationError, match="Refusing to use token cache file"):
            cache.load("dev")

    def test_corrupt_cache_returns_none(self, tmp_path: Path) -> None:
        cache = FileTokenCache(tmp_path)
        path = tmp_path / "dev.token.json"
        path.write_text("{broken", encoding="utf-8")
        path.chmod(0o600)
        assert cache.load("dev") is None

    def test_clear_removes_file(self, tmp_path: Path) -> None:
        cache = FileTokenCache(tmp_path)
        cache.save("dev", _token())
        cache.clear("dev")
        assert not (tmp_path / "dev.token.json").exists()


class TestDecodeTokenExpiry:
    def test_reads_exp_claim(self) -> None:
        exp = int(datetime(2026, 6, 1, 12, 0, tzinfo=UTC).timestamp())
        token = _make_access_jwt(exp=exp)
        assert _decode_token_expiry(token) == datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    def test_missing_exp_raises(self) -> None:
        token = jwt.encode({"sub": "user"}, "secret", algorithm="HS256")
        with pytest.raises(AuthenticationError, match="missing exp"):
            _decode_token_expiry(token)


class TestTokenManager:
    def test_invalidate_clears_cache(self) -> None:
        cache = MemoryTokenCache()
        key = _load_fixture_key()
        cache.save(_sa_cache_key(key), _token())
        tm = _make_token_manager(cache=cache, key=key)
        tm.invalidate()
        assert cache.load(_sa_cache_key(key)) is None

    def test_needs_refresh_when_near_expiry(self) -> None:
        tm = _make_token_manager()
        near_expiry = _token(seconds_until_expiry=_EXPIRY_SHORT)
        assert tm._needs_refresh(near_expiry) is True

    def test_no_refresh_when_valid(self) -> None:
        tm = _make_token_manager()
        valid = _token(seconds_until_expiry=_EXPIRY_LONG)
        assert tm._needs_refresh(valid) is False

    def test_get_token_uses_cache_when_valid(self) -> None:
        cache = MemoryTokenCache()
        key = _load_fixture_key()
        cached = _token(seconds_until_expiry=_EXPIRY_LONG)
        cache.save(_sa_cache_key(key), cached)
        transport = _mock_transport(_BASE)
        tm = _make_token_manager(cache=cache, transport=transport, key=key)
        assert tm.get_token() == cached.access_token
        transport.request.assert_not_called()

    @respx.mock
    def test_get_token_refreshes_when_near_expiry(self) -> None:
        cache = MemoryTokenCache()
        key = _load_fixture_key()
        stale = _token(seconds_until_expiry=_EXPIRY_SHORT)
        cache.save(_sa_cache_key(key), stale)
        access = _make_access_jwt()
        respx.post(_AUTH_URL).mock(
            return_value=Response(200, json={"accessToken": access}),
        )
        transport = HttpTransport(base_url=_BASE)
        tm = _make_token_manager(cache=cache, transport=transport, key=key)
        assert tm.get_token() == access
        saved = cache.load(_sa_cache_key(key))
        assert saved is not None
        assert saved.access_token == access

    @respx.mock
    def test_fetch_token_posts_assertion(self) -> None:
        access = _make_access_jwt()
        route = respx.post(_AUTH_URL).mock(
            return_value=Response(200, json={"accessToken": access}),
        )
        transport = HttpTransport(base_url=_BASE)
        tm = _make_token_manager(transport=transport)
        token = tm.get_token()
        assert token == access
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert "jwtAssertion" in body
        header = _jwt_header(body["jwtAssertion"])
        assert header["alg"] == "RS512"
        assert header.get("kid") == _FIXTURE_KEY_ID

    def test_assertion_jose_header_alg_rs512_and_numeric_kid(self) -> None:
        tm = _make_token_manager()
        assertion = tm._build_assertion()
        header = _jwt_header(assertion)
        assert header["alg"] == "RS512"
        assert isinstance(header.get("kid"), int)
        assert header["kid"] == _FIXTURE_KEY_ID

    def test_assertion_body_numeric_iss_and_constant_aud(self) -> None:
        tm = _make_token_manager()
        assertion = tm._build_assertion()
        payload = _jwt_payload(assertion)
        assert payload["aud"] == TokenManager.AUDIENCE
        assert payload["iss"] == _FIXTURE_CLIENT_ID
        assert isinstance(payload["iss"], int)
        assert "jti" in payload

    def test_assertion_jti_differs_across_calls(self) -> None:
        tm = _make_token_manager()
        a1 = _jwt_payload(tm._build_assertion())
        a2 = _jwt_payload(tm._build_assertion())
        assert a1["jti"] != a2["jti"]

    def test_assertion_rejects_ttl_exceeding_vendor_cap(self) -> None:
        tm = _make_token_manager()
        original = tm.ASSERTION_TTL_SECONDS
        try:
            tm.__class__.ASSERTION_TTL_SECONDS = 601  # type: ignore[misc]
            with pytest.raises(AuthenticationError, match="vendor cap"):
                tm._build_assertion()
        finally:
            tm.__class__.ASSERTION_TTL_SECONDS = original  # type: ignore[misc]


class TestTokenInvalidationOn401:
    @respx.mock
    def test_transport_calls_invalidator_on_401(self) -> None:
        cache = MemoryTokenCache()
        key = _load_fixture_key()
        cache.save(_sa_cache_key(key), _token())
        invalidated: list[str] = []

        transport = HttpTransport(
            base_url=_BASE,
            token_invalidator=lambda: invalidated.append("yes"),
        )
        respx.get(_BASE + "/core/auth/current-user-data").mock(return_value=Response(401))
        with pytest.raises(AuthenticationError):
            transport.request("GET", "/core/auth/current-user-data")
        assert invalidated == ["yes"]

    @respx.mock
    def test_token_manager_invalidate_wired_to_transport(self) -> None:
        cache = MemoryTokenCache()
        key = _load_fixture_key()
        cache.save(_sa_cache_key(key), _token())
        tm = _make_token_manager(cache=cache, key=key, transport=HttpTransport(base_url=_BASE))
        transport = HttpTransport(
            base_url=_BASE,
            token_invalidator=tm.invalidate,
        )
        respx.get(_BASE + "/core/auth/current-user-data").mock(return_value=Response(401))
        with pytest.raises(AuthenticationError):
            transport.request("GET", "/core/auth/current-user-data")
        assert cache.load(_sa_cache_key(key)) is None


def _make_google_manager(
    *,
    cache: TokenCache | None = None,
    transport: HttpTransport | None = None,
    credentials: GoogleOAuth2Credentials | None = None,
    clock: MagicMock | None = None,
) -> GoogleOAuth2TokenManager:
    return GoogleOAuth2TokenManager(
        credentials or GoogleOAuth2Credentials(token="google-access-token"),
        cache or MemoryTokenCache(),
        transport or _mock_transport(_GOOGLE_BASE),
        cache_key=_GOOGLE_CACHE_KEY,
        clock=clock or (lambda: datetime.now(tz=UTC)),
    )


class TestGoogleOAuth2Credentials:
    def test_requires_exactly_one_source_neither(self) -> None:
        with pytest.raises(AuthenticationError):
            GoogleOAuth2Credentials()

    def test_requires_exactly_one_source_both(self) -> None:
        with pytest.raises(AuthenticationError):
            GoogleOAuth2Credentials(token="x", token_provider=lambda: "y")

    def test_static_token(self) -> None:
        creds = GoogleOAuth2Credentials(token="abc")
        assert creds.get_google_token() == "abc"

    def test_provider_callable(self) -> None:
        calls: list[int] = []

        def provider() -> str:
            calls.append(1)
            return "fresh"

        creds = GoogleOAuth2Credentials(token_provider=provider)
        assert creds.get_google_token() == "fresh"
        assert creds.get_google_token() == "fresh"
        assert calls == [1, 1]  # provider consulted on each call


class TestGoogleOAuth2AccessTokenResponse:
    def test_reads_camelcase(self) -> None:
        resp = GoogleOAuth2AccessTokenResponse.from_dict({"accessToken": "tok"})
        assert resp.access_token == "tok"

    def test_falls_back_to_snake_case(self) -> None:
        resp = GoogleOAuth2AccessTokenResponse.from_dict({"access_token": "tok"})
        assert resp.access_token == "tok"

    def test_missing_returns_none(self) -> None:
        assert GoogleOAuth2AccessTokenResponse.from_dict({}).access_token is None


class TestGoogleOAuth2TokenManager:
    def test_satisfies_token_provider_protocol(self) -> None:
        assert isinstance(_make_google_manager(), TokenProvider)

    @respx.mock
    def test_fetch_posts_google_token_in_body(self) -> None:
        access = _make_access_jwt()
        route = respx.post(_GOOGLE_AUTH_URL).mock(
            return_value=Response(200, json={"accessToken": access}),
        )
        creds = GoogleOAuth2Credentials(token="my-google-token")
        tm = _make_google_manager(credentials=creds, transport=HttpTransport(base_url=_GOOGLE_BASE))
        assert tm.get_token() == access
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body == {"googleOAuth2Token": "my-google-token"}

    @respx.mock
    def test_tolerates_snake_case_response(self) -> None:
        access = _make_access_jwt()
        respx.post(_GOOGLE_AUTH_URL).mock(
            return_value=Response(200, json={"access_token": access}),
        )
        tm = _make_google_manager(transport=HttpTransport(base_url=_GOOGLE_BASE))
        assert tm.get_token() == access

    @respx.mock
    def test_missing_access_token_raises(self) -> None:
        respx.post(_GOOGLE_AUTH_URL).mock(return_value=Response(200, json={}))
        tm = _make_google_manager(transport=HttpTransport(base_url=_GOOGLE_BASE))
        with pytest.raises(AuthenticationError, match="missing accessToken"):
            tm.get_token()

    @respx.mock
    def test_uses_cache_when_valid(self) -> None:
        cache = MemoryTokenCache()
        cached = _token()
        cache.save(_google_cache_key(), cached)
        route = respx.post(_GOOGLE_AUTH_URL).mock(return_value=Response(200, json={}))
        tm = _make_google_manager(cache=cache, transport=HttpTransport(base_url=_GOOGLE_BASE))
        assert tm.get_token() == cached.access_token
        assert not route.called

    @respx.mock
    def test_refreshes_when_near_expiry(self) -> None:
        cache = MemoryTokenCache()
        cache.save(_google_cache_key(), _token(seconds_until_expiry=_EXPIRY_SHORT))
        access = _make_access_jwt()
        respx.post(_GOOGLE_AUTH_URL).mock(
            return_value=Response(200, json={"accessToken": access}),
        )
        tm = _make_google_manager(cache=cache, transport=HttpTransport(base_url=_GOOGLE_BASE))
        assert tm.get_token() == access
        saved = cache.load(_google_cache_key())
        assert saved is not None
        assert saved.access_token == access

    @respx.mock
    def test_provider_token_used_on_fetch(self) -> None:
        access = _make_access_jwt()
        route = respx.post(_GOOGLE_AUTH_URL).mock(
            return_value=Response(200, json={"accessToken": access}),
        )
        creds = GoogleOAuth2Credentials(token_provider=lambda: "provided-token")
        tm = _make_google_manager(credentials=creds, transport=HttpTransport(base_url=_GOOGLE_BASE))
        assert tm.get_token() == access
        body = json.loads(route.calls[0].request.content)
        assert body == {"googleOAuth2Token": "provided-token"}

    def test_invalidate_clears_cache(self) -> None:
        cache = MemoryTokenCache()
        cache.save(_google_cache_key(), _token())
        tm = _make_google_manager(cache=cache)
        tm.invalidate()
        assert cache.load(_google_cache_key()) is None


class TestTenantScopedCacheKey:
    """Finding B (v0.9.3): the cache key must identify the tenant, not just the credential."""

    _OTHER_BASE = "https://other-tenant.example.com/portal/api/external/v2"

    def test_same_client_id_different_tenants_do_not_share_a_key(self) -> None:
        key = _load_fixture_key()
        assert build_cache_key(_BASE, str(key.client_id)) != build_cache_key(
            self._OTHER_BASE, str(key.client_id)
        )

    def test_key_is_stable_for_the_same_tenant(self) -> None:
        assert build_cache_key(_BASE, "1001") == build_cache_key(_BASE, "1001")

    def test_production_token_is_not_served_to_another_tenant(self) -> None:
        """The concrete attack: two profiles, one client_id, one shared cache file."""
        cache = MemoryTokenCache()
        key = _load_fixture_key()
        prod = _make_token_manager(cache=cache, key=key, transport=_mock_transport(_BASE))
        staging = _make_token_manager(
            cache=cache, key=key, transport=_mock_transport(self._OTHER_BASE)
        )
        cache.save(prod._profile, _token(seconds_until_expiry=_EXPIRY_LONG))

        assert cache.load(prod._profile) is not None
        assert cache.load(staging._profile) is None

    def test_google_manager_scopes_its_key_too(self) -> None:
        one = _make_google_manager(transport=_mock_transport(_GOOGLE_BASE))
        other = _make_google_manager(transport=_mock_transport(self._OTHER_BASE))
        assert one._profile != other._profile


class TestFileTokenCacheTenantAssertion:
    """Defence in depth: the stored file records its tenant and is rejected elsewhere."""

    _OTHER_BASE = "https://other-tenant.example.com/portal/api/external/v2"

    def test_save_records_the_api_base(self, tmp_path: Path) -> None:
        cache = FileTokenCache(tmp_path, api_base=_BASE)
        cache.save("k", _token())
        stored = json.loads((tmp_path / "k.token.json").read_text(encoding="utf-8"))
        assert stored["api_base"] == _BASE

    def test_entry_written_for_another_tenant_is_rejected(self, tmp_path: Path) -> None:
        FileTokenCache(tmp_path, api_base=_BASE).save("k", _token())
        assert FileTokenCache(tmp_path, api_base=self._OTHER_BASE).load("k") is None

    def test_legacy_entry_without_api_base_is_accepted(self, tmp_path: Path) -> None:
        """A file written by <= 0.9.2 has no api_base; upgrading must not be a hard break."""
        legacy = _token()
        (tmp_path / "k.token.json").write_text(
            json.dumps(
                {
                    "access_token": legacy.access_token,
                    "expires_at": legacy.expires_at.isoformat(),
                    "obtained_at": legacy.obtained_at.isoformat(),
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "k.token.json").chmod(0o600)
        loaded = FileTokenCache(tmp_path, api_base=_BASE).load("k")
        assert loaded is not None
        assert loaded.access_token == legacy.access_token

    def test_no_api_base_configured_means_no_checking(self, tmp_path: Path) -> None:
        FileTokenCache(tmp_path, api_base=_BASE).save("k", _token())
        assert FileTokenCache(tmp_path).load("k") is not None
