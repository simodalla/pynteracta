# SPDX-License-Identifier: Apache-2.0
"""Test della superficie pubblica del login Google: sessione, login, stato, logout (spec 10)."""

from __future__ import annotations

import json
import sys
import urllib.parse
import webbrowser
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
import respx
from api_helpers import load_payload
from google_fakes import (
    ACCESS_TOKEN,
    API_BASE,
    BASE,
    CLIENT_ID,
    CLIENT_SECRET,
    EMAIL,
    LOGIN_AT,
    REFRESH_TOKEN,
    FakeBrowser,
    MemoryKeychain,
    error_response,
    save_session,
    token_response,
    userinfo_response,
)
from structlog.testing import capture_logs

from pynteracta import google_login, google_oauth
from pynteracta.auth import CachedToken, FileTokenCache, build_cache_key
from pynteracta.config import Profile, load_config
from pynteracta.exceptions import AuthenticationError, ConfigurationError, TransportError
from pynteracta.keychain import client_secret_entry, session_entry
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


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------

EXCHANGE_URL = (
    f"{BASE}/portal/api/core/auth/create-access-token-by-google-oauth2-access-token-credentials"
)
ME_URL = f"{API_BASE}/core/auth/current-user-data"


def interacta_token(seconds: int = 3600) -> str:
    exp = int((datetime.now(tz=UTC) + timedelta(seconds=seconds)).timestamp())
    return jwt.encode({"sub": "u", "exp": exp}, "test-secret-key-0123456789abcdef", "HS256")


def write_config(
    tmp_path: Path,
    *,
    name: str = "default",
    client_id: str | None = CLIENT_ID,
    extra: str = "",
) -> Path:
    config_file = tmp_path / "config.toml"
    lines = [f'current_profile = "{name}"', "", f"[profiles.{name}]", f'base_url = "{BASE}"']
    if client_id is not None:
        lines.append(f'google_client_id = "{client_id}"')
    lines.append(f'token_cache_dir = "{tmp_path / "tokens"}"')
    config_file.write_text("\n".join(lines) + "\n" + extra, encoding="utf-8")
    return config_file


def mock_login_flow(
    router: respx.MockRouter,
    *,
    token: httpx.Response | None = None,
    userinfo: httpx.Response | None = None,
    exchange_status: int = 200,
) -> dict[str, respx.Route]:
    """Rotte di Google e di Interacta per un login completo."""
    return {
        "token": router.post(google_oauth.TOKEN_URL).mock(return_value=token or token_response()),
        "userinfo": router.get(google_oauth.USERINFO_URL).mock(
            return_value=userinfo or userinfo_response()
        ),
        "exchange": router.post(EXCHANGE_URL).mock(
            return_value=httpx.Response(exchange_status, json={"accessToken": interacta_token()})
        ),
        "me": router.get(ME_URL).mock(
            return_value=httpx.Response(200, json=load_payload("current_user_data_response.json"))
        ),
    }


@pytest.fixture
def browser(monkeypatch: pytest.MonkeyPatch) -> FakeBrowser:
    fake = FakeBrowser()
    monkeypatch.setattr(webbrowser, "open", fake)
    return fake


def _state(config_file: Path, kc: MemoryKeychain) -> tuple[bytes | None, dict[str, str]]:
    return (config_file.read_bytes() if config_file.exists() else None, dict(kc.entries))


