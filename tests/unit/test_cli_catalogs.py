# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'catalogs' command group."""

from __future__ import annotations

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}

_CATALOGS_URL = f"{BASE_URL}/communication/settings/post-definition/catalogs"
_ENTRIES_URL = f"{BASE_URL}/communication/settings/post-definition/catalogs/5/entries"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCatalogsList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs",
            load_payload("catalogs.json"),
        )
        result = runner.invoke(app, ["catalogs", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs",
            load_payload("catalogs.json"),
        )
        result = runner.invoke(app, ["--output", "json", "catalogs", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


class TestCatalogsEntries:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs/5/entries",
            load_payload("catalog_entries.json"),
        )
        result = runner.invoke(app, ["catalogs", "entries", "5"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/settings/post-definition/catalogs/5/entries",
            load_payload("catalog_entries.json"),
        )
        result = runner.invoke(app, ["--output", "json", "catalogs", "entries", "5"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_all_pages(self, runner: CliRunner) -> None:
        page1 = {
            "items": [{"id": 100, "catalogId": 5, "label": "Engineering", "externalId": "ENG"}],
            "nextPageToken": "tok",
        }
        page2 = {
            "items": [{"id": 101, "catalogId": 5, "label": "Marketing", "externalId": "MKT"}],
            "nextPageToken": None,
        }
        respx.post(_ENTRIES_URL).mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        result = runner.invoke(app, ["catalogs", "entries", "5", "--all"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "Engineering" in result.output
        assert "Marketing" in result.output
