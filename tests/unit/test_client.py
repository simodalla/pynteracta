# SPDX-License-Identifier: Apache-2.0
"""Tests for InteractaClient wiring."""

from __future__ import annotations

import sys
import urllib.parse
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
import respx
from api_helpers import BASE_URL, load_payload, mock_json
from google_fakes import (
    ACCESS_TOKEN,
    CLIENT_ID,
    REFRESH_TOKEN,
    MemoryKeychain,
    error_response,
    save_session,
    token_response,
)

from pynteracta import google_oauth, keychain
from pynteracta.api.catalogs import CatalogsAPI
from pynteracta.api.communities import CommunitiesAPI
from pynteracta.auth import GoogleOAuth2TokenManager, build_cache_key, load_service_account_key
from pynteracta.client import InteractaClient
from pynteracta.config import Profile
from pynteracta.exceptions import AuthenticationError

_SA_KEY = Path(__file__).resolve().parent.parent / "fixtures" / "sa_key.json"
# Google exchange is at /portal/api/core/... (no /external/v2/ prefix).
# BASE_URL is "https://api.example.com/portal/api/external/v2"; strip the external part.
_GOOGLE_BASE = BASE_URL.rsplit("/external/", 1)[0]
_GOOGLE_EXCHANGE_URL = (
    f"{_GOOGLE_BASE}/core/auth/create-access-token-by-google-oauth2-access-token-credentials"
)


def _access_token() -> str:
    exp = int((datetime.now(tz=UTC) + timedelta(hours=1)).timestamp())
    return jwt.encode({"sub": "user", "exp": exp}, "secret", algorithm="HS256")


class TestInteractaClient:
    @respx.mock
    def test_without_credentials(self) -> None:
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)
        with InteractaClient("https://api.example.com") as client:
            result = client.users.me()
            assert result.user_data_typed is not None
            assert client.web_urls.post(1) == "https://api.example.com/portal/post/1"

    @respx.mock
    def test_with_credentials_wires_token(self) -> None:
        token_payload = {"accessToken": _access_token()}
        user_payload = load_payload("current_user_data_response.json")
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        route = mock_json("GET", "core/auth/current-user-data", user_payload)
        key = load_service_account_key(_SA_KEY)
        with InteractaClient("https://api.example.com", credentials=key) as client:
            assert client._token_manager is not None
            client.users.me()
            auth = route.calls[0].request.headers.get("authorization")
            # Regression: the API silently returns 200 with an empty body for a raw
            # (non-"Bearer") token, so the default scheme must prefix "Bearer ".
            assert auth is not None
            assert auth.startswith("Bearer ")

    @respx.mock
    def test_default_auth_scheme_is_bearer(self) -> None:
        """Regression for the missing-Bearer auth bug: omitting auth_scheme must send Bearer."""
        token_payload = {"accessToken": _access_token()}
        user_payload = load_payload("current_user_data_response.json")
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        route = mock_json("GET", "core/auth/current-user-data", user_payload)
        key = load_service_account_key(_SA_KEY)
        with InteractaClient("https://api.example.com", credentials=key) as client:
            client.users.me()
        assert route.calls[0].request.headers["authorization"].startswith("Bearer ")

    @respx.mock
    def test_explicit_none_auth_scheme_sends_raw_token(self) -> None:
        """Passing auth_scheme=None explicitly still disables the prefix (raw token)."""
        token_payload = {"accessToken": _access_token()}
        user_payload = load_payload("current_user_data_response.json")
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        route = mock_json("GET", "core/auth/current-user-data", user_payload)
        key = load_service_account_key(_SA_KEY)
        with InteractaClient(
            "https://api.example.com", credentials=key, auth_scheme=None
        ) as client:
            client.users.me()
        assert not route.calls[0].request.headers["authorization"].startswith("Bearer ")

    def test_context_manager_closes(self) -> None:
        client = InteractaClient("https://api.example.com")
        with client:
            pass
        client.close()


