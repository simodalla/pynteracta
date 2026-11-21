# SPDX-License-Identifier: Apache-2.0
"""Test del protocollo OAuth di Google: PKCE, consenso, listener, chiamate (spec 10)."""

from __future__ import annotations

import base64
import hashlib
import socket
import urllib.parse
from collections.abc import Iterator

import httpx
import pytest
import respx
from google_fakes import (
    ACCESS_TOKEN,
    AUTH_CODE,
    CLIENT_ID,
    CLIENT_SECRET,
    EMAIL,
    REFRESH_TOKEN,
    FakeBrowser,
    error_response,
    token_response,
    userinfo_response,
)
from structlog.testing import capture_logs

from pynteracta import google_oauth
from pynteracta.exceptions import AuthenticationError, ServerError, TransportError
from pynteracta.transport import HttpTransport

_SHORT = 0.3


def _query(url: str) -> dict[str, list[str]]:
    return urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)


class TestPkce:
    # criterio: 10-C01
    def test_challenge_is_sha256_of_verifier(self) -> None:
        pkce = google_oauth.new_pkce()
        digest = hashlib.sha256(pkce.verifier.encode("ascii")).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        assert pkce.challenge == expected
        assert 43 <= len(pkce.verifier) <= 128  # noqa: PLR2004 (RFC 7636)

    # criterio: 10-C01
    def test_values_change_every_call(self) -> None:
        a, b = google_oauth.new_pkce(), google_oauth.new_pkce()
        assert a.verifier != b.verifier
        assert a.state != b.state

    def test_repr_hides_verifier(self) -> None:
        pkce = google_oauth.new_pkce()
        assert pkce.verifier not in repr(pkce)


class TestBuildAuthUrl:
    # criterio: 10-C01
    def test_parameters(self) -> None:
        url = google_oauth.build_auth_url(
            client_id=CLIENT_ID,
            redirect_uri="http://127.0.0.1:5555",
            challenge="chal",
            state="st",
        )
        assert url.startswith(google_oauth.AUTH_URL + "?")
        q = _query(url)
        assert q["client_id"] == [CLIENT_ID]
        assert q["scope"] == ["email"]
        assert q["response_type"] == ["code"]
        assert q["code_challenge"] == ["chal"]
        assert q["code_challenge_method"] == ["S256"]
        assert q["state"] == ["st"]
        assert q["redirect_uri"] == ["http://127.0.0.1:5555"]
        assert q["access_type"] == ["offline"]
        assert q["prompt"] == ["consent"]


def _auth_url(receiver: google_oauth.LoopbackReceiver, state: str) -> str:
    return google_oauth.build_auth_url(
        client_id=CLIENT_ID, redirect_uri=receiver.redirect_uri, challenge="c", state=state
    )


class TestLoopbackReceiver:
    # criterio: 10-C10
    def test_listens_on_loopback_only(self) -> None:
        with google_oauth.LoopbackReceiver() as receiver:
            host, port = receiver.address
            assert host == "127.0.0.1"
            assert receiver.redirect_uri == f"http://127.0.0.1:{port}"

    # criterio: 10-C01
    def test_returns_code_with_matching_state(self) -> None:
        browser = FakeBrowser()
        with google_oauth.LoopbackReceiver() as receiver:
            browser(_auth_url(receiver, "giusto"))
            assert receiver.wait("giusto", timeout=5) == AUTH_CODE
        browser.join()
        assert browser.pages[0][0] == 200  # noqa: PLR2004

    # criterio: 10-C08
    def test_state_mismatch(self) -> None:
        browser = FakeBrowser(query={"code": AUTH_CODE, "state": "altro"})
        with google_oauth.LoopbackReceiver() as receiver:
            browser(_auth_url(receiver, "giusto"))
            with pytest.raises(AuthenticationError, match="state"):
                receiver.wait("giusto", timeout=5)
        browser.join()

    # criterio: 10-C09
    def test_access_denied(self) -> None:
        browser = FakeBrowser(query={"error": "access_denied", "state": "giusto"})
        with google_oauth.LoopbackReceiver() as receiver:
            browser(_auth_url(receiver, "giusto"))
            with pytest.raises(AuthenticationError, match="access_denied"):
                receiver.wait("giusto", timeout=5)
        browser.join()

    # criterio: 10-C09, 10-C10
    def test_timeout_closes_socket(self) -> None:
        receiver = google_oauth.LoopbackReceiver()
        _, port = receiver.address
        with pytest.raises(AuthenticationError, match="No sign-in response"):
            receiver.wait("giusto", timeout=_SHORT)
        with (
            pytest.raises(ConnectionRefusedError),
            socket.create_connection(("127.0.0.1", port), timeout=1),
        ):
            pass

    # criterio: 10-C10
    def test_request_without_code_is_ignored_with_404(self) -> None:
        browser = FakeBrowser(before=("/favicon.ico",))
        with google_oauth.LoopbackReceiver() as receiver:
            browser(_auth_url(receiver, "giusto"))
            assert receiver.wait("giusto", timeout=5) == AUTH_CODE
        browser.join()
        assert [status for status, _ in browser.pages] == [404, 200]

    # criterio: 10-C10
    def test_second_connection_refused_after_first_response(self) -> None:
        browser = FakeBrowser(after=("/?code=altro&state=giusto",))
        receiver = google_oauth.LoopbackReceiver()
        browser(_auth_url(receiver, "giusto"))
        assert receiver.wait("giusto", timeout=5) == AUTH_CODE
        browser.join()
        assert browser.refused_after == [True]

    # criterio: 10-C36
    @pytest.mark.parametrize(
        ("query", "ok"),
        [
            ({"code": AUTH_CODE, "state": "giusto"}, True),
            ({"code": AUTH_CODE, "state": "sbagliato"}, False),
            ({"error": "access_denied", "state": "giusto"}, False),
        ],
    )
    def test_result_page_has_no_secrets_and_nothing_is_logged(
        self, capfd: pytest.CaptureFixture[str], query: dict[str, str], ok: bool
    ) -> None:
        browser = FakeBrowser(query=query)
        with google_oauth.LoopbackReceiver() as receiver:
            browser(_auth_url(receiver, "giusto"))
            try:
                receiver.wait("giusto", timeout=5)
            except AuthenticationError:
                assert not ok
        browser.join()
        _status, page = browser.pages[-1]
        expected = "Sign-in complete" if ok else "Sign-in failed"
        assert expected in page
        for value in (AUTH_CODE, "giusto", "sbagliato", "access_denied"):
            assert value not in page
        out, err = capfd.readouterr()
        assert out == ""
        assert err == ""


