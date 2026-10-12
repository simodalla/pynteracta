# SPDX-License-Identifier: Apache-2.0
"""CLI: comandi dei post evento (spec 08)."""

from __future__ import annotations

import json
from typing import Any

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_COMMUNITY_ID = 79
_POST_ID = 21269
_OCC_TOKEN = 5

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}

_MANAGE = "communication/posts/manage"
_FOR_CREATE_PATH = f"{_MANAGE}/event-post-data-for-create/{_COMMUNITY_ID}"
_FOR_EDIT_PATH = f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}"
_FOR_COPY_PATH = f"{_MANAGE}/event-post-data-for-copy/{_POST_ID}"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route, index: int = 0) -> dict[str, Any]:
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


def _table_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if "│" in line]


# criterio: 08-C20
@pytest.mark.parametrize(
    "command",
    ["get-event-for-create", "get-event-for-edit", "get-event-for-copy"],
)
def test_posts_help_lists_event_commands(runner: CliRunner, command: str) -> None:
    result = runner.invoke(app, ["posts", "--help"], env=BASE_ENV)
    assert result.exit_code == 0
    assert command in result.output


class TestPrepCommands:
    # criterio: 08-C20
    @respx.mock
    def test_get_event_for_edit_table_starts_with_occ_token(
        self, runner: CliRunner, snapshot: object
    ) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("event_post_for_edit_response.json"))
        result = runner.invoke(app, ["posts", "get-event-for-edit", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        lines = _table_lines(result.output)
        assert "occ_token" in lines[0]
        for column in (
            "community_id",
            "title",
            "start_at",
            "end_at",
            "timezone",
            "all_day",
            "location",
            "participants_count",
            "visibility",
        ):
            assert column in result.output
        assert "Sala A" in result.output
        assert result.output == snapshot

    # criterio: 08-C20
    @respx.mock
    def test_get_event_for_copy_table(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _FOR_COPY_PATH, load_payload("event_post_for_copy_response.json"))
        result = runner.invoke(app, ["posts", "get-event-for-copy", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "occ_token" in _table_lines(result.output)[0]
        assert "start_at" in result.output
        assert "announcement" in result.output
        assert result.output == snapshot

    # criterio: 08-C20
    @respx.mock
    def test_get_event_for_create_table(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _FOR_CREATE_PATH, load_payload("event_post_for_create_response.json"))
        result = runner.invoke(
            app, ["posts", "get-event-for-create", str(_COMMUNITY_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert "visibility" in result.output
        assert "announcement" in result.output
        assert result.output == snapshot

    # criterio: 08-C20
    @pytest.mark.parametrize(
        ("command", "path", "fixture"),
        [
            ("get-event-for-edit", _FOR_EDIT_PATH, "event_post_for_edit_response.json"),
            ("get-event-for-copy", _FOR_COPY_PATH, "event_post_for_copy_response.json"),
        ],
    )
    @respx.mock
    def test_no_attachments_sends_query(
        self, runner: CliRunner, command: str, path: str, fixture: str
    ) -> None:
        route = mock_json("GET", path, load_payload(fixture))
        result = runner.invoke(
            app, ["posts", command, str(_POST_ID), "--no-attachments"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["loadAttachments"] == "false"

    # criterio: 08-C20
    @respx.mock
    def test_full_json(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("event_post_for_edit_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "get-event-for-edit", str(_POST_ID), "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["occToken"] == _OCC_TOKEN
        assert data["contentData"]["event"]["location"] == "Sala A"

    @respx.mock
    def test_read_error_exits_with_mapped_code(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_CREATE_PATH, {"message": "no"}, status=404)
        result = runner.invoke(
            app, ["posts", "get-event-for-create", str(_COMMUNITY_ID)], env=BASE_ENV
        )
        assert result.exit_code == 5  # noqa: PLR2004
