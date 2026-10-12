# SPDX-License-Identifier: Apache-2.0
"""CLI: comandi dei post evento (spec 08)."""

from __future__ import annotations

import json
import pathlib
from typing import Any

import httpx
import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli.posts_event import (
    event_copy_base,
    event_edit_base,
    event_write_block,
    merge_event,
)
from pynteracta.models.facade.posts_event import EventPostForCopy, EventPostForEdit

_COMMUNITY_ID = 79
_POST_ID = 21269
_OCC_TOKEN = 5

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}

_MANAGE = "communication/posts/manage"
_FOR_CREATE_PATH = f"{_MANAGE}/event-post-data-for-create/{_COMMUNITY_ID}"
_FOR_EDIT_PATH = f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}"
_FOR_COPY_PATH = f"{_MANAGE}/event-post-data-for-copy/{_POST_ID}"
_CREATE_PATH = f"{_MANAGE}/create-event-post/{_COMMUNITY_ID}"
_EDIT_PATH = f"{_MANAGE}/edit-event-post/{_POST_ID}/{_OCC_TOKEN}"
_COPY_PATH = f"{_MANAGE}/copy-event-post/{_POST_ID}/{_OCC_TOKEN}"
_EXIT_CONFIG = 2
_EXIT_GENERIC = 1
_EXIT_NOT_FOUND = 5
_EXIT_CONFLICT = 9
_HTTP_404 = 404
_HTTP_409 = 409
_PARTICIPATE_PATH = f"{_MANAGE}/post-event/{_POST_ID}/partecipate"
_EXIT_PERMISSION = 4
_HTTP_403 = 403
_CONFLICT_MESSAGE = f"Post {_POST_ID} changed since it was read: fetch it again and retry"
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
    [
        "get-event-for-create",
        "get-event-for-edit",
        "get-event-for-copy",
        "create-event",
        "edit-event",
        "copy-event",
        "participate",
    ],
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


_EDIT_FORM = load_payload("event_post_for_edit_response.json")
_COPY_FORM = load_payload("event_post_for_copy_response.json")
_DELTA = _EDIT_FORM["contentData"]["descriptionDelta"]
_CLEAN_EVENT: dict[str, Any] = {
    "startAt": _START_BLOCK,
    "endAt": _END_BLOCK,
    "timezone": "Europe/Rome",
    "allDay": False,
    "location": "Sala A",
    "invitations": {
        "users": [{"id": 7, "typeId": 2}],
        "groups": [{"id": 3, "typeId": 0}],
        "sendEditPostNotifications": False,
    },
}
_EDIT_BASE: dict[str, Any] = {
    "title": "Riunione di prova",
    "description": _DELTA,
    "descriptionFormat": 1,
    "visibility": 2,
    "coverImageContentRef": "ref-1",
    "event": _CLEAN_EVENT,
}


def _mock_edit_flow(form: dict[str, Any] | None = None) -> tuple[respx.Route, respx.Route]:
    read = mock_json("GET", _FOR_EDIT_PATH, form or _EDIT_FORM)
    write = mock_json("PUT", _EDIT_PATH, load_payload("edit_event_post_response.json"))
    return read, write


def _mock_copy_flow() -> tuple[respx.Route, respx.Route]:
    read = mock_json("GET", _FOR_COPY_PATH, _COPY_FORM)
    write = mock_json("PUT", _COPY_PATH, load_payload("copy_event_post_response.json"))
    return read, write


def _edit(runner: CliRunner, *args: str) -> Any:
    return runner.invoke(app, ["posts", "edit-event", str(_POST_ID), *args], env=BASE_ENV)


def _copy(runner: CliRunner, *args: str) -> Any:
    return runner.invoke(app, ["posts", "copy-event", str(_POST_ID), *args], env=BASE_ENV)


