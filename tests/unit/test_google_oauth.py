# SPDX-License-Identifier: Apache-2.0
"""Test del protocollo OAuth di Google: PKCE, consenso, listener, chiamate (spec 10)."""

from __future__ import annotations

import base64
import hashlib
import socket
import urllib.parse

import pytest
from google_fakes import AUTH_CODE, CLIENT_ID, FakeBrowser

from pynteracta import google_oauth
from pynteracta.exceptions import AuthenticationError

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
