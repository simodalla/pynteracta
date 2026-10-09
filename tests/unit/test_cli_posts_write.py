# SPDX-License-Identifier: Apache-2.0
"""CLI: comandi di scrittura dei post (spec 03)."""

from __future__ import annotations

import json
import pathlib
from typing import NamedTuple

import httpx
import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli.posts_write import copy_base, edit_base, merge_custom_data
from pynteracta.models.facade.posts_write import PostForCopy, PostForEdit

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
_EDIT_PATH = f"{_MANAGE}/edit-post/{_POST_ID}/{_OCC_TOKEN}"
_CUSTOM_DATA_PATH = f"{_MANAGE}/edit-post-custom-data/{_POST_ID}/{_OCC_TOKEN}"
_COPY_PATH = f"{_MANAGE}/copy-post/{_POST_ID}/{_OCC_TOKEN}"
_EXIT_GENERIC = 1
_WATCHERS_PATH = f"{_MANAGE}/edit-post-watchers/{_POST_ID}"
_DETAIL_PATH = f"communication/posts/data/post-detail-by-id/{_POST_ID}"
_POST_TITLE = "Aggiornamento procedure sicurezza Q2 2026"
_EXIT_NOT_FOUND = 5
_EXIT_CONFLICT = 9
_HTTP_404 = 404
_HTTP_409 = 409
_CONFLICT_MESSAGE = f"Post {_POST_ID} changed since it was read: fetch it again and retry"
_READ_CONTENT = load_payload("post_for_edit_response.json")["contentData"]
_READ_BASE = {
    "title": _READ_CONTENT["title"],
    "description": _READ_CONTENT["descriptionDelta"],
    "descriptionFormat": 1,
    "customData": {"1411": 226, "1413": True},
    "visibility": 1,
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route, index: int = 0) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