class _RecordingHooks:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def on_request(self, req: object) -> None:
        return

    def on_response(self, resp: object) -> None:
        return

    def on_error(self, exc: BaseException) -> None:
        self.errors.append(exc)


@pytest.fixture
def hooks() -> _RecordingHooks:
    return _RecordingHooks()


@pytest.fixture
def transport(hooks: _RecordingHooks) -> Iterator[HttpTransport]:
    with HttpTransport("https://oauth2.googleapis.com", hooks=hooks) as t:
        yield t


@pytest.fixture
def google_mock() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        yield router


def _form(route: respx.Route) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(route.calls[0].request.content.decode("ascii")))


class TestExchangeCode:
    # criterio: 10-C20
    def test_sends_form_and_returns_tokens(
        self, transport: HttpTransport, google_mock: respx.MockRouter
    ) -> None:
        route = google_mock.post(google_oauth.TOKEN_URL).mock(return_value=token_response())
        tokens = google_oauth.exchange_code(
            transport,
            code=AUTH_CODE,
            verifier="verificatore",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri="http://127.0.0.1:5555",
        )
        assert tokens.access_token == ACCESS_TOKEN
        assert tokens.refresh_token == REFRESH_TOKEN
        assert _form(route) == {
            "grant_type": "authorization_code",
            "code": AUTH_CODE,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": "http://127.0.0.1:5555",
            "code_verifier": "verificatore",
        }
        assert route.call_count == 1
        assert ACCESS_TOKEN not in repr(tokens)
        assert REFRESH_TOKEN not in repr(tokens)

    # criterio: 10-C09
    def test_missing_refresh_token(
        self, transport: HttpTransport, google_mock: respx.MockRouter
    ) -> None:
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        with pytest.raises(AuthenticationError, match="refresh token"):
            google_oauth.exchange_code(
                transport,
                code=AUTH_CODE,
                verifier="v",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri="http://127.0.0.1:1",
            )

    # criterio: 10-C20
    def test_invalid_client(
        self, transport: HttpTransport, google_mock: respx.MockRouter, hooks: _RecordingHooks
    ) -> None:
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=error_response("invalid_client", status=401)
        )
        with pytest.raises(AuthenticationError, match="--replace-client-secret") as info:
            google_oauth.exchange_code(
                transport,
                code=AUTH_CODE,
                verifier="v",
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri="http://127.0.0.1:1",
            )
        assert hooks.errors == [info.value]


