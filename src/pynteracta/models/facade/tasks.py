# SPDX-License-Identifier: Apache-2.0
"""Facade models for the tasks endpoints."""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated


class TaskCapabilities:
    """Thin facade over :class:`~generated.TaskCapabilitiesDTO1`.

    Attributes:
        raw: The underlying typed DTO.
    """

    def __init__(self, raw: generated.TaskCapabilitiesDTO1) -> None:
        self.raw = raw

    @property
    def can_view_detail(self) -> bool | None:
        return self.raw.canViewDetail

    @property
    def can_modify(self) -> bool | None:
        return self.raw.canModify

    @property
    def can_update_state(self) -> bool | None:
        return self.raw.canUpdateState

    @property
    def can_copy(self) -> bool | None:
        return self.raw.canCopy

    @property
    def can_delete(self) -> bool | None:
        return self.raw.canDelete

    @property
    def can_add_comment(self) -> bool | None:
        return self.raw.canAddComment

    @property
    def can_edit_attachments(self) -> bool | None:
        return self.raw.canEditAttachments

    @property
    def can_edit_reminders(self) -> bool | None:
        return self.raw.canEditReminders


class SubTask:
    """Thin facade over :class:`~generated.SubTaskDTO1`.

    Attributes:
        raw: The underlying typed DTO.
    """

    def __init__(self, raw: generated.SubTaskDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def description(self) -> str | None:
        return self.raw.description

    @property
    def state(self) -> int | None:
        return self.raw.state


class TaskReminder:
    """Thin facade over :class:`~generated.TaskReminderDTO1`.

    Attributes:
        raw: The underlying typed DTO.
    """

    def __init__(self, raw: generated.TaskReminderDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def value(self) -> int | None:
        return self.raw.value

    @property
    def range(self) -> int | None:
        return self.raw.range

    @property
    def types(self) -> list[int] | None:
        return self.raw.types


def _resolve_root(obj: object) -> object:
    """Unwrap a RootModel stub to its inner dict."""
    root = getattr(obj, "root", None)
    return root if root is not None else obj


class Task:
    """Narrow facade over :class:`~generated.GetTaskDetailResponseDTO`.

    Nested ``TaskCapabilitiesDTO``, ``SubTaskDTO``, and ``TaskReminderDTO`` are generated as
    ``RootModel[Any]`` stubs; this facade re-validates them against their typed ``…1`` siblings.

    ``descriptionDelta`` (Quill rich-text JSON), ``surveyData``, and ``surveyDataCommentsInfo``
    are left on ``.raw`` per D-v0.4-4.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetTaskDetailResponseDTO) -> None:
        self.raw = raw
        self._capabilities: TaskCapabilities | None = None
        if raw.capabilities is not None:
            root = _resolve_root(raw.capabilities)
            if isinstance(root, dict):
                self._capabilities = TaskCapabilities(
                    generated.TaskCapabilitiesDTO1.model_validate(root)
                )

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def post_id(self) -> int | None:
        return self.raw.postId

    @property
    def title(self) -> str | None:
        return self.raw.title

    @property
    def description_plain_text(self) -> str | None:
        return self.raw.descriptionPlainText

    @property
    def expiration(self) -> generated.ZonedDatetimeDTO | None:
        return self.raw.expiration

    @property
    def priority(self) -> int | None:
        return self.raw.priority

    @property
    def state(self) -> int | None:
        """Task lifecycle state (integer code). Use ``.raw.currentWorkflowState`` for the post
        workflow state DTO."""
        return self.raw.state

    @property
    def current_workflow_state(self) -> generated.PostWorkflowDefinitionStateDTO | None:
        return self.raw.currentWorkflowState

    @property
    def attachments_count(self) -> int | None:
        return self.raw.attachmentsCount

    @property
    def creation_timestamp(self) -> int | None:
        return self.raw.creationTimestamp

    @property
    def creator_user(self) -> generated.UserDTO | None:
        return self.raw.creatorUser

    @property
    def assignee_user(self) -> generated.UserDTO | None:
        return self.raw.assigneeUser

    @property
    def assignee_group(self) -> generated.GroupDTO | None:
        return self.raw.assigneeGroup

    @property
    def watcher_users(self) -> list[generated.UserDTO] | None:
        return self.raw.watcherUsers

    @property
    def watcher_groups(self) -> list[generated.GroupDTO] | None:
        return self.raw.watcherGroups

    @property
    def capabilities(self) -> TaskCapabilities | None:
        """Typed capabilities facade."""
        return self._capabilities

    @property
    def sub_tasks(self) -> list[SubTask]:
        """Re-validate each opaque ``SubTaskDTO`` stub into :class:`SubTask`."""
        if not self.raw.subTasks:
            return []
        result = []
        for item in self.raw.subTasks:
            root = _resolve_root(item)
            if isinstance(root, dict):
                result.append(SubTask(generated.SubTaskDTO1.model_validate(root)))
        return result

    @property
    def reminders(self) -> list[TaskReminder]:
        """Re-validate each opaque ``TaskReminderDTO`` stub into :class:`TaskReminder`."""
        if not self.raw.reminders:
            return []
        result = []
        for item in self.raw.reminders:
            root = _resolve_root(item)
            if isinstance(root, dict):
                result.append(TaskReminder(generated.TaskReminderDTO1.model_validate(root)))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> Task:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`Task`.
        """
        raw = generated.GetTaskDetailResponseDTO.model_validate(data)
        return cls(raw)
