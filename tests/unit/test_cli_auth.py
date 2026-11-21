# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'auth' command group and exit-code mapping."""

from __future__ import annotations

import json
import sys
import urllib.parse
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
import respx
import typer
from api_helpers import BASE_URL, load_payload, mock_json
from click.testing import Result
from google_fakes import (
    CLIENT_ID,
    CLIENT_SECRET,
    EMAIL,
    REFRESH_TOKEN,
    FakeBrowser,
    MemoryKeychain,
    error_response,
    save_session,
    token_response,
    userinfo_response,
)
from typer.testing import CliRunner

from pynteracta import google_oauth, keychain
from pynteracta.auth import CachedToken, FileTokenCache, MemoryTokenCache, build_cache_key
from pynteracta.cli import _common as _cli_common
from pynteracta.cli import _write as _cli_write
from pynteracta.cli import app
from pynteracta.cli import auth as cli_auth
from pynteracta.cli._common import (
    EXIT_AUTH,
    EXIT_CONFIG,
    EXIT_NOT_FOUND,
    EXIT_PERMISSION,
    EXIT_SERVER,
    EXIT_TRANSPORT,
    EXIT_VALIDATION,
)
from pynteracta.config import load_config
from pynteracta.keychain import client_secret_entry, session_entry
from pynteracta.urls import build_api_base


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}
_API_BASE = build_api_base("https://api.example.com", "/portal", 2)
_GOOGLE_TOKEN_ENV = "PYNTERACTA_GOOGLE_OAUTH2_TOKEN"
# Google exchange is at /portal/api/core/... (no /external/v2/ prefix).
_GOOGLE_BASE = BASE_URL.rsplit("/external/", 1)[0]
_GOOGLE_EXCHANGE_URL = (
    f"{_GOOGLE_BASE}/core/auth/create-access-token-by-google-oauth2-access-token-credentials"
)

_SA_KEY_PATH = Path(__file__).parent.parent / "fixtures" / "sa_key.json"


def _fake_token() -> str:
    exp = int((datetime.now(tz=UTC) + timedelta(hours=1)).timestamp())
    return jwt.encode({"sub": "svc", "exp": exp}, "secret", algorithm="HS256")


class TestAuthWhoami:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)
        result = runner.invoke(app, ["auth", "whoami"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)
        result = runner.invoke(app, ["--output", "json", "auth", "whoami"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


class TestAuthLogin:
    @respx.mock
    def test_login_writes_config_and_fetches_token(self, runner: CliRunner, tmp_path: Path) -> None:
        token_payload = {"accessToken": _fake_token()}
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)

        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--service-account-key",
                str(_SA_KEY_PATH),
                "--profile",
                "myprofile",
            ],
            env={"PYNTERACTA_BASE_URL": "https://api.example.com"},
        )
        assert result.exit_code == 0, result.output
        assert config_file.exists()
        content = config_file.read_text(encoding="utf-8")
        assert "service_account_key" in content
        assert "myprofile" in content

    @respx.mock
    def test_login_preserves_toml_comments(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "# my config comment\n"
            'current_profile = "default"\n\n'
            "[profiles.default]\n"
            'base_url = "https://api.example.com"\n',
            encoding="utf-8",
        )

        token_payload = {"accessToken": _fake_token()}
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)

        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--service-account-key",
                str(_SA_KEY_PATH),
                "--profile",
                "default",
            ],
            env={"PYNTERACTA_BASE_URL": "https://api.example.com"},
        )
        assert result.exit_code == 0, result.output
        updated = config_file.read_text(encoding="utf-8")
        assert "# my config comment" in updated, "tomlkit should preserve comments"


