# SPDX-License-Identifier: Apache-2.0
"""Test del comando ``admin-manage edit-workspace`` (spec 06)."""

from __future__ import annotations

import copy
import json
import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli.admin_manage_write import _workspace_body

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}
_WORKSPACE_ID = 88
_OCC_TOKEN = 17
_FORM_PATH = f"admin/manage/workspaces/{_WORKSPACE_ID}/edit"
_PUT_PATH = f"admin/manage/workspaces/{_WORKSPACE_ID}/{_OCC_TOKEN}"
_FORM = load_payload("get_workspace_for_edit_response.json")
_EXIT_GENERIC = 1
_EXIT_CONFIG = 2
_EXIT_CONFLICT = 9
_ARGS = [
    "admin-manage",
    "edit-workspace",
    str(_WORKSPACE_ID),
    "--name",
    "WS",
    "--description",
    "it=Desc",
    "--add-user",
    "1",
    "--remove-group",
    "2",
    "--add-user-role",
    "1=4",
    "--remove-role-association",
    "9",
]
_EXPECTED_BODY = {
    "name": "WS",
    "description": {"it": "Desc"},
    "addUserIds": [1],
    "removeGroupIds": [2],
    "addUserRoleAssociations": [{"userId": 1, "roleId": 4}],
    "removeRoleAssociationIds": [9],
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


def _mock_flow(*, status: int = 200) -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", _FORM_PATH, _FORM)
    put_route = mock_json(
        "PUT",
        _PUT_PATH,
        load_payload("edit_workspace_response.json") if status == 200 else {},  # noqa: PLR2004
        status=status,
    )
    return get_route, put_route


# criterio: 06-C17
def test_workspace_body_all_inputs() -> None:
    body = _workspace_body(
        {"description": {"en": "Ops"}, "translations": {"en": "WS"}},
        name="WS",
        description={"it": "Desc"},
        add_user=[1],
        remove_user=[3],
        add_group=[5],
        remove_group=[2],
        user_roles=[(1, 4)],
        group_roles=[(5, 6)],
        remove_role_association=[9],
    )
    assert body == {
        "description": {"en": "Ops", "it": "Desc"},
        "translations": {"en": "WS"},
        "name": "WS",
        "addUserIds": [1],
        "removeUserIds": [3],
        "addGroupIds": [5],
        "removeGroupIds": [2],
        "addUserRoleAssociations": [{"userId": 1, "roleId": 4}],
        "addGroupRoleAssociations": [{"groupId": 5, "roleId": 6}],
        "removeRoleAssociationIds": [9],
    }


# criterio: 06-C17
def test_workspace_body_empty_without_inputs() -> None:
    assert (
        _workspace_body(
            {},
            name=None,
            description={},
            add_user=None,
            remove_user=[],
            add_group=None,
            remove_group=None,
            user_roles=[],
            group_roles=[],
            remove_role_association=None,
        )
        == {}
    )


class TestEditWorkspace:
    # criterio: 06-C17
    @respx.mock
    def test_flags_read_token_then_put_exact_body(
        self, runner: CliRunner, snapshot: object
    ) -> None:
        get_route, put_route = _mock_flow()
        result = runner.invoke(app, _ARGS, env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == _EXPECTED_BODY
        assert result.output == snapshot

    # criterio: 06-C17
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        _mock_flow()
        result = runner.invoke(app, ["--output", "json", *_ARGS], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 06-C17
    @respx.mock
    def test_occ_token_skips_get(self, runner: CliRunner) -> None:
        get_route = mock_json("GET", _FORM_PATH, _FORM)
        put_route = mock_json(
            "PUT",
            f"admin/manage/workspaces/{_WORKSPACE_ID}/10",
            load_payload("edit_workspace_response.json"),
        )
        result = runner.invoke(app, [*_ARGS, "--occ-token", "10"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert not get_route.called
        assert put_route.call_count == 1

    # criterio: 06-C17
    @respx.mock
    def test_add_user_role_without_eq_exits_2(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_flow()
        result = runner.invoke(
            app,
            ["admin-manage", "edit-workspace", str(_WORKSPACE_ID), "--add-user-role", "1"],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_CONFIG
        assert "USER_ID=ROLE_ID" in result.output
        assert not get_route.called
        assert not put_route.called

    # criterio: 06-C17
    @respx.mock
    def test_no_flags_exits_2_without_requests(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_flow()
        result = runner.invoke(
            app, ["admin-manage", "edit-workspace", str(_WORKSPACE_ID)], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFIG
        assert "Nothing to send" in result.output
        assert not get_route.called
        assert not put_route.called

    # criterio: 06-C17
    @respx.mock
    def test_json_description_merged_with_flag(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        _, put_route = _mock_flow()
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"description": {"it": "X", "en": "Ops"}}), "utf-8")
        result = runner.invoke(
            app,
            [
                "admin-manage",
                "edit-workspace",
                str(_WORKSPACE_ID),
                "--description",
                "it=Desc",
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {"description": {"it": "Desc", "en": "Ops"}}

    @respx.mock
    def test_missing_occ_token_exits_1(self, runner: CliRunner) -> None:
        form = copy.deepcopy(_FORM)
        form.pop("occToken")
        mock_json("GET", _FORM_PATH, form)
        result = runner.invoke(
            app,
            ["admin-manage", "edit-workspace", str(_WORKSPACE_ID), "--name", "WS"],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_GENERIC
        assert "--occ-token" in result.output

    # criterio: 06-C13
    @respx.mock
    def test_409_exits_9(self, runner: CliRunner) -> None:
        _, put_route = _mock_flow(status=409)
        result = runner.invoke(app, _ARGS, env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFLICT
        assert (
            f"Workspace {_WORKSPACE_ID} changed since it was read: fetch it again and retry"
            in result.output
        )
        assert put_route.call_count == 1
