# SPDX-License-Identifier: Apache-2.0
"""Helper di scrittura della CLI (spec 03, T09).

I test ``TestParseZonedDatetime``, ``TestMergeBody`` e ``TestValidateBody`` sono di
caratterizzazione: fissano ciò che gli helper di ``cli/tasks.py`` facevano prima di essere
spostati in ``cli/_write.py``.
"""

from __future__ import annotations

import pytest
import typer

from pynteracta.cli._write import merge_body, parse_kv_values, validate_body
from pynteracta.cli._write import parse_zoned_datetime as _parse_zoned_datetime
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
