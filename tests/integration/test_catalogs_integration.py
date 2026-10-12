# SPDX-License-Identifier: Apache-2.0
"""Integration test opt-in del ciclo di scrittura di un catalogo e di una voce (spec 06).

Crea un catalogo e una voce con nome ``pynteracta-it-<timestamp>`` sul tenant e li disabilita al
termine, anche se un passo intermedio fallisce: l'API non ha l'eliminazione fisica. Le stampe
``[06-C21]`` servono al maintainer (task T14).
"""

from __future__ import annotations

import os
import time

import pytest

from pynteracta.client import InteractaClient
from pynteracta.exceptions import ValidationError

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


class TestCatalogsWriteIntegration:
    # criterio: 06-C21
    def test_create_edit_entry_delete_cycle(self, client: InteractaClient) -> None:
        name = f"pynteracta-it-{int(time.time())}"
        catalog_id: int | None = None
        with client:
            try:
                created = client.catalogs.create(name={"it": name})
                catalog_id = created.catalog_id
                assert catalog_id is not None

                form = client.catalogs.get_for_edit(catalog_id)
                assert form.occ_token is not None
                print(
                    f"\n[06-C21] catalogs.get_for_edit: occ_token={form.occ_token} "
                    f"parent_catalog_id={form.parent_catalog_id} name={form.name}"
                )

                edited = client.catalogs.edit(catalog_id, form.occ_token, name={"en": f"{name}-en"})
                assert edited.catalog_id == catalog_id
                after_edit = client.catalogs.get_for_edit(catalog_id)
                print(
                    f"[06-C21] catalogs.edit(name={{'en': …}}) con la sola lingua en: "
                    f"name={after_edit.name} (prima: {form.name}) "
                    f"parent_catalog_id={after_edit.parent_catalog_id}"
                )

                entry = client.catalogs.create_entry(
                    catalog_id, label={"it": f"{name}-voce"}, external_id=f"{name}-ext"
                )
                entry_id = entry.entry_id
                assert entry_id is not None
                entry_form = client.catalogs.get_entry_for_edit(catalog_id, entry_id)
                assert entry_form.occ_token is not None

                client.catalogs.edit_entry(
                    catalog_id, entry_id, entry_form.occ_token, label={"en": f"{name}-entry"}
                )
                after_entry_edit = client.catalogs.get_entry_for_edit(catalog_id, entry_id)
                print(
                    f"[06-C21] catalogs.edit_entry(label={{'en': …}}) con external id e parent "
                    f"omessi: label={after_entry_edit.label} (prima: {entry_form.label}) "
                    f"external_id={after_entry_edit.external_id} (prima: {entry_form.external_id}) "
                    f"parents_count={after_entry_edit.parents_count}"
                )

                entry_deleted = client.catalogs.set_entry_deleted(catalog_id, entry_id, True)
                assert entry_deleted.deleted is True
                print(
                    f"[06-C21] set_entry_deleted: risposta {entry_deleted.raw.model_dump()} "
                    f"({type(entry_deleted.raw).__name__})"
                )
            finally:
                if catalog_id is not None:
                    client.catalogs.set_deleted(catalog_id, True)
            try:
                listed = client.catalogs.list([catalog_id])
                visible = [c.id for c in listed.items_typed]
                print(f"[06-C21] catalogs.list([id]) dopo set_deleted(True): ids={visible}")
            # catalogs.list() senza id restituisce una lista vuota sul tenant di prova (T14):
            # la visibilità dei disabilitati si prova solo chiedendoli per id.
            except ValidationError as exc:  # il tenant risponde 400 NOT_EXISTS (T14)
                print(
                    f"[06-C21] catalogs.list([id]) dopo set_deleted(True): {exc.status_code} "
                    f"{exc.response_body}"
                )
            final = client.catalogs.get_for_edit(catalog_id)
        assert final.deleted is True