class TestInteractaClientGoogleOAuth2:
    @respx.mock
    def test_with_google_token_wires_manager(self) -> None:
        token_payload = {"accessToken": _access_token()}
        user_payload = load_payload("current_user_data_response.json")
        exchange = respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json=token_payload)
        )
        me_route = mock_json("GET", "core/auth/current-user-data", user_payload)
        with InteractaClient("https://api.example.com", google_token="g-tok") as client:
            assert isinstance(client._token_manager, GoogleOAuth2TokenManager)
            client.users.me()
        assert exchange.called
        body = exchange.calls[0].request.content
        assert b"g-tok" in body
        assert me_route.calls[0].request.headers.get("authorization") is not None

    @respx.mock
    def test_with_google_token_provider(self) -> None:
        token_payload = {"accessToken": _access_token()}
        user_payload = load_payload("current_user_data_response.json")
        exchange = respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json=token_payload)
        )
        mock_json("GET", "core/auth/current-user-data", user_payload)
        with InteractaClient(
            "https://api.example.com",
            google_token_provider=lambda: "provided-tok",
        ) as client:
            assert isinstance(client._token_manager, GoogleOAuth2TokenManager)
            client.users.me()
        assert b"provided-tok" in exchange.calls[0].request.content

    @respx.mock
    def test_explicit_token_wins_over_profile_token(self) -> None:
        """Caratterizzazione: ``google_token`` esplicito vince sul token del profilo (ambiente)."""
        exchange = respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _access_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        profile = Profile(
            base_url="https://api.example.com",  # type: ignore[arg-type]
            auth_method="google_oauth2",
            google_oauth2_token="env-tok",
            token_cache="memory",
        )
        with InteractaClient(profile=profile, google_token="explicit-tok") as client:
            client.users.me()
        body = exchange.calls[0].request.content
        assert b"explicit-tok" in body
        assert b"env-tok" not in body

    def test_explicit_provider_with_profile_token(self) -> None:
        """Caratterizzazione: provider esplicito più token del profilo → errore."""
        profile = Profile(
            base_url="https://api.example.com",  # type: ignore[arg-type]
            auth_method="google_oauth2",
            google_oauth2_token="env-tok",
            token_cache="memory",
        )
        with pytest.raises(AuthenticationError, match="exactly one"):
            InteractaClient(profile=profile, google_token_provider=lambda: "p")

    # criterio: 10-C40
    def test_current_profile_names_the_cache_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'current_profile = "prod"\n\n[profiles.prod]\n'
            'base_url = "https://api.example.com"\nauth_method = "google_oauth2"\n'
            'token_cache = "memory"\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("PYNTERACTA_CONFIG_FILE", str(config_file))
        monkeypatch.setenv("PYNTERACTA_GOOGLE_OAUTH2_TOKEN", "g-tok")
        with InteractaClient() as client:
            manager = client._token_manager
            assert isinstance(manager, GoogleOAuth2TokenManager)
            assert manager._profile == build_cache_key(BASE_URL, "prod")

    # criterio: 10-C18
    def test_google_auth_method_without_token_raises(self, memory_keychain: MemoryKeychain) -> None:
        profile = Profile(
            base_url="https://api.example.com",  # type: ignore[arg-type]
            auth_method="google_oauth2",
            google_client_id=CLIENT_ID,
        )
        with pytest.raises(AuthenticationError, match="auth login --google") as info:
            InteractaClient(profile=profile)
        assert "pynteracta[google]" not in str(info.value)

    # criterio: 10-C18
    def test_google_without_keyring_names_the_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "keyring", None)
        profile = Profile(
            base_url="https://api.example.com",  # type: ignore[arg-type]
            auth_method="google_oauth2",
        )
        with pytest.raises(AuthenticationError) as info:
            InteractaClient(profile=profile)
        assert "auth login --google" in str(info.value)
        assert "pynteracta[google]" in str(info.value)

    def test_communities_and_catalogs_wired(self) -> None:
        with InteractaClient("https://api.example.com") as client:
            assert isinstance(client.communities, CommunitiesAPI)
            assert isinstance(client.catalogs, CatalogsAPI)

    def test_audit_kwargs_propagate_to_api_transport(self) -> None:
        with InteractaClient("https://api.example.com", audit=True, audit_bodies=True) as client:
            assert client._api_transport._audit is True
            assert client._api_transport._audit_bodies is True

    def test_audit_disabled_by_default(self) -> None:
        with InteractaClient("https://api.example.com") as client:
            assert client._api_transport._audit is False
            assert client._api_transport._audit_bodies is False

    def test_audit_from_profile(self) -> None:
        profile = Profile(
            base_url="https://api.example.com",  # type: ignore[arg-type]
            audit_log=True,
            audit_log_bodies=True,
        )
        with InteractaClient(profile=profile) as client:
            assert client._api_transport._audit is True
            assert client._api_transport._audit_bodies is True


def _google_profile_file(
    tmp_path: Path, *, current: str = "default", name: str = "default"
) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f'current_profile = "{current}"\n\n[profiles.{name}]\n'
        'base_url = "https://api.example.com"\nauth_method = "google_oauth2"\n'
        f'google_client_id = "{CLIENT_ID}"\ntoken_cache = "memory"\n',
        encoding="utf-8",
    )
    return config_file


def _jwt_expiring_in(seconds: int) -> str:
    exp = int((datetime.now(tz=UTC) + timedelta(seconds=seconds)).timestamp())
    return jwt.encode({"sub": "user", "exp": exp, "n": seconds}, "secret", algorithm="HS256")


