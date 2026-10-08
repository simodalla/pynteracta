# SPDX-License-Identifier: Apache-2.0
"""Tests for TasksAPI."""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.tasks import TasksAPI
from pynteracta.exceptions import ConcurrencyError, TransportError
from pynteracta.models.generated import external_v2 as generated

_TASK_ID = 7001
_POST_ID = 21269
_SUB_TASK_ID_1 = 801
_SUB_TASK_ID_2 = 802
_SUB_TASK_COUNT = 2
_REMINDER_ID = 501
_REMINDER_COUNT = 1


class TestTasksGet:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        route = respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = TasksAPI(make_transport())
        task = api.get(_TASK_ID)
        assert route.called
        assert task.id == _TASK_ID
        assert task.post_id == _POST_ID

    @respx.mock
    def test_facade_fields(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = TasksAPI(make_transport())
        task = api.get(_TASK_ID)
        assert task.title == payload["title"]
        assert task.description_plain_text == payload["descriptionPlainText"]
        assert task.priority == payload["priority"]
        assert task.state == payload["state"]
        assert task.attachments_count == payload["attachmentsCount"]
        assert task.creation_timestamp == payload["creationTimestamp"]

    @respx.mock
    def test_capabilities_typed(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = TasksAPI(make_transport())
        task = api.get(_TASK_ID)
        caps = task.capabilities
        assert caps is not None
        assert caps.can_view_detail is True
        assert caps.can_modify is True
        assert caps.can_delete is False

    @respx.mock
    def test_sub_tasks_typed(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = TasksAPI(make_transport())
        task = api.get(_TASK_ID)
        sub_tasks = task.sub_tasks
        assert len(sub_tasks) == _SUB_TASK_COUNT
        assert sub_tasks[0].id == _SUB_TASK_ID_1
        assert sub_tasks[0].description == "Read introduction"
        assert sub_tasks[1].id == _SUB_TASK_ID_2

    @respx.mock
    def test_reminders_typed(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = TasksAPI(make_transport())
        task = api.get(_TASK_ID)
        reminders = task.reminders
        assert len(reminders) == _REMINDER_COUNT
        assert reminders[0].id == _REMINDER_ID

    @respx.mock
    def test_raw_accessible(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = TasksAPI(make_transport())
        task = api.get(_TASK_ID)
        assert task.raw is not None
        assert task.raw.id == _TASK_ID
        assert task.raw.occToken == payload["occToken"]

    # criterio: 02-C07
    @respx.mock
    def test_occ_token_exposed(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        respx.get(f"{BASE_URL}/communication/tasks/data/task-detail-by-id/{_TASK_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        task = TasksAPI(make_transport()).get(_TASK_ID)
        assert task.occ_token == payload["occToken"]


_CREATE_PATH = f"{BASE_URL}/communication/tasks/manage/create-task/{_POST_ID}"
_EDIT_PATH = f"{BASE_URL}/communication/tasks/manage/edit-task/{_TASK_ID}/3"
_DELETE_PATH = f"{BASE_URL}/communication/tasks/manage/delete-task/{_TASK_ID}"
_CREATED_TASK_ID = 7002
_HTTP_409 = 409
_WATCHER_ID = 7
_PRIORITY = 2


def _sent_body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


class TestTasksCreate:
    # criterio: 02-C01
    @respx.mock
    def test_create_sends_only_given_fields_and_wraps_response(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_task_response.json"))
        )
        result = TasksAPI(make_transport()).create(
            _POST_ID, title="T", priority=_PRIORITY, watcher_user_ids=[_WATCHER_ID]
        )
        assert route.call_count == 1
        assert _sent_body(route) == {
            "title": "T",
            "priority": _PRIORITY,
            "watcherUserIds": [_WATCHER_ID],
        }
        assert result.task_id == _CREATED_TASK_ID
        assert result.next_occ_token == 1
        assert result.task is not None
        assert result.task.title == "Prepare the quarterly report"
        assert result.capabilities is not None
        assert result.capabilities.can_modify is True
        assert result.raw.taskId == _CREATED_TASK_ID

    # criterio: 02-C02
    @respx.mock
    def test_create_raw_equivalent(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_task_response.json"))
        )
        result = TasksAPI(make_transport()).create_raw(
            _POST_ID, generated.CreateTaskRequestDTO(title="T")
        )
        assert route.call_count == 1
        assert _sent_body(route) == {"title": "T"}
        assert result.task_id == _CREATED_TASK_ID

    # criterio: 02-C03
    @respx.mock
    def test_create_expiration_zoneinfo_in_body(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_task_response.json"))
        )
        TasksAPI(make_transport()).create(
            _POST_ID,
            title="T",
            expiration=datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome")),
        )
        assert _sent_body(route)["expiration"] == {
            "datetime": "2026-12-31T18:00:00",
            "timezone": "Europe/Rome",
        }

    # criterio: 02-C03
    @respx.mock
    def test_create_naive_expiration_raises_before_request(self) -> None:
        route = respx.post(_CREATE_PATH).mock(return_value=httpx.Response(200, json={}))
        with pytest.raises(ValueError, match="timezone"):
            TasksAPI(make_transport()).create(
                _POST_ID, title="T", expiration=datetime(2026, 12, 31, 18, 0)
            )
        assert route.call_count == 0

    # criterio: 02-C13
    @respx.mock
    def test_create_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(_CREATE_PATH).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(TransportError):
            TasksAPI(make_transport()).create(_POST_ID, title="T")
        assert route.call_count == 1


_EDIT_NEXT_OCC_TOKEN = 4
_OCC_TOKEN = 3


class TestTasksEdit:
    # criterio: 02-C04
    @respx.mock
    def test_edit_sends_only_given_fields(self) -> None:
        route = respx.put(_EDIT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("edit_task_response.json"))
        )
        result = TasksAPI(make_transport()).edit(
            _TASK_ID, _OCC_TOKEN, title="T2", remove_watcher_user_ids=[_WATCHER_ID]
        )
        assert route.call_count == 1
        assert _sent_body(route) == {"title": "T2", "removeWatcherUserIds": [_WATCHER_ID]}
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN
        assert result.task_id == _TASK_ID
        assert result.task is not None
        assert result.task.title == "Review quarterly report (updated)"

    # criterio: 02-C04
    @respx.mock
    def test_edit_raw_equivalent(self) -> None:
        route = respx.put(_EDIT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("edit_task_response.json"))
        )
        result = TasksAPI(make_transport()).edit_raw(
            _TASK_ID,
            _OCC_TOKEN,
            generated.EditTaskRequestDTO(title="T2", removeWatcherUserIds=[_WATCHER_ID]),
        )
        assert _sent_body(route) == {"title": "T2", "removeWatcherUserIds": [_WATCHER_ID]}
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN

    # criterio: 02-C04
    @respx.mock
    def test_edit_without_fields_sends_empty_body(self) -> None:
        route = respx.put(_EDIT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("edit_task_response.json"))
        )
        TasksAPI(make_transport()).edit(_TASK_ID, _OCC_TOKEN)
        assert _sent_body(route) == {}

    # criterio: 02-C03
    @respx.mock
    def test_edit_naive_expiration_raises_before_request(self) -> None:
        route = respx.put(_EDIT_PATH).mock(return_value=httpx.Response(200, json={}))
        with pytest.raises(ValueError, match="timezone"):
            TasksAPI(make_transport()).edit(
                _TASK_ID, _OCC_TOKEN, expiration=datetime(2026, 12, 31, 18, 0)
            )
        assert route.call_count == 0

    # criterio: 02-C05
    @respx.mock
    def test_edit_409_raises_concurrency_error_once(self) -> None:
        route = respx.put(_EDIT_PATH).mock(
            return_value=httpx.Response(_HTTP_409, json={"message": "occToken mismatch"})
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            TasksAPI(make_transport()).edit(_TASK_ID, _OCC_TOKEN, title="T2")
        assert exc_info.value.status_code == _HTTP_409
        assert route.call_count == 1


class TestTasksDelete:
    # criterio: 02-C06
    @respx.mock
    def test_delete_returns_post_id(self) -> None:
        route = respx.delete(_DELETE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("delete_task_response.json"))
        )
        post_id = TasksAPI(make_transport()).delete(_TASK_ID)
        assert route.call_count == 1
        assert post_id == _POST_ID

    # criterio: 02-C06
    @respx.mock
    def test_delete_without_body_returns_none(self) -> None:
        route = respx.delete(_DELETE_PATH).mock(return_value=httpx.Response(200))
        assert TasksAPI(make_transport()).delete(_TASK_ID) is None
        assert route.call_count == 1
