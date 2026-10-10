# SPDX-License-Identifier: Apache-2.0
"""Test degli helper condivisi della CLI in ``cli/_common.py``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from rich.console import Console

from pynteracta.cli import _common
from pynteracta.cli._common import (
    EXIT_AUTH,
    EXIT_CONFIG,
    EXIT_GENERIC,
    EXIT_NOT_FOUND,
    EXIT_PERMISSION,
    EXIT_SERVER,
    EXIT_TRANSPORT,
    EXIT_VALIDATION,
    error_exit_code,
)
from pynteracta.exceptions import (
    AuthenticationError,
    ConcurrencyError,
    InteractaError,
    NotFoundError,
    ServerError,
    TransportError,
    ValidationError,
)
from pynteracta.exceptions import PermissionError as InteractaPermissionError
from pynteracta.models.generated.external_v2 import CreateTaskRequestDTO

_EXIT_CONFLICT = 9
_HTTP_409 = 409


class TestErrorExitCode:
    # Caratterizzazione: la mappa esistente, fissata prima di aggiungere il 409.
    @pytest.mark.parametrize(
        ("exc", "code"),
        [
            (AuthenticationError("x"), EXIT_AUTH),
            (InteractaPermissionError("x"), EXIT_PERMISSION),
            (NotFoundError("x"), EXIT_NOT_FOUND),
            (ValidationError("x"), EXIT_VALIDATION),
            (TransportError("x"), EXIT_TRANSPORT),
            (ServerError("x"), EXIT_SERVER),
            (InteractaError("x"), EXIT_GENERIC),
        ],
    )
    def test_existing_mapping(self, exc: InteractaError, code: int) -> None:
        assert error_exit_code(exc) == code

    # criterio: 02-C10
    def test_concurrency_is_9(self) -> None:
        assert _common.EXIT_CONFLICT == _EXIT_CONFLICT
        exc = ConcurrencyError("Conflict", status_code=_HTTP_409)
        assert error_exit_code(exc) == _EXIT_CONFLICT

    # criterio: 02-C10
    def test_handle_error_concurrency_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        exc = ConcurrencyError("Conflict", status_code=_HTTP_409)
        exit_ = _common.handle_error(exc, console=Console())
        assert exit_.exit_code == _EXIT_CONFLICT
        err = capsys.readouterr().err
        assert "changed since it was read" in err
        assert "fetch it again and retry" in err

    # criterio: 03-C28
    def test_handle_error_concurrency_with_resource(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exc = ConcurrencyError("Conflict", status_code=_HTTP_409)
        exit_ = _common.handle_error(exc, console=Console(), resource="Post 21269")
        assert exit_.exit_code == _EXIT_CONFLICT
        err = capsys.readouterr().err
        assert "Post 21269 changed since it was read: fetch it again and retry" in err


class TestConfirmDestructive:
    # criterio: 02-C12
    def test_yes_skips_prompt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: False)
        assert _common.confirm_destructive("Delete?", yes=True) is True

    # criterio: 02-C11
    @pytest.mark.parametrize(("answer", "expected"), [(True, True), (False, False)])
    def test_interactive_prompt_returns_answer(
        self, monkeypatch: pytest.MonkeyPatch, answer: bool, expected: bool
    ) -> None:
        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)
        asked: list[str] = []

        def fake_confirm(prompt: str, **kwargs: object) -> bool:
            asked.append(prompt)
            return answer

        monkeypatch.setattr(typer, "confirm", fake_confirm)
        assert _common.confirm_destructive('Delete task 7001 "T"?', yes=False) is expected
        assert asked == ['Delete task 7001 "T"?']

    # criterio: 02-C12
    def test_non_interactive_without_yes_exits_2_with_message(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: False)
        with pytest.raises(typer.Exit) as exc_info:
            _common.confirm_destructive("Delete?", yes=False)
        assert exc_info.value.exit_code == EXIT_CONFIG
        assert "--yes is required when not running interactively" in capsys.readouterr().err


class TestLoadJsonBody:
    # criterio: 02-C08
    def test_from_file(self, tmp_path: Path) -> None:
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"title": "X", "assigneeUserId": 9}), encoding="utf-8")
        assert _common.load_json_body(str(body), CreateTaskRequestDTO) == {
            "title": "X",
            "assigneeUserId": 9,
        }

    # criterio: 02-C08
    def test_from_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import io  # noqa: PLC0415
        import sys  # noqa: PLC0415

        monkeypatch.setattr(sys, "stdin", io.StringIO('{"title": "from stdin"}'))
        assert _common.load_json_body("-", CreateTaskRequestDTO) == {"title": "from stdin"}

    # criterio: 02-C08
    def test_none_source_gives_empty_body(self) -> None:
        assert _common.load_json_body(None, CreateTaskRequestDTO) == {}

    # criterio: 02-C08
    def test_invalid_json_exits_2(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        body = tmp_path / "body.json"
        body.write_text("{not json", encoding="utf-8")
        with pytest.raises(typer.Exit) as exc_info:
            _common.load_json_body(str(body), CreateTaskRequestDTO)
        assert exc_info.value.exit_code == EXIT_CONFIG
        assert "invalid JSON" in capsys.readouterr().err

    # criterio: 02-C08
    def test_unknown_keys_exit_2(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        body = tmp_path / "body.json"
        body.write_text(json.dumps({"title": "X", "bogus": 1}), encoding="utf-8")
        with pytest.raises(typer.Exit) as exc_info:
            _common.load_json_body(str(body), CreateTaskRequestDTO)
        assert exc_info.value.exit_code == EXIT_CONFIG
        assert "bogus" in capsys.readouterr().err

    # criterio: 02-C08
    def test_non_object_json_exits_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        body = tmp_path / "body.json"
        body.write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(typer.Exit) as exc_info:
            _common.load_json_body(str(body), CreateTaskRequestDTO)
        assert exc_info.value.exit_code == EXIT_CONFIG
        assert "JSON object" in capsys.readouterr().err
