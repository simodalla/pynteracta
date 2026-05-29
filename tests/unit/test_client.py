# SPDX-License-Identifier: Apache-2.0
"""Tests for InteractaClient wiring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import respx
from api_helpers import load_payload, mock_json

from pynteracta.auth import load_service_account_key
from pynteracta.client import InteractaClient

_SA_KEY = Path(__file__).resolve().parent.parent / "fixtures" / "sa_key.json"


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
            assert route.calls[0].request.headers.get("authorization") is not None

    def test_context_manager_closes(self) -> None:
        client = InteractaClient("https://api.example.com")
        with client:
            pass
        client.close()
