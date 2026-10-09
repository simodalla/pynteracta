# SPDX-License-Identifier: Apache-2.0
"""Integration test opt-in delle scritture dei post (spec 03, 03-C31).

Il ciclo scrive solo in una community di prova (``PYNTERACTA_TEST_WRITE_COMMUNITY_ID``) e cancella
ciò che crea anche quando un passo intermedio fallisce. Le stampe ``[T16]`` servono al maintainer
per annotare ciò che lo swagger non documenta (task manuale T16): campi omessi in ``edit``,
contenuto della copia, formato della descrizione in modifica.
"""

from __future__ import annotations

import contextlib
import json
import os
import time

import pytest

from pynteracta.cli.posts_write import to_write_values
from pynteracta.client import InteractaClient
from pynteracta.exceptions import InteractaError, NotFoundError

pytestmark = pytest.mark.integration

_TITLE = "pynteracta integration test - safe to delete"
_TITLE_EDITED = "pynteracta integration test (edited) - safe to delete"
_TITLE_COPY = "pynteracta integration test (copy) - safe to delete"
_DESCRIPTION = "Created by the post write integration test; safe to delete."
_DESCRIPTION_EDITED = "Edited by the post write integration test; safe to delete."
_PLAIN_TEXT = 2


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


def _custom_data() -> dict[str, object] | None:
    """Campi custom per ``create`` da ``PYNTERACTA_TEST_WRITE_CUSTOM_DATA`` (JSON), se impostata.

    Servono quando la community di prova ha campi obbligatori; i riferimenti a catalogo o utenti
    si scrivono come liste di id, per esempio ``{"2003": [89]}``.
    """
    raw = os.environ.get("PYNTERACTA_TEST_WRITE_CUSTOM_DATA")
    if not raw:
        return None
    value = json.loads(raw)
    assert isinstance(value, dict), "PYNTERACTA_TEST_WRITE_CUSTOM_DATA must be a JSON object"
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


class TestPostsWriteIntegration:
    # criterio: 03-C31
    def test_full_cycle(self, client: InteractaClient) -> None:
        community_id = int(_require_env("PYNTERACTA_TEST_WRITE_COMMUNITY_ID"))
        watcher_id = int(_require_env("PYNTERACTA_TEST_USER_ID"))
        client_uid = f"pynteracta-it-{int(time.time())}"
        created_ids: list[int] = []
        with client:
            try:
                created = client.posts.create(
                    community_id,
                    title=_TITLE,
                    description=_DESCRIPTION,
                    description_format=_PLAIN_TEXT,
                    custom_data=_custom_data(),
                    client_uid=client_uid,
                )
                post_id = created.post_id
                assert post_id is not None
                created_ids.append(post_id)

                found = client.posts.get_by_client_uid(client_uid)
                assert found.id == post_id

                form = client.posts.get_for_edit(post_id)
                assert form.occ_token is not None
                before = form.content_data
                print(
                    f"\n[T16] read before edit: description="
                    f"{before.descriptionPlainText if before else None!r} "
                    f"visibility={before.visibility if before else None} "
                    f"customData={before.customData if before else None!r}"
                )

                # edit sostituisce il post: si rimandano i campi letti, con i riferimenti
                # tradotti in id come fa la CLI; la descrizione nuova va in testo semplice per
                # verificare descriptionFormat 2 in modifica (T16, punto c).
                edited = client.posts.edit(
                    post_id,
                    form.occ_token,
                    title=_TITLE_EDITED,
                    description=_DESCRIPTION_EDITED,
                    description_format=_PLAIN_TEXT,
                    custom_data=to_write_values(before.customData if before else None) or None,
                    visibility=before.visibility if before else None,
                )
                assert edited.next_occ_token is not None
                after = client.posts.get_for_edit(post_id).content_data
                assert after is not None
                assert after.title == _TITLE_EDITED
                print(
                    f"[T16] after edit (plain-text description, custom data as ids): description="
                    f"{after.descriptionPlainText!r} visibility={after.visibility} "
                    f"customData={after.customData!r}"
                )

                client.posts.edit_watchers(post_id, add_user_ids=[watcher_id])
                comment = client.posts.add_comment(
                    post_id, comment="Integration test comment", comment_format=_PLAIN_TEXT
                )
                assert comment.id is not None

                copy_form = client.posts.get_for_copy(post_id)
                assert copy_form.occ_token is not None
                copied = client.posts.copy(post_id, copy_form.occ_token, title=_TITLE_COPY)
                assert copied.post_id is not None
                assert copied.post_id != post_id
                created_ids.append(copied.post_id)
                copy_content = client.posts.get_for_edit(copied.post_id).content_data
                print(
                    f"[T16] copy with title only: description="
                    f"{copy_content.descriptionPlainText if copy_content else None!r} "
                    f"customData={copy_content.customData if copy_content else None!r}"
                )
            except InteractaError as exc:
                # Il dettaglio del server serve al maintainer per T16 (campo rifiutato, ecc.).
                print(
                    f"\n[T16] {exc.request_method} {exc.request_url} failed "
                    f"({exc.status_code}): {exc.response_body!r}"
                )
                raise
            finally:
                for created_id in reversed(created_ids):
                    with contextlib.suppress(NotFoundError):
                        client.posts.delete(created_id)
            for created_id in created_ids:
                with pytest.raises(NotFoundError):
                    client.posts.get(created_id)

    # criterio: 03-C31
    def test_workflow_screen_read_only(self, client: InteractaClient) -> None:
        post_id = int(_require_env("PYNTERACTA_TEST_WORKFLOW_POST_ID"))
        with client:
            screen = client.posts.get_workflow_screen(post_id)
        assert screen.screen_occ_token is not None
        assert screen.current_workflow_state is not None
        print(f"\n[T16] workflow screen: {screen.screen_data!r}")
