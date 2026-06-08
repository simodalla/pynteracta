# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'admin-manage' command group."""

from __future__ import annotations

import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_WORKSPACE_ID = 88
_CATALOG_ID = 5
_ENTRY_ID = 100
_USER_ID = 1042

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestAdminManageWorkspace:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        result = runner.invoke(app, ["admin-manage", "workspace", str(_WORKSPACE_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "admin-manage", "workspace", str(_WORKSPACE_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_full_includes_occ_token(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "admin-manage", "workspace", str(_WORKSPACE_ID), "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert "occToken" in result.output

    @respx.mock
    def test_occ_token_absent_from_default_table(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        result = runner.invoke(app, ["admin-manage", "workspace", str(_WORKSPACE_ID)], env=BASE_ENV)
        assert result.exit_code == 0
        assert "occToken" not in result.output
        assert "occ_token" not in result.output

    @respx.mock
    def test_fields_selection(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "admin-manage", "workspace", str(_WORKSPACE_ID), "--fields", "id"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert '"id": 88' in result.output

    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        out = pathlib.Path(str(tmp_path)) / "workspace.csv"
        result = runner.invoke(
            app,
            ["admin-manage", "workspace", str(_WORKSPACE_ID), "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()
        assert "Operations" in out.read_text()

    @respx.mock
    def test_export_full_includes_occ_token(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/edit",
            load_payload("get_workspace_for_edit_response.json"),
        )
        out = pathlib.Path(str(tmp_path)) / "workspace_full.json"
        result = runner.invoke(
            app,
            ["admin-manage", "workspace", str(_WORKSPACE_ID), "--full", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()
        assert "occToken" in out.read_text()


class TestAdminManageCatalog:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/catalogs/{_CATALOG_ID}/edit",
            load_payload("get_catalog_for_edit_response.json"),
        )
        result = runner.invoke(app, ["admin-manage", "catalog", str(_CATALOG_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/catalogs/{_CATALOG_ID}/edit",
            load_payload("get_catalog_for_edit_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "admin-manage", "catalog", str(_CATALOG_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot


class TestAdminManageCatalogEntry:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/catalogs/{_CATALOG_ID}/entries/{_ENTRY_ID}/edit",
            load_payload("get_catalog_entry_for_edit_response.json"),
        )
        result = runner.invoke(
            app, ["admin-manage", "catalog-entry", str(_CATALOG_ID), str(_ENTRY_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/catalogs/{_CATALOG_ID}/entries/{_ENTRY_ID}/edit",
            load_payload("get_catalog_entry_for_edit_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "admin-manage", "catalog-entry", str(_CATALOG_ID), str(_ENTRY_ID)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot


class TestAdminManageUserCredentials:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/users/{_USER_ID}/credentials/edit",
            load_payload("get_user_credentials_for_edit_response.json"),
        )
        result = runner.invoke(
            app, ["admin-manage", "user-credentials", str(_USER_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            f"admin/manage/users/{_USER_ID}/credentials/edit",
            load_payload("get_user_credentials_for_edit_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "admin-manage", "user-credentials", str(_USER_ID)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot
