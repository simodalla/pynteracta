# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'tasks' command group."""

from __future__ import annotations

import json
import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_TASK_ID = 7001
_POST_ID = 21269

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}

_TASKS_GET_PATH = f"communication/tasks/data/task-detail-by-id/{_TASK_ID}"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestTasksGet:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(app, ["tasks", "get", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(
            app, ["--output", "json", "tasks", "get", str(_TASK_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_full_includes_raw_fields(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(
            app, ["--output", "json", "tasks", "get", str(_TASK_ID), "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        # full JSON exposes all facade properties
        assert "description_plain_text" in result.output or "description" in result.output

    @respx.mock
    def test_fields_option(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(
            app,
            ["tasks", "get", str(_TASK_ID), "--fields", "id,title,state"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "id" in result.output
        assert "title" in result.output

    @respx.mock
    def test_web_url_included(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(app, ["tasks", "get", str(_TASK_ID), "--web-url"], env=BASE_ENV)
        assert result.exit_code == 0
        assert f"/post/{_POST_ID}" in result.output

    @respx.mock
    def test_web_url_not_shown_by_default(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(app, ["tasks", "get", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == 0
        assert "/post/" not in result.output

    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        out = pathlib.Path(str(tmp_path)) / "task.csv"
        result = runner.invoke(
            app,
            ["tasks", "get", str(_TASK_ID), "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "Review quarterly report" in content

    def test_help_shows_web_url(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["tasks", "get", "--help"], env=BASE_ENV)
        assert "--web-url" in result.output

    def test_delta_not_in_default_table(self, runner: CliRunner) -> None:
        with respx.mock:
            mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
            result = runner.invoke(app, ["tasks", "get", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == 0
        assert "descriptionDelta" not in result.output
        assert "surveyData" not in result.output


# ---------------------------------------------------------------------------
# Scritture (spec 02)
# ---------------------------------------------------------------------------

_TASKS_CREATE_PATH = f"communication/tasks/manage/create-task/{_POST_ID}"
_EXIT_USAGE = 2
_WATCHER_A = 7
_WATCHER_B = 8
_ASSIGNEE = 9
_PRIORITY = 2


def _sent_body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


class TestTasksCreate:
    # criterio: 02-C08
    @respx.mock
    def test_flags_and_json_merge_flags_win(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"title": "X", "assigneeUserId": _ASSIGNEE}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "tasks",
                "create",
                str(_POST_ID),
                "--title",
                "T",
                "--priority",
                str(_PRIORITY),
                "--watcher-user",
                str(_WATCHER_A),
                "--watcher-user",
                str(_WATCHER_B),
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "title": "T",
            "priority": _PRIORITY,
            "watcherUserIds": [_WATCHER_A, _WATCHER_B],
            "assigneeUserId": _ASSIGNEE,
        }

    # criterio: 02-C08
    @respx.mock
    def test_description_and_client_uid_flags(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            ["tasks", "create", str(_POST_ID), "--description", "Plain", "--client-uid", "u-1"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"descriptionPlainText": "Plain", "clientUid": "u-1"}

    # criterio: 02-C08
    @respx.mock
    def test_expiration_flag_default_timezone(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            ["tasks", "create", str(_POST_ID), "--expiration", "2026-12-31T18:00"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route)["expiration"] == {
            "datetime": "2026-12-31T18:00:00",
            "timezone": "Europe/Rome",
        }

    # criterio: 02-C08
    @respx.mock
    def test_expiration_flag_explicit_timezone(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            [
                "tasks",
                "create",
                str(_POST_ID),
                "--expiration",
                "2026-12-31T18:00",
                "--timezone",
                "UTC",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route)["expiration"] == {
            "datetime": "2026-12-31T18:00:00",
            "timezone": "UTC",
        }

    # criterio: 02-C08
    @respx.mock
    def test_expiration_with_offset_ignores_timezone(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            [
                "tasks",
                "create",
                str(_POST_ID),
                "--expiration",
                "2026-12-31T18:00+01:00",
                "--timezone",
                "Europe/Rome",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        # offset fisso: la libreria converte in UTC
        assert _sent_body(route)["expiration"] == {
            "datetime": "2026-12-31T17:00:00",
            "timezone": "UTC",
        }

    # criterio: 02-C08
    @respx.mock
    def test_invalid_timezone_exits_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            [
                "tasks",
                "create",
                str(_POST_ID),
                "--expiration",
                "2026-12-31T18:00",
                "--timezone",
                "Mars/Olympus",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_USAGE
        assert "Mars/Olympus" in result.output
        assert route.call_count == 0

    # criterio: 02-C08
    @respx.mock
    def test_invalid_expiration_exits_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app, ["tasks", "create", str(_POST_ID), "--expiration", "tomorrow"], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_USAGE
        assert "--expiration" in result.output
        assert route.call_count == 0

    # criterio: 02-C08
    @respx.mock
    def test_json_unknown_key_exits_2(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"bogus": 1}), encoding="utf-8")
        result = runner.invoke(
            app, ["tasks", "create", str(_POST_ID), "--json", str(body)], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_USAGE
        assert "bogus" in result.output
        assert route.call_count == 0

    # criterio: 02-C08
    @respx.mock
    def test_json_from_stdin(self, runner: CliRunner) -> None:
        route = mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            ["tasks", "create", str(_POST_ID), "--json", "-"],
            env=BASE_ENV,
            input=json.dumps({"title": "from stdin", "subTasks": [{"description": "s"}]}),
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"title": "from stdin", "subTasks": [{"description": "s"}]}

    # criterio: 02-C08
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app, ["tasks", "create", str(_POST_ID), "--title", "T"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 02-C08
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _TASKS_CREATE_PATH, load_payload("create_task_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "tasks", "create", str(_POST_ID), "--title", "T"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 02-C08
    def test_help_lists_options(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["tasks", "create", "--help"], env=BASE_ENV)
        assert result.exit_code == 0
        for option in ("--title", "--expiration", "--timezone", "--watcher-user", "--json"):
            assert option in result.output


_FIXTURE_OCC_TOKEN = 3  # occToken in get_task_detail_response.json
_FORCED_OCC_TOKEN = 5
_EXIT_CONFLICT = 9
_HTTP_409 = 409


def _edit_path(occ_token: int) -> str:
    return f"communication/tasks/manage/edit-task/{_TASK_ID}/{occ_token}"


class TestTasksEdit:
    # criterio: 02-C09
    @respx.mock
    def test_edit_reads_occ_token_then_puts(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        put_route = mock_json(
            "PUT", _edit_path(_FIXTURE_OCC_TOKEN), load_payload("edit_task_response.json")
        )
        result = runner.invoke(app, ["tasks", "edit", str(_TASK_ID), "--title", "T2"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {"title": "T2"}

    # criterio: 02-C09
    @respx.mock
    def test_edit_with_occ_token_skips_get(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        put_route = mock_json(
            "PUT", _edit_path(_FORCED_OCC_TOKEN), load_payload("edit_task_response.json")
        )
        result = runner.invoke(
            app,
            [
                "tasks",
                "edit",
                str(_TASK_ID),
                "--occ-token",
                str(_FORCED_OCC_TOKEN),
                "--priority",
                str(_PRIORITY),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 0
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {"priority": _PRIORITY}

    # criterio: 02-C09
    @respx.mock
    def test_edit_watcher_flags_map_to_add_and_remove(self, runner: CliRunner) -> None:
        put_route = mock_json(
            "PUT", _edit_path(_FORCED_OCC_TOKEN), load_payload("edit_task_response.json")
        )
        result = runner.invoke(
            app,
            [
                "tasks",
                "edit",
                str(_TASK_ID),
                "--occ-token",
                str(_FORCED_OCC_TOKEN),
                "--watcher-user",
                str(_WATCHER_A),
                "--remove-watcher-user",
                str(_WATCHER_B),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "addWatcherUserIds": [_WATCHER_A],
            "removeWatcherUserIds": [_WATCHER_B],
        }

    # criterio: 02-C10
    @respx.mock
    def test_edit_conflict_exits_9_without_retry(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        put_route = mock_json(
            "PUT",
            _edit_path(_FIXTURE_OCC_TOKEN),
            {"message": "occToken mismatch"},
            status=_HTTP_409,
        )
        result = runner.invoke(app, ["tasks", "edit", str(_TASK_ID), "--title", "T2"], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFLICT
        assert "changed since it was read" in result.output
        assert "fetch it again and retry" in result.output
        assert put_route.call_count == 1

    # criterio: 02-C09
    @respx.mock
    def test_edit_task_without_occ_token_exits_1(self, runner: CliRunner) -> None:
        payload = dict(load_payload("get_task_detail_response.json"))
        del payload["occToken"]
        mock_json("GET", _TASKS_GET_PATH, payload)
        put_route = mock_json(
            "PUT", _edit_path(_FIXTURE_OCC_TOKEN), load_payload("edit_task_response.json")
        )
        result = runner.invoke(app, ["tasks", "edit", str(_TASK_ID), "--title", "T2"], env=BASE_ENV)
        assert result.exit_code == 1
        assert "occToken" in result.output
        assert put_route.call_count == 0

    # criterio: 02-C09
    @respx.mock
    def test_edit_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        mock_json("PUT", _edit_path(_FIXTURE_OCC_TOKEN), load_payload("edit_task_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "tasks", "edit", str(_TASK_ID), "--title", "T2"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot


_TASKS_DELETE_PATH = f"communication/tasks/manage/delete-task/{_TASK_ID}"
_DELETE_DONE = f"Task {_TASK_ID} deleted (post {_POST_ID})"


def _mock_delete_flow() -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
    delete_route = mock_json(
        "DELETE", _TASKS_DELETE_PATH, load_payload("delete_task_response.json")
    )
    return get_route, delete_route


class TestTasksDelete:
    # criterio: 02-C11
    @respx.mock
    def test_prompt_shows_id_and_title_and_y_deletes(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pynteracta.cli import _common  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)
        get_route, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["tasks", "delete", str(_TASK_ID)], env=BASE_ENV, input="y\n")
        assert result.exit_code == 0, result.output
        assert f'Delete task {_TASK_ID} "Review quarterly report"?' in result.output
        assert get_route.call_count == 1
        assert delete_route.call_count == 1
        assert _DELETE_DONE in result.output

    # criterio: 02-C11
    @respx.mock
    def test_prompt_n_does_nothing(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pynteracta.cli import _common  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["tasks", "delete", str(_TASK_ID)], env=BASE_ENV, input="n\n")
        assert result.exit_code == 0, result.output
        assert delete_route.call_count == 0
        assert _DELETE_DONE not in result.output

    # criterio: 02-C12
    @respx.mock
    def test_yes_skips_prompt(self, runner: CliRunner) -> None:
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["tasks", "delete", str(_TASK_ID), "--yes"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "?" not in result.output
        assert delete_route.call_count == 1
        assert _DELETE_DONE in result.output

    # criterio: 02-C12
    @respx.mock
    def test_short_yes_flag(self, runner: CliRunner) -> None:
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["tasks", "delete", str(_TASK_ID), "-y"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert delete_route.call_count == 1

    # criterio: 02-C12
    @respx.mock
    def test_non_interactive_without_yes_refuses(self, runner: CliRunner) -> None:
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["tasks", "delete", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_USAGE
        assert "--yes is required when not running interactively" in result.output
        assert delete_route.call_count == 0

    # criterio: 02-C11
    @respx.mock
    def test_json_output(self, runner: CliRunner) -> None:
        _mock_delete_flow()
        result = runner.invoke(
            app, ["--output", "json", "tasks", "delete", str(_TASK_ID), "--yes"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {"task_id": _TASK_ID, "post_id": _POST_ID}

    # criterio: 02-C11
    @respx.mock
    def test_not_found_exits_5_without_delete(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, {"message": "not found"}, status=404)
        delete_route = mock_json("DELETE", _TASKS_DELETE_PATH, {"postId": _POST_ID})
        result = runner.invoke(app, ["tasks", "delete", str(_TASK_ID), "--yes"], env=BASE_ENV)
        assert result.exit_code == 5  # noqa: PLR2004
        assert delete_route.call_count == 0
