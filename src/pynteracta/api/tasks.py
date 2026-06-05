# SPDX-License-Identifier: Apache-2.0
"""Tasks resource client."""

from __future__ import annotations

from pynteracta.api._base import ResourceClient
from pynteracta.models.facade.tasks import Task
from pynteracta.transport import HttpTransport

_GET_TASK_PATH = "communication/tasks/data/task-detail-by-id/{task_id}"


class TasksAPI(ResourceClient):
    """Client for the tasks read endpoint."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def get(self, task_id: int) -> Task:
        """GET ``/communication/tasks/data/task-detail-by-id/{taskId}``.

        Args:
            task_id: The task ID to fetch.

        Returns:
            A :class:`~pynteracta.models.facade.tasks.Task` facade.
        """
        path = _GET_TASK_PATH.format(task_id=task_id)
        return Task.from_dict(self._get(path))