class TestEventWriteBlock:
    # criterio: 08-C21
    @pytest.mark.parametrize(
        ("event", "expected"),
        [
            (_EDIT_FORM["contentData"]["event"], _CLEAN_EVENT),
            (
                {"startAt": _START_BLOCK, "timezone": "Europe/Rome"},
                {"startAt": _START_BLOCK, "timezone": "Europe/Rome"},
            ),
            ({"invitations": {"users": [{"id": 7}]}}, {"invitations": {"users": [{"id": 7}]}}),
            (None, {}),
        ],
    )
    def test_event_write_block(self, event: dict[str, Any] | None, expected: dict) -> None:  # type: ignore[type-arg]
        assert event_write_block(event) == expected

    # criterio: 08-C21
    def test_null_keys_and_empty_dates_dropped(self) -> None:
        event = {
            "startAt": {"zonedDatetime": "x"},
            "endAt": None,
            "timezone": None,
            "location": "L",
            "invitations": {"users": None, "groups": [], "sendEditPostNotifications": None},
        }
        assert event_write_block(event) == {"location": "L", "invitations": {"groups": []}}
        assert event_write_block({"invitations": {}}) == {}


class TestEventBases:
    # criterio: 08-C14
    def test_edit_base(self) -> None:
        assert event_edit_base(EventPostForEdit.from_dict(_EDIT_FORM)) == _EDIT_BASE

    # criterio: 08-C16
    def test_copy_base(self) -> None:
        assert event_copy_base(EventPostForCopy.from_dict(_COPY_FORM)) == {
            **_EDIT_BASE,
            "announcement": True,
        }

    # criterio: 08-C14
    def test_bases_without_content(self) -> None:
        assert event_edit_base(EventPostForEdit.from_dict({"occToken": 1})) == {}
        assert event_copy_base(EventPostForCopy.from_dict({"occToken": 1})) == {}