class TestLogin:
    # criterio: 10-C32, 10-C03
    @pytest.mark.usefixtures("fresh_loggers")
    def test_full_login_with_secret_parameter(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        routes = mock_login_flow(google_mock)
        config_file = write_config(tmp_path, client_id=None)
        # I log vanno su capture_logs: structlog non configurato stamperebbe su stdout, e qui si
        # verifica che login() di suo non scriva nulla.
        with capture_logs():
            result = google_login.login(
                config_file=config_file, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
            )
        browser.join()
        assert result.profile_name == "default"
        assert result.base_url == BASE
        assert result.email == EMAIL
        assert result.user_name == "Maria Rossi"
        assert EMAIL not in repr(result)
        session = json.loads(memory_keychain.entries[session_entry(API_BASE, "default")])
        assert session["refresh_token"] == REFRESH_TOKEN
        assert session["email"] == EMAIL
        assert datetime.fromisoformat(session["login_at"]).tzinfo is not None
        assert memory_keychain.entries[client_secret_entry(CLIENT_ID)] == CLIENT_SECRET
        profile = load_config(config_file).profiles["default"]
        assert profile.auth_method == "google_oauth2"
        assert profile.google_client_id == CLIENT_ID
        assert str(profile.base_url).rstrip("/") == BASE
        token_form = dict(urllib.parse.parse_qsl(routes["token"].calls[0].request.content.decode()))
        assert token_form["client_secret"] == CLIENT_SECRET
        assert ACCESS_TOKEN.encode() in routes["exchange"].calls[0].request.content
        out, err = capsys.readouterr()
        assert (out, err) == ("", "")

    # criterio: 10-C02
    def test_on_auth_url_when_browser_fails(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        monkeypatch: pytest.MonkeyPatch,
        google_mock: respx.MockRouter,
    ) -> None:
        fake = FakeBrowser(opens=False)
        monkeypatch.setattr(webbrowser, "open", fake)
        mock_login_flow(google_mock)
        printed: list[str] = []
        google_login.login(
            config_file=write_config(tmp_path),
            client_secret=CLIENT_SECRET,
            on_auth_url=printed.append,
        )
        fake.join()
        assert printed == fake.urls

    # criterio: 10-C02
    def test_no_browser_uses_on_auth_url_only(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        mock_login_flow(google_mock)
        visitor = FakeBrowser()
        google_login.login(
            config_file=write_config(tmp_path),
            client_secret=CLIENT_SECRET,
            open_browser=False,
            on_auth_url=visitor,
        )
        visitor.join()
        assert not browser.called
        assert len(visitor.urls) == 1

    # criterio: 10-C04
    def test_missing_client_id(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        with pytest.raises(ConfigurationError, match="google_client_id"):
            google_login.login(config_file=write_config(tmp_path, client_id=None))
        assert not browser.called
        assert google_mock.calls.call_count == 0

    # criterio: 10-C04
    def test_missing_secret(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        with pytest.raises(ConfigurationError, match="client secret"):
            google_login.login(config_file=write_config(tmp_path))
        assert not browser.called
        assert google_mock.calls.call_count == 0

    # criterio: 10-C09, 10-C11
    @pytest.mark.parametrize("case", ["access_denied", "timeout", "no_refresh_token", "not_linked"])
    def test_failures_leave_everything_unchanged(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        monkeypatch: pytest.MonkeyPatch,
        google_mock: respx.MockRouter,
        case: str,
    ) -> None:
        config_file = write_config(tmp_path)
        memory_keychain.set(client_secret_entry(CLIENT_ID), "GOCSPX-example-old")
        before = _state(config_file, memory_keychain)
        fake = FakeBrowser(
            query={"error": "access_denied", "state": "x"} if case == "access_denied" else None,
            follow=case != "timeout",
        )
        monkeypatch.setattr(webbrowser, "open", fake)
        mock_login_flow(
            google_mock,
            token=token_response(refresh_token=None) if case == "no_refresh_token" else None,
            exchange_status=401 if case == "not_linked" else 200,
        )
        with pytest.raises(AuthenticationError) as info:
            google_login.login(config_file=config_file, client_secret=CLIENT_SECRET, timeout=0.5)
        fake.join()
        if case == "not_linked":
            assert "not linked to an Interacta user" in str(info.value)
            assert EMAIL not in str(info.value)
        assert _state(config_file, memory_keychain) == before

    # criterio: 10-C30
    def test_new_secret_replaces_old_only_on_success(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        memory_keychain.set(client_secret_entry(CLIENT_ID), "GOCSPX-example-A")
        routes = mock_login_flow(google_mock)
        google_login.login(config_file=write_config(tmp_path), client_secret="GOCSPX-example-B")
        browser.join()
        form = dict(urllib.parse.parse_qsl(routes["token"].calls[0].request.content.decode()))
        assert form["client_secret"] == "GOCSPX-example-B"
        assert memory_keychain.get(client_secret_entry(CLIENT_ID)) == "GOCSPX-example-B"

    # criterio: 10-C30
    def test_new_secret_not_saved_when_login_fails(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        memory_keychain.set(client_secret_entry(CLIENT_ID), "GOCSPX-example-A")
        google_mock.post(google_oauth.TOKEN_URL).mock(
            return_value=error_response("invalid_client", status=401)
        )
        with pytest.raises(AuthenticationError, match="--replace-client-secret"):
            google_login.login(config_file=write_config(tmp_path), client_secret="GOCSPX-example-B")
        browser.join()
        assert memory_keychain.get(client_secret_entry(CLIENT_ID)) == "GOCSPX-example-A"

    # criterio: 10-C30
    def test_replace_without_secret_is_configuration_error(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, browser: FakeBrowser
    ) -> None:
        memory_keychain.set(client_secret_entry(CLIENT_ID), "GOCSPX-example-A")
        with pytest.raises(ConfigurationError, match="client secret"):
            google_login.login(config_file=write_config(tmp_path), replace_client_secret=True)
        assert not browser.called

    # criterio: 10-C31
    def test_second_profile_reuses_saved_secret(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        mock_login_flow(google_mock)
        config_file = write_config(
            tmp_path,
            extra=f'\n[profiles.cert]\nbase_url = "{BASE}"\ngoogle_client_id = "{CLIENT_ID}"\n',
        )
        google_login.login(config_file=config_file, client_secret=CLIENT_SECRET)
        browser.join()
        result = google_login.login("cert", config_file=config_file)
        browser.join()
        assert result.profile_name == "cert"
        assert session_entry(API_BASE, "cert") in memory_keychain.entries

    # criterio: 10-C23
    def test_success_clears_cached_interacta_token(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        mock_login_flow(google_mock)
        config_file = write_config(tmp_path)
        cache = FileTokenCache(tmp_path / "tokens", api_base=API_BASE)
        key = build_cache_key(API_BASE, "default")
        cache.save(
            key,
            CachedToken(
                access_token="old-identity",
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        google_login.login(config_file=config_file, client_secret=CLIENT_SECRET)
        browser.join()
        assert cache.load(key) is None

    # criterio: 10-C03
    def test_userinfo_without_email(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
    ) -> None:
        mock_login_flow(google_mock, userinfo=userinfo_response(None))
        result = google_login.login(config_file=write_config(tmp_path), client_secret=CLIENT_SECRET)
        browser.join()
        assert result.email is None
        session = json.loads(memory_keychain.entries[session_entry(API_BASE, "default")])
        assert session["email"] is None

    def test_profile_write_failure_restores_keychain(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_file = write_config(tmp_path)
        old_entry = save_session(memory_keychain, refresh_token="1//example-old", secret="old")
        before = dict(memory_keychain.entries)
        mock_login_flow(google_mock)

        def _fail(*_a: object, **_k: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(google_login, "write_profile_fields", _fail)
        with pytest.raises(OSError, match="disk full"):
            google_login.login(config_file=config_file, client_secret=CLIENT_SECRET)
        browser.join()
        assert memory_keychain.entries == before
        assert old_entry in memory_keychain.entries

    def test_profile_write_failure_removes_new_entries(
        self,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        browser: FakeBrowser,
        google_mock: respx.MockRouter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_login_flow(google_mock)

        def _fail(*_a: object, **_k: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(google_login, "write_profile_fields", _fail)
        with pytest.raises(OSError, match="disk full"):
            google_login.login(config_file=write_config(tmp_path), client_secret=CLIENT_SECRET)
        browser.join()
        assert memory_keychain.entries == {}


# ---------------------------------------------------------------------------
# status() e logout()
# ---------------------------------------------------------------------------


def _google_config(tmp_path: Path, extra: str = "") -> Path:
    return write_config(tmp_path, extra='auth_method = "google_oauth2"\n' + extra)


class TestStatus:
    # criterio: 10-C24, 10-C32
    def test_with_session(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, google_mock: respx.MockRouter
    ) -> None:
        save_session(memory_keychain)
        st = google_login.status(config_file=_google_config(tmp_path))
        assert st.profile == "default"
        assert st.base_url == BASE
        assert st.auth_method == "google_oauth2"
        assert st.google_client_id == CLIENT_ID
        assert st.keychain == "available"
        assert st.google_session is True
        assert st.google_account == EMAIL
        assert st.google_login_at == LOGIN_AT
        assert st.client_secret_saved is True
        assert google_mock.calls.call_count == 0
        for secret in (REFRESH_TOKEN, CLIENT_SECRET, EMAIL):
            assert secret not in repr(st)

    # criterio: 10-C24
    def test_without_session(self, tmp_path: Path, memory_keychain: MemoryKeychain) -> None:
        st = google_login.status(config_file=_google_config(tmp_path))
        assert st.google_session is False
        assert st.google_account is None
        assert st.google_login_at is None
        assert st.client_secret_saved is False

    # criterio: 10-C25
    def test_service_account_profile(self, tmp_path: Path, memory_keychain: MemoryKeychain) -> None:
        st = google_login.status(config_file=write_config(tmp_path, client_id=None))
        assert st.auth_method == "service_account"
        assert st.google_client_id is None
        assert st.google_session is False
        assert st.client_secret_saved is False

    # criterio: 10-C25
    def test_keyring_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "keyring", None)
        st = google_login.status(config_file=_google_config(tmp_path))
        assert "pynteracta[google]" in st.keychain
        assert st.google_session is None
        assert st.client_secret_saved is None

    # criterio: 10-C25
    def test_backend_rejected(self, tmp_path: Path) -> None:
        # Il fixture automatico _no_system_keychain dà il backend "fail".
        st = google_login.status(config_file=_google_config(tmp_path))
        assert "static Google token" in st.keychain
        assert st.google_session is None


class TestLogout:
    # criterio: 10-C27, 10-C32
    def test_removes_session_and_cache_only_of_this_profile(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, google_mock: respx.MockRouter
    ) -> None:
        config_file = _google_config(tmp_path)
        mine = save_session(memory_keychain)
        other = save_session(memory_keychain, "cert")
        cache = FileTokenCache(tmp_path / "tokens", api_base=API_BASE)
        key = build_cache_key(API_BASE, "default")
        cache.save(
            key,
            CachedToken(
                access_token="t",
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        result = google_login.logout(config_file=config_file)
        assert result.session_removed is True
        assert result.client_secret_removed is False
        assert result.revoked is False
        assert result.keychain_error is None
        assert mine not in memory_keychain.entries
        assert other in memory_keychain.entries
        assert client_secret_entry(CLIENT_ID) in memory_keychain.entries
        assert cache.load(key) is None
        assert google_mock.calls.call_count == 0

    # criterio: 10-C27
    def test_without_session(self, tmp_path: Path, memory_keychain: MemoryKeychain) -> None:
        result = google_login.logout(config_file=_google_config(tmp_path))
        assert result.session_removed is False

    # criterio: 10-C28
    def test_forget_client_secret(self, tmp_path: Path, memory_keychain: MemoryKeychain) -> None:
        save_session(memory_keychain)
        result = google_login.logout(
            config_file=_google_config(tmp_path), forget_client_secret=True
        )
        assert result.client_secret_removed is True
        assert memory_keychain.entries == {}

    # criterio: 10-C29
    def test_revoke_then_delete(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, google_mock: respx.MockRouter
    ) -> None:
        entry = save_session(memory_keychain)
        route = google_mock.post(google_oauth.REVOKE_URL).mock(return_value=httpx.Response(200))
        result = google_login.logout(config_file=_google_config(tmp_path), revoke=True)
        assert result.revoked is True
        assert _form(route.calls[0]) == {"token": REFRESH_TOKEN}
        assert entry not in memory_keychain.entries

    # criterio: 10-C29
    def test_revoke_failure_still_deletes(
        self, tmp_path: Path, memory_keychain: MemoryKeychain, google_mock: respx.MockRouter
    ) -> None:
        entry = save_session(memory_keychain)
        google_mock.post(google_oauth.REVOKE_URL).mock(side_effect=httpx.ConnectError("x"))
        with pytest.raises(TransportError):
            google_login.logout(config_file=_google_config(tmp_path), revoke=True)
        assert entry not in memory_keychain.entries

    # criterio: 10-C25, 10-C27
    def test_without_keychain_clears_cache_and_reports(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sys.modules, "keyring", None)
        result = google_login.logout(config_file=_google_config(tmp_path))
        assert result.cache_cleared is True
        assert result.session_removed is False
        assert result.keychain_error is not None
        assert "pynteracta[google]" in result.keychain_error
