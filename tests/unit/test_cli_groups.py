# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'groups' and 'hashtags' command groups."""

from __future__ import annotations

import json
import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_GROUP_ID = 201
_COMMUNITY_ID = 79

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestGroupsList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", "admin/data/groups", load_payload("list_groups_response.json"))
        result = runner.invoke(app, ["groups", "list"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", "admin/data/groups", load_payload("list_groups_response.json"))
        result = runner.invoke(app, ["--output", "json", "groups", "list"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json("POST", "admin/data/groups", load_payload("list_groups_response.json"))
        out = pathlib.Path(str(tmp_path)) / "groups.csv"
        result = runner.invoke(app, ["groups", "list", "--export", str(out)], env=BASE_ENV)
        assert result.exit_code == 0
        assert out.exists()
        assert "Engineering" in out.read_text()


class TestGroupsListFilters:
    @respx.mock
    def test_status_and_workspace_repeatable(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/groups", {"items": [], "nextPageToken": None})
        result = runner.invoke(
            app,
            ["groups", "list", "--status", "1", "--status", "2", "--workspace", "10"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["statusFilter"] == [1, 2]
        assert body["workspaceIds"] == [10]

    @respx.mock
    def test_filters_forwarded_with_all(self, runner: CliRunner) -> None:
        route = mock_json("POST", "admin/data/groups", {"items": [], "nextPageToken": None})
        result = runner.invoke(
            app, ["groups", "list", "--all", "--status", "1", "--workspace", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["statusFilter"] == [1]
        assert body["workspaceIds"] == [10]

    @respx.mock
    def test_web_url_column(self, runner: CliRunner) -> None:
        mock_json("POST", "admin/data/groups", load_payload("list_groups_response.json"))
        result = runner.invoke(
            app, ["--output", "json", "groups", "list", "--web-url"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data[0]["web_url"] == f"https://api.example.com/portal/admin/group/{_GROUP_ID}"

    @respx.mock
    def test_web_url_absent_by_default(self, runner: CliRunner) -> None:
        mock_json("POST", "admin/data/groups", load_payload("list_groups_response.json"))
        result = runner.invoke(app, ["--output", "json", "groups", "list"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "web_url" not in result.output

    @respx.mock
    def test_web_url_with_full(self, runner: CliRunner) -> None:
        mock_json("POST", "admin/data/groups", load_payload("list_groups_response.json"))
        result = runner.invoke(
            app, ["--output", "json", "groups", "list", "--web-url", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data[0]["web_url"].endswith(f"/admin/group/{_GROUP_ID}")


class TestGroupsMembers:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            f"admin/data/groups/{_GROUP_ID}/members",
            load_payload("list_group_members_response.json"),
        )
        result = runner.invoke(app, ["groups", "members", str(_GROUP_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            f"admin/data/groups/{_GROUP_ID}/members",
            load_payload("list_group_members_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "groups", "members", str(_GROUP_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot


class TestGroupsGet:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/groups/{_GROUP_ID}/edit",
            load_payload("get_group_for_edit_response.json"),
        )
        result = runner.invoke(app, ["groups", "get", str(_GROUP_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_web_url_included(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            f"admin/manage/groups/{_GROUP_ID}/edit",
            load_payload("get_group_for_edit_response.json"),
        )
        result = runner.invoke(app, ["groups", "get", str(_GROUP_ID), "--web-url"], env=BASE_ENV)
        assert result.exit_code == 0
        assert f"/admin/group/{_GROUP_ID}" in result.output

    @respx.mock
    def test_web_url_absent_by_default(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            f"admin/manage/groups/{_GROUP_ID}/edit",
            load_payload("get_group_for_edit_response.json"),
        )
        result = runner.invoke(app, ["groups", "get", str(_GROUP_ID)], env=BASE_ENV)
        assert result.exit_code == 0
        assert "/admin/group/" not in result.output

    def test_help_shows_web_url(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["groups", "get", "--help"], env=BASE_ENV)
        assert "--web-url" in result.output


class TestHashtagsList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            f"admin/data/communities/{_COMMUNITY_ID}/hashtags",
            load_payload("list_community_hashtags_response.json"),
        )
        result = runner.invoke(app, ["hashtags", "list", str(_COMMUNITY_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            f"admin/data/communities/{_COMMUNITY_ID}/hashtags",
            load_payload("list_community_hashtags_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "hashtags", "list", str(_COMMUNITY_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json(
            "POST",
            f"admin/data/communities/{_COMMUNITY_ID}/hashtags",
            load_payload("list_community_hashtags_response.json"),
        )
        out = pathlib.Path(str(tmp_path)) / "hashtags.csv"
        result = runner.invoke(
            app, ["hashtags", "list", str(_COMMUNITY_ID), "--export", str(out)], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert out.exists()
        assert "engineering" in out.read_text()