# criterio: 03-C18
@pytest.mark.parametrize(
    "command",
    [
        "create",
        "comment",
        "get-for-create",
        "get-for-edit",
        "get-for-copy",
        "edit",
        "edit-custom-data",
        "copy",
        "edit-watchers",
        "delete",
        "mark-erasable",
    ],
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


class TestPostsEdit:
    # criterio: 03-C19
    def test_edit_base_from_fixture(self) -> None:
        form = PostForEdit.from_dict(load_payload("post_for_edit_response.json"))
        assert edit_base(form) == _READ_BASE

    # criterio: 03-C19
    def test_edit_base_skips_missing_fields(self) -> None:
        payload = load_payload("post_for_edit_response.json")
        for key in ("descriptionDelta", "customData", "visibility"):
            payload["contentData"][key] = None
        assert edit_base(PostForEdit.from_dict(payload)) == {"title": _READ_CONTENT["title"]}
        assert edit_base(PostForEdit.from_dict({"occToken": 1})) == {}

    # criterio: 03-C19
    @respx.mock
    def test_edit_reads_for_edit_then_puts_patched_body(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(app, ["posts", "edit", str(_POST_ID), "--title", "T2"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {**_READ_BASE, "title": "T2"}

    # criterio: 03-C19
    @respx.mock
    def test_edit_with_occ_token_still_reads_base(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json(
            "PUT", f"{_MANAGE}/edit-post/{_POST_ID}/3", load_payload("edit_post_response.json")
        )
        result = runner.invoke(
            app,
            ["posts", "edit", str(_POST_ID), "--title", "T2", "--occ-token", "3"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert _sent_body(put_route) == {**_READ_BASE, "title": "T2"}

    # criterio: 03-C19
    @respx.mock
    def test_edit_base_skips_missing_fields_in_request(self, runner: CliRunner) -> None:
        payload = load_payload("post_for_edit_response.json")
        payload["contentData"]["descriptionDelta"] = None
        payload["contentData"]["customData"] = None
        mock_json("GET", _FOR_EDIT_PATH, payload)
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(app, ["posts", "edit", str(_POST_ID), "--title", "T2"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {"title": "T2", "visibility": 1}

    # criterio: 03-C19
    @respx.mock
    def test_edit_without_occ_token_in_response_exits_1(self, runner: CliRunner) -> None:
        payload = load_payload("post_for_edit_response.json")
        payload["occToken"] = None
        mock_json("GET", _FOR_EDIT_PATH, payload)
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(app, ["posts", "edit", str(_POST_ID), "--title", "T2"], env=BASE_ENV)
        assert result.exit_code == _EXIT_GENERIC
        assert "--occ-token" in result.output
        assert put_route.call_count == 0

    # criterio: 03-C19
    @respx.mock
    def test_edit_post_not_found_exits_5_without_put(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, {"message": "not found"}, status=_HTTP_404)
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(
            app,
            ["posts", "edit", str(_POST_ID), "--title", "T2", "--occ-token", "5"],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_NOT_FOUND
        assert put_route.call_count == 0

    # criterio: 03-C20
    @respx.mock
    def test_edit_description_flag_sets_plain_format(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(
            app, ["posts", "edit", str(_POST_ID), "--description", "X"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = _sent_body(put_route)
        assert body["description"] == "X"
        assert body["descriptionFormat"] == 2  # noqa: PLR2004

    # criterio: 03-C20
    @respx.mock
    def test_edit_flags_win_over_json_over_read(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        body_file = tmp_path / "body.json"
        body_file.write_text(json.dumps({"visibility": 2, "customData": {"1412": "a"}}), "utf-8")
        result = runner.invoke(
            app,
            [
                "posts", "edit", str(_POST_ID),
                "--description", "X",
                "--custom-data", "1411=300",
                "--json", str(body_file),
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "title": _READ_CONTENT["title"],
            "description": "X",
            "descriptionFormat": 2,
            "visibility": 2,
            "customData": {"1411": 300, "1412": "a", "1413": True},
        }

    # criterio: 03-C20
    @respx.mock
    def test_edit_json_description_keeps_read_format(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        body_file = tmp_path / "body.json"
        body_file.write_text(json.dumps({"description": '{"ops":[]}'}), "utf-8")
        result = runner.invoke(
            app, ["posts", "edit", str(_POST_ID), "--json", str(body_file)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = _sent_body(put_route)
        assert body["description"] == '{"ops":[]}'
        assert body["descriptionFormat"] == 1

    # criterio: 03-C20
    @respx.mock
    def test_edit_watcher_flags_map_to_add_and_remove(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(
            app,
            [
                "posts", "edit", str(_POST_ID),
                "--watcher-user", "7",
                "--remove-watcher-user", "8",
                "--draft",
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            **_READ_BASE,
            "addWatcherUserIds": [7],
            "removeWatcherUserIds": [8],
            "draft": True,
        }

    # criterio: 03-C20
    def test_merge_custom_data(self) -> None:
        assert merge_custom_data(
            {"customData": {"1411": 226, "1413": True}},
            {"customData": {"1412": "a", "1411": 1}},
            {"1411": 300},
        ) == {"1411": 300, "1412": "a", "1413": True}
        assert merge_custom_data({}, {}, {}) == {}

    # criterio: 03-C19
    @respx.mock
    def test_edit_json_output(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        mock_json("PUT", _EDIT_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "edit", str(_POST_ID), "--title", "T2"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["id"] == _POST_ID
        assert data["next_occ_token"] == 6  # noqa: PLR2004


class TestPostsEditCustomData:
    # criterio: 03-C21
    @respx.mock
    def test_reads_then_puts_merged_custom_data(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json("PUT", _CUSTOM_DATA_PATH, load_payload("edit_post_response.json"))
        result = runner.invoke(
            app,
            ["posts", "edit-custom-data", str(_POST_ID), "--custom-data", "1411=300"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert _sent_body(put_route) == {"customData": {"1411": 300, "1413": True}}

    # criterio: 03-C21
    @respx.mock
    def test_json_and_occ_token(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        put_route = mock_json(
            "PUT",
            f"{_MANAGE}/edit-post-custom-data/{_POST_ID}/3",
            load_payload("edit_post_response.json"),
        )
        body_file = tmp_path / "body.json"
        body_file.write_text(
            json.dumps({"customData": {"1412": "a"}, "deltaAreaFormat": 2}), "utf-8"
        )
        result = runner.invoke(
            app,
            [
                "posts", "edit-custom-data", str(_POST_ID),
                "--json", str(body_file),
                "--occ-token", "3",
            ],
            env=BASE_ENV,
        )  # fmt: skip
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "customData": {"1411": 226, "1412": "a", "1413": True},
            "deltaAreaFormat": 2,
        }

    # criterio: 03-C21
    @respx.mock
    def test_without_data_exits_2_without_requests(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _FOR_EDIT_PATH, load_payload("post_for_edit_response.json"))
        result = runner.invoke(app, ["posts", "edit-custom-data", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert get_route.call_count == 0


class TestPostsCopy:
    # criterio: 03-C22
    def test_copy_base_from_fixture(self) -> None:
        form = PostForCopy.from_dict(load_payload("post_for_copy_response.json"))
        assert copy_base(form) == {**_READ_BASE, "announcement": False}

    # criterio: 03-C22
    @respx.mock
    def test_copy_reads_for_copy_then_puts_base_with_title(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _FOR_COPY_PATH, load_payload("post_for_copy_response.json"))
        put_route = mock_json("PUT", _COPY_PATH, load_payload("copy_post_response.json"))
        result = runner.invoke(
            app, ["posts", "copy", str(_POST_ID), "--title", "Copia"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert _sent_body(put_route) == {**_READ_BASE, "announcement": False, "title": "Copia"}

    # criterio: 03-C22
    @respx.mock
    def test_copy_table_shows_new_post(self, runner: CliRunner) -> None:
        mock_json("GET", _FOR_COPY_PATH, load_payload("post_for_copy_response.json"))
        mock_json("PUT", _COPY_PATH, load_payload("copy_post_response.json"))
        result = runner.invoke(
            app,
            ["posts", "copy", str(_POST_ID), "--title", "Copia", "--announcement"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert "21271" in result.output
        assert "Copia della procedura" in result.output


class TestPostsConflicts:
    # criterio: 03-C28
    @pytest.mark.parametrize(
        ("args", "get_path", "get_fixture", "write_path"),
        [
            (["edit", "--title", "T2"], _FOR_EDIT_PATH, "post_for_edit_response.json", _EDIT_PATH),
            (
                ["edit-custom-data", "--custom-data", "1411=1"],
                _FOR_EDIT_PATH,
                "post_for_edit_response.json",
                _CUSTOM_DATA_PATH,
            ),
            (["copy", "--title", "C"], _FOR_COPY_PATH, "post_for_copy_response.json", _COPY_PATH),
        ],
    )
    @respx.mock
    def test_conflict_exits_9_without_retry(
        self,
        runner: CliRunner,
        args: list[str],
        get_path: str,
        get_fixture: str,
        write_path: str,
    ) -> None:
        mock_json("GET", get_path, load_payload(get_fixture))
        write_route = mock_json("PUT", write_path, {"message": "conflict"}, status=_HTTP_409)
        command, *rest = args
        result = runner.invoke(app, ["posts", command, str(_POST_ID), *rest], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFLICT
        assert _CONFLICT_MESSAGE in result.output
        assert write_route.call_count == 1


class TestPostsEditWatchers:
    # criterio: 03-C23
    @respx.mock
    def test_add_and_remove_body_and_message(self, runner: CliRunner) -> None:
        route = respx.put(f"https://api.example.com/portal/api/external/v2/{_WATCHERS_PATH}").mock(
            return_value=httpx.Response(200)
        )
        result = runner.invoke(
            app,
            ["posts", "edit-watchers", str(_POST_ID), "--add", "7", "--remove", "8"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {"addWatcherUserIds": [7], "removeWatcherUserIds": [8]}
        assert f"Watchers of post {_POST_ID} updated" in result.output

    # criterio: 03-C23
    @respx.mock
    def test_json_output(self, runner: CliRunner) -> None:
        respx.put(f"https://api.example.com/portal/api/external/v2/{_WATCHERS_PATH}").mock(
            return_value=httpx.Response(200)
        )
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "edit-watchers", str(_POST_ID), "--add", "7"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {
            "post_id": _POST_ID,
            "added_user_ids": [7],
            "removed_user_ids": [],
        }

    # criterio: 03-C23
    @respx.mock
    def test_without_flags_exits_2(self, runner: CliRunner) -> None:
        route = respx.put(f"https://api.example.com/portal/api/external/v2/{_WATCHERS_PATH}").mock(
            return_value=httpx.Response(200)
        )
        result = runner.invoke(app, ["posts", "edit-watchers", str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0


class _Destructive(NamedTuple):
    command: str
    method: str
    path: str
    fixture: str
    prompt: str
    done: str


_DESTRUCTIVE = [
    _Destructive(
        "delete",
        "DELETE",
        f"{_MANAGE}/delete-post/{_POST_ID}",
        "delete_post_response.json",
        f'Delete post {_POST_ID} "{_POST_TITLE}"?',
        f"Post {_POST_ID} deleted",
    ),
    _Destructive(
        "mark-erasable",
        "PUT",
        f"{_MANAGE}/mark-post-as-erasable/{_POST_ID}",
        "mark_post_erasable_response.json",
        f'Mark post {_POST_ID} "{_POST_TITLE}" as erasable?',
        f"Post {_POST_ID} marked as erasable",
    ),
]


def _mock_destructive(case: _Destructive) -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", _DETAIL_PATH, load_payload("get_post_detail_response.json"))
    return get_route, mock_json(case.method, case.path, load_payload(case.fixture))


# criterio: 03-C24
@pytest.mark.parametrize("case", _DESTRUCTIVE, ids=["delete", "mark-erasable"])
class TestPostsDestructive:
    @respx.mock
    def test_prompt_shows_id_and_title_and_y_writes(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, case: _Destructive
    ) -> None:
        from pynteracta.cli import _common  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)
        get_route, write_route = _mock_destructive(case)
        result = runner.invoke(
            app, ["posts", case.command, str(_POST_ID)], env=BASE_ENV, input="y\n"
        )
        assert result.exit_code == 0, result.output
        assert case.prompt in result.output
        assert get_route.call_count == 1
        assert write_route.call_count == 1
        assert case.done in result.output

    @respx.mock
    def test_prompt_n_does_nothing(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch, case: _Destructive
    ) -> None:
        from pynteracta.cli import _common  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)
        _, write_route = _mock_destructive(case)
        result = runner.invoke(
            app, ["posts", case.command, str(_POST_ID)], env=BASE_ENV, input="n\n"
        )
        assert result.exit_code == 0, result.output
        assert write_route.call_count == 0
        assert case.done not in result.output

    @respx.mock
    def test_yes_skips_prompt(self, runner: CliRunner, case: _Destructive) -> None:
        _, write_route = _mock_destructive(case)
        result = runner.invoke(app, ["posts", case.command, str(_POST_ID), "--yes"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert case.prompt not in result.output
        assert write_route.call_count == 1
        assert case.done in result.output

    @respx.mock
    def test_non_interactive_without_yes_refuses(
        self, runner: CliRunner, case: _Destructive
    ) -> None:
        _, write_route = _mock_destructive(case)
        result = runner.invoke(app, ["posts", case.command, str(_POST_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "--yes is required" in result.output
        assert write_route.call_count == 0

    @respx.mock
    def test_json_output(self, runner: CliRunner, case: _Destructive) -> None:
        _mock_destructive(case)
        result = runner.invoke(
            app, ["--output", "json", "posts", case.command, str(_POST_ID), "-y"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {"post_id": _POST_ID}
