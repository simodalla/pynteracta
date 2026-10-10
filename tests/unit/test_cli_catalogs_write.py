# SPDX-License-Identifier: Apache-2.0
"""Test dei comandi di scrittura di cataloghi e voci (spec 06)."""

from __future__ import annotations

import json
import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}
_EXIT_CONFIG = 2
_CATALOG_ID = 5
_ENTRY_ID = 100
_PARENT_ID = 3
_CATALOGS_PATH = "admin/manage/catalogs"
_ENTRIES_PATH = f"admin/manage/catalogs/{_CATALOG_ID}/entries"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route, index: int = 0) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


class TestCatalogsCreate:
    # criterio: 06-C10
    @respx.mock
    def test_flags_and_json_merge_name_key_by_key(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"name": {"it": "X", "de": "Standorte"}}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "catalogs",
                "create",
                "--name",
                "it=Sedi",
                "--name",
                "en=Sites",
                "--parent",
                str(_PARENT_ID),
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "name": {"it": "Sedi", "de": "Standorte", "en": "Sites"},
            "parentId": _PARENT_ID,
        }

    # criterio: 06-C10
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        result = runner.invoke(
            app,
            ["catalogs", "create", "--name", "it=Sedi", "--parent", str(_PARENT_ID)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 06-C10
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "catalogs", "create", "--name", "it=Sedi"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 06-C10
    @pytest.mark.parametrize("value", ["Sedi", "=Sedi"])
    @respx.mock
    def test_malformed_name_exits_2_without_requests(self, runner: CliRunner, value: str) -> None:
        route = mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        result = runner.invoke(app, ["catalogs", "create", "--name", value], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "LANG=TEXT" in result.output
        assert not route.called

    @respx.mock
    def test_json_unknown_key_exits_2(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"title": "x"}), encoding="utf-8")
        result = runner.invoke(app, ["catalogs", "create", "--json", str(body)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert not route.called


class TestCatalogEntriesCreate:
    # criterio: 06-C16
    @respx.mock
    def test_flags_body_and_table(self, runner: CliRunner, snapshot: object) -> None:
        route = mock_json("POST", _ENTRIES_PATH, load_payload("create_catalog_entry_response.json"))
        result = runner.invoke(
            app,
            [
                "catalogs",
                "create-entry",
                str(_CATALOG_ID),
                "--label",
                "it=Bologna",
                "--parent-entry",
                "10",
                "--parent-entry",
                "11",
                "--external-id",
                "BO",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "label": {"it": "Bologna"},
            "parentIds": [10, 11],
            "externalId": "BO",
        }
        assert result.output == snapshot

    # criterio: 06-C16
    @respx.mock
    def test_json_label_merged_with_flag(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _ENTRIES_PATH, load_payload("create_catalog_entry_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"label": {"it": "Bologna"}}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "catalogs",
                "create-entry",
                str(_CATALOG_ID),
                "--label",
                "en=Bologna",
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"label": {"it": "Bologna", "en": "Bologna"}}
