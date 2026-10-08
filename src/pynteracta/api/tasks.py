# SPDX-License-Identifier: Apache-2.0
"""Tasks resource client."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_write_body, zoned_datetime_input
from pynteracta.models.facade.tasks import Task, TaskWriteResult
from pynteracta.models.generated.external_v2 import CreateTaskRequestDTO
from pynteracta.transport import HttpTransport

_GET_TASK_PATH = "communication/tasks/data/task-detail-by-id/{task_id}"
_CREATE_TASK_PATH = "communication/tasks/manage/create-task/{post_id}"

# Elementi di sub-task e allegati: dict nella forma del DTO oppure il modello generato.
WriteItems = list[dict[str, Any]] | list[Any] | None


class TasksAPI(ResourceClient):
    """Client for the tasks endpoints: one read, plus create, edit and delete (spec 02)."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def create(  # noqa: PLR0913
        self,
        post_id: int,
        *,
        title: str | None = None,
        description_delta: str | None = None,
        description_plain_text: str | None = None,
        expiration: datetime | None = None,
        priority: int | None = None,
        sub_tasks: WriteItems = None,
        assignee_user_id: int | None = None,
        assignee_group_id: int | None = None,
        attachments: WriteItems = None,
        watcher_user_ids: list[int] | None = None,
        watcher_group_ids: list[int] | None = None,
        client_uid: str | None = None,
    ) -> TaskWriteResult:
        """POST ``/communication/tasks/manage/create-task/{postId}``.

        Il corpo contiene solo i campi passati, in camelCase. ``expiration`` deve avere un fuso
        orario (``ValueError`` altrimenti, prima di qualunque chiamata). Una sola richiesta: un
        errore del server o di rete risale al chiamante, mai un nuovo tentativo.

        Args:
            post_id: Il post a cui il task appartiene.
            title: Titolo del task.
            description_delta: Descrizione in formato Quill delta (JSON).
            description_plain_text: Descrizione in testo semplice.
            expiration: Scadenza, ``datetime`` con fuso.
            priority: Priorità (intero del tenant).
            sub_tasks: Sub-task, nella forma di ``SubTaskDTO`` (dict o modello).
            assignee_user_id: Utente assegnatario.
            assignee_group_id: Gruppo assegnatario.
            attachments: Allegati già noti al server, nella forma di ``InputTaskAttachmentDTO``.
            watcher_user_ids: Utenti osservatori.
            watcher_group_ids: Gruppi osservatori.
            client_uid: Identificativo scelto dal chiamante.

        Returns:
            Un :class:`~pynteracta.models.facade.tasks.TaskWriteResult` con ``task_id``,
            ``next_occ_token``, ``task`` e ``capabilities``.
        """
        body = build_write_body(
            title=title,
            description_delta=description_delta,
            description_plain_text=description_plain_text,
            expiration=zoned_datetime_input(expiration) if expiration is not None else None,
            priority=priority,
            sub_tasks=sub_tasks,
            assignee_user_id=assignee_user_id,
            assignee_group_id=assignee_group_id,
            attachments=attachments,
            watcher_user_ids=watcher_user_ids,
            watcher_group_ids=watcher_group_ids,
            client_uid=client_uid,
        )
        path = _CREATE_TASK_PATH.format(post_id=post_id)
        return TaskWriteResult.from_create(self._post(path, json=body))

    def create_raw(self, post_id: int, req: CreateTaskRequestDTO) -> TaskWriteResult:
        """Come :meth:`create`, da un ``CreateTaskRequestDTO`` già costruito."""
        path = _CREATE_TASK_PATH.format(post_id=post_id)
        return TaskWriteResult.from_create(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def get(self, task_id: int) -> Task:
        """GET ``/communication/tasks/data/task-detail-by-id/{taskId}``.

        Args:
            task_id: The task ID to fetch.

        Returns:
            A :class:`~pynteracta.models.facade.tasks.Task` facade.
        """
        path = _GET_TASK_PATH.format(task_id=task_id)
        return Task.from_dict(self._get(path))
