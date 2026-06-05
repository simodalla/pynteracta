# SPDX-License-Identifier: Apache-2.0
"""Tests for TasksAPI."""

from __future__ import annotations

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.tasks import TasksAPI

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
        # occToken only reachable via .raw
        assert task.raw.occToken == payload["occToken"]
