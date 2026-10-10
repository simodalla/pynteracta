# SPDX-License-Identifier: Apache-2.0
"""Test dei comandi di scrittura di cataloghi e voci (spec 06)."""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Any

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli.catalogs_write import _catalog_edit_base, _entry_edit_base
from pynteracta.models.facade.admin_manage import CatalogEntryForEdit, CatalogForEdit

BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}
_EXIT_CONFIG = 2
_CATALOG_ID = 5
_ENTRY_ID = 100
_PARENT_ID = 3
_CATALOGS_PATH = "admin/manage/catalogs"
_ENTRIES_PATH = f"admin/manage/catalogs/{_CATALOG_ID}/entries"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route, index: int = 0) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


class TestCatalogsCreate:
    # criterio: 06-C10
    @respx.mock
    def test_flags_and_json_merge_name_key_by_key(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"name": {"it": "X", "de": "Standorte"}}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "catalogs",
                "create",
                "--name",
                "it=Sedi",
                "--name",
                "en=Sites",
                "--parent",
                str(_PARENT_ID),
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "name": {"it": "Sedi", "de": "Standorte", "en": "Sites"},
            "parentId": _PARENT_ID,
        }

    # criterio: 06-C10
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        result = runner.invoke(
            app,
            ["catalogs", "create", "--name", "it=Sedi", "--parent", str(_PARENT_ID)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 06-C10
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "catalogs", "create", "--name", "it=Sedi"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 06-C10
    @pytest.mark.parametrize("value", ["Sedi", "=Sedi"])
    @respx.mock
    def test_malformed_name_exits_2_without_requests(self, runner: CliRunner, value: str) -> None:
        route = mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        result = runner.invoke(app, ["catalogs", "create", "--name", value], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "LANG=TEXT" in result.output
        assert not route.called

    @respx.mock
    def test_json_unknown_key_exits_2(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _CATALOGS_PATH, load_payload("create_catalog_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"title": "x"}), encoding="utf-8")
        result = runner.invoke(app, ["catalogs", "create", "--json", str(body)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert not route.called


class TestCatalogEntriesCreate:
    # criterio: 06-C16
    @respx.mock
    def test_flags_body_and_table(self, runner: CliRunner, snapshot: object) -> None:
        route = mock_json("POST", _ENTRIES_PATH, load_payload("create_catalog_entry_response.json"))
        result = runner.invoke(
            app,
            [
                "catalogs",
                "create-entry",
                str(_CATALOG_ID),
                "--label",
                "it=Bologna",
                "--parent-entry",
                "10",
                "--parent-entry",
                "11",
                "--external-id",
                "BO",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "label": {"it": "Bologna"},
            "parentIds": [10, 11],
            "externalId": "BO",
        }
        assert result.output == snapshot

    # criterio: 06-C16
    @respx.mock
    def test_json_label_merged_with_flag(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _ENTRIES_PATH, load_payload("create_catalog_entry_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"label": {"it": "Bologna"}}), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "catalogs",
                "create-entry",
                str(_CATALOG_ID),
                "--label",
                "en=Bologna",
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {"label": {"it": "Bologna", "en": "Bologna"}}


_CATALOG_PATH = f"{_CATALOGS_PATH}/{_CATALOG_ID}"
_ENTRY_PATH = f"{_ENTRIES_PATH}/{_ENTRY_ID}"
_CATALOG_FORM = load_payload("get_catalog_for_edit_response.json")
_ENTRY_FORM = load_payload("get_catalog_entry_for_edit_response.json")
_CATALOG_OCC_TOKEN = 9
_ENTRY_OCC_TOKEN = 4
_EXIT_GENERIC = 1
_EXIT_NOT_FOUND = 5
_EXIT_CONFLICT = 9


def _form_with_parent() -> dict[str, Any]:
    form = copy.deepcopy(_CATALOG_FORM)
    form["contentData"]["parentCatalog"] = {"id": _PARENT_ID, "name": "Root"}
    return form


def _mock_catalog_edit(
    form: dict[str, Any], *, status: int = 200
) -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", f"{_CATALOG_PATH}/edit", form)
    put_route = mock_json(
        "PUT",
        _CATALOG_PATH,
        load_payload("edit_catalog_response.json") if status == 200 else {},  # noqa: PLR2004
        status=status,
    )
    return get_route, put_route


def _mock_entry_edit(form: dict[str, Any], *, status: int = 200) -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", f"{_ENTRY_PATH}/edit", form)
    put_route = mock_json(
        "PUT",
        _ENTRY_PATH,
        load_payload("edit_catalog_entry_response.json") if status == 200 else {},  # noqa: PLR2004
        status=status,
    )
    return get_route, put_route


# criterio: 06-C11
def test_catalog_edit_base_with_parent() -> None:
    assert _catalog_edit_base(CatalogForEdit.from_dict(_form_with_parent())) == {
        "name": {"en": "Departments", "it": "Reparti"},
        "parentId": _PARENT_ID,
    }


# criterio: 06-C11
def test_catalog_edit_base_without_parent() -> None:
    assert _catalog_edit_base(CatalogForEdit.from_dict(_CATALOG_FORM)) == {
        "name": {"en": "Departments", "it": "Reparti"},
    }


# criterio: 06-C11
def test_catalog_edit_base_without_content_data() -> None:
    assert _catalog_edit_base(CatalogForEdit.from_dict({"id": _CATALOG_ID})) == {}


# criterio: 06-C12
def test_entry_edit_base_with_parents() -> None:
    assert _entry_edit_base(CatalogEntryForEdit.from_dict(_ENTRY_FORM)) == {
        "label": {"en": "Engineering", "it": "Ingegneria"},
        "externalId": "ENG",
        "parentIds": [1],
    }


# criterio: 06-C12
def test_entry_edit_base_without_parents() -> None:
    form = copy.deepcopy(_ENTRY_FORM)
    form.pop("parents")
    assert "parentIds" not in _entry_edit_base(CatalogEntryForEdit.from_dict(form))


# criterio: 06-C12
def test_entry_edit_base_skips_parents_without_id() -> None:
    form = copy.deepcopy(_ENTRY_FORM)
    form["parents"] = [{"label": "x"}, {"id": 2}]
    assert _entry_edit_base(CatalogEntryForEdit.from_dict(form))["parentIds"] == [2]


class TestCatalogsEdit:
    # criterio: 06-C11
    @respx.mock
    def test_edit_reads_form_then_puts_patched_body(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_catalog_edit(_form_with_parent())
        result = runner.invoke(
            app, ["catalogs", "edit", str(_CATALOG_ID), "--name", "en=Sites"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {
            "name": {"en": "Sites", "it": "Reparti"},
            "parentId": _PARENT_ID,
            "occToken": _CATALOG_OCC_TOKEN,
        }

    # criterio: 06-C11
    @respx.mock
    def test_parent_flag_wins(self, runner: CliRunner) -> None:
        _, put_route = _mock_catalog_edit(_form_with_parent())
        result = runner.invoke(
            app, ["catalogs", "edit", str(_CATALOG_ID), "--parent", "4"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route)["parentId"] == 4  # noqa: PLR2004

    # criterio: 06-C11
    @respx.mock
    def test_occ_token_overrides_but_get_still_happens(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_catalog_edit(_CATALOG_FORM)
        result = runner.invoke(
            app,
            ["catalogs", "edit", str(_CATALOG_ID), "--name", "it=Sedi", "--occ-token", "8"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.called
        assert _sent_body(put_route)["occToken"] == 8  # noqa: PLR2004

    # criterio: 06-C11
    @respx.mock
    def test_form_without_parent_omits_parent_id(self, runner: CliRunner) -> None:
        _, put_route = _mock_catalog_edit(_CATALOG_FORM)
        result = runner.invoke(
            app, ["catalogs", "edit", str(_CATALOG_ID), "--name", "en=Sites"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "name": {"en": "Sites", "it": "Reparti"},
            "occToken": _CATALOG_OCC_TOKEN,
        }

    # criterio: 06-C11
    @respx.mock
    def test_no_flags_resends_form(self, runner: CliRunner) -> None:
        _, put_route = _mock_catalog_edit(_CATALOG_FORM)
        result = runner.invoke(app, ["catalogs", "edit", str(_CATALOG_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "name": {"en": "Departments", "it": "Reparti"},
            "occToken": _CATALOG_OCC_TOKEN,
        }

    # criterio: 06-C11
    @respx.mock
    def test_json_then_flags_precedence(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        _, put_route = _mock_catalog_edit(_CATALOG_FORM)
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"name": {"de": "Abteilungen"}, "parentId": 7}), "utf-8")
        result = runner.invoke(
            app,
            [
                "catalogs",
                "edit",
                str(_CATALOG_ID),
                "--json",
                str(body),
                "--name",
                "en=Sites",
                "--parent",
                "8",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "name": {"de": "Abteilungen", "en": "Sites"},
            "parentId": 8,
            "occToken": _CATALOG_OCC_TOKEN,
        }

    @respx.mock
    def test_missing_occ_token_exits_1(self, runner: CliRunner) -> None:
        form = copy.deepcopy(_CATALOG_FORM)
        form.pop("occToken")
        _, put_route = _mock_catalog_edit(form)
        result = runner.invoke(app, ["catalogs", "edit", str(_CATALOG_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_GENERIC
        assert "--occ-token" in result.output
        assert not put_route.called

    # criterio: 06-C13
    @respx.mock
    def test_409_exits_9(self, runner: CliRunner) -> None:
        _, put_route = _mock_catalog_edit(_CATALOG_FORM, status=409)
        result = runner.invoke(
            app, ["catalogs", "edit", str(_CATALOG_ID), "--name", "en=Sites"], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFLICT
        assert (
            f"Catalog {_CATALOG_ID} changed since it was read: fetch it again and retry"
            in result.output
        )
        assert put_route.call_count == 1

    # criterio: 06-C09
    @respx.mock
    def test_404_exits_5_without_put(self, runner: CliRunner) -> None:
        mock_json("GET", f"{_CATALOG_PATH}/edit", {}, status=404)
        put_route = mock_json("PUT", _CATALOG_PATH, {})
        result = runner.invoke(app, ["catalogs", "edit", str(_CATALOG_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_NOT_FOUND
        assert not put_route.called


class TestCatalogEntriesEdit:
    # criterio: 06-C12
    @respx.mock
    def test_edit_entry_reads_form_then_puts_patched_body(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_entry_edit(_ENTRY_FORM)
        result = runner.invoke(
            app,
            [
                "catalogs",
                "edit-entry",
                str(_CATALOG_ID),
                str(_ENTRY_ID),
                "--label",
                "en=Bologna",
                "--parent-entry",
                "11",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {
            "label": {"en": "Bologna", "it": "Ingegneria"},
            "parentIds": [11],
            "externalId": "ENG",
            "occToken": _ENTRY_OCC_TOKEN,
        }

    # criterio: 06-C12
    @respx.mock
    def test_parent_ids_from_form_without_flag(self, runner: CliRunner) -> None:
        _, put_route = _mock_entry_edit(_ENTRY_FORM)
        result = runner.invoke(
            app,
            ["catalogs", "edit-entry", str(_CATALOG_ID), str(_ENTRY_ID), "--external-id", "X"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route)["parentIds"] == [1]
        assert _sent_body(put_route)["externalId"] == "X"

    # criterio: 06-C12
    @respx.mock
    def test_form_without_parents_omits_key(self, runner: CliRunner) -> None:
        form = copy.deepcopy(_ENTRY_FORM)
        form.pop("parents")
        _, put_route = _mock_entry_edit(form)
        result = runner.invoke(
            app, ["catalogs", "edit-entry", str(_CATALOG_ID), str(_ENTRY_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert "parentIds" not in _sent_body(put_route)

    # criterio: 06-C12
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        _mock_entry_edit(_ENTRY_FORM)
        result = runner.invoke(
            app, ["catalogs", "edit-entry", str(_CATALOG_ID), str(_ENTRY_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 06-C13
    @respx.mock
    def test_409_exits_9(self, runner: CliRunner) -> None:
        _, put_route = _mock_entry_edit(_ENTRY_FORM, status=409)
        result = runner.invoke(
            app, ["catalogs", "edit-entry", str(_CATALOG_ID), str(_ENTRY_ID)], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFLICT
        assert (
            f"Entry {_ENTRY_ID} of catalog {_CATALOG_ID} changed since it was read: "
            "fetch it again and retry" in result.output
        )
        assert put_route.call_count == 1
