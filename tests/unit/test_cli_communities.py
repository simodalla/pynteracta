# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'communities' command group."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli._common import EXIT_NOT_FOUND

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


# ---------------------------------------------------------------------------
# Spec 09: caratterizzazione dei comandi esistenti (copertura del file)
# ---------------------------------------------------------------------------

_NOT_FOUND = {"errorCode": "NOT_FOUND", "description": "missing"}


class TestCommunitiesDetailsBulk:
    # criterio: 09-C13
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        route = mock_json(
            "POST",
            "communication/settings/communities/details",
            load_payload("communities_list.json"),
        )
        result = runner.invoke(
            app, ["communities", "details-bulk", "--id", "10", "--id", "20"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot
        assert json.loads(route.calls[0].request.content) == {"communityIds": [10, 20]}

    # criterio: 09-C13
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/settings/communities/details",
            load_payload("communities_list.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "communities", "details-bulk", "--id", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot


class TestCommunitiesPostDefinitions:
    _PATH = "communication/settings/communities/post-definitions"

    # criterio: 09-C13
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        route = mock_json("POST", self._PATH, load_payload("post_definitions_map.json"))
        result = runner.invoke(
            app, ["communities", "post-definitions", "--id", "10", "--id", "20"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot
        assert json.loads(route.calls[0].request.content) == {"communityIds": [10, 20]}

    # criterio: 09-C13
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", self._PATH, load_payload("post_definitions_map.json"))
        result = runner.invoke(
            app, ["--output", "json", "communities", "post-definitions", "--id", "10"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    # criterio: 09-C13
    @respx.mock
    def test_full_table(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", self._PATH, load_payload("post_definitions_map.json"))
        result = runner.invoke(
            app, ["communities", "post-definitions", "--id", "10", "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    # criterio: 09-C13
    @respx.mock
    def test_fields(self, runner: CliRunner) -> None:
        mock_json("POST", self._PATH, load_payload("post_definitions_map.json"))
        result = runner.invoke(
            app,
            [
                "--output",
                "json",
                "communities",
                "post-definitions",
                "--id",
                "10",
                "--fields",
                "community_id,label",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = json.loads(result.output)
        assert rows
        assert all(set(row) == {"community_id", "label"} for row in rows)

    # criterio: 09-C13
    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: Path) -> None:
        mock_json("POST", self._PATH, load_payload("post_definitions_map.json"))
        target = tmp_path / "defs.csv"
        result = runner.invoke(
            app,
            ["communities", "post-definitions", "--id", "10", "--export", str(target)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "Wrote" in result.output
        assert target.read_text(encoding="utf-8").startswith("community_id")

    # criterio: 09-C13
    @respx.mock
    def test_export_quiet(self, runner: CliRunner, tmp_path: Path) -> None:
        mock_json("POST", self._PATH, load_payload("post_definitions_map.json"))
        target = tmp_path / "defs.json"
        result = runner.invoke(
            app,
            ["--quiet", "communities", "post-definitions", "--id", "10", "--export", str(target)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "Wrote" not in result.output
        assert json.loads(target.read_text(encoding="utf-8"))


class TestCommunitiesErrors:
    # criterio: 09-C13
    @respx.mock
    @pytest.mark.parametrize(
        ("method", "path", "args"),
        [
            ("GET", "communication/settings/communities", ["communities", "list"]),
            (
                "GET",
                "communication/settings/communities/10/details",
                ["communities", "details", "10"],
            ),
            (
                "POST",
                "communication/settings/communities/details",
                ["communities", "details-bulk", "--id", "10"],
            ),
            (
                "GET",
                "communication/settings/communities/10/post-definition",
                ["communities", "post-definition", "10"],
            ),
            (
                "POST",
                "communication/settings/communities/post-definitions",
                ["communities", "post-definitions", "--id", "10"],
            ),
        ],
    )
    def test_not_found_exits_5(
        self, runner: CliRunner, method: str, path: str, args: list[str]
    ) -> None:
        route = mock_json(method, path, _NOT_FOUND, status=404)
        result = runner.invoke(app, args, env=BASE_ENV)
        assert result.exit_code == EXIT_NOT_FOUND
        assert route.call_count == 1
