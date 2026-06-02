# SPDX-License-Identifier: Apache-2.0
"""Tests for InteractaClient wiring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
import respx
from api_helpers import BASE_URL, load_payload, mock_json

from pynteracta.api.catalogs import CatalogsAPI
from pynteracta.api.communities import CommunitiesAPI
from pynteracta.auth import GoogleOAuth2TokenManager, load_service_account_key
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

    def test_google_auth_method_without_token_raises(self) -> None:
        profile = Profile(
            base_url="https://api.example.com",  # type: ignore[arg-type]
            auth_method="google_oauth2",
        )
        with pytest.raises(AuthenticationError, match="no Google access token"):
            InteractaClient(profile=profile)

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
