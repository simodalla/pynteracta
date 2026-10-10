# SPDX-License-Identifier: Apache-2.0
"""Test dei comandi di scrittura ``users create|edit|delete|edit-credentials`` (spec 05)."""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_USER_ID = 42
_CREATED_USER_ID = 1043
_EXIT_CONFIG = 2
BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}
_CREATE_PATH = "admin/manage/users"
_CREATE_URL = f"{BASE_URL}/{_CREATE_PATH}"
_CUSTOM_BLOCK = {"custom": {"username": "ab", "active": True}}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


def _not_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    from pynteracta.cli import _common  # noqa: PLC0415

    monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: False)


def _interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    from pynteracta.cli import _common  # noqa: PLC0415

    monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)


class TestUsersCreate:
    # criterio: 05-C11
    @respx.mock
    def test_flags_and_json_merge_flags_win(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        body = tmp_path / "body.json"
        body.write_text(
            json.dumps({"firstname": "X", "userPreferences": {"defaultLanguageId": "it"}}),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "users",
                "create",
                "--first-name",
                "A",
                "--last-name",
                "B",
                "--contact-email",
                "a@b.it",
                "--username",
                "ab",
                "--generate-password",
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "firstname": "A",
            "lastname": "B",
            "contactEmail": "a@b.it",
            "userPreferences": {"defaultLanguageId": "it"},
            "userCredentialsConfiguration": _CUSTOM_BLOCK,
            "resetUserCustomCredentialsCommand": {"generatePassword": True},
        }
        assert str(_CREATED_USER_ID) in result.output
        assert "Xk7-fake-pw" in result.output

    # criterio: 05-C11
    @respx.mock
    def test_table_output_shows_generated_password(
        self, runner: CliRunner, snapshot: object
    ) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--first-name", "A", "--username", "ab", "--generate-password"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 05-C11
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "users", "create", "--first-name", "A", "--generate-password"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot
        assert json.loads(result.output)["generated_password"] == "Xk7-fake-pw"

    # criterio: 05-C11
    @respx.mock
    def test_json_full_output_has_raw_list(self, runner: CliRunner) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "users", "create", "--generate-password", "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["generatedPassword"] == ["Xk7-fake-pw"]

    # criterio: 05-C11
    @respx.mock
    def test_google_microsoft_and_notify_flags(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            [
                "users",
                "create",
                "--google-account",
                "a@gmail.test",
                "--microsoft-account",
                "a@outlook.test",
                "--force-password-change",
                "--notify-email",
                "x@b.it",
                "--notify-email",
                "y@b.it",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "userCredentialsConfiguration": {
                "google": {"googleAccountId": "a@gmail.test", "enabled": True},
                "microsoft": {"microsoftAccountId": "a@outlook.test", "enabled": True},
            },
            "resetUserCustomCredentialsCommand": {
                "forceCredentialsExpiration": True,
                "emailNotifyRecipients": ["x@b.it", "y@b.it"],
            },
        }

    # criterio: 05-C12
    @respx.mock
    def test_password_stdin_non_interactive(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _not_interactive(monkeypatch)
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--username", "ab", "--password-stdin"],
            env=BASE_ENV,
            input="S3gret!\n",
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "userCredentialsConfiguration": _CUSTOM_BLOCK,
            "resetUserCustomCredentialsCommand": {"password": ["S3gret!"]},
        }
        assert "S3gret!" not in result.output

    # criterio: 05-C12
    @respx.mock
    def test_password_prompt_interactive(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pynteracta.cli import _write  # noqa: PLC0415

        _interactive(monkeypatch)
        calls: list[dict[str, Any]] = []

        def fake_prompt(text: str, **kwargs: Any) -> str:
            calls.append({"text": text, **kwargs})
            return "S3gret!"

        monkeypatch.setattr(_write.typer, "prompt", fake_prompt)
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app, ["users", "create", "--username", "ab", "--password-stdin"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert calls == [{"text": "Password", "hide_input": True, "confirmation_prompt": True}]
        assert _sent_body(route)["resetUserCustomCredentialsCommand"] == {"password": ["S3gret!"]}
        assert "S3gret!" not in result.output

    # criterio: 05-C12
    @respx.mock
    def test_generate_and_stdin_together_exit_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--username", "ab", "--generate-password", "--password-stdin"],
            env=BASE_ENV,
            input="S3gret!\n",
        )
        assert result.exit_code == _EXIT_CONFIG
        assert "mutually exclusive" in result.output
        assert route.call_count == 0

    # criterio: 05-C12
    @respx.mock
    def test_stdin_and_json_dash_exit_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--password-stdin", "--json", "-"],
            env=BASE_ENV,
            input='{"firstname": "A"}',
        )
        assert result.exit_code == _EXIT_CONFIG
        assert "--password-stdin" in result.output
        assert route.call_count == 0

    # criterio: 05-C12
    def test_help_has_no_password_option(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["users", "create", "--help"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "--password-stdin" in result.output
        assert "--generate-password" in result.output
        assert re.search(r"--password(?![-\w])", result.output) is None

    # criterio: 05-C11
    @respx.mock
    def test_json_unknown_key_exits_2(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"nope": 1}), encoding="utf-8")
        result = runner.invoke(app, ["users", "create", "--json", str(body)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "unknown keys" in result.output
        assert route.call_count == 0

    # criterio: 05-C11
    @respx.mock
    def test_server_validation_error_exits_6(self, runner: CliRunner) -> None:
        respx.post(_CREATE_URL).mock(
            return_value=httpx.Response(400, json={"message": "Dati inseriti non validi"})
        )
        result = runner.invoke(app, ["users", "create", "--first-name", "A"], env=BASE_ENV)
        assert result.exit_code == 6  # noqa: PLR2004
