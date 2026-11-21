# SPDX-License-Identifier: Apache-2.0
"""Test della superficie pubblica del login Google: sessione, login, stato, logout (spec 10)."""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Iterator

import httpx
import pytest
import respx
from google_fakes import (
    ACCESS_TOKEN,
    BASE,
    CLIENT_ID,
    CLIENT_SECRET,
    EMAIL,
    LOGIN_AT,
    REFRESH_TOKEN,
    MemoryKeychain,
    error_response,
    save_session,
    token_response,
)

from pynteracta import google_login, google_oauth
from pynteracta.config import Profile
from pynteracta.exceptions import AuthenticationError, TransportError
from pynteracta.keychain import client_secret_entry
from pynteracta.transport import HttpTransport


def _profile(**kwargs: object) -> Profile:
    data: dict[str, object] = {
        "base_url": BASE,
        "auth_method": "google_oauth2",
        "google_client_id": CLIENT_ID,
        "token_cache": "memory",
    }
    data.update(kwargs)
    return Profile.model_validate(data)


@pytest.fixture
def google_transport() -> Iterator[HttpTransport]:
    with HttpTransport("https://oauth2.googleapis.com") as t:
        yield t


@pytest.fixture
def google_mock() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        yield router


def _form(call: respx.models.Call) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(call.request.content.decode("ascii")))


class TestSessionTokenProvider:
    # criterio: 10-C19
    def test_returns_access_token_after_one_call(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
    ) -> None:
        save_session(memory_keychain)
        route = google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        assert provider() == ACCESS_TOKEN
        assert route.call_count == 1
        assert _form(route.calls[0])["refresh_token"] == REFRESH_TOKEN
        assert _form(route.calls[0])["client_secret"] == CLIENT_SECRET

    # criterio: 10-C19
    def test_missing_session_at_construction(
        self, memory_keychain: MemoryKeychain, google_transport: HttpTransport
    ) -> None:
        with pytest.raises(AuthenticationError, match="auth login --google"):
            google_login.session_token_provider(_profile(), "default", google_transport)

    # criterio: 10-C19
    @pytest.mark.parametrize("missing", ["session", "secret"])
    def test_missing_entry_at_call(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
        missing: str,
    ) -> None:
        entry = save_session(memory_keychain)
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        memory_keychain.delete(entry if missing == "session" else client_secret_entry(CLIENT_ID))
        with pytest.raises(AuthenticationError, match="auth login --google"):
            provider()

    # criterio: 10-C19
    def test_invalid_grant_keeps_entry(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
    ) -> None:
        entry = save_session(memory_keychain)
        before = memory_keychain.get(entry)
        google_mock.post(google_oauth.TOKEN_URL).mock(return_value=error_response("invalid_grant"))
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        with pytest.raises(AuthenticationError, match="auth login --google"):
            provider()
        assert memory_keychain.get(entry) == before

    # criterio: 10-C20
    def test_invalid_client(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
    ) -> None:
        save_session(memory_keychain)
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=error_response("invalid_client", status=401)
        )
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        with pytest.raises(AuthenticationError, match="--replace-client-secret"):
            provider()

    # criterio: 10-C21
    @pytest.mark.parametrize(
        "exc", [httpx.ConnectTimeout("timeout"), httpx.ConnectError("refused")]
    )
    def test_network_error_keeps_entry(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
        exc: Exception,
    ) -> None:
        entry = save_session(memory_keychain)
        before = memory_keychain.get(entry)
        route = google_mock.post(google_oauth.TOKEN_URL).mock(side_effect=exc)
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        with pytest.raises(TransportError):
            provider()
        assert route.call_count == 1
        assert memory_keychain.get(entry) == before

    # criterio: 10-C22
    def test_rotated_refresh_token_is_saved(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
    ) -> None:
        entry = save_session(memory_keychain)
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token="1//example-rotated")
        )
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        provider()
        stored = json.loads(memory_keychain.get(entry) or "")
        assert stored == {
            "refresh_token": "1//example-rotated",
            "email": EMAIL,
            "login_at": LOGIN_AT,
        }

    # criterio: 10-C22
    def test_session_is_reread_every_call(
        self,
        memory_keychain: MemoryKeychain,
        google_transport: HttpTransport,
        google_mock: respx.MockRouter,
    ) -> None:
        save_session(memory_keychain)
        route = google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        provider()
        save_session(memory_keychain, refresh_token="1//example-new-login")
        provider()
        assert [_form(c)["refresh_token"] for c in route.calls] == [
            REFRESH_TOKEN,
            "1//example-new-login",
        ]

    def test_repr_has_no_secrets(
        self, memory_keychain: MemoryKeychain, google_transport: HttpTransport
    ) -> None:
        save_session(memory_keychain)
        provider = google_login.session_token_provider(_profile(), "default", google_transport)
        for secret in (REFRESH_TOKEN, CLIENT_SECRET, EMAIL):
            assert secret not in repr(provider)