@pytest.fixture
def no_browser(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    opened: list[str] = []
    monkeypatch.setattr(webbrowser, "open", lambda url, *a, **k: bool(opened.append(url)))
    return opened


class TestInteractaClientGoogleSession:
    # criterio: 10-C14
    @respx.mock
    def test_session_refresh_then_exchange(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, no_browser: list[str]
    ) -> None:
        save_session(memory_keychain)
        token_route = respx.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        exchange = respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _access_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        with InteractaClient(
            profile_name="default", config_file=_google_profile_file(tmp_path)
        ) as client:
            client.users.me()
        form = dict(urllib.parse.parse_qsl(token_route.calls[0].request.content.decode()))
        assert form["grant_type"] == "refresh_token"
        assert form["refresh_token"] == REFRESH_TOKEN
        assert ACCESS_TOKEN.encode() in exchange.calls[0].request.content
        assert no_browser == []

    # criterio: 10-C15
    @respx.mock
    def test_near_expiry_refreshes_and_uses_new_token(
        self, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        first, second = _jwt_expiring_in(30), _jwt_expiring_in(3600)
        token_route = respx.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            side_effect=[
                httpx.Response(200, json={"accessToken": first}),
                httpx.Response(200, json={"accessToken": second}),
            ]
        )
        me = mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        with InteractaClient(
            profile_name="default", config_file=_google_profile_file(tmp_path)
        ) as client:
            client.users.me()
            client.users.me()
        assert token_route.call_count == 2  # noqa: PLR2004
        assert me.calls[1].request.headers["Authorization"] == f"Bearer {second}"

    # criterio: 10-C16
    @pytest.mark.parametrize("source", ["explicit", "env"])
    @respx.mock
    def test_static_token_wins_over_session(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        monkeypatch: pytest.MonkeyPatch,
        source: str,
    ) -> None:
        save_session(memory_keychain)
        token_route = respx.post(google_oauth.TOKEN_URL).mock(return_value=token_response())
        exchange = respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _access_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        kwargs: dict[str, object] = {}
        if source == "explicit":
            kwargs["google_token"] = "static-tok"
        else:
            monkeypatch.setenv("PYNTERACTA_GOOGLE_OAUTH2_TOKEN", "static-tok")
        with InteractaClient(
            profile_name="default", config_file=_google_profile_file(tmp_path), **kwargs
        ) as client:
            client.users.me()
        assert token_route.call_count == 0
        assert b"static-tok" in exchange.calls[0].request.content

    # criterio: 10-C17
    def test_session_bound_to_tenant_and_profile(
        self, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        config_file = _google_profile_file(tmp_path)
        with pytest.raises(AuthenticationError, match="auth login --google"):
            InteractaClient(
                profile=Profile(
                    base_url="https://altro.example.com",  # type: ignore[arg-type]
                    auth_method="google_oauth2",
                    google_client_id=CLIENT_ID,
                    token_cache="memory",
                ),
                profile_name="default",
            )
        other_dir = tmp_path / "altro"
        other_dir.mkdir()
        other = _google_profile_file(other_dir, name="altro", current="altro")
        assert config_file.exists()
        with pytest.raises(AuthenticationError, match="auth login --google"):
            InteractaClient(profile_name="altro", config_file=other)

    # criterio: 10-C17
    def test_base_url_only_never_opens_keychain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom() -> None:
            raise AssertionError("open_keychain must not be called")

        monkeypatch.setattr(keychain, "open_keychain", _boom)
        with InteractaClient("https://api.example.com") as client:
            assert client._token_manager is None

    # criterio: 10-C40
    @respx.mock
    def test_current_profile_session(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        save_session(memory_keychain, "prod")
        config_file = _google_profile_file(tmp_path, current="prod", name="prod")
        monkeypatch.setenv("PYNTERACTA_CONFIG_FILE", str(config_file))
        respx.post(google_oauth.TOKEN_URL).mock(return_value=token_response(refresh_token=None))
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _access_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        with InteractaClient() as client:
            client.users.me()
            manager = client._token_manager
            assert isinstance(manager, GoogleOAuth2TokenManager)
            assert manager._profile == build_cache_key(BASE_URL, "prod")

    def test_close_closes_google_transport(
        self, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        client = InteractaClient(profile_name="default", config_file=_google_profile_file(tmp_path))
        google_transport = client._google_oauth_transport
        assert google_transport is not None
        client.close()
        assert google_transport._client.is_closed

    # criterio: 10-C19
    @respx.mock
    def test_invalid_grant_on_first_request(
        self, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        respx.post(google_oauth.TOKEN_URL).mock(return_value=error_response("invalid_grant"))
        with (
            InteractaClient(
                profile_name="default", config_file=_google_profile_file(tmp_path)
            ) as client,
            pytest.raises(AuthenticationError, match="auth login --google"),
        ):
            client.users.me()
