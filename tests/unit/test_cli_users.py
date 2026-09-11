# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: PLR2004
"""CLI tests for the 'users' command group."""

from __future__ import annotations

import json
from typing import ClassVar

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

_EPOCH_2025_01_01 = 1735689600000
_EPOCH_2025_01_02 = 1735776000000


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


class TestUsersListFilters:
    """Tests for the new filter/sort flags on `users list`."""

    _PAYLOAD: ClassVar[dict] = {"items": [], "nextPageToken": None}

    @respx.mock
    def test_full_text_flag(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(app, ["users", "list", "--full-text", "rossi"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["fullTextFilter"] == "rossi"

    @respx.mock
    def test_status_repeatable(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app, ["users", "list", "--status", "1", "--status", "2"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["statusFilter"] == [1, 2]

    @respx.mock
    def test_workspace_and_community_repeatable(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app,
            ["users", "list", "--workspace", "10", "--community", "20", "--community", "21"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["workspaceIds"] == [10]
        assert body["communityIds"] == [20, 21]

    @respx.mock
    def test_role_flag(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(app, ["users", "list", "--role", "ADMIN"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["role"] == "ADMIN"

    @respx.mock
    def test_order_by_desc(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app, ["users", "list", "--order-by", "lastName", "--desc"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["orderTypeId"] == "lastName"
        assert body["orderDesc"] is True

    @respx.mock
    def test_order_asc(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(app, ["users", "list", "--asc"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["orderDesc"] is False

    @respx.mock
    def test_created_from_coercion(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app,
            ["users", "list", "--created-from", "2025-01-01T00:00:00+00:00"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["creationTimestampFrom"] == 1735689600000

    @respx.mock
    def test_last_access_range_coercion(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "users",
                "list",
                "--last-access-from",
                "2025-01-01T00:00:00+00:00",
                "--last-access-to",
                "1735776000000",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["lastAccessTimestampFrom"] == _EPOCH_2025_01_01
        assert body["lastAccessTimestampTo"] == _EPOCH_2025_01_02

    @respx.mock
    def test_generic_filter_passthrough_snake_to_camel(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app,
            ["users", "list", "--filter", "external_id_full_text_filter=EXT-1"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["externalIdFullTextFilter"] == "EXT-1"

    @respx.mock
    def test_generic_filter_typed_tokens(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/users", self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "users",
                "list",
                "--filter",
                "people_section_enabled=false",
                "--filter",
                "reduced_profile=TRUE",
                "--filter",
                "place=Bologna",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["peopleSectionEnabled"] is False
        assert body["reducedProfile"] is True
        assert body["place"] == "Bologna"

    def test_filter_bad_format(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["users", "list", "--filter", "bad"], env=BASE_ENV)
        assert result.exit_code != 0