class TestEditEvent:
    # criterio: 08-C14
    @respx.mock
    def test_edit_reads_form_then_puts_patched_body(self, runner: CliRunner) -> None:
        read, write = _mock_edit_flow()
        result = _edit(runner, "--title", "T2", "--location", "Sala B")
        assert result.exit_code == 0, result.output
        assert read.call_count == 1
        assert write.call_count == 1
        assert _sent_body(write) == {
            **_EDIT_BASE,
            "title": "T2",
            "event": {**_CLEAN_EVENT, "location": "Sala B"},
        }

    # criterio: 08-C14
    @respx.mock
    def test_edit_with_occ_token_still_reads_base(self, runner: CliRunner) -> None:
        read = mock_json("GET", _FOR_EDIT_PATH, _EDIT_FORM)
        write = mock_json(
            "PUT",
            f"{_MANAGE}/edit-event-post/{_POST_ID}/3",
            load_payload("edit_event_post_response.json"),
        )
        result = _edit(runner, "--occ-token", "3", "--title", "T2")
        assert result.exit_code == 0, result.output
        assert read.call_count == 1
        assert write.call_count == 1

    # criterio: 08-C14
    @respx.mock
    def test_edit_base_skips_missing_fields(self, runner: CliRunner) -> None:
        form = json.loads(json.dumps(_EDIT_FORM))
        del form["contentData"]["descriptionDelta"]
        del form["contentData"]["coverImageContentRef"]
        del form["contentData"]["event"]["endAt"]
        _read, write = _mock_edit_flow(form)
        result = _edit(runner, "--title", "T2")
        assert result.exit_code == 0, result.output
        body = _sent_body(write)
        assert "description" not in body
        assert "descriptionFormat" not in body
        assert "coverImageContentRef" not in body
        assert "endAt" not in body["event"]

    # criterio: 08-C14
    @respx.mock
    def test_edit_without_occ_token_in_response_exits_1(self, runner: CliRunner) -> None:
        form = {k: v for k, v in _EDIT_FORM.items() if k != "occToken"}
        _read, write = _mock_edit_flow(form)
        result = _edit(runner, "--title", "T2")
        assert result.exit_code == _EXIT_GENERIC
        assert write.call_count == 0

    # criterio: 08-C14
    @respx.mock
    def test_edit_post_not_found_exits_5_without_put(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, {"message": "not found"}, status=_HTTP_404)
        write = mock_json("PUT", _EDIT_PATH, load_payload("edit_event_post_response.json"))
        result = _edit(runner, "--occ-token", "5", "--title", "T2")
        assert result.exit_code == _EXIT_NOT_FOUND
        assert write.call_count == 0

    # criterio: 08-C15
    @respx.mock
    def test_start_without_timezone_uses_read_zone(self, runner: CliRunner) -> None:
        _read, write = _mock_edit_flow()
        result = _edit(runner, "--start", "2026-11-06T09:00:00")
        assert result.exit_code == 0, result.output
        event = _sent_body(write)["event"]
        assert event["startAt"] == {"localDatetime": "2026-11-06T09:00:00"}
        assert event["timezone"] == "Europe/Rome"
        assert event["endAt"] == _END_BLOCK

    # criterio: 08-C15
    @respx.mock
    def test_read_zone_used_when_not_default(self, runner: CliRunner) -> None:
        form = json.loads(json.dumps(_EDIT_FORM))
        form["contentData"]["event"]["timezone"] = "America/New_York"
        del form["contentData"]["event"]["startAt"]["zonedDatetime"]
        _read, write = _mock_edit_flow(form)
        result = _edit(runner, "--start", "2026-11-06T09:00:00")
        assert result.exit_code == 0, result.output
        event = _sent_body(write)["event"]
        assert event["startAt"] == {"localDatetime": "2026-11-06T09:00:00"}
        assert event["timezone"] == "America/New_York"

    # criterio: 08-C15
    @respx.mock
    def test_timezone_flag_changes_event_zone(self, runner: CliRunner) -> None:
        _read, write = _mock_edit_flow()
        result = _edit(runner, "--start", "2026-11-06T09:00:00", "--timezone", "America/New_York")
        assert result.exit_code == 0, result.output
        assert _sent_body(write)["event"]["timezone"] == "America/New_York"

    # criterio: 08-C15
    @respx.mock
    def test_invite_user_replaces_users_keeps_groups(self, runner: CliRunner) -> None:
        _read, write = _mock_edit_flow()
        result = _edit(runner, "--invite-user", "9")
        assert result.exit_code == 0, result.output
        assert _sent_body(write)["event"]["invitations"] == {
            "users": [{"id": 9}],
            "groups": [{"id": 3, "typeId": 0}],
            "sendEditPostNotifications": False,
        }

    # criterio: 08-C15
    @respx.mock
    def test_json_event_over_read_flags_over_json(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        body_file = tmp_path / "body.json"
        body_file.write_text(
            json.dumps({"event": {"location": "Sala C"}, "pinned": True}), encoding="utf-8"
        )
        _read, write = _mock_edit_flow()
        result = _edit(runner, "--json", str(body_file))
        assert result.exit_code == 0, result.output
        body = _sent_body(write)
        assert body["event"]["location"] == "Sala C"
        assert body["event"]["startAt"] == _START_BLOCK
        assert body["pinned"] is True
        _read, write = _mock_edit_flow()
        result = _edit(runner, "--json", str(body_file), "--location", "Sala D")
        assert result.exit_code == 0, result.output
        assert _sent_body(write, -1)["event"]["location"] == "Sala D"

    @respx.mock
    def test_other_flags(self, runner: CliRunner) -> None:
        _read, write = _mock_edit_flow()
        result = _edit(
            runner,
            "--description", "D",
            "--watcher-user", "7",
            "--remove-watcher-user", "8",
            "--watcher-group", "4",
            "--remove-watcher-group", "5",
            "--visibility", "1",
            "--pinned",
            "--draft",
            "--scheduled-publication", "2026-11-01T09:00",
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        body = _sent_body(write)
        assert body["description"] == "D"
        assert body["descriptionFormat"] == 2  # noqa: PLR2004
        assert body["addWatcherUserIds"] == [7]
        assert body["removeWatcherUserIds"] == [8]
        assert body["addWatcherGroupIds"] == [4]
        assert body["removeWatcherGroupIds"] == [5]
        assert body["visibility"] == 1
        assert body["pinned"] is True
        assert body["draft"] is True
        assert body["scheduledPublication"]["timezone"] == "Europe/Rome"

    @respx.mock
    def test_without_event_in_form_and_flags_no_event_key(self, runner: CliRunner) -> None:
        form = json.loads(json.dumps(_EDIT_FORM))
        del form["contentData"]["event"]
        _read, write = _mock_edit_flow(form)
        result = _edit(runner, "--title", "T2")
        assert result.exit_code == 0, result.output
        assert "event" not in _sent_body(write)


class TestCopyEvent:
    # criterio: 08-C16
    @respx.mock
    def test_copy_reads_form_then_puts_base_with_title(self, runner: CliRunner) -> None:
        read, write = _mock_copy_flow()
        result = _copy(runner, "--title", "Copia")
        assert result.exit_code == 0, result.output
        assert read.call_count == 1
        assert write.call_count == 1
        assert _sent_body(write) == {**_EDIT_BASE, "title": "Copia", "announcement": True}

    # criterio: 08-C16
    @respx.mock
    def test_copy_table_shows_new_post(self, runner: CliRunner, snapshot: object) -> None:
        _mock_copy_flow()
        result = _copy(runner, "--title", "Copia")
        assert result.exit_code == 0, result.output
        assert "21271" in result.output
        assert result.output == snapshot

    @respx.mock
    def test_copy_flags(self, runner: CliRunner) -> None:
        _read, write = _mock_copy_flow()
        result = _copy(
            runner,
            "--start", "2026-11-12T10:00",
            "--client-uid", "uid-2",
            "--watcher-user", "7",
            "--watcher-group", "4",
            "--announcement",
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        body = _sent_body(write)
        assert body["clientUid"] == "uid-2"
        assert body["addWatcherUserIds"] == [7]
        assert body["addWatcherGroupIds"] == [4]
        assert body["announcement"] is True
        assert body["event"]["startAt"] == {"localDatetime": "2026-11-12T10:00:00"}
        assert body["event"]["endAt"] == _END_BLOCK


class TestConflicts:
    # criterio: 08-C19
    @pytest.mark.parametrize(
        ("command", "read_path", "fixture", "write_path"),
        [
            ("edit-event", _FOR_EDIT_PATH, "event_post_for_edit_response.json", _EDIT_PATH),
            ("copy-event", _FOR_COPY_PATH, "event_post_for_copy_response.json", _COPY_PATH),
        ],
    )
    @respx.mock
    def test_conflict_exits_9_without_retry(
        self, runner: CliRunner, command: str, read_path: str, fixture: str, write_path: str
    ) -> None:
        mock_json("GET", read_path, load_payload(fixture))
        write = mock_json("PUT", write_path, {"message": "occToken mismatch"}, status=_HTTP_409)
        result = runner.invoke(
            app, ["posts", command, str(_POST_ID), "--title", "T2"], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFLICT
        assert _CONFLICT_MESSAGE in " ".join(result.output.split())
        assert write.call_count == 1


def _mock_participate(status: int = 200) -> respx.Route:
    return respx.put(f"https://api.example.com/portal/api/external/v2/{_PARTICIPATE_PATH}").mock(
        return_value=httpx.Response(status)
    )


class TestParticipate:
    # criterio: 08-C17
    @respx.mock
    def test_yes_with_notes_body_and_message(self, runner: CliRunner) -> None:
        route = _mock_participate()
        result = runner.invoke(
            app,
            ["posts", "participate", str(_POST_ID), "yes", "--notes", "Arrivo tardi"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {"typeId": 1, "notes": "Arrivo tardi"}
        assert f"Participation to post {_POST_ID} recorded: yes" in result.output

    # criterio: 08-C17
    @pytest.mark.parametrize(("choice", "type_id"), [("maybe", 2), ("no", 3)])
    @respx.mock
    def test_maybe_and_no_type_ids(self, runner: CliRunner, choice: str, type_id: int) -> None:
        route = _mock_participate()
        result = runner.invoke(app, ["posts", "participate", str(_POST_ID), choice], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"typeId": type_id}

    # criterio: 08-C17
    @respx.mock
    def test_json_output(self, runner: CliRunner) -> None:
        _mock_participate()
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "participate", str(_POST_ID), "yes"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {"post_id": _POST_ID, "answer": "yes", "type_id": 1}

    # criterio: 08-C17
    @respx.mock
    def test_invalid_choice_exits_2_without_requests(self, runner: CliRunner) -> None:
        route = _mock_participate()
        result = runner.invoke(
            app, ["posts", "participate", str(_POST_ID), "perhaps"], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0

    @respx.mock
    def test_quiet_prints_nothing(self, runner: CliRunner) -> None:
        _mock_participate()
        result = runner.invoke(
            app, ["--quiet", "posts", "participate", str(_POST_ID), "no"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == ""


class TestParticipateExitCodes:
    # criterio: 08-C09
    @respx.mock
    def test_participate_not_found_exits_5(self, runner: CliRunner) -> None:
        route = _mock_participate(_HTTP_404)
        result = runner.invoke(app, ["posts", "participate", str(_POST_ID), "yes"], env=BASE_ENV)
        assert result.exit_code == _EXIT_NOT_FOUND
        assert route.call_count == 1

    # criterio: 08-C09
    @respx.mock
    def test_participate_forbidden_exits_4(self, runner: CliRunner) -> None:
        route = _mock_participate(_HTTP_403)
        result = runner.invoke(app, ["posts", "participate", str(_POST_ID), "yes"], env=BASE_ENV)
        assert result.exit_code == _EXIT_PERMISSION
        assert route.call_count == 1


_UPLOAD_PATH = "core/storage/upload-new-attachment"
_STORAGE_URL = "https://storage.example.com/bucket-test"
_CONTENT_REF = load_payload("upload_new_attachment_response.json")["contentRef"]
_EXIT_UPLOAD = 11


def _mock_storage(*responses: httpx.Response) -> respx.Route:
    """Il primo passo risponde sempre con la fixture; lo storage con ``responses`` in ordine."""
    mock_json("POST", _UPLOAD_PATH, load_payload("upload_new_attachment_response.json"))
    route = respx.post(_STORAGE_URL)
    if len(responses) > 1:
        route.mock(side_effect=list(responses))
    else:
        route.mock(return_value=responses[0] if responses else httpx.Response(204))
    return route


def _files(tmp_path: pathlib.Path, *names: str) -> list[str]:
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"contenuto di " + name.encode())
        paths.append(str(path))
    return paths


class TestCoverAndAttach:
    # criterio: 08-C18
    @respx.mock
    def test_cover_then_attach_uploaded_in_order(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        storage = _mock_storage()
        route = _mock_create()
        cover, doc = _files(tmp_path, "cover.png", "doc.pdf")
        result = _create(
            runner, "--start", "2026-11-05T10:00:00", "--cover", cover, "--attach", doc
        )
        assert result.exit_code == 0, result.output
        assert storage.call_count == 2  # noqa: PLR2004
        assert b'filename="cover.png"' in storage.calls[0].request.content
        assert b'filename="doc.pdf"' in storage.calls[1].request.content
        body = _sent_body(route)
        assert body["coverImageContentRef"] == _CONTENT_REF
        assert body["attachments"] == [{"name": "doc.pdf", "contentRef": _CONTENT_REF}]
        urls = [str(call.request.url) for call in respx.calls]
        assert urls[-1].endswith(_CREATE_PATH)

    # criterio: 08-C18
    @respx.mock
    def test_cover_upload_failure_exits_11_without_write(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        storage = _mock_storage(httpx.Response(400, text="<Error/>"))
        route = _mock_create()
        cover, doc = _files(tmp_path, "cover.png", "doc.pdf")
        result = _create(
            runner, "--start", "2026-11-05T10:00:00", "--cover", cover, "--attach", doc
        )
        assert result.exit_code == _EXIT_UPLOAD
        assert "Upload of cover.png failed" in result.output
        assert storage.call_count == 1
        assert route.call_count == 0

    # criterio: 08-C18
    @respx.mock
    def test_edit_event_cover_wins_over_read(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        _mock_storage()
        _read, write = _mock_edit_flow()
        (cover,) = _files(tmp_path, "cover.png")
        result = _edit(runner, "--cover", cover)
        assert result.exit_code == 0, result.output
        assert _sent_body(write)["coverImageContentRef"] == _CONTENT_REF

    # criterio: 08-C18
    @respx.mock
    def test_copy_event_cover(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        _mock_storage()
        _read, write = _mock_copy_flow()
        cover, doc = _files(tmp_path, "cover.png", "doc.pdf")
        result = _copy(runner, "--cover", cover, "--attach", doc)
        assert result.exit_code == 0, result.output
        body = _sent_body(write)
        assert body["coverImageContentRef"] == _CONTENT_REF
        assert body["addAttachments"] == [{"name": "doc.pdf", "contentRef": _CONTENT_REF}]

    # criterio: 08-C18
    @respx.mock
    def test_invalid_body_exits_2_before_cover_upload(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        storage = _mock_storage()
        route = _mock_create()
        (cover,) = _files(tmp_path, "cover.png")
        result = _create(
            runner, "--start", "2026-11-05T10:00:00", "--visibility", "x", "--cover", cover
        )
        assert result.exit_code == _EXIT_CONFIG
        assert storage.call_count == 0
        assert route.call_count == 0