class TestAuthLoginGoogle:
    @respx.mock
    def test_login_google_persists_method_not_token(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        token_payload = {"accessToken": _fake_token()}
        respx.post(_GOOGLE_EXCHANGE_URL).mock(return_value=httpx.Response(200, json=token_payload))
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)

        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--google",
                "--profile",
                "gprofile",
            ],
            env={
                "PYNTERACTA_BASE_URL": "https://api.example.com",
                "PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "super-secret-google-token",
            },
        )
        assert result.exit_code == 0, result.output
        content = config_file.read_text(encoding="utf-8")
        assert 'auth_method = "google_oauth2"' in content
        assert "super-secret-google-token" not in content, "token must never be persisted"

    @respx.mock
    def test_login_google_token_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        token_payload = {"accessToken": _fake_token()}
        exchange = respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json=token_payload)
        )
        payload = load_payload("current_user_data_response.json")
        mock_json("GET", "core/auth/current-user-data", payload)

        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--google-token",
                "flag-google-token",
            ],
            env={"PYNTERACTA_BASE_URL": "https://api.example.com"},
        )
        assert result.exit_code == 0, result.output
        assert b"flag-google-token" in exchange.calls[0].request.content

    def test_login_mutually_exclusive(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--google",
                "--service-account-key",
                str(_SA_KEY_PATH),
            ],
            env={
                "PYNTERACTA_BASE_URL": "https://api.example.com",
                "PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok",
            },
        )
        assert result.exit_code == EXIT_CONFIG
        assert "mutually exclusive" in result.output

    @respx.mock
    def test_static_login_writes_profile_before_validation(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Caratterizzazione: con token statico il profilo è scritto prima dello scambio."""
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "auth", "login", "--google", "--profile", "g"],
            env={**BASE_ENV, "PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok"},
        )
        assert result.exit_code == EXIT_AUTH
        profile = load_config(config_file).profiles["g"]
        assert profile.auth_method == "google_oauth2"
        assert str(profile.base_url).rstrip("/") == "https://api.example.com"

    @pytest.mark.parametrize("method", ["google", "service_account"])
    @respx.mock
    def test_static_login_without_profile_uses_default_when_current_is_default(
        self, runner: CliRunner, tmp_path: Path, method: str
    ) -> None:
        """Caratterizzazione: senza ``--profile`` e senza profilo corrente scrive in ``default``."""
        token_payload = {"accessToken": _fake_token()}
        respx.post(_GOOGLE_EXCHANGE_URL).mock(return_value=httpx.Response(200, json=token_payload))
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        config_file = tmp_path / "config.toml"
        args = (
            ["--google-token", "tok"]
            if method == "google"
            else ["--service-account-key", str(_SA_KEY_PATH)]
        )
        result = runner.invoke(
            app, ["--config-file", str(config_file), "auth", "login", *args], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert list(load_config(config_file).profiles) == ["default"]

    # criterio: 10-C04
    def test_login_google_missing_token(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        """Senza token statico parte il login integrato, che senza id del client esce 2."""
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "auth", "login", "--google"],
            env={"PYNTERACTA_BASE_URL": "https://api.example.com"},
        )
        assert result.exit_code == EXIT_CONFIG
        assert "google_client_id" in result.output
        assert not config_file.exists()


class TestAuthLoginCurrentProfile:
    """Senza ``--profile`` il login lavora sul profilo corrente di ``config.toml``."""

    _PROD = 'current_profile = "prod"\n\n[profiles.prod]\nbase_url = "https://api.example.com"\n'

    def _mock_tenant(self) -> None:
        token_payload = {"accessToken": _fake_token()}
        respx.post(_GOOGLE_EXCHANGE_URL).mock(return_value=httpx.Response(200, json=token_payload))
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )

    @staticmethod
    def _args(method: str) -> list[str]:
        if method == "google":
            return ["--google-token", "tok"]
        return ["--service-account-key", str(_SA_KEY_PATH)]

    # criterio: 10-C39
    @pytest.mark.parametrize("method", ["google", "service_account"])
    @respx.mock
    def test_without_profile_writes_current_profile(
        self, runner: CliRunner, tmp_path: Path, method: str
    ) -> None:
        self._mock_tenant()
        config_file = tmp_path / "config.toml"
        config_file.write_text(self._PROD, encoding="utf-8")
        result = runner.invoke(
            app, ["--config-file", str(config_file), "auth", "login", *self._args(method)]
        )
        assert result.exit_code == 0, result.output
        assert "'prod'" in result.output
        profiles = load_config(config_file).profiles
        assert list(profiles) == ["prod"]
        expected = "google_oauth2" if method == "google" else "service_account"
        assert profiles["prod"].auth_method == expected

    # criterio: 10-C39
    @pytest.mark.parametrize("method", ["google", "service_account"])
    @respx.mock
    def test_with_profile_writes_that_profile(
        self, runner: CliRunner, tmp_path: Path, method: str
    ) -> None:
        self._mock_tenant()
        config_file = tmp_path / "config.toml"
        config_file.write_text(self._PROD, encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                *self._args(method),
                "--profile",
                "altro",
            ],
        )
        assert result.exit_code == 0, result.output
        profiles = load_config(config_file).profiles
        assert set(profiles) == {"prod", "altro"}
        assert profiles["prod"].auth_method == "service_account"


class TestAuthLoginNewProfile:
    """Il login su un profilo che non esiste deve lasciare un ``config.toml`` valido."""

    def _mock_tenant(self) -> None:
        token_payload = {"accessToken": _fake_token()}
        respx.post(_GOOGLE_EXCHANGE_URL).mock(return_value=httpx.Response(200, json=token_payload))
        mock_json("POST", "core/auth/create-access-token-by-service-account", token_payload)
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )

    @respx.mock
    def test_google_login_on_new_profile_keeps_config_loadable(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        self._mock_tenant()
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "--base-url",
                "https://api.example.com",
                "auth",
                "login",
                "--google",
                "--profile",
                "nuovo",
            ],
            env={"PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok"},
        )
        assert result.exit_code == 0, result.output

        profile = load_config(config_file).profiles["nuovo"]
        assert str(profile.base_url).rstrip("/") == "https://api.example.com"
        assert profile.auth_method == "google_oauth2"

        # Il comando successivo sullo stesso profilo non deve più richiedere --base-url.
        again = runner.invoke(
            app,
            ["--config-file", str(config_file), "--profile", "nuovo", "auth", "whoami"],
            env={"PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok", "PYNTERACTA_TOKEN_CACHE": "memory"},
        )
        assert again.exit_code == 0, again.output

    @respx.mock
    def test_service_account_login_on_new_profile_keeps_config_loadable(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        self._mock_tenant()
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--service-account-key",
                str(_SA_KEY_PATH),
                "--profile",
                "nuovo",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        profile = load_config(config_file).profiles["nuovo"]
        assert str(profile.base_url).rstrip("/") == "https://api.example.com"

    @respx.mock
    def test_login_on_new_profile_persists_non_default_base_path(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        token_payload = {"accessToken": _fake_token()}
        respx.post(
            "https://api.example.com/altro/api/core/auth/"
            "create-access-token-by-google-oauth2-access-token-credentials"
        ).mock(return_value=httpx.Response(200, json=token_payload))
        respx.get("https://api.example.com/altro/api/external/v2/core/auth/current-user-data").mock(
            return_value=httpx.Response(200, json=load_payload("current_user_data_response.json"))
        )
        config_file = tmp_path / "config.toml"
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "--base-path",
                "/altro",
                "auth",
                "login",
                "--google",
                "--profile",
                "nuovo",
            ],
            env={**BASE_ENV, "PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok"},
        )
        assert result.exit_code == 0, result.output
        assert load_config(config_file).profiles["nuovo"].base_path == "/altro"

    @respx.mock
    def test_login_does_not_overwrite_existing_base_url(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        self._mock_tenant()
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[profiles.esistente]\nbase_url = "https://altro.example.com"\n', encoding="utf-8"
        )
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "auth",
                "login",
                "--google",
                "--profile",
                "esistente",
            ],
            env={**BASE_ENV, "PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok"},
        )
        assert result.exit_code == 0, result.output
        profile = load_config(config_file).profiles["esistente"]
        assert str(profile.base_url).rstrip("/") == "https://altro.example.com"


class TestAuthLogout:
    def test_logout_clears_memory_cache(self, runner: CliRunner, tmp_path: Path) -> None:
        cache = MemoryTokenCache()
        fake_token_str = _fake_token()
        cache.save(
            "svc-account@example.com",
            CachedToken(
                access_token=fake_token_str,
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        assert cache.load("svc-account@example.com") is not None
        cache.clear("svc-account@example.com")
        assert cache.load("svc-account@example.com") is None

    def test_logout_command_exits_cleanly(self, runner: CliRunner, tmp_path: Path) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[profiles.default]\nbase_url = "https://api.example.com"\ntoken_cache = "memory"\n',
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "auth", "logout"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0

    def test_logout_clears_the_file_the_managers_write(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Regression for v0.9.3: logout must derive the same tenant-scoped key.

        If the two derivations drift apart, ``auth logout`` reports success while the token file
        stays on disk — the worst possible failure mode for a command whose whole purpose is
        removing a credential.
        """
        cache_dir = tmp_path / "tokens"
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[profiles.default]\n"
            'base_url = "https://api.example.com"\n'
            'base_path = "/portal"\n'
            f'token_cache_dir = "{cache_dir}"\n',
            encoding="utf-8",
        )
        api_base = build_api_base("https://api.example.com", "/portal", 2)
        key_id = "default"
        cache = FileTokenCache(cache_dir, api_base=api_base)
        cache.save(
            build_cache_key(api_base, key_id),
            CachedToken(
                access_token="tok",
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        written = list(cache_dir.glob("*.token.json"))
        assert len(written) == 1, "precondition: exactly one cache file exists"

        result = runner.invoke(
            app, ["--config-file", str(config_file), "auth", "logout"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert not written[0].exists(), "logout reported success but left the token file on disk"

    def test_logout_unresolvable_profile_exits_1(self, runner: CliRunner, tmp_path: Path) -> None:
        """Caratterizzazione: senza indirizzo del tenant il logout esce con ``1``."""
        result = runner.invoke(
            app, ["--config-file", str(tmp_path / "missing.toml"), "auth", "logout"]
        )
        assert result.exit_code == 1
        assert "Cannot resolve profile" in result.output

    def test_logout_google_profile_clears_profile_key(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Caratterizzazione: profilo Google → voce con indirizzo dell'API e nome del profilo."""
        cache_dir = tmp_path / "tokens"
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[profiles.default]\n"
            'base_url = "https://api.example.com"\n'
            'auth_method = "google_oauth2"\n'
            f'token_cache_dir = "{cache_dir}"\n',
            encoding="utf-8",
        )
        api_base = build_api_base("https://api.example.com", "/portal", 2)
        cache = FileTokenCache(cache_dir, api_base=api_base)
        key = build_cache_key(api_base, "default")
        cache.save(
            key,
            CachedToken(
                access_token="tok",
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        result = runner.invoke(app, ["--config-file", str(config_file), "auth", "logout"])
        assert result.exit_code == 0
        assert cache.load(key) is None

    def _google_config(self, tmp_path: Path) -> tuple[Path, Path]:
        cache_dir = tmp_path / "tokens"
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[profiles.default]\n"
            'base_url = "https://api.example.com"\n'
            'auth_method = "google_oauth2"\n'
            f'token_cache_dir = "{cache_dir}"\n',
            encoding="utf-8",
        )
        return config_file, cache_dir

    # criterio: 10-C41
    @respx.mock
    def test_logout_google_removes_client_cache_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        config_file, cache_dir = self._google_config(tmp_path)
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _fake_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        whoami = runner.invoke(
            app,
            ["--config-file", str(config_file), "auth", "whoami"],
            env={"PYNTERACTA_GOOGLE_OAUTH2_TOKEN": "tok"},
        )
        assert whoami.exit_code == 0, whoami.output
        assert len(list(cache_dir.glob("*.token.json"))) == 1, "precondizione: cache scritta"

        result = runner.invoke(app, ["--config-file", str(config_file), "auth", "logout"])
        assert result.exit_code == 0
        assert list(cache_dir.glob("*.token.json")) == []

    # criterio: 10-C41
    def test_logout_google_removes_legacy_cache_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        config_file, cache_dir = self._google_config(tmp_path)
        legacy_base = "https://api.example.com/portal/api"
        cache = FileTokenCache(
            cache_dir, api_base=build_api_base(BASE_ENV["PYNTERACTA_BASE_URL"], "/portal", 2)
        )
        cache.save(
            build_cache_key(legacy_base, "default"),
            CachedToken(
                access_token="tok",
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        result = runner.invoke(app, ["--config-file", str(config_file), "auth", "logout"])
        assert result.exit_code == 0
        assert list(cache_dir.glob("*.token.json")) == []


def _google_config_file(tmp_path: Path, name: str = "default") -> Path:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        f'current_profile = "{name}"\n\n[profiles.{name}]\n'
        'base_url = "https://api.example.com"\nauth_method = "google_oauth2"\n'
        f'google_client_id = "{CLIENT_ID}"\ntoken_cache = "memory"\n',
        encoding="utf-8",
    )
    return config_file


class TestGoogleSessionCommands:
    """Un comando qualunque usa la sessione salvata, senza variabili d'ambiente."""

    # criterio: 10-C14
    @respx.mock
    def test_whoami_with_session(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        token_route = respx.post(google_oauth.TOKEN_URL).mock(
            return_value=token_response(refresh_token=None)
        )
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _fake_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        result = runner.invoke(
            app, ["--config-file", str(_google_config_file(tmp_path)), "auth", "whoami"]
        )
        assert result.exit_code == 0, result.output
        assert token_route.call_count == 1

    # criterio: 10-C18
    def test_whoami_without_session_exits_3(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        result = runner.invoke(
            app, ["--config-file", str(_google_config_file(tmp_path)), "auth", "whoami"]
        )
        assert result.exit_code == EXIT_AUTH
        assert "auth login --google" in result.output

    # criterio: 10-C19
    @respx.mock
    def test_invalid_grant_exits_3(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        respx.post(google_oauth.TOKEN_URL).mock(return_value=error_response("invalid_grant"))
        result = runner.invoke(
            app, ["--config-file", str(_google_config_file(tmp_path)), "auth", "whoami"]
        )
        assert result.exit_code == EXIT_AUTH

    # criterio: 10-C21
    @respx.mock
    def test_network_error_exits_7(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        route = respx.post(google_oauth.TOKEN_URL).mock(side_effect=httpx.ConnectError("x"))
        result = runner.invoke(
            app, ["--config-file", str(_google_config_file(tmp_path)), "auth", "whoami"]
        )
        assert result.exit_code == EXIT_TRANSPORT
        assert route.call_count == 1


class TestExitCodes:
    """Verify that InteractaError subclasses map to the correct exit codes."""

    @respx.mock
    def test_auth_error_gives_exit_3(self, runner: CliRunner) -> None:
        base = "https://api.example.com/portal/api/external/v2"
        respx.get(f"{base}/core/auth/current-user-data").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )
        result = runner.invoke(app, ["auth", "whoami"], env=BASE_ENV)
        assert result.exit_code == EXIT_AUTH

    @respx.mock
    def test_permission_error_gives_exit_4(self, runner: CliRunner) -> None:
        base = "https://api.example.com/portal/api/external/v2"
        respx.get(f"{base}/admin/manage/users/999/edit").mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )
        result = runner.invoke(app, ["users", "get-for-edit", "999"], env=BASE_ENV)
        assert result.exit_code == EXIT_PERMISSION

    @respx.mock
    def test_not_found_gives_exit_5(self, runner: CliRunner) -> None:
        base = "https://api.example.com/portal/api/external/v2"
        respx.get(f"{base}/admin/manage/users/404/edit").mock(
            return_value=httpx.Response(404, json={"error": "Not Found"})
        )
        result = runner.invoke(app, ["users", "get-for-edit", "404"], env=BASE_ENV)
        assert result.exit_code == EXIT_NOT_FOUND

    @respx.mock
    def test_validation_error_gives_exit_6(self, runner: CliRunner) -> None:
        base = "https://api.example.com/portal/api/external/v2"
        respx.post(f"{base}/admin/data/users").mock(
            return_value=httpx.Response(400, json={"error": "Bad Request"})
        )
        result = runner.invoke(app, ["users", "list"], env=BASE_ENV)
        assert result.exit_code == EXIT_VALIDATION

    @respx.mock
    def test_server_error_gives_exit_8(self, runner: CliRunner) -> None:
        base = "https://api.example.com/portal/api/external/v2"
        respx.get(f"{base}/core/auth/current-user-data").mock(
            return_value=httpx.Response(500, json={"error": "Server Error"})
        )
        result = runner.invoke(app, ["auth", "whoami"], env=BASE_ENV)
        assert result.exit_code == EXIT_SERVER


class TestGlobalFlagPrecedence:
    """CLI flag overrides env which overrides file config."""

    @respx.mock
    def test_flag_overrides_env(self, runner: CliRunner, tmp_path: Path) -> None:
        """--base-url flag takes precedence over PYNTERACTA_BASE_URL env var."""
        v2 = "portal/api/external/v2"
        flag_url = f"https://flag.example.com/{v2}/core/auth/current-user-data"
        env_url = f"https://env.example.com/{v2}/core/auth/current-user-data"

        payload = load_payload("current_user_data_response.json")
        respx.get(flag_url).mock(return_value=httpx.Response(200, json=payload))
        respx.get(env_url).mock(return_value=httpx.Response(200, json=payload))

        result = runner.invoke(
            app,
            ["--base-url", "https://flag.example.com", "auth", "whoami"],
            env={"PYNTERACTA_BASE_URL": "https://env.example.com"},
        )
        assert result.exit_code == 0
        assert respx.routes[0].call_count == 1


# ---------------------------------------------------------------------------
# auth login --google dal browser (spec 10)
# ---------------------------------------------------------------------------

_INTEGRATED_FLAGS = [
    ["--google-client-id", CLIENT_ID],
    ["--client-secret-stdin"],
    ["--replace-client-secret"],
    ["--no-browser"],
    ["--login-timeout", "10"],
]


def _browser_config(
    tmp_path: Path,
    *,
    name: str = "default",
    client_id: str | None = CLIENT_ID,
    extra: str = "",
) -> Path:
    config_file = tmp_path / "config.toml"
    lines = [f'current_profile = "{name}"', "", f"[profiles.{name}]"]
    lines.append('base_url = "https://api.example.com"')
    if client_id is not None:
        lines.append(f'google_client_id = "{client_id}"')
    lines.append(f'token_cache_dir = "{tmp_path / "tokens"}"')
    config_file.write_text("\n".join(lines) + "\n" + extra, encoding="utf-8")
    return config_file


def _mock_browser_login(
    *,
    token: httpx.Response | None = None,
    exchange_status: int = 200,
    exchange_token: str | None = None,
) -> dict[str, respx.Route]:
    payload = load_payload("current_user_data_response.json")
    return {
        "token": respx.post(google_oauth.TOKEN_URL).mock(return_value=token or token_response()),
        "userinfo": respx.get(google_oauth.USERINFO_URL).mock(return_value=userinfo_response()),
        "exchange": respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(
                exchange_status, json={"accessToken": exchange_token or _fake_token()}
            )
        ),
        "me": mock_json("GET", "core/auth/current-user-data", payload),
    }


@pytest.fixture
def fake_browser(monkeypatch: pytest.MonkeyPatch) -> FakeBrowser:
    fake = FakeBrowser()
    monkeypatch.setattr(webbrowser, "open", fake)
    return fake


@pytest.fixture
def no_prompt(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Registra le richieste del secret; da terminale non interattivo per default."""
    asked: list[str] = []

    def _prompt(text: str, **_kwargs: object) -> str:
        asked.append(text)
        return "GOCSPX-example-prompted"

    monkeypatch.setattr(_cli_write.typer, "prompt", _prompt)
    monkeypatch.setattr(_cli_common, "_stdin_is_interactive", lambda: False)
    return asked


def _snapshot(config_file: Path, kc: MemoryKeychain) -> tuple[bytes | None, dict[str, str]]:
    return (config_file.read_bytes() if config_file.exists() else None, dict(kc.entries))


def _login(runner: CliRunner, config_file: Path, *args: str, stdin: str | None = None) -> Result:
    return runner.invoke(
        app,
        ["--config-file", str(config_file), "auth", "login", "--google", *args],
        input=stdin,
    )


@pytest.mark.usefixtures("no_prompt")
class TestAuthLoginGoogleBrowser:
    # criterio: 10-C01, 10-C03
    @respx.mock
    def test_full_login(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        _mock_browser_login()
        config_file = _browser_config(tmp_path)
        result = _login(runner, config_file, "--client-secret-stdin", stdin=CLIENT_SECRET + "\n")
        fake_browser.join()
        assert result.exit_code == 0, result.output
        assert "✓ Authenticated as: Maria Rossi" in result.output
        assert "✓ Google session saved for profile 'default'" in result.output
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(fake_browser.urls[0]).query)
        assert query["client_id"] == [CLIENT_ID]
        assert query["scope"] == ["email"]
        assert query["code_challenge_method"] == ["S256"]
        assert query["state"][0]
        assert query["redirect_uri"][0].startswith("http://127.0.0.1:")
        profile = load_config(config_file).profiles["default"]
        assert profile.auth_method == "google_oauth2"
        assert profile.google_client_id == CLIENT_ID
        session = json.loads(memory_keychain.entries[session_entry(_API_BASE, "default")])
        assert set(session) == {"refresh_token", "email", "login_at"}
        assert memory_keychain.entries[client_secret_entry(CLIENT_ID)] == CLIENT_SECRET
        assert CLIENT_SECRET not in result.output

    # criterio: 10-C02
    @respx.mock
    def test_browser_failure_prints_url(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakeBrowser(opens=False)
        monkeypatch.setattr(webbrowser, "open", fake)
        _mock_browser_login()
        save_session(memory_keychain, "nessuno")  # solo il secret serve
        result = _login(runner, _browser_config(tmp_path))
        fake.join()
        assert result.exit_code == 0, result.output
        assert "Open this URL to sign in:" in result.output
        assert fake.urls[0] in result.output

    # criterio: 10-C02
    @respx.mock
    def test_no_browser_prints_url_only(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _mock_browser_login()
        memory_keychain.set(client_secret_entry(CLIENT_ID), CLIENT_SECRET)
        visitor = FakeBrowser()
        original = cli_auth._show_auth_url

        def _show(url: str) -> None:
            original(url)
            visitor.start(url)

        monkeypatch.setattr(cli_auth, "_show_auth_url", _show)
        result = _login(runner, _browser_config(tmp_path), "--no-browser")
        visitor.join()
        assert result.exit_code == 0, result.output
        assert not fake_browser.called
        assert "Open this URL to sign in:" in result.output

    # criterio: 10-C04
    @respx.mock
    def test_missing_client_id(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        result = _login(runner, _browser_config(tmp_path, client_id=None))
        assert result.exit_code == EXIT_CONFIG
        assert "google_client_id" in result.output
        assert not fake_browser.called
        assert respx.calls.call_count == 0

    # criterio: 10-C04, 10-C03
    @respx.mock
    def test_client_id_flag_is_saved(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        _mock_browser_login()
        config_file = _browser_config(tmp_path, client_id=None)
        result = _login(
            runner,
            config_file,
            "--google-client-id",
            CLIENT_ID,
            "--client-secret-stdin",
            stdin=CLIENT_SECRET,
        )
        fake_browser.join()
        assert result.exit_code == 0, result.output
        assert load_config(config_file).profiles["default"].google_client_id == CLIENT_ID

    # criterio: 10-C05
    def test_missing_keyring(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        fake_browser: FakeBrowser,
    ) -> None:
        monkeypatch.setitem(sys.modules, "keyring", None)
        result = _login(runner, _browser_config(tmp_path))
        assert result.exit_code == EXIT_CONFIG
        assert "pynteracta[google]" in result.output
        assert not fake_browser.called

    # criterio: 10-C06
    def test_rejected_keychain_writes_nothing(
        self, runner: CliRunner, tmp_path: Path, fake_browser: FakeBrowser
    ) -> None:
        config_file = _browser_config(tmp_path)
        before = sorted(p.name for p in tmp_path.rglob("*"))
        result = _login(runner, config_file)
        assert result.exit_code == EXIT_CONFIG
        assert "static Google token" in result.output
        assert sorted(p.name for p in tmp_path.rglob("*")) == before
        assert not fake_browser.called

    # criterio: 10-C07
    @respx.mock
    def test_interactive_prompt_without_confirmation(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calls: list[dict[str, object]] = []

        def _prompt(text: str, **kwargs: object) -> str:
            calls.append({"text": text, **kwargs})
            return CLIENT_SECRET

        monkeypatch.setattr(_cli_write.typer, "prompt", _prompt)
        monkeypatch.setattr(_cli_common, "_stdin_is_interactive", lambda: True)
        _mock_browser_login()
        result = _login(runner, _browser_config(tmp_path))
        fake_browser.join()
        assert result.exit_code == 0, result.output
        assert calls == [
            {
                "text": "Google OAuth client secret",
                "hide_input": True,
                "confirmation_prompt": False,
            }
        ]

    # criterio: 10-C07
    def test_non_interactive_without_flag_exits_2(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        result = _login(runner, _browser_config(tmp_path))
        assert result.exit_code == EXIT_CONFIG
        assert "--client-secret-stdin" in result.output
        assert not fake_browser.called

    # criterio: 10-C07
    def test_no_option_takes_the_secret_as_value(self) -> None:
        command = typer.main.get_command(app)
        login_cmd = command.commands["auth"].commands["login"]  # type: ignore[attr-defined]
        for param in login_cmd.params:
            if "secret" in (param.name or ""):
                assert param.is_flag, f"{param.name} must not accept a value"

    # criterio: 10-C08
    @respx.mock
    def test_state_mismatch(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = FakeBrowser(query={"code": "4/x", "state": "forged"})
        monkeypatch.setattr(webbrowser, "open", fake)
        routes = _mock_browser_login()
        config_file = _browser_config(tmp_path)
        memory_keychain.set(client_secret_entry(CLIENT_ID), CLIENT_SECRET)
        before = _snapshot(config_file, memory_keychain)
        result = _login(runner, config_file)
        fake.join()
        assert result.exit_code == EXIT_AUTH
        assert routes["token"].call_count == 0
        assert _snapshot(config_file, memory_keychain) == before

    # criterio: 10-C09
    @pytest.mark.parametrize("case", ["access_denied", "timeout", "no_refresh_token"])
    @respx.mock
    def test_failures_change_nothing(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        monkeypatch: pytest.MonkeyPatch,
        case: str,
    ) -> None:
        fake = FakeBrowser(
            query={"error": "access_denied"} if case == "access_denied" else None,
            follow=case != "timeout",
        )
        monkeypatch.setattr(webbrowser, "open", fake)
        _mock_browser_login(
            token=token_response(refresh_token=None) if case == "no_refresh_token" else None
        )
        config_file = _browser_config(tmp_path)
        before = _snapshot(config_file, memory_keychain)
        result = _login(
            runner,
            config_file,
            "--client-secret-stdin",
            "--login-timeout",
            "0.5",
            stdin=CLIENT_SECRET,
        )
        fake.join()
        assert result.exit_code == EXIT_AUTH, result.output
        assert _snapshot(config_file, memory_keychain) == before

    # criterio: 10-C11
    @respx.mock
    def test_account_not_linked(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        _mock_browser_login(exchange_status=401)
        config_file = _browser_config(tmp_path)
        before = _snapshot(config_file, memory_keychain)
        result = _login(runner, config_file, "--client-secret-stdin", stdin=CLIENT_SECRET)
        fake_browser.join()
        assert result.exit_code == EXIT_AUTH
        assert "not linked to an Interacta user" in result.output
        assert _snapshot(config_file, memory_keychain) == before
        assert client_secret_entry(CLIENT_ID) not in memory_keychain.entries

    # criterio: 10-C12
    @pytest.mark.parametrize("source", ["flag", "env"])
    @respx.mock
    def test_static_token_skips_browser_and_keychain(
        self,
        runner: CliRunner,
        tmp_path: Path,
        fake_browser: FakeBrowser,
        monkeypatch: pytest.MonkeyPatch,
        source: str,
    ) -> None:
        def _boom() -> None:
            raise AssertionError("open_keychain must not be called")

        monkeypatch.setattr(keychain, "open_keychain", _boom)
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _fake_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        args = ["--google-token", "static"] if source == "flag" else []
        env = {_GOOGLE_TOKEN_ENV: "static"} if source == "env" else {}
        result = runner.invoke(
            app,
            ["--config-file", str(_browser_config(tmp_path)), "auth", "login", "--google", *args],
            env=env,
        )
        assert result.exit_code == 0, result.output
        assert "token not persisted" in result.output
        assert not fake_browser.called

    # criterio: 10-C13
    @pytest.mark.parametrize("flag", _INTEGRATED_FLAGS, ids=lambda f: f[0])
    @pytest.mark.parametrize("source", ["flag", "env"])
    @respx.mock
    def test_integrated_flag_with_static_token(  # noqa: PLR0913, PLR0917
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
        flag: list[str],
        source: str,
    ) -> None:
        config_file = _browser_config(tmp_path)
        before = _snapshot(config_file, memory_keychain)
        args = ["--google-token", "static"] if source == "flag" else []
        env = {_GOOGLE_TOKEN_ENV: "static"} if source == "env" else {}
        result = runner.invoke(
            app,
            ["--config-file", str(config_file), "auth", "login", "--google", *flag, *args],
            env=env,
        )
        assert result.exit_code == EXIT_CONFIG
        assert flag[0] in result.output
        assert "static Google token" in result.output
        if source == "env":
            assert _GOOGLE_TOKEN_ENV in result.output
        assert respx.calls.call_count == 0
        assert not fake_browser.called
        assert _snapshot(config_file, memory_keychain) == before

    # criterio: 10-C23
    @respx.mock
    def test_new_login_replaces_cached_identity(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        config_file = _browser_config(tmp_path, extra='auth_method = "google_oauth2"\n')
        save_session(memory_keychain, refresh_token="1//example-old-account")
        cache = FileTokenCache(tmp_path / "tokens", api_base=_API_BASE)
        key = build_cache_key(_API_BASE, "default")
        cache.save(
            key,
            CachedToken(
                access_token="old-identity",
                expires_at=datetime.now(tz=UTC) + timedelta(hours=1),
                obtained_at=datetime.now(tz=UTC),
            ),
        )
        new_token = _fake_token()
        routes = _mock_browser_login(exchange_token=new_token)
        result = _login(runner, config_file)
        fake_browser.join()
        assert result.exit_code == 0, result.output
        assert cache.load(key) is None
        routes["token"].mock(return_value=token_response(refresh_token=None))
        again = runner.invoke(app, ["--config-file", str(config_file), "auth", "whoami"])
        assert again.exit_code == 0, again.output
        assert routes["me"].calls[-1].request.headers["Authorization"] == f"Bearer {new_token}"

    # criterio: 10-C30
    @pytest.mark.parametrize("how", ["stdin", "prompt"])
    @respx.mock
    def test_replace_secret_saved_on_success(  # noqa: PLR0913, PLR0917
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
        monkeypatch: pytest.MonkeyPatch,
        how: str,
    ) -> None:
        memory_keychain.set(client_secret_entry(CLIENT_ID), "GOCSPX-example-A")
        routes = _mock_browser_login()
        if how == "stdin":
            args, stdin = ["--client-secret-stdin"], "GOCSPX-example-B\n"
        else:
            monkeypatch.setattr(_cli_common, "_stdin_is_interactive", lambda: True)
            monkeypatch.setattr(_cli_write.typer, "prompt", lambda *_a, **_k: "GOCSPX-example-B")
            args, stdin = ["--replace-client-secret"], None
        result = _login(runner, _browser_config(tmp_path), *args, stdin=stdin)
        fake_browser.join()
        assert result.exit_code == 0, result.output
        form = dict(urllib.parse.parse_qsl(routes["token"].calls[0].request.content.decode()))
        assert form["client_secret"] == "GOCSPX-example-B"
        assert memory_keychain.get(client_secret_entry(CLIENT_ID)) == "GOCSPX-example-B"

    # criterio: 10-C30
    @respx.mock
    def test_replace_secret_kept_on_failure(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        memory_keychain.set(client_secret_entry(CLIENT_ID), "GOCSPX-example-A")
        respx.post(google_oauth.TOKEN_URL).mock(
            return_value=error_response("invalid_client", status=401)
        )
        result = _login(
            runner, _browser_config(tmp_path), "--client-secret-stdin", stdin="GOCSPX-example-B"
        )
        fake_browser.join()
        assert result.exit_code == EXIT_AUTH
        assert "--replace-client-secret" in result.output
        assert memory_keychain.get(client_secret_entry(CLIENT_ID)) == "GOCSPX-example-A"

    # criterio: 10-C31
    @respx.mock
    def test_second_profile_does_not_ask_secret(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
        no_prompt: list[str],
    ) -> None:
        _mock_browser_login()
        config_file = _browser_config(
            tmp_path,
            extra=(
                '\n[profiles.cert]\nbase_url = "https://api.example.com"\n'
                f'google_client_id = "{CLIENT_ID}"\n'
            ),
        )
        first = _login(runner, config_file, "--client-secret-stdin", stdin=CLIENT_SECRET)
        fake_browser.join()
        assert first.exit_code == 0, first.output
        second = runner.invoke(
            app,
            ["--config-file", str(config_file), "auth", "login", "--google", "--profile", "cert"],
        )
        fake_browser.join()
        assert second.exit_code == 0, second.output
        assert no_prompt == []
        assert session_entry(_API_BASE, "cert") in memory_keychain.entries

    # criterio: 10-C39
    @respx.mock
    def test_current_profile_is_the_default(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        fake_browser: FakeBrowser,
    ) -> None:
        _mock_browser_login()
        config_file = _browser_config(tmp_path, name="prod")
        result = _login(runner, config_file, "--client-secret-stdin", stdin=CLIENT_SECRET)
        fake_browser.join()
        assert result.exit_code == 0, result.output
        assert list(load_config(config_file).profiles) == ["prod"]
        assert session_entry(_API_BASE, "prod") in memory_keychain.entries
        assert "profile 'prod'" in result.output


# ---------------------------------------------------------------------------
# auth status (spec 10)
# ---------------------------------------------------------------------------


class TestAuthStatus:
    def _status(self, runner: CliRunner, config_file: Path, *args: str) -> Result:
        return runner.invoke(app, ["--config-file", str(config_file), *args, "auth", "status"])

    # criterio: 10-C24
    @respx.mock
    def test_table_with_session(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        snapshot: object,
    ) -> None:
        save_session(memory_keychain)
        result = self._status(runner, _google_config_file(tmp_path))
        assert result.exit_code == 0, result.output
        assert result.output == snapshot
        assert respx.calls.call_count == 0
        assert REFRESH_TOKEN not in result.output
        assert CLIENT_SECRET not in result.output

    # criterio: 10-C24
    @respx.mock
    def test_json_with_session(
        self,
        runner: CliRunner,
        tmp_path: Path,
        memory_keychain: MemoryKeychain,
        snapshot: object,
    ) -> None:
        save_session(memory_keychain)
        result = self._status(runner, _google_config_file(tmp_path), "--output", "json")
        assert result.exit_code == 0, result.output
        assert result.output == snapshot
        data = json.loads(result.output)
        assert data["google_session"] is True
        assert data["google_account"] == EMAIL
        assert data["client_secret_saved"] is True
        assert respx.calls.call_count == 0

    # criterio: 10-C24
    def test_without_session_exits_0(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        result = self._status(runner, _google_config_file(tmp_path), "--output", "json")
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["google_session"] is False
        assert data["google_account"] is None

    # criterio: 10-C24
    def test_session_without_email_reports_unknown_account(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain, email=None)
        result = self._status(runner, _google_config_file(tmp_path), "--output", "json")
        assert json.loads(result.output)["google_account"] == "unknown"

    # criterio: 10-C25
    def test_service_account_profile(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[profiles.default]\nbase_url = "https://api.example.com"\n', encoding="utf-8"
        )
        result = self._status(runner, config_file, "--output", "json")
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["auth_method"] == "service_account"
        assert data["google_session"] is False

    # criterio: 10-C25
    @pytest.mark.parametrize("case", ["keyring_missing", "backend_rejected"])
    def test_unreadable_keychain_exits_0_with_reason(
        self,
        runner: CliRunner,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        case: str,
    ) -> None:
        if case == "keyring_missing":
            monkeypatch.setitem(sys.modules, "keyring", None)
        result = self._status(runner, _google_config_file(tmp_path), "--output", "json")
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        expected = "pynteracta[google]" if case == "keyring_missing" else "static Google token"
        assert expected in data["keychain"]
        assert data["google_session"] == "unreadable"
        assert data["client_secret_saved"] == "unreadable"

    # criterio: 10-C24
    def test_fields_and_export(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        config_file = _google_config_file(tmp_path)
        fields = runner.invoke(
            app,
            [
                "--config-file",
                str(config_file),
                "--output",
                "json",
                "auth",
                "status",
                "--fields",
                "profile,google_session",
            ],
        )
        assert fields.exit_code == 0, fields.output
        assert json.loads(fields.output) == {"profile": "default", "google_session": True}
        target = tmp_path / "status.json"
        export = runner.invoke(
            app, ["--config-file", str(config_file), "auth", "status", "--export", str(target)]
        )
        assert export.exit_code == 0, export.output
        exported = json.loads(target.read_text(encoding="utf-8"))
        assert exported["google_account"] == EMAIL
        assert REFRESH_TOKEN not in target.read_text(encoding="utf-8")

    # criterio: 10-C26
    @respx.mock
    def test_check_with_valid_session(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        respx.post(google_oauth.TOKEN_URL).mock(return_value=token_response(refresh_token=None))
        respx.post(_GOOGLE_EXCHANGE_URL).mock(
            return_value=httpx.Response(200, json={"accessToken": _fake_token()})
        )
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        result = runner.invoke(
            app,
            [
                "--config-file",
                str(_google_config_file(tmp_path)),
                "--output",
                "json",
                "auth",
                "status",
                "--check",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data["check"] == "ok"
        assert data["authenticated_as"] == "Maria Rossi"

    # criterio: 10-C26
    @respx.mock
    def test_check_with_rejected_session_exits_3(
        self, runner: CliRunner, tmp_path: Path, memory_keychain: MemoryKeychain
    ) -> None:
        save_session(memory_keychain)
        respx.post(google_oauth.TOKEN_URL).mock(return_value=error_response("invalid_grant"))
        result = runner.invoke(
            app,
            ["--config-file", str(_google_config_file(tmp_path)), "auth", "status", "--check"],
        )
        assert result.exit_code == EXIT_AUTH
