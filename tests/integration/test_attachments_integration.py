# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the attachments endpoints.

Il ciclo di upload (spec 04, 04-C18) scrive solo nella community di prova
(``PYNTERACTA_TEST_WRITE_COMMUNITY_ID``) e cancella il post che crea anche quando un passo
intermedio fallisce. Le stampe ``[T15]`` servono al maintainer per il task manuale T15: cosa fa
il server con il nome del file in ``updateAttachments``.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

import pytest

from pynteracta.client import InteractaClient
from pynteracta.exceptions import InteractaError, NotFoundError

pytestmark = pytest.mark.integration


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


def _custom_data() -> dict[str, object] | None:
    """Campi custom per ``create`` da ``PYNTERACTA_TEST_WRITE_CUSTOM_DATA`` (JSON), se impostata.

    Duplicato di ``test_posts_integration.py``: la community di prova può avere campi
    obbligatori.
    """
    raw = os.environ.get("PYNTERACTA_TEST_WRITE_CUSTOM_DATA")
    if not raw:
        return None
    value = json.loads(raw)
    assert isinstance(value, dict), "PYNTERACTA_TEST_WRITE_CUSTOM_DATA must be a JSON object"
    return value


@pytest.fixture
def client() -> InteractaClient:
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


class TestAttachmentsIntegration:
    def test_list_for_post(self, client: InteractaClient) -> None:
        post_id = int(_require_env("PYNTERACTA_TEST_POST_ID"))
        with client:
            result = client.attachments.list_for_post(post_id)
        assert result.total_items_count is not None
        assert isinstance(result.items_typed, list)

    def test_get_attachment(self, client: InteractaClient) -> None:
        attachment_id = int(_require_env("PYNTERACTA_TEST_ATTACHMENT_ID"))
        with client:
            detail = client.attachments.get(attachment_id)
        assert detail.id == attachment_id
        assert detail.name is not None

    def test_check_visibility(self, client: InteractaClient) -> None:
        attachment_id = int(_require_env("PYNTERACTA_TEST_ATTACHMENT_ID"))
        with client:
            result = client.attachments.check_visibility([attachment_id])
        assert isinstance(result.ids, list)

    def test_iterate_for_post(self, client: InteractaClient) -> None:
        post_id = int(_require_env("PYNTERACTA_TEST_POST_ID"))
        with client:
            items = list(client.attachments.iterate_for_post(post_id, page_size=2))
        assert isinstance(items, list)


_PLAIN_TEXT = 2


class TestAttachmentsUploadIntegration:
    # criterio: 04-C18
    def test_full_cycle(self, client: InteractaClient, tmp_path: Path) -> None:
        community_id = int(_require_env("PYNTERACTA_TEST_WRITE_COMMUNITY_ID"))
        first = tmp_path / "pynteracta-it-nota.txt"
        first.write_text("pynteracta integration test - safe to delete\n", encoding="utf-8")
        second = tmp_path / "pynteracta-it-nota-v2.txt"
        second.write_text("pynteracta integration test, version 2\n", encoding="utf-8")
        post_id: int | None = None
        with client:
            try:
                uploaded = client.attachments.upload(first)
                assert uploaded.content_ref
                created = client.posts.create(
                    community_id,
                    title="pynteracta upload integration test - safe to delete",
                    description="Created by the upload integration test; safe to delete.",
                    description_format=_PLAIN_TEXT,
                    custom_data=_custom_data(),
                    attachments=[uploaded],
                    client_uid=f"pynteracta-it-upload-{int(time.time())}",
                )
                post_id = created.post_id
                assert post_id is not None

                items = client.attachments.list_for_post(post_id).items_typed
                attached = [item for item in items if item.name == first.name]
                assert attached, f"{first.name} not in {[item.name for item in items]}"
                attachment_id = attached[0].id
                assert attachment_id is not None
                print(
                    f"\n[T15] attached: id={attachment_id} name={attached[0].name!r} "
                    f"version={attached[0].version_number} mime={attached[0].content_mime_type}"
                )

                version = client.attachments.upload(second)
                updated = client.posts.edit_attachments(
                    post_id, update=[version.as_version_of(attachment_id)]
                )
                assert updated.updated, "updateAttachments returned no attachment"
                after = updated.updated[0]
                print(
                    f"[T15] new version: id={after.id} name={after.name!r} "
                    f"version={after.versionNumber} (name sent: {second.name!r})"
                )

                removed = client.posts.edit_attachments(post_id, remove_ids=[after.id or 0])
                assert after.id in removed.removed_ids
                remaining = client.attachments.list_for_post(post_id).items_typed
                assert all(item.id != after.id for item in remaining)
            except InteractaError as exc:
                print(
                    f"\n[T15] {exc.request_method} {exc.request_url} failed "
                    f"({exc.status_code}): {exc.response_body!r}"
                )
                raise
            finally:
                if post_id is not None:
                    with contextlib.suppress(NotFoundError):
                        client.posts.delete(post_id)
