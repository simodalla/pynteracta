# SPDX-License-Identifier: Apache-2.0
"""Tests for AuthAPI."""

from __future__ import annotations

import json

import respx
from api_helpers import FAKE_JWT, load_payload, make_transport, mock_json

from pynteracta.api.auth import AuthAPI
from pynteracta.models.facade.auth import CreateAccessTokenByServiceAccountRequestDTO


class TestAuthAPI:
    @respx.mock
    def test_current_user_data(self) -> None:
        payload = load_payload("current_user_data_response.json")
        route = mock_json("GET", "core/auth/current-user-data", payload)
        api = AuthAPI(make_transport())
        result = api.current_user_data()
        assert route.called
        assert result.has_google_credentials is False
        typed = result.user_data_typed
        assert typed is not None
        assert typed.firstName == "Maria"

    @respx.mock
    def test_create_access_token_raw_no_auth_header(self) -> None:
        payload = load_payload("create_access_token_response.json")
        route = mock_json(
            "POST",
            "core/auth/create-access-token-by-service-account",
            payload,
        )
        unauth = make_transport(token_provider=None)
        authed = make_transport()
        api = AuthAPI(authed, unauthenticated_transport=unauth)
        req = CreateAccessTokenByServiceAccountRequestDTO(jwtAssertion="assertion.jwt.token")
        result = api.create_access_token_raw(req)
        assert result.access_token == payload["accessToken"]
        sent = route.calls[0].request
        assert sent.headers.get("authorization") is None
        body = json.loads(sent.content)
        assert body["jwtAssertion"] == "assertion.jwt.token"

    @respx.mock
    def test_current_user_data_sends_auth_header(self) -> None:
        payload = load_payload("current_user_data_response.json")
        route = mock_json("GET", "core/auth/current-user-data", payload)
        api = AuthAPI(make_transport())
        api.current_user_data()
        assert route.calls[0].request.headers["authorization"] == f"Bearer {FAKE_JWT}"
