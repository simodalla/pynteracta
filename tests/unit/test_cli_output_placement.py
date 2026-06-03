# SPDX-License-Identifier: Apache-2.0
"""Tests for hybrid --output placement: global (before command) and per-command (after command)."""

from __future__ import annotations

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli._common import EXIT_CONFIG

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestPerCommandOutputPlacement:
    """Per-command --output (after command name) works for data-emitting commands."""

    @respx.mock
    def test_communities_details_per_command_json(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["communities", "details", "10", "--output", "json"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "{" in result.output

    @respx.mock
    def test_communities_list_per_command_json(self, runner: CliRunner) -> None:
        mock_json(
            "GET", "communication/settings/communities", load_payload("communities_list.json")
        )
        result = runner.invoke(
            app, ["communities", "list", "--output", "json"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "[" in result.output

    @respx.mock
    def test_communities_details_short_flag(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["communities", "details", "10", "-o", "json"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "{" in result.output


class TestOutputPrecedence:
    """Command-level --output wins over the global --output when both are provided."""

    @respx.mock
    def test_command_level_wins_over_global(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "table", "communities", "details", "10", "--output", "json"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "{" in result.output

    @respx.mock
    def test_global_still_works_as_fallback(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "communities", "details", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "{" in result.output


class TestInvalidPerCommandOutput:
    """An invalid per-command --output value exits with EXIT_CONFIG."""

    @respx.mock
    def test_invalid_value_exits_config(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/settings/communities/10/details",
            load_payload("community_details.json"),
        )
        result = runner.invoke(
            app, ["communities", "details", "10", "--output", "xml"], env=BASE_ENV
        )
        assert result.exit_code == EXIT_CONFIG
        assert "xml" in result.output


class TestExcludedCommandsUnaffected:
    """config commands do not have a per-command --output flag."""

    def test_config_get_has_no_output_option(self, runner: CliRunner, tmp_path: object) -> None:
        result = runner.invoke(app, ["config", "get", "--help"])
        assert result.exit_code == 0
        assert "--output" not in result.output
