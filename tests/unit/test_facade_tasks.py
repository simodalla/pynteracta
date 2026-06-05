# SPDX-License-Identifier: Apache-2.0
"""Unit tests for Task facade and nested sub-facades."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

from pynteracta.models.facade.tasks import SubTask, Task, TaskCapabilities, TaskReminder
from pynteracta.models.generated import external_v2 as generated

_PAYLOAD = load_payload("get_task_detail_response.json")
_TASK_ID = 7001
_POST_ID = 21269
_PRIORITY = 2
_STATE = 1
_ATTACHMENTS_COUNT = 2
_CREATION_TS = 1748000000000
_CREATOR_USER_ID = 1099
_ASSIGNEE_USER_ID = 1042
_OCC_TOKEN = 3
_WATCHER_COUNT = 1
_SUB_TASK_COUNT = 2
_SUB_TASK_ID_1 = 801
_REMINDER_ID = 501
_REMINDER_RANGE = 2


@pytest.fixture
def task() -> Task:
    return Task.from_dict(_PAYLOAD)


class TestTaskFacade:
    def test_id(self, task: Task) -> None:
        assert task.id == _TASK_ID

    def test_post_id(self, task: Task) -> None:
        assert task.post_id == _POST_ID

    def test_title(self, task: Task) -> None:
        assert task.title == "Review quarterly report"

    def test_description_plain_text(self, task: Task) -> None:
        assert task.description_plain_text == "Please review the attached quarterly report."

    def test_priority(self, task: Task) -> None:
        assert task.priority == _PRIORITY

    def test_state(self, task: Task) -> None:
        assert task.state == _STATE

    def test_attachments_count(self, task: Task) -> None:
        assert task.attachments_count == _ATTACHMENTS_COUNT

    def test_creation_timestamp(self, task: Task) -> None:
        assert task.creation_timestamp == _CREATION_TS

    def test_creator_user(self, task: Task) -> None:
        assert isinstance(task.creator_user, generated.UserDTO)
        assert task.creator_user.root["id"] == _CREATOR_USER_ID

    def test_assignee_user(self, task: Task) -> None:
        assert isinstance(task.assignee_user, generated.UserDTO)
        assert task.assignee_user.root["id"] == _ASSIGNEE_USER_ID

    def test_watcher_users(self, task: Task) -> None:
        assert task.watcher_users is not None
        assert len(task.watcher_users) == _WATCHER_COUNT

    def test_raw_escape_hatch(self, task: Task) -> None:
        assert task.raw is not None
        assert task.raw.occToken == _OCC_TOKEN

    def test_description_delta_only_on_raw(self, task: Task) -> None:
        assert not hasattr(task, "description_delta")
        assert task.raw.descriptionDelta is not None

    def test_survey_data_only_on_raw(self, task: Task) -> None:
        assert not hasattr(task, "survey_data")
        assert task.raw.surveyData is None


class TestTaskCapabilitiesFacade:
    def test_capabilities(self, task: Task) -> None:
        caps = task.capabilities
        assert isinstance(caps, TaskCapabilities)
        assert caps.can_view_detail is True
        assert caps.can_modify is True
        assert caps.can_update_state is True
        assert caps.can_copy is False
        assert caps.can_delete is False
        assert caps.can_add_comment is True
        assert caps.can_edit_attachments is True
        assert caps.can_edit_reminders is True

    def test_capabilities_raw(self, task: Task) -> None:
        caps = task.capabilities
        assert caps is not None
        assert isinstance(caps.raw, generated.TaskCapabilitiesDTO1)


class TestSubTaskFacade:
    def test_sub_tasks(self, task: Task) -> None:
        sub_tasks = task.sub_tasks
        assert len(sub_tasks) == _SUB_TASK_COUNT
        assert all(isinstance(st, SubTask) for st in sub_tasks)

    def test_sub_task_fields(self, task: Task) -> None:
        st = task.sub_tasks[0]
        assert st.id == _SUB_TASK_ID_1
        assert st.description == "Read introduction"
        assert st.state == 1

    def test_sub_task_raw(self, task: Task) -> None:
        st = task.sub_tasks[0]
        assert isinstance(st.raw, generated.SubTaskDTO1)


class TestTaskReminderFacade:
    def test_reminders(self, task: Task) -> None:
        reminders = task.reminders
        assert len(reminders) == 1
        assert all(isinstance(r, TaskReminder) for r in reminders)

    def test_reminder_fields(self, task: Task) -> None:
        r = task.reminders[0]
        assert r.id == _REMINDER_ID
        assert r.value == 1
        assert r.range == _REMINDER_RANGE
        assert r.types == [1, 2]

    def test_reminder_raw(self, task: Task) -> None:
        r = task.reminders[0]
        assert isinstance(r.raw, generated.TaskReminderDTO1)