class TestRefreshAccessToken:
    # criterio: 10-C20
    def test_sends_refresh_grant(
        self, transport: HttpTransport, google_mock: respx.MockRouter
    ) -> None:
        route = google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        tokens = google_oauth.refresh_access_token(
            transport,
            refresh_token=REFRESH_TOKEN,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        assert tokens.access_token == ACCESS_TOKEN
        assert tokens.refresh_token is None
        assert _form(route) == {
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }

    # criterio: 10-C20, 10-C21
    @pytest.mark.parametrize(
        ("error", "status", "fragment"),
        [
            ("invalid_grant", 400, "auth login --google"),
            ("invalid_client", 401, "--replace-client-secret"),
            ("unsupported_grant_type", 400, "unsupported_grant_type"),
        ],
    )
    def test_oauth_errors(  # noqa: PLR0913, PLR0917
        self,
        transport: HttpTransport,
        google_mock: respx.MockRouter,
        hooks: _RecordingHooks,
        error: str,
        status: int,
        fragment: str,
    ) -> None:
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=error_response(error, status=status, description="Bad Request")
        )
        with capture_logs() as logs, pytest.raises(AuthenticationError) as info:
            google_oauth.refresh_access_token(
                transport, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret="s"
            )
        assert fragment in str(info.value)
        assert error in str(info.value)
        assert info.value.status_code == status
        assert info.value.request_url == google_oauth.TOKEN_URL
        assert info.value.response_body == {"error": error, "error_description": "Bad Request"}
        assert hooks.errors == [info.value]
        events = [e for e in logs if e["event"] == "google.token_error"]
        assert events == [{"event": "google.token_error", "error": error, "log_level": "warning"}]

    # criterio: 10-C21
    def test_server_error_without_body(
        self, transport: HttpTransport, google_mock: respx.MockRouter
    ) -> None:
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=httpx.Response(500, json={"refresh_token": REFRESH_TOKEN})
        )
        with pytest.raises(ServerError) as info:
            google_oauth.refresh_access_token(
                transport, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret="s"
            )
        assert info.value.response_body is None
        assert REFRESH_TOKEN not in str(info.value)

    # criterio: 10-C21
    @pytest.mark.parametrize("status", [200, 400])
    def test_non_json_body(
        self, transport: HttpTransport, google_mock: respx.MockRouter, status: int
    ) -> None:
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=httpx.Response(status, text=f"<html>{REFRESH_TOKEN}</html>")
        )
        with pytest.raises(AuthenticationError, match="Unexpected response") as info:
            google_oauth.refresh_access_token(
                transport, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret="s"
            )
        assert info.value.response_body is None

    # criterio: 10-C21
    @pytest.mark.parametrize(
        "exc", [httpx.ConnectTimeout("timeout"), httpx.ConnectError("refused")]
    )
    def test_network_error_single_request(
        self, transport: HttpTransport, google_mock: respx.MockRouter, exc: Exception
    ) -> None:
        route = google_mock.post(google_oauth.TOKEN_URL).mock(side_effect=exc)
        with pytest.raises(TransportError):
            google_oauth.refresh_access_token(
                transport, refresh_token=REFRESH_TOKEN, client_id=CLIENT_ID, client_secret="s"
            )
        assert route.call_count == 1


class TestFetchEmail:
    def test_bearer_and_email(
        self, transport: HttpTransport, google_mock: respx.MockRouter
    ) -> None:
        route = google_mock.get(google_oauth.USERINFO_URL).mock(return_value=userinfo_response())
        assert google_oauth.fetch_email(transport, ACCESS_TOKEN) == EMAIL
        assert route.calls[0].request.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"

    @pytest.mark.parametrize(
        "response",
        [userinfo_response(None), httpx.Response(401, json={}), httpx.Response(200, text="x")],
    )
    def test_missing_email_is_none(
        self, transport: HttpTransport, google_mock: respx.MockRouter, response: httpx.Response
    ) -> None:
        google_mock.get(google_oauth.USERINFO_URL).mock(return_value=response)
        assert google_oauth.fetch_email(transport, ACCESS_TOKEN) is None


class TestRevoke:
    def test_sends_token(self, transport: HttpTransport, google_mock: respx.MockRouter) -> None:
        route = google_mock.post(google_oauth.REVOKE_URL).mock(return_value=httpx.Response(200))
        google_oauth.revoke(transport, REFRESH_TOKEN)
        assert _form(route) == {"token": REFRESH_TOKEN}

    def test_already_invalid_token_is_success(
        self, transport: HttpTransport, google_mock: respx.MockRouter
    ) -> None:
        google_mock.post(google_oauth.REVOKE_URL).mock(return_value=error_response("invalid_token"))
        google_oauth.revoke(transport, REFRESH_TOKEN)

    def test_server_error(self, transport: HttpTransport, google_mock: respx.MockRouter) -> None:
        google_mock.post(google_oauth.REVOKE_URL).mock(return_value=httpx.Response(503))
        with pytest.raises(ServerError):
            google_oauth.revoke(transport, REFRESH_TOKEN)
