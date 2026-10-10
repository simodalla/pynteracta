# SPDX-License-Identifier: Apache-2.0
"""Test dei comandi di scrittura ``users create|edit|delete|edit-credentials`` (spec 05)."""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_USER_ID = 42
_CREATED_USER_ID = 1043
_EXIT_CONFIG = 2
BASE_ENV = {"PYNTERACTA_BASE_URL": "https://api.example.com"}
_CREATE_PATH = "admin/manage/users"
_CREATE_URL = f"{BASE_URL}/{_CREATE_PATH}"
_CUSTOM_BLOCK = {"custom": {"username": "ab", "active": True}}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sent_body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


def _not_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    from pynteracta.cli import _common  # noqa: PLC0415

    monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: False)


def _interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    from pynteracta.cli import _common  # noqa: PLC0415

    monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)


class TestUsersCreate:
    # criterio: 05-C11
    @respx.mock
    def test_flags_and_json_merge_flags_win(
        self, runner: CliRunner, tmp_path: pathlib.Path
    ) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        body = tmp_path / "body.json"
        body.write_text(
            json.dumps({"firstname": "X", "userPreferences": {"defaultLanguageId": "it"}}),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "users",
                "create",
                "--first-name",
                "A",
                "--last-name",
                "B",
                "--contact-email",
                "a@b.it",
                "--username",
                "ab",
                "--generate-password",
                "--json",
                str(body),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert route.call_count == 1
        assert _sent_body(route) == {
            "firstname": "A",
            "lastname": "B",
            "contactEmail": "a@b.it",
            "userPreferences": {"defaultLanguageId": "it"},
            "userCredentialsConfiguration": _CUSTOM_BLOCK,
            "resetUserCustomCredentialsCommand": {"generatePassword": True},
        }
        assert str(_CREATED_USER_ID) in result.output
        assert "Xk7-fake-pw" in result.output

    # criterio: 05-C11
    @respx.mock
    def test_table_output_shows_generated_password(
        self, runner: CliRunner, snapshot: object
    ) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--first-name", "A", "--username", "ab", "--generate-password"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    # criterio: 05-C11
    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "users", "create", "--first-name", "A", "--generate-password"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot
        assert json.loads(result.output)["generated_password"] == "Xk7-fake-pw"

    # criterio: 05-C11
    @respx.mock
    def test_json_full_output_has_raw_list(self, runner: CliRunner) -> None:
        mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["--output", "json", "users", "create", "--generate-password", "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["generatedPassword"] == ["Xk7-fake-pw"]

    # criterio: 05-C11
    @respx.mock
    def test_google_microsoft_and_notify_flags(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            [
                "users",
                "create",
                "--google-account",
                "a@gmail.test",
                "--microsoft-account",
                "a@outlook.test",
                "--force-password-change",
                "--notify-email",
                "x@b.it",
                "--notify-email",
                "y@b.it",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "userCredentialsConfiguration": {
                "google": {"googleAccountId": "a@gmail.test", "enabled": True},
                "microsoft": {"microsoftAccountId": "a@outlook.test", "enabled": True},
            },
            "resetUserCustomCredentialsCommand": {
                "forceCredentialsExpiration": True,
                "emailNotifyRecipients": ["x@b.it", "y@b.it"],
            },
        }

    # criterio: 05-C12
    @respx.mock
    def test_password_stdin_non_interactive(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _not_interactive(monkeypatch)
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--username", "ab", "--password-stdin"],
            env=BASE_ENV,
            input="S3gret!\n",
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(route) == {
            "userCredentialsConfiguration": _CUSTOM_BLOCK,
            "resetUserCustomCredentialsCommand": {"password": ["S3gret!"]},
        }
        assert "S3gret!" not in result.output

    # criterio: 05-C12
    @respx.mock
    def test_password_prompt_interactive(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pynteracta.cli import _write  # noqa: PLC0415

        _interactive(monkeypatch)
        calls: list[dict[str, Any]] = []

        def fake_prompt(text: str, **kwargs: Any) -> str:
            calls.append({"text": text, **kwargs})
            return "S3gret!"

        monkeypatch.setattr(_write.typer, "prompt", fake_prompt)
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app, ["users", "create", "--username", "ab", "--password-stdin"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert calls == [{"text": "Password", "hide_input": True, "confirmation_prompt": True}]
        assert _sent_body(route)["resetUserCustomCredentialsCommand"] == {"password": ["S3gret!"]}
        assert "S3gret!" not in result.output

    # criterio: 05-C12
    @respx.mock
    def test_generate_and_stdin_together_exit_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--username", "ab", "--generate-password", "--password-stdin"],
            env=BASE_ENV,
            input="S3gret!\n",
        )
        assert result.exit_code == _EXIT_CONFIG
        assert "mutually exclusive" in result.output
        assert route.call_count == 0

    # criterio: 05-C12
    @respx.mock
    def test_stdin_and_json_dash_exit_2(self, runner: CliRunner) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "create", "--password-stdin", "--json", "-"],
            env=BASE_ENV,
            input='{"firstname": "A"}',
        )
        assert result.exit_code == _EXIT_CONFIG
        assert "--password-stdin" in result.output
        assert route.call_count == 0

    # criterio: 05-C12
    def test_help_has_no_password_option(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["users", "create", "--help"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "--password-stdin" in result.output
        assert "--generate-password" in result.output
        assert re.search(r"--password(?![-\w])", result.output) is None

    # criterio: 05-C11
    @respx.mock
    def test_json_unknown_key_exits_2(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        route = mock_json("POST", _CREATE_PATH, load_payload("create_user_response.json"))
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"nope": 1}), encoding="utf-8")
        result = runner.invoke(app, ["users", "create", "--json", str(body)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "unknown keys" in result.output
        assert route.call_count == 0

    # criterio: 05-C11
    @respx.mock
    def test_server_validation_error_exits_6(self, runner: CliRunner) -> None:
        respx.post(_CREATE_URL).mock(
            return_value=httpx.Response(400, json={"message": "Dati inseriti non validi"})
        )
        result = runner.invoke(app, ["users", "create", "--first-name", "A"], env=BASE_ENV)
        assert result.exit_code == 6  # noqa: PLR2004


# ---------------------------------------------------------------------------
# users edit / edit-credentials (T10)
# ---------------------------------------------------------------------------

_FORM_PATH = f"admin/manage/users/{_USER_ID}/edit"
_EDIT_PATH = f"admin/manage/users/{_USER_ID}"
_EDIT_URL = f"{BASE_URL}/{_EDIT_PATH}"
_CREDENTIALS_FORM_PATH = f"admin/manage/users/{_USER_ID}/credentials/edit"
_CREDENTIALS_PATH = f"admin/manage/users/{_USER_ID}/credentials"
_CREDENTIALS_URL = f"{BASE_URL}/{_CREDENTIALS_PATH}"
_FORM_OCC_TOKEN = 42
_CREDENTIALS_OCC_TOKEN = 12
_FORCED_OCC_TOKEN = 6
_EXIT_CONFLICT = 9
_CONFLICT = "User 42 changed since it was read: fetch it again and retry"
_EDIT_BASE = {
    "firstname": "Maria",
    "lastname": "Rossi",
    "contactEmail": "m.rossi@example.it",
    "externalId": "EXT-1042",
    "userPreferences": {
        "defaultLanguageId": "it",
        "defaultTimezoneId": 1,
        "emailNotificationsEnabled": True,
    },
    "userInfo": {
        "area": {"id": 5, "name": "Software Engineering"},
        "businessUnit": {"id": 10, "name": "IT Department"},
        "privateEmailVerified": False,
        "privateEmailVerificationRequired": False,
    },
    "userSettings": {
        "peopleSectionEnabled": True,
        "visibleInPeopleSection": True,
        "reducedProfile": False,
        "viewUserProfiles": True,
    },
}
_CUSTOM_READ = {"username": "m.rossi", "canUserManageCustomCredentials": True, "active": True}


def _mock_edit_flow(
    form: dict | None = None,  # type: ignore[type-arg]
) -> tuple[respx.Route, respx.Route]:
    get_route = mock_json(
        "GET",
        _FORM_PATH,
        form if form is not None else load_payload("get_user_for_edit_response.json"),
    )
    put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_user_response.json"))
    return get_route, put_route


def _mock_credentials_flow(
    form: dict | None = None,  # type: ignore[type-arg]
) -> tuple[respx.Route, respx.Route]:
    payload = (
        form if form is not None else load_payload("get_user_credentials_for_edit_response.json")
    )
    get_route = mock_json("GET", _CREDENTIALS_FORM_PATH, payload)
    put_route = mock_json(
        "PUT", _CREDENTIALS_PATH, load_payload("edit_user_credentials_response.json")
    )
    return get_route, put_route


class TestEditBase:
    # criterio: 05-C13
    def test_edit_base_revalidates_blocks_and_drops_none(self) -> None:
        from pynteracta.cli.users_write import _edit_base  # noqa: PLC0415
        from pynteracta.models.facade.users import UserForEdit  # noqa: PLC0415

        user = UserForEdit.from_dict(load_payload("get_user_for_edit_response.json"))
        assert _edit_base(user) == _EDIT_BASE

    # criterio: 05-C13
    def test_edit_base_without_blocks(self) -> None:
        from pynteracta.cli.users_write import _edit_base  # noqa: PLC0415
        from pynteracta.models.facade.users import UserForEdit  # noqa: PLC0415

        user = UserForEdit.from_dict({"firstname": "A", "occToken": 1})
        assert _edit_base(user) == {"firstname": "A"}


class TestUsersEdit:
    # criterio: 05-C13
    @respx.mock
    def test_edit_reads_form_then_puts_patched_body(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_edit_flow()
        result = runner.invoke(
            app, ["users", "edit", str(_USER_ID), "--last-name", "C"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert put_route.call_count == 1
        assert _sent_body(put_route) == {
            **_EDIT_BASE,
            "lastname": "C",
            "occToken": _FORM_OCC_TOKEN,
        }
        assert str(_USER_ID) in result.output

    # criterio: 05-C13
    @respx.mock
    def test_json_then_flags_precedence(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        _, put_route = _mock_edit_flow()
        body = tmp_path / "body.json"
        body.write_text(
            json.dumps({"externalId": "E9", "privateEmail": "p@b.it"}), encoding="utf-8"
        )
        result = runner.invoke(
            app,
            ["users", "edit", str(_USER_ID), "--json", str(body), "--external-id", "E10"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        sent = _sent_body(put_route)
        assert sent["externalId"] == "E10"
        assert sent["privateEmail"] == "p@b.it"
        assert sent["firstname"] == "Maria"

    # criterio: 05-C13
    @respx.mock
    def test_occ_token_overrides_but_get_still_happens(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_edit_flow()
        result = runner.invoke(
            app,
            ["users", "edit", str(_USER_ID), "--last-name", "C", "--occ-token", "6"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert _sent_body(put_route)["occToken"] == _FORCED_OCC_TOKEN
        assert _sent_body(put_route)["firstname"] == "Maria"

    # criterio: 05-C13
    @respx.mock
    def test_missing_fields_are_not_invented(self, runner: CliRunner) -> None:
        form = load_payload("get_user_for_edit_response.json")
        for key in ("privateEmail", "externalId", "userSettings", "userInfo"):
            form.pop(key, None)
        _, put_route = _mock_edit_flow(form)
        result = runner.invoke(
            app, ["users", "edit", str(_USER_ID), "--last-name", "C"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        sent = _sent_body(put_route)
        assert "privateEmail" not in sent
        assert "externalId" not in sent
        assert "userSettings" not in sent
        assert "userInfo" not in sent
        assert sent["userPreferences"] == _EDIT_BASE["userPreferences"]

    # criterio: 05-C15
    @respx.mock
    def test_409_exits_9_without_retry(self, runner: CliRunner) -> None:
        mock_json("GET", _FORM_PATH, load_payload("get_user_for_edit_response.json"))
        put_route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(409, json={"message": "Concurrency error"})
        )
        result = runner.invoke(
            app, ["users", "edit", str(_USER_ID), "--last-name", "C"], env=BASE_ENV
        )
        assert result.exit_code == _EXIT_CONFLICT
        assert _CONFLICT in result.output
        assert put_route.call_count == 1

    # criterio: 05-C13
    @respx.mock
    def test_missing_occ_token_exits_1_without_put(self, runner: CliRunner) -> None:
        form = load_payload("get_user_for_edit_response.json")
        form.pop("occToken")
        _, put_route = _mock_edit_flow(form)
        result = runner.invoke(
            app, ["users", "edit", str(_USER_ID), "--last-name", "C"], env=BASE_ENV
        )
        assert result.exit_code == 1
        assert "--occ-token" in result.output
        assert put_route.call_count == 0

    # criterio: 05-C13
    @respx.mock
    def test_form_not_found_exits_5_without_put(self, runner: CliRunner) -> None:
        respx.get(f"{BASE_URL}/{_FORM_PATH}").mock(
            return_value=httpx.Response(404, json={"message": "Utente non esistente"})
        )
        put_route = mock_json("PUT", _EDIT_PATH, load_payload("edit_user_response.json"))
        result = runner.invoke(
            app,
            ["users", "edit", str(_USER_ID), "--last-name", "C", "--occ-token", "6"],
            env=BASE_ENV,
        )
        assert result.exit_code == 5  # noqa: PLR2004
        assert put_route.call_count == 0


class TestCredentialsBase:
    # criterio: 05-C14
    def test_credentials_base_drops_read_only_fields(self) -> None:
        from pynteracta.cli.users_write import _credentials_base  # noqa: PLC0415
        from pynteracta.models.facade.admin_manage import UserCredentialsForEdit  # noqa: PLC0415

        form = UserCredentialsForEdit.from_dict(
            load_payload("get_user_credentials_for_edit_response.json")
        )
        assert _credentials_base(form) == {"google": {"enabled": True}, "custom": _CUSTOM_READ}

    # criterio: 05-C14
    def test_credentials_base_empty_form(self) -> None:
        from pynteracta.cli.users_write import _credentials_base  # noqa: PLC0415
        from pynteracta.models.facade.admin_manage import UserCredentialsForEdit  # noqa: PLC0415

        assert _credentials_base(UserCredentialsForEdit.from_dict({"occToken": 1})) == {}


class TestUsersEditCredentials:
    # criterio: 05-C14
    @respx.mock
    def test_google_flag_and_no_custom(self, runner: CliRunner) -> None:
        get_route, put_route = _mock_credentials_flow()
        result = runner.invoke(
            app,
            [
                "users",
                "edit-credentials",
                str(_USER_ID),
                "--google-account",
                "a@b.it",
                "--no-custom",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert get_route.call_count == 1
        assert _sent_body(put_route) == {
            "userCredentialsConfiguration": {
                "google": {"googleAccountId": "a@b.it", "enabled": True}
            },
            "occToken": _CREDENTIALS_OCC_TOKEN,
        }

    # criterio: 05-C14
    @respx.mock
    def test_username_and_inactive_keep_read_block_without_read_only_fields(
        self, runner: CliRunner
    ) -> None:
        _, put_route = _mock_credentials_flow()
        result = runner.invoke(
            app,
            [
                "users",
                "edit-credentials",
                str(_USER_ID),
                "--username",
                "new.name",
                "--custom-inactive",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route)["userCredentialsConfiguration"] == {
            "google": {"enabled": True},
            "custom": {**_CUSTOM_READ, "username": "new.name", "active": False},
        }

    # criterio: 05-C14
    @respx.mock
    def test_no_google_when_absent_is_fine(self, runner: CliRunner) -> None:
        form = {
            "occToken": _CREDENTIALS_OCC_TOKEN,
            "userCredentialsConfiguration": {"custom": _CUSTOM_READ},
        }
        _, put_route = _mock_credentials_flow(form)
        result = runner.invoke(
            app,
            ["users", "edit-credentials", str(_USER_ID), "--no-google", "--no-microsoft"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route)["userCredentialsConfiguration"] == {"custom": _CUSTOM_READ}

    # criterio: 05-C14
    @respx.mock
    def test_json_block_overlays_read_form(self, runner: CliRunner, tmp_path: pathlib.Path) -> None:
        _, put_route = _mock_credentials_flow()
        body = tmp_path / "body.json"
        body.write_text(
            json.dumps(
                {
                    "userCredentialsConfiguration": {
                        "microsoft": {"microsoftAccountId": "m@b.it", "enabled": True}
                    }
                }
            ),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "users",
                "edit-credentials",
                str(_USER_ID),
                "--json",
                str(body),
                "--occ-token",
                str(_FORCED_OCC_TOKEN),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert _sent_body(put_route) == {
            "userCredentialsConfiguration": {
                "google": {"enabled": True},
                "custom": _CUSTOM_READ,
                "microsoft": {"microsoftAccountId": "m@b.it", "enabled": True},
            },
            "occToken": _FORCED_OCC_TOKEN,
        }

    # criterio: 05-C15
    @respx.mock
    def test_409_exits_9_without_retry(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            _CREDENTIALS_FORM_PATH,
            load_payload("get_user_credentials_for_edit_response.json"),
        )
        put_route = respx.put(_CREDENTIALS_URL).mock(
            return_value=httpx.Response(409, json={"message": "Concurrency error"})
        )
        result = runner.invoke(
            app,
            ["users", "edit-credentials", str(_USER_ID), "--google-account", "a@b.it"],
            env=BASE_ENV,
        )
        assert result.exit_code == _EXIT_CONFLICT
        assert _CONFLICT in result.output
        assert put_route.call_count == 1


# ---------------------------------------------------------------------------
# users delete (T11)
# ---------------------------------------------------------------------------

_DELETE_DONE = f"User {_USER_ID} deleted"
_DELETE_PROMPT = f'Delete user {_USER_ID} "Maria Rossi"?'


def _mock_delete_flow() -> tuple[respx.Route, respx.Route]:
    get_route = mock_json("GET", _FORM_PATH, load_payload("get_user_for_edit_response.json"))
    delete_route = respx.delete(_EDIT_URL).mock(return_value=httpx.Response(200))
    return get_route, delete_route


class TestUsersDelete:
    # criterio: 05-C16
    @respx.mock
    def test_prompt_shows_id_and_full_name_and_y_deletes(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _interactive(monkeypatch)
        get_route, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["users", "delete", str(_USER_ID)], env=BASE_ENV, input="y\n")
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
        _interactive(monkeypatch)
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["users", "delete", str(_USER_ID)], env=BASE_ENV, input="n\n")
        assert result.exit_code == 0, result.output
        assert delete_route.call_count == 0
        assert _DELETE_DONE not in result.output

    # criterio: 05-C16
    @respx.mock
    def test_yes_skips_prompt(self, runner: CliRunner) -> None:
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["users", "delete", str(_USER_ID), "--yes"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert "?" not in result.output
        assert delete_route.call_count == 1
        assert _DELETE_DONE in result.output

    # criterio: 05-C16
    @respx.mock
    def test_json_output(self, runner: CliRunner) -> None:
        _mock_delete_flow()
        result = runner.invoke(
            app, ["--output", "json", "users", "delete", str(_USER_ID), "-y"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output) == {"user_id": _USER_ID}

    # criterio: 05-C16
    @respx.mock
    def test_non_interactive_without_yes_refuses(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _not_interactive(monkeypatch)
        _, delete_route = _mock_delete_flow()
        result = runner.invoke(app, ["users", "delete", str(_USER_ID)], env=BASE_ENV)
        assert result.exit_code == _EXIT_CONFIG
        assert "--yes is required" in result.output
        assert delete_route.call_count == 0

    # criterio: 05-C16
    @respx.mock
    def test_not_found_exits_5(self, runner: CliRunner) -> None:
        respx.get(f"{BASE_URL}/{_FORM_PATH}").mock(
            return_value=httpx.Response(404, json={"message": "Utente non esistente"})
        )
        result = runner.invoke(app, ["users", "delete", str(_USER_ID), "--yes"], env=BASE_ENV)
        assert result.exit_code == 5  # noqa: PLR2004
