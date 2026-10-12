# SPDX-License-Identifier: Apache-2.0
"""Helper di scrittura della CLI (spec 03, T09).

I test ``TestParseZonedDatetime``, ``TestMergeBody`` e ``TestValidateBody`` sono di
caratterizzazione: fissano ciò che gli helper di ``cli/tasks.py`` facevano prima di essere
spostati in ``cli/_write.py``.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import typer

from pynteracta.cli._write import (
    append_attachments,
    merge_body,
    merge_lang_map,
    parse_event_datetime,
    parse_id_path_pairs,
    parse_int_pairs,
    parse_kv_values,
    parse_lang_map,
    read_password,
    upload_all,
    validate_body,
)
from pynteracta.cli._write import parse_zoned_datetime as _parse_zoned_datetime
from pynteracta.exceptions import UploadError
from pynteracta.models.generated.external_v2 import CreateTaskRequestDTO

_EXIT_CONFIG = 2


def parse_zoned_datetime(value: str | None, timezone: str) -> dict[str, str] | None:
    return _parse_zoned_datetime(value, timezone, option="--expiration")


class TestParseZonedDatetime:
    def test_none_passes_through(self) -> None:
        assert parse_zoned_datetime(None, "Europe/Rome") is None

    def test_without_offset_uses_timezone(self) -> None:
        assert parse_zoned_datetime("2026-12-31T18:00", "Europe/Rome") == {
            "datetime": "2026-12-31T18:00:00",
            "timezone": "Europe/Rome",
        }

    def test_with_offset_ignores_timezone(self) -> None:
        assert parse_zoned_datetime("2026-12-31T18:00+01:00", "America/New_York") == {
            "datetime": "2026-12-31T17:00:00",
            "timezone": "UTC",
        }

    def test_not_iso_exits_2(self) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            parse_zoned_datetime("tomorrow", "Europe/Rome")
        assert exc_info.value.exit_code == _EXIT_CONFIG

    def test_unknown_timezone_exits_2(self) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            parse_zoned_datetime("2026-12-31T18:00", "Mars/Olympus")
        assert exc_info.value.exit_code == _EXIT_CONFIG


class TestParseEventDatetime:
    # criterio: 08-C13
    def test_none_passes_through(self) -> None:
        assert parse_event_datetime(None, "Europe/Rome", option="--start") is None

    # criterio: 08-C13
    def test_date_only_is_local_midnight(self) -> None:
        parsed = parse_event_datetime("2026-11-05", "Europe/Rome", option="--start")
        assert parsed == datetime(2026, 11, 5, 0, 0, tzinfo=ZoneInfo("Europe/Rome"))
        assert parsed is not None
        assert parsed.tzinfo == ZoneInfo("Europe/Rome")

    # criterio: 08-C13
    def test_without_offset_uses_timezone(self) -> None:
        parsed = parse_event_datetime("2026-11-05T10:00", "America/New_York", option="--start")
        assert parsed == datetime(2026, 11, 5, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        assert parsed is not None
        assert parsed.tzinfo == ZoneInfo("America/New_York")

    # criterio: 08-C13
    def test_explicit_offset_kept(self) -> None:
        parsed = parse_event_datetime("2026-11-05T10:00:00+02:00", "Europe/Rome", option="--end")
        assert parsed is not None
        assert parsed.utcoffset() == timedelta(hours=2)
        assert parsed.tzinfo == timezone(timedelta(hours=2))

    # criterio: 08-C13
    def test_not_iso_exits_2_naming_option(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            parse_event_datetime("tomorrow", "Europe/Rome", option="--end")
        assert exc_info.value.exit_code == _EXIT_CONFIG
        assert "--end" in capsys.readouterr().err

    # criterio: 08-C13
    def test_unknown_timezone_exits_2(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            parse_event_datetime("2026-11-05", "Nowhere/Town", option="--start")
        assert exc_info.value.exit_code == _EXIT_CONFIG
        assert "--timezone: unknown IANA time zone" in capsys.readouterr().err


class TestMergeBody:
    def test_flags_override_json_keys_in_camel_case(self) -> None:
        merged = merge_body({"title": "X", "priority": 1}, title="T", watcher_user_ids=[7])
        assert merged == {"title": "T", "priority": 1, "watcherUserIds": [7]}

    def test_none_flags_are_ignored(self) -> None:
        assert merge_body({"title": "X"}, title=None) == {"title": "X"}


class TestValidateBody:
    def test_valid_body_returns_dto(self) -> None:
        assert validate_body({"title": "T"}, CreateTaskRequestDTO).title == "T"

    def test_invalid_body_exits_2_naming_the_dto(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            validate_body({"priority": "high"}, CreateTaskRequestDTO)
        assert exc_info.value.exit_code == _EXIT_CONFIG
        assert "CreateTaskRequestDTO" in capsys.readouterr().err


class TestParseKvValues:
    # criterio: 03-C18
    def test_types(self) -> None:
        values = ["1411=226", "1412=a", "1413=true", "1414=false", "1415=x=y", " 1416 = -3"]
        assert parse_kv_values(values, option="--custom-data") == {
            "1411": 226,
            "1412": "a",
            "1413": True,
            "1414": False,
            "1415": "x=y",
            "1416": -3,
        }

    # criterio: 03-C18
    def test_none_or_empty(self) -> None:
        assert parse_kv_values(None, option="--custom-data") == {}

    # criterio: 03-C18
    def test_missing_eq_raises(self) -> None:
        with pytest.raises(typer.BadParameter, match="--screen-data"):
            parse_kv_values(["5"], option="--screen-data")


# ---------------------------------------------------------------------------
# Spec 04: helper per --attach e posts edit-attachments
# ---------------------------------------------------------------------------


class _FakeUploaded:
    def __init__(self, name: str) -> None:
        self.name = name

    def as_write_input(self) -> dict[str, str]:
        return {"name": self.name, "contentRef": f"ref-{self.name}"}


class _FakeAttachments:
    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[str] = []
        self.fail_on = fail_on

    def upload(self, path: Path) -> _FakeUploaded:
        self.calls.append(path.name)
        if path.name == self.fail_on:
            raise UploadError(f"Upload of {path.name} failed", file_name=path.name)
        return _FakeUploaded(path.name)


class _FakeClient:
    def __init__(self, fail_on: str | None = None) -> None:
        self.attachments = _FakeAttachments(fail_on)


class TestUploadAll:
    # criterio: 04-C11
    def test_uploads_in_order(self) -> None:
        client = _FakeClient()
        items = upload_all(client, [Path("a.txt"), Path("b.pdf")])  # type: ignore[arg-type]
        assert client.attachments.calls == ["a.txt", "b.pdf"]
        assert items == [
            {"name": "a.txt", "contentRef": "ref-a.txt"},
            {"name": "b.pdf", "contentRef": "ref-b.pdf"},
        ]

    # criterio: 04-C14
    def test_first_error_propagates_and_stops(self) -> None:
        client = _FakeClient(fail_on="b.pdf")
        with pytest.raises(UploadError):
            upload_all(client, [Path("a.txt"), Path("b.pdf"), Path("c.txt")])  # type: ignore[arg-type]
        assert client.attachments.calls == ["a.txt", "b.pdf"]

    # criterio: 04-C11
    def test_none_gives_empty_list(self) -> None:
        assert upload_all(_FakeClient(), None) == []  # type: ignore[arg-type]


class TestAppendAttachments:
    # criterio: 04-C11
    def test_key_absent(self) -> None:
        merged: dict[str, Any] = {"title": "T"}
        append_attachments(merged, "attachments", [{"name": "a"}])
        assert merged == {"title": "T", "attachments": [{"name": "a"}]}

    # criterio: 04-C11
    def test_key_present_items_appended(self) -> None:
        merged: dict[str, Any] = {"attachments": [{"attachmentId": 3}]}
        append_attachments(merged, "attachments", [{"name": "a"}])
        assert merged == {"attachments": [{"attachmentId": 3}, {"name": "a"}]}

    # criterio: 04-C11
    def test_empty_items_leave_body_unchanged(self) -> None:
        merged: dict[str, Any] = {"title": "T"}
        append_attachments(merged, "addAttachments", [])
        assert merged == {"title": "T"}


class TestParseIdPathPairs:
    # criterio: 04-C13
    def test_valid(self) -> None:
        assert parse_id_path_pairs(["5=b.pdf", "6=dir/c=d.txt"], option="--update") == [
            (5, Path("b.pdf")),
            (6, Path("dir/c=d.txt")),
        ]

    # criterio: 04-C13
    def test_none_is_empty(self) -> None:
        assert parse_id_path_pairs(None, option="--update") == []

    # criterio: 04-C13
    @pytest.mark.parametrize("value", ["b.pdf", "x=b.pdf", "=b.pdf", "5="])
    def test_malformed_raises_bad_parameter(self, value: str) -> None:
        with pytest.raises(typer.BadParameter, match="--update"):
            parse_id_path_pairs([value], option="--update")


class TestReadPassword:
    """``--password-stdin`` (spec 05): prompt nascosto su terminale, o prima riga di stdin."""

    # criterio: 05-C12
    def test_interactive_prompts_hidden_with_confirmation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pynteracta.cli import _common, _write  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: True)
        calls: list[dict[str, Any]] = []

        def fake_prompt(text: str, **kwargs: Any) -> str:
            calls.append({"text": text, **kwargs})
            return "S3gret!"

        monkeypatch.setattr(_write.typer, "prompt", fake_prompt)
        assert read_password() == "S3gret!"
        assert calls == [{"text": "Password", "hide_input": True, "confirmation_prompt": True}]

    # criterio: 05-C12
    def test_non_interactive_reads_first_stdin_line(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pynteracta.cli import _common  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: False)
        monkeypatch.setattr("sys.stdin", io.StringIO("S3gret!\r\nsecond line\n"))
        assert read_password() == "S3gret!"

    # criterio: 05-C12
    def test_empty_stdin_exits_2(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from pynteracta.cli import _common  # noqa: PLC0415

        monkeypatch.setattr(_common, "_stdin_is_interactive", lambda: False)
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        with pytest.raises(typer.Exit) as exc_info:
            read_password()
        assert exc_info.value.exit_code == _EXIT_CONFIG
        assert "--password-stdin: no password read from stdin." in capsys.readouterr().err


class TestParseLangMap:
    # criterio: 06-C10
    def test_pairs(self) -> None:
        assert parse_lang_map(["it=Sedi", "en=Sites"], option="--name") == {
            "it": "Sedi",
            "en": "Sites",
        }

    # criterio: 06-C10
    def test_text_keeps_equals_and_is_not_coerced(self) -> None:
        assert parse_lang_map(["it=a=b", "en=12", "de=true"], option="--name") == {
            "it": "a=b",
            "en": "12",
            "de": "true",
        }

    # criterio: 06-C10
    def test_none_is_empty(self) -> None:
        assert parse_lang_map(None, option="--name") == {}

    # criterio: 06-C10
    @pytest.mark.parametrize("value", ["Sedi", "=Sedi", " =Sedi"])
    def test_malformed_raises_bad_parameter(self, value: str) -> None:
        with pytest.raises(typer.BadParameter, match=r"--name must be LANG=TEXT"):
            parse_lang_map([value], option="--name")


class TestParseIntPairs:
    # criterio: 06-C17
    def test_pairs(self) -> None:
        assert parse_int_pairs(["1=4", "2=5"], option="--add-user-role") == [(1, 4), (2, 5)]

    # criterio: 06-C17
    def test_none_is_empty(self) -> None:
        assert parse_int_pairs(None, option="--add-user-role") == []

    # criterio: 06-C17
    @pytest.mark.parametrize("value", ["1", "a=4", "1=", "=4", "1=b"])
    def test_malformed_raises_bad_parameter(self, value: str) -> None:
        with pytest.raises(typer.BadParameter, match=r"--add-group-role must be GROUP_ID=ROLE_ID"):
            parse_int_pairs([value], option="--add-group-role", form="GROUP_ID=ROLE_ID")


class TestMergeLangMap:
    # criterio: 06-C10
    def test_key_absent(self) -> None:
        body: dict[str, Any] = {"parentId": 3}
        merge_lang_map(body, "name", {"it": "Sedi"})
        assert body == {"parentId": 3, "name": {"it": "Sedi"}}

    # criterio: 06-C10
    def test_key_present_merged_flags_win(self) -> None:
        body: dict[str, Any] = {"name": {"it": "X", "de": "Standorte"}}
        merge_lang_map(body, "name", {"it": "Sedi", "en": "Sites"})
        assert body == {"name": {"it": "Sedi", "de": "Standorte", "en": "Sites"}}

    # criterio: 06-C10
    def test_none_value_replaced(self) -> None:
        body: dict[str, Any] = {"name": None}
        merge_lang_map(body, "name", {"it": "Sedi"})
        assert body == {"name": {"it": "Sedi"}}

    # criterio: 06-C10
    def test_empty_flags_leave_body_unchanged(self) -> None:
        body: dict[str, Any] = {"name": {"it": "X"}}
        merge_lang_map(body, "name", {})
        assert body == {"name": {"it": "X"}}
