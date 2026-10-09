# SPDX-License-Identifier: Apache-2.0
"""CLI: comandi di scrittura dei post (spec 03)."""

from __future__ import annotations

import json
import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_COMMUNITY_ID = 79
_POST_ID = 21269
_OCC_TOKEN = 5
_EXIT_CONFIG = 2
_EXIT_VALIDATION = 6
_HTTP_400 = 400

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}

_MANAGE = "communication/posts/manage"
_CREATE_PATH = f"{_MANAGE}/create-post/{_COMMUNITY_ID}"
_COMMENT_PATH = f"{_MANAGE}/create-comment/{_POST_ID}"
_FOR_CREATE_PATH = f"{_MANAGE}/post-data-for-create/{_COMMUNITY_ID}"
_FOR_EDIT_PATH = f"{_MANAGE}/post-data-for-edit/{_POST_ID}"
_FOR_COPY_PATH = f"{_MANAGE}/post-data-for-copy/{_POST_ID}"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route, index: int = 0) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


# criterio: 03-C18
@pytest.mark.parametrize(
    "command", ["create", "comment", "get-for-create", "get-for-edit", "get-for-copy"]
)
def test_posts_help_lists_write_commands(runner: CliRunner, command: str) -> None:
    result = runner.invoke(app, ["posts", "--help"], env=BASE_ENV)
    assert result.exit_code == 0
    assert command in result.output


class TestPostsCreate:
    # criterio: 03-C18
    @respx.mock
    def test_flags_and_json_merge_flags_win(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        body_file = tmp_path / "body.json"
        body_file.write_text(json.dumps({"title": "X", "visibility": 1}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "posts", "create", str(_COMMUNITY_ID),
                "--title", "T",
                "--description", "D",
                "--custom-data", "1411=226",
                "--watcher-user", "7",
                "--announcement",
                "--json", str(body_file),
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "announcement": True,
            "title": "T",
            "description": "D",
            "descriptionFormat": 2,
            "customData": {"1411": 226},
            "watcherUserIds": [7],
            "visibility": 1,
        }

    # criterio: 03-C18
    @respx.mock
    def test_announcement_false_by_default(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        result = runner.invoke(
            app, ["posts", "create", str(_COMMUNITY_ID), "--title", "T"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"announcement": False, "title": "T"}

    # criterio: 03-C18
    @respx.mock
    def test_json_custom_data_merged_with_flags(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        body_file = tmp_path / "body.json"
        body_file.write_text(json.dumps({"customData": {"1411": 1, "1412": "a"}}), "utf-8")
        result = runner.invoke(
            app,
            [
                "posts", "create", str(_COMMUNITY_ID),
                "--custom-data", "1411=226",
                "--json", str(body_file),
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert _sent_body(route)["customData"] == {"1411": 226, "1412": "a"}

    # criterio: 03-C18
    @respx.mock
    def test_scheduled_publication_default_timezone(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        result = runner.invoke(
            app,
            [
                "posts", "create", str(_COMMUNITY_ID),
                "--draft",
                "--scheduled-publication", "2026-12-31T18:00",
                "--workflow-init-state", "31",
                "--client-uid", "uid-1",
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "announcement": False,
            "draft": True,
            "scheduledPublication": {"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"},
            "workflowInitStateId": 31,
            "clientUid": "uid-1",
        }

    # criterio: 03-C18
    @respx.mock
    def test_custom_data_bad_token_exits_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        result = runner.invoke(
            app,
            ["posts", "create", str(_COMMUNITY_ID), "--custom-data", "1411"],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0

    # criterio: 03-C16
    @respx.mock
    def test_validation_error_exits_6_with_body(self, runner: CliRunner) -> None:
        route = mock_json(
            "POST",
            _CREATE_PATH,
            load_payload("custom_field_validation_error_response.json"),
            status=_HTTP_400,
        )
        result = runner.invoke(
            app,
            ["posts", "create", str(_COMMUNITY_ID), "--custom-data", "1411=bad"],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_VALIDATION
        assert "INVALID_VALUE" in result.output
        assert route.call_count == 1

    # criterio: 03-C18
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        result = runner.invoke(
            app, ["posts", "create", str(_COMMUNITY_ID), "--title", "T"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 03-C18
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_post_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "create", str(_COMMUNITY_ID), "--title", "T"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot


class TestPostsComment:
    # criterio: 03-C25
    @respx.mock
    def test_text_and_parent_body(self, runner: CliRunner) -> None:
        route = mock_json("POST", _COMMENT_PATH, load_payload("create_post_comment_response.json"))
        result = runner.invoke(
            app,
            ["posts", "comment", str(_POST_ID), "--text", "Ciao", "--parent", "5"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {"comment": "Ciao", "commentFormat": 2, "parentCommentId": 5}

    # criterio: 03-C25
    @respx.mock
    def test_json_body_with_client_uid(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _COMMENT_PATH, load_payload("create_post_comment_response.json"))
        body_file = tmp_path / "c.json"
        body_file.write_text(json.dumps({"comment": '{"ops":[]}', "commentFormat": 1}), "utf-8")
        result = runner.invoke(
            app,
            ["posts", "comment", str(_POST_ID), "--json", str(body_file), "--client-uid", "u"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "comment": '{"ops":[]}',
            "commentFormat": 1,
            "clientUid": "u",
        }

    # criterio: 03-C25
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _COMMENT_PATH, load_payload("create_post_comment_response.json"))
        result = runner.invoke(
            app, ["posts", "comment", str(_POST_ID), "--text", "Ciao"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 03-C25
    @respx.mock
    def test_json_output(self, runner: CliRunner) -> None:
        mock_json("POST", _COMMENT_PATH, load_payload("create_post_comment_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "comment", str(_POST_ID), "--text", "Ciao"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["id"] == 5601  # noqa: PLR2004

    # criterio: 03-C25
    @respx.mock
    def test_without_text_exits_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _COMMENT_PATH, load_payload("create_post_comment_response.json"))
        result = runner.invoke(app, ["posts", "comment", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0


class TestPostsPrep:
    # criterio: 03-C26
    @respx.mock
    def test_get_for_edit_table_starts_with_occ_token(
        self, runner: CliRunner, snapshot: object
    ) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        result = runner.invoke(app, ["posts", "get-for-edit", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        lines = [line for line in result.output.splitlines() if "│" in line]
        assert "occ_token" in lines[0]
        assert result.output == snapshot

    # criterio: 03-C26
    @respx.mock
    def test_get_for_copy_table(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_COPY_PATH, load_payload("post_for_copy_response.json"))
        result = runner.invoke(app, ["posts", "get-for-copy", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "occ_token" in result.output
        assert "Procedura di prova" in result.output

    # criterio: 03-C26
    @respx.mock
    def test_get_for_create_table(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_CREATE_PATH, load_payload("post_for_create_response.json"))
        result = runner.invoke(app, ["posts", "get-for-create", str(_COMMUNITY_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "visibility" in result.output
        assert "announcement" in result.output

    # criterio: 03-C26
    @respx.mock
    def test_no_attachments_sends_query(self, runner: CliRunner) -> None:
        route = mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        result = runner.invoke(
            app, ["posts", "get-for-edit", str(_POST_ID), "--no-attachments"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert route.calls[0].request.url.params["loadAttachments"] == "false"

    # criterio: 03-C26
    @respx.mock
    def test_full_json(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "get-for-edit", str(_POST_ID), "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["occToken"] == _OCC_TOKEN
        assert data["contentData"]["customData"] == {"1411": 226, "1413": True}
