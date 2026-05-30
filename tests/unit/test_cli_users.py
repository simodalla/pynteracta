# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'users' command group."""

from __future__ import annotations

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}


class TestUsersMe:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        result = runner.invoke(app, ["users", "me"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        result = runner.invoke(app, ["--output", "json", "users", "me"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_yaml_output(self, runner: CliRunner) -> None:
        pytest.importorskip("ruamel.yaml")
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        result = runner.invoke(app, ["--output", "yaml", "users", "me"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "firstName" in result.output or "Maria" in result.output


class TestUsersProfile:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", "core/user-profile/info", load_payload("user_profile_info_response.json"))
        result = runner.invoke(app, ["users", "profile"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", "core/user-profile/info", load_payload("user_profile_info_response.json"))
        result = runner.invoke(app, ["--output", "json", "users", "profile"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


class TestUsersGetForEdit:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "admin/manage/users/1042/edit",
            load_payload("get_user_for_edit_response.json"),
        )
        result = runner.invoke(app, ["users", "get-for-edit", "1042"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "admin/manage/users/1042/edit",
            load_payload("get_user_for_edit_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "users", "get-for-edit", "1042"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_with_web_url(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "admin/manage/users/1042/edit",
            load_payload("get_user_for_edit_response.json"),
        )
        result = runner.invoke(app, ["users", "get-for-edit", "1042", "--web-url"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "web_url" in result.output or "/admin/user/1042/" in result.output

    @respx.mock
    def test_without_web_url(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "admin/manage/users/1042/edit",
            load_payload("get_user_for_edit_response.json"),
        )
        result = runner.invoke(app, ["users", "get-for-edit", "1042"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "/admin/user/1042/" not in result.output


class TestUsersList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", "admin/data/users", load_payload("list_system_users_response.json"))
        result = runner.invoke(app, ["users", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", "admin/data/users", load_payload("list_system_users_response.json"))
        result = runner.invoke(app, ["--output", "json", "users", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot
