# SPDX-License-Identifier: Apache-2.0
"""Test dei comandi di scrittura ``groups create|edit|delete|edit-members`` (spec 05)."""

from __future__ import annotations

import json
import pathlib

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_GROUP_ID = 201
_CREATED_GROUP_ID = 202
_EXIT_CONFIG = 2
_EXIT_CONFLICT = 9
BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}
_CREATE_PATH = "admin/manage/groups"
_FORM_PATH = f"admin/manage/groups/{_GROUP_ID}/edit"
_EDIT_PATH = f"admin/manage/groups/{_GROUP_ID}"
_EDIT_URL = f"{BASE_URL}/{_EDIT_PATH}"
_FORM = load_payload("get_group_for_edit_response.json")
_FORM_OCC_TOKEN = 5
_FORCED_OCC_TOKEN = 9
_MEMBER_IDS = [m["id"] for m in _FORM["members"]]
_EDIT_BASE = {
    "name": "Engineering",
    "email": "engineering@example.com",
    "externalId": "eng-001",
    "visible": True,
    "memberIds": _MEMBER_IDS,
}
_CONFLICT = f"Group {_GROUP_ID} changed since it was read: fetch it again and retry"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


def _interactive(monkeypatch: pytest.MonkeyPatch, value: bool) -> None:
    from pynteracta.cli import _common  # noqa: PLC0415

    monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: value)


def _mock_edit_flow(
    form: dict | None = None,  # type: ignore[type-arg]
) -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", _FORM_PATH, form if form is not None else _FORM)
    put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_group_response.json"))
    return get_route, put_route


class TestGroupsCreate:
    # criterio: 05-C17
    @respx.mock
    def test_flags_body_and_table(self, runner: CliRunner, snapshot: object) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_group_response.json"))
        result = runner.invoke(
            app,
            ["groups", "create", "--name", "G", "--member", "1", "--member", "2", "--system"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {"name": "G", "memberIds": [1, 2], "visible": False}
        assert result.output == snapshot

    # criterio: 05-C17
    @respx.mock
    def test_json_and_flags_merge(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_group_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"name": "X", "email": "g@b.it"}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "--output",
                "json",
                "groups",
                "create",
                "--name",
                "G",
                "--visible",
                "--external-id",
                "E1",
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "name": "G",
            "email": "g@b.it",
            "visible": True,
            "externalId": "E1",
        }
        assert json.loads(result.output)["group_id"] == _CREATED_GROUP_ID

    # criterio: 05-C17
    @respx.mock
    def test_unknown_json_key_exits_2(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_group_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"nope": 1}), encoding="utf-8")
        result = runner.invoke(app, ["groups", "create", "--json", str(body)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert route.call_count == 0


class TestGroupEditBase:
    # criterio: 05-C17
    def test_group_edit_base_from_form(self) -> None:
        from pynteracta.cli.groups_write import _group_edit_base  # noqa: PLC0415
        from pynteracta.models.facade.groups import GroupForEdit  # noqa: PLC0415

        assert _group_edit_base(GroupForEdit.from_dict(_FORM)) == _EDIT_BASE

    # criterio: 05-C17
    def test_group_edit_base_members_always_present(self) -> None:
        from pynteracta.cli.groups_write import _group_edit_base  # noqa: PLC0415
        from pynteracta.models.facade.groups import GroupForEdit  # noqa: PLC0415

        group = GroupForEdit.from_dict({"id": 1, "name": "G", "occToken": 1})
        assert _group_edit_base(group) == {"name": "G", "memberIds": []}


class TestGroupsEdit:
    # criterio: 05-C17
    @respx.mock
    def test_edit_reads_form_then_puts_patched_body(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_edit_flow()
        result = runner.invoke(
            app, ["groups", "edit", str(_GROUP_ID), "--name", "G2"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {**_EDIT_BASE, "name": "G2", "occToken": _FORM_OCC_TOKEN}
        assert str(_GROUP_ID) in result.output

    # criterio: 05-C17
    @respx.mock
    def test_json_member_ids_replace_read_list(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        _, put_route = _mock_edit_flow()
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"memberIds": [7]}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "groups",
                "edit",
                str(_GROUP_ID),
                "--json",
                str(body),
                "--system",
                "--occ-token",
                str(_FORCED_OCC_TOKEN),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            **_EDIT_BASE,
            "memberIds": [7],
            "visible": False,
            "occToken": _FORCED_OCC_TOKEN,
        }

    # criterio: 05-C15
    @respx.mock
    def test_409_exits_9_without_retry(self, runner: CliRunner) -> None:
        mock_json("GET", _FORM_PATH, _FORM)
        put_route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(409, json={"message": "Concurrency error"})
        )
        result = runner.invoke(
            app, ["groups", "edit", str(_GROUP_ID), "--name", "G2"], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFLICT
        assert _CONFLICT in result.output
        assert put_route.call_count == 1

    # criterio: 05-C17
    @respx.mock
    def test_missing_occ_token_exits_1_without_put(self, runner: CliRunner) -> None:
        form = dict(_FORM)
        form.pop("occToken")
        _, put_route = _mock_edit_flow(form)
        result = runner.invoke(
            app, ["groups", "edit", str(_GROUP_ID), "--name", "G2"], env=BASE_ENV
        )
        assert result.exit_code == 1
        assert put_route.call_count == 0


_DELETE_DONE = f"Group {_GROUP_ID} deleted"
_DELETE_PROMPT = f'Delete group {_GROUP_ID} "Engineering"?'


def _mock_delete_flow() -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", _FORM_PATH, _FORM)
    delete_route = respx.delete(_EDIT_URL).mock(return_value=httpx.Response(200))
    return get_route, delete_route


class TestGroupsDelete:
    # criterio: 05-C16
    @respx.mock
    def test_prompt_shows_id_and_name_and_y_deletes(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _interactive(monkeypatch, True)
        get_route, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["groups", "delete", str(_GROUP_ID)], env=BASE_ENV, input="y\n")
        assert result.exit_code == 0, result.output
        assert _DELETE_PROMPT in result.output
        assert get_route.call_count == 1
        assert delete_route.call_count == 1
        assert _DELETE_DONE in result.output

    # criterio: 05-C16
    @respx.mock
    def test_prompt_n_does_nothing(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _interactive(monkeypatch, True)
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["groups", "delete", str(_GROUP_ID)], env=BASE_ENV, input="n\n")
        assert result.exit_code == 0, result.output
        assert delete_route.call_count == 0

    # criterio: 05-C16
    @respx.mock
    def test_yes_skips_prompt(self, runner: CliRunner) -> None:
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["groups", "delete", str(_GROUP_ID), "--yes"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "?" not in result.output
        assert delete_route.call_count == 1
        assert _DELETE_DONE in result.output

    # criterio: 05-C16
    @respx.mock
    def test_json_output(self, runner: CliRunner) -> None:
        _mock_delete_flow()
        result = runner.invoke(
            app, ["--output", "json", "groups", "delete", str(_GROUP_ID), "-y"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {"group_id": _GROUP_ID}

    # criterio: 05-C16
    @respx.mock
    def test_non_interactive_without_yes_refuses(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _interactive(monkeypatch, False)
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["groups", "delete", str(_GROUP_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "--yes is required" in result.output
        assert delete_route.call_count == 0
