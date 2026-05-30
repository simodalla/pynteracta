# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'auth' command group and exit-code mapping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import jwt
import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.auth import CachedToken, MemoryTokenCache
from pynteracta.cli import app
from pynteracta.cli._common import (
    EXIT_AUTH,
    EXIT_NOT_FOUND,
    EXIT_PERMISSION,
    EXIT_SERVER,
    EXIT_VALIDATION,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}

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
