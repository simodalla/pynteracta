# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'communities' command group."""

from __future__ import annotations

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestCommunitiesList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET", "communication/settings/communities", load_payload("communities_list.json")
        )
        result = runner.invoke(app, ["communities", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET", "communication/settings/communities", load_payload("communities_list.json")
        )
        result = runner.invoke(app, ["--output", "json", "communities", "list"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


class TestCommunitiesDetails:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(app, ["communities", "details", "10"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "communities", "details", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_web_url_present(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "communities", "details", "10", "--web-url"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "web_url" in result.output

    @respx.mock
    def test_web_url_absent_by_default(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "communities", "details", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "web_url" not in result.output


class TestCommunitiesPostDefinition:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/post-definition",
            load_payload("post_definition.json"),
        )
        result = runner.invoke(app, ["communities", "post-definition", "10"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/post-definition",
            load_payload("post_definition.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "communities", "post-definition", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot
        assert "FEEDBACK" in result.output
        assert "ENUM" in result.output
