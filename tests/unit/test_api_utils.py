# SPDX-License-Identifier: Apache-2.0
"""Test delle utilità di scrittura in ``api/_utils.py``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from pynteracta.api._utils import build_write_body, zoned_datetime_input
from pynteracta.models.generated import external_v2 as generated


class TestZonedDatetimeInput:
    # criterio: 02-C03
    def test_zoneinfo_keeps_local_time_and_iana_name(self) -> None:
        dt = datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome"))
        assert zoned_datetime_input(dt) == {
            "datetime": "2026-12-31T18:00:00",
            "timezone": "Europe/Rome",
        }

    # criterio: 02-C03
    def test_utc_zoneinfo(self) -> None:
        dt = datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("UTC"))
        assert zoned_datetime_input(dt) == {"datetime": "2026-12-31T18:00:00", "timezone": "UTC"}

    # criterio: 02-C03
    def test_fixed_offset_is_converted_to_utc(self) -> None:
        dt = datetime(2026, 12, 31, 18, 0, tzinfo=timezone(timedelta(hours=1)))
        assert zoned_datetime_input(dt) == {"datetime": "2026-12-31T17:00:00", "timezone": "UTC"}

    # criterio: 02-C03
    def test_stdlib_utc_constant(self) -> None:
        dt = datetime(2026, 12, 31, 18, 0, tzinfo=UTC)
        assert zoned_datetime_input(dt) == {"datetime": "2026-12-31T18:00:00", "timezone": "UTC"}

    # criterio: 02-C03
    def test_naive_datetime_raises(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            zoned_datetime_input(datetime(2026, 12, 31, 18, 0))


class TestBuildWriteBody:
    # criterio: 02-C01
    def test_camel_case_and_skips_none(self) -> None:
        body = build_write_body(title="T", priority=None, watcher_user_ids=[7], client_uid=None)
        assert body == {"title": "T", "watcherUserIds": [7]}

    # criterio: 02-C01
    def test_empty_when_nothing_given(self) -> None:
        assert build_write_body(title=None) == {}

    # criterio: 02-C01
    def test_models_in_lists_are_dumped_without_none(self) -> None:
        body = build_write_body(
            sub_tasks=[generated.SubTaskDTO1(description="x"), {"description": "y", "state": 1}],
            expiration={"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"},
        )
        assert body == {
            "subTasks": [{"description": "x"}, {"description": "y", "state": 1}],
            "expiration": {"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"},
        }
