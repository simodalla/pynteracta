# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the tasks endpoint."""

from __future__ import annotations

import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from pynteracta.client import InteractaClient
from pynteracta.exceptions import NotFoundError

pytestmark = pytest.mark.integration


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


@pytest.fixture
def client() -> InteractaClient:
    from pathlib import Path  # noqa: PLC0415

    from pynteracta.auth import load_service_account_key  # noqa: PLC0415

    base_url = _require_env("PYNTERACTA_BASE_URL")
    base_path = os.environ.get("PYNTERACTA_BASE_PATH", "/portal")
    api_version = int(os.environ.get("PYNTERACTA_API_VERSION", "2"))
    sa_path = Path(_require_env("PYNTERACTA_SERVICE_ACCOUNT_KEY"))
    if not sa_path.exists():
        pytest.skip(f"Service account key not found: {sa_path}")
    credentials = load_service_account_key(sa_path)
    return InteractaClient(
        base_url, base_path=base_path, api_version=api_version, credentials=credentials
    )


class TestTasksIntegration:
    def test_get_task(self, client: InteractaClient) -> None:
        task_id = int(_require_env("PYNTERACTA_TEST_TASK_ID"))
        with client:
            task = client.tasks.get(task_id)
        assert task.id == task_id
        assert task.post_id is not None
        assert task.title is not None


_WRITE_TITLE = "pynteracta integration test"
_WRITE_TITLE_EDITED = "pynteracta integration test (edited)"


class TestTasksWriteIntegration:
    """Ciclo completo di scrittura su un post di una community di prova (spec 02).

    Le stampe ``[T11]`` servono al maintainer per annotare il formato reale di ``expiration`` e
    l'effetto dei campi omessi in ``edit`` (task manuale T11 della spec 02).
    """

    # criterio: 02-C16
    def test_create_edit_delete_cycle(self, client: InteractaClient) -> None:
        post_id = int(_require_env("PYNTERACTA_TEST_WRITE_POST_ID"))
        client_uid = f"pynteracta-it-{int(time.time())}"
        expiration = datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome"))
        with client:
            created = client.tasks.create(
                post_id,
                title=_WRITE_TITLE,
                description_plain_text="Created by the write integration test; safe to delete.",
                priority=1,
                expiration=expiration,
                client_uid=client_uid,
            )
            task_id = created.task_id
            assert task_id is not None
            try:
                created_expiration = created.task.expiration if created.task else None
                print(f"\n[T11] created task {task_id}: expiration={created_expiration!r}")
                task = client.tasks.get(task_id)
                assert task.title == _WRITE_TITLE
                assert task.occ_token is not None
                print(
                    f"[T11] get: priority={task.priority} expiration={task.expiration!r} "
                    f"occ_token={task.occ_token}"
                )
                edited = client.tasks.edit(task_id, task.occ_token, title=_WRITE_TITLE_EDITED)
                assert edited.next_occ_token is not None
                after = client.tasks.get(task_id)
                assert after.title == _WRITE_TITLE_EDITED
                print(
                    f"[T11] after edit with title only: priority={after.priority} "
                    f"expiration={after.expiration!r} (before: priority=1, expiration set)"
                )
            finally:
                deleted_post = client.tasks.delete(task_id)
                print(f"[T11] deleted task {task_id} (post {deleted_post})")
            with pytest.raises(NotFoundError):
                client.tasks.get(task_id)
