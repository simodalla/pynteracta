# SPDX-License-Identifier: Apache-2.0
"""CLI: comandi dei post evento (spec 08)."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli.posts_event import merge_event

_COMMUNITY_ID = 79
_POST_ID = 21269
_OCC_TOKEN = 5

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}

_MANAGE = "communication/posts/manage"
_FOR_CREATE_PATH = f"{_MANAGE}/event-post-data-for-create/{_COMMUNITY_ID}"
_FOR_EDIT_PATH = f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}"
_FOR_COPY_PATH = f"{_MANAGE}/event-post-data-for-copy/{_POST_ID}"
_CREATE_PATH = f"{_MANAGE}/create-event-post/{_COMMUNITY_ID}"
_EXIT_CONFIG = 2
_EXIT_VALIDATION = 6
_HTTP_400 = 400
_START_BLOCK = {"localDatetime": "2026-11-05T10:00:00"}
_END_BLOCK = {"localDatetime": "2026-11-05T12:00:00"}


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
    ["get-event-for-create", "get-event-for-edit", "get-event-for-copy", "create-event"],
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


def _mock_create() -> respx.Route:
    return mock_json("POST", _CREATE_PATH, load_payload("create_event_post_response.json"))


def _create(runner: CliRunner, *args: str) -> Any:
    return runner.invoke(app, ["posts", "create-event", str(_COMMUNITY_ID), *args], env=BASE_ENV)


class TestMergeEvent:
    # criterio: 08-C12
    def test_flags_win_and_invitations_merge_by_key(self) -> None:
        merged = merge_event(
            {},
            {"allDay": False, "location": "X", "invitations": {"users": [{"id": 99}]}},
            {
                "startAt": _START_BLOCK,
                "timezone": "Europe/Rome",
                "location": "Sala A",
                "invitations": {"groups": [{"id": 3}]},
            },
        )
        assert merged == {
            "allDay": False,
            "location": "Sala A",
            "startAt": _START_BLOCK,
            "timezone": "Europe/Rome",
            "invitations": {"users": [{"id": 99}], "groups": [{"id": 3}]},
        }

    # criterio: 08-C15
    def test_json_replaces_read_invitations_and_flag_replaces_users_only(self) -> None:
        base = {"location": "Sala A", "invitations": {"users": [{"id": 7}], "groups": [{"id": 3}]}}
        assert merge_event(base, {"invitations": {"users": [{"id": 8}]}}, {}) == {
            "location": "Sala A",
            "invitations": {"users": [{"id": 8}]},
        }
        assert merge_event(base, {}, {"invitations": {"users": [{"id": 9}]}}) == {
            "location": "Sala A",
            "invitations": {"users": [{"id": 9}], "groups": [{"id": 3}]},
        }

    def test_all_empty(self) -> None:
        assert merge_event({}, {}, {}) == {}


class TestCreateEvent:
    # criterio: 08-C12
    @respx.mock
    def test_flags_and_json_merge_flags_win(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = _mock_create()
        body_file = tmp_path / "body.json"
        body_file.write_text(
            json.dumps(
                {
                    "title": "X",
                    "visibility": 1,
                    "linkPreview": {"url": "https://example.org"},
                    "event": {"allDay": False, "invitations": {"users": [{"id": 99}]}},
                }
            ),
            encoding="utf-8",
        )
        result = _create(
            runner,
            "--start", "2026-11-05T10:00:00",
            "--end", "2026-11-05T12:00:00",
            "--location", "Sala A",
            "--invite-user", "7",
            "--invite-group", "3",
            "--invite-type", "2",
            "--notify-on-edit",
            "--title", "T",
            "--description", "D",
            "--watcher-user", "8",
            "--watcher-group", "4",
            "--announcement",
            "--pinned",
            "--json", str(body_file),
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "title": "T",
            "description": "D",
            "descriptionFormat": 2,
            "visibility": 1,
            "linkPreview": {"url": "https://example.org"},
            "watcherUserIds": [8],
            "watcherGroupIds": [4],
            "announcement": True,
            "pinned": True,
            "event": {
                "startAt": _START_BLOCK,
                "endAt": _END_BLOCK,
                "timezone": "Europe/Rome",
                "allDay": False,
                "location": "Sala A",
                "invitations": {
                    "users": [{"id": 7, "typeId": 2}],
                    "groups": [{"id": 3, "typeId": 2}],
                    "sendEditPostNotifications": True,
                },
            },
        }

    # criterio: 08-C12
    @respx.mock
    def test_without_announcement_and_pinned_keys_missing(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--start", "2026-11-05T10:00:00", "--title", "T")
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "title": "T",
            "event": {"startAt": _START_BLOCK, "timezone": "Europe/Rome"},
        }

    # criterio: 08-C12
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        _mock_create()
        result = _create(runner, "--start", "2026-11-05T10:00:00", "--title", "T")
        assert result.exit_code == 0, result.output
        for column in (
            "id",
            "community_id",
            "title",
            "start_at",
            "end_at",
            "timezone",
            "location",
            "visibility",
            "next_occ_token",
        ):
            assert column in result.output
        assert result.output == snapshot

    # criterio: 08-C12
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        _mock_create()
        result = runner.invoke(
            app,
            [
                "--output", "json",
                "posts", "create-event", str(_COMMUNITY_ID),
                "--start", "2026-11-05T10:00:00",
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["id"] == 21270  # noqa: PLR2004
        assert result.output == snapshot

    @respx.mock
    def test_table_without_event_in_response_has_empty_columns(self, runner: CliRunner) -> None:
        payload = load_payload("create_event_post_response.json")
        del payload["postData"]["event"]
        mock_json("POST", _CREATE_PATH, payload)
        result = _create(runner, "--start", "2026-11-05T10:00:00")
        assert result.exit_code == 0, result.output
        assert "Sala A" not in result.output
        assert "start_at" in result.output

    # criterio: 08-C13
    @respx.mock
    def test_date_only_is_local_midnight_and_all_day(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--start", "2026-11-05", "--all-day")
        assert result.exit_code == 0, result.output
        assert _sent_body(route)["event"] == {
            "startAt": {"localDatetime": "2026-11-05T00:00:00"},
            "timezone": "Europe/Rome",
            "allDay": True,
        }

    # criterio: 08-C13
    @respx.mock
    def test_explicit_offset_sends_utc(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--start", "2026-11-05T10:00:00+02:00")
        assert result.exit_code == 0, result.output
        assert _sent_body(route)["event"] == {
            "startAt": {"localDatetime": "2026-11-05T08:00:00"},
            "timezone": "UTC",
        }

    # criterio: 08-C13
    @respx.mock
    def test_timezone_flag_applied(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--start", "2026-11-05T10:00:00", "--timezone", "America/New_York")
        assert result.exit_code == 0, result.output
        assert _sent_body(route)["event"] == {
            "startAt": _START_BLOCK,
            "timezone": "America/New_York",
        }

    # criterio: 08-C13
    @respx.mock
    def test_unknown_timezone_exits_2(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--start", "2026-11-05T10:00:00", "--timezone", "Nowhere/Town")
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0

    # criterio: 08-C13
    @respx.mock
    def test_bad_start_exits_2(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--start", "tomorrow")
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0

    # criterio: 08-C13
    @respx.mock
    def test_missing_start_exits_2_without_requests(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(runner, "--title", "T")
        assert result.exit_code == _EXIT_CONFIG
        assert "--start" in result.output
        assert route.call_count == 0

    # criterio: 08-C13
    @respx.mock
    def test_start_from_json_event_is_enough(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = _mock_create()
        body_file = tmp_path / "body.json"
        event = {"startAt": _START_BLOCK, "timezone": "Europe/Rome"}
        body_file.write_text(json.dumps({"event": event}), encoding="utf-8")
        result = _create(runner, "--json", str(body_file))
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"event": event}

    @respx.mock
    def test_other_flags(self, runner: CliRunner) -> None:
        route = _mock_create()
        result = _create(
            runner,
            "--start", "2026-11-05T10:00:00",
            "--visibility", "2",
            "--draft",
            "--scheduled-publication", "2026-11-01T09:00",
            "--client-uid", "uid-1",
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        body = _sent_body(route)
        assert body["visibility"] == 2  # noqa: PLR2004
        assert body["draft"] is True
        assert body["clientUid"] == "uid-1"
        assert body["scheduledPublication"] == {
            "datetime": "2026-11-01T09:00:00",
            "timezone": "Europe/Rome",
        }


class TestExitCodes:
    # criterio: 08-C09
    @respx.mock
    def test_create_validation_error_exits_6(self, runner: CliRunner) -> None:
        route = mock_json(
            "POST",
            _CREATE_PATH,
            load_payload("custom_field_validation_error_response.json"),
            status=_HTTP_400,
        )
        result = _create(runner, "--start", "2026-11-05T10:00:00")
        assert result.exit_code == _EXIT_VALIDATION
        assert route.call_count == 1
