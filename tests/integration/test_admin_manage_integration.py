# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the admin/manage edit (read-form) endpoints."""

from __future__ import annotations

import os

import pytest

from pynteracta.client import InteractaClient
from pynteracta.models.facade.admin_manage import WorkspaceForEdit

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


class TestAdminManageIntegration:
    def test_workspace_for_edit(self, client: InteractaClient) -> None:
        workspace_id = int(_require_env("PYNTERACTA_TEST_WORKSPACE_ID"))
        with client:
            ws = client.admin_manage.workspace_for_edit(workspace_id)
        assert ws.id == workspace_id
        assert ws.raw.occToken is not None

    def test_catalog_for_edit(self, client: InteractaClient) -> None:
        catalog_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ID"))
        with client:
            catalog = client.admin_manage.catalog_for_edit(catalog_id)
        assert catalog.id == catalog_id
        assert catalog.raw.occToken is not None

    def test_catalog_entry_for_edit(self, client: InteractaClient) -> None:
        catalog_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ID"))
        entry_id = int(_require_env("PYNTERACTA_TEST_CATALOG_ENTRY_ID"))
        with client:
            entry = client.admin_manage.catalog_entry_for_edit(catalog_id, entry_id)
        assert entry.id == entry_id
        assert entry.raw.occToken is not None

    def test_user_credentials_for_edit(self, client: InteractaClient) -> None:
        user_id = int(_require_env("PYNTERACTA_TEST_USER_ID"))
        with client:
            creds = client.admin_manage.user_credentials_for_edit(user_id)
        assert creds.raw.occToken is not None


def _member_user_ids(form: WorkspaceForEdit) -> list[int]:
    """Id della prima pagina di ``contentData.memberUsers`` del form (bastano per il test)."""
    content = form.raw.contentData
    root = content.root if content is not None else None
    member_users = root.get("memberUsers") if isinstance(root, dict) else None
    items = (member_users or {}).get("items") or []
    return [item["id"] for item in items if isinstance(item, dict) and "id" in item]


def _require_flag(name: str) -> None:
    if os.environ.get(name) != "1":
        pytest.skip(f"{name} is not 1")


class TestWorkspaceWriteIntegration:
    """Ciclo di scrittura del workspace di prova (spec 06, opt-in dedicato).

    Il workspace è condiviso con utenti reali: parte solo con
    ``PYNTERACTA_TEST_WRITE_WORKSPACE=1``, aggiunge e toglie l'utente di prova e, se la ``PUT``
    avesse cambiato nome o descrizione, li rimette come li ha letti. Ogni ``PUT`` ripassa nome,
    traduzioni e descrizione letti, perché il server vuole il nome in ogni modifica (T14). Le
    stampe ``[06-C22]`` servono al maintainer (task T14).
    """

    # criterio: 06-C22
    def test_add_remove_member_cycle(self, client: InteractaClient) -> None:
        _require_flag("PYNTERACTA_TEST_WRITE_WORKSPACE")
        workspace_id = int(_require_env("PYNTERACTA_TEST_WORKSPACE_ID"))
        user_id = int(_require_env("PYNTERACTA_TEST_USER_ID"))
        with client:
            before = client.admin_manage.workspace_for_edit(workspace_id)
            assert before.occ_token is not None
            if user_id in _member_user_ids(before):
                pytest.skip("the test user is already a member of the test workspace")
            # Il server vuole il nome in ogni modifica (T14): si ripassano i campi letti.
            keep = {
                "name": before.name,
                "translations": before.translations,
                "description": before.description,
            }
            added = None
            try:
                added = client.admin_manage.edit_workspace(
                    workspace_id, before.occ_token, add_user_ids=[user_id], **keep
                )
                after_add = client.admin_manage.workspace_for_edit(workspace_id)
                print(
                    "\n[06-C22] edit_workspace(add_user_ids) con nome, traduzioni e descrizione "
                    f"letti: utente aggiunto={user_id in _member_user_ids(after_add)} "
                    f"member_users_count {before.member_users_count} -> "
                    f"{after_add.member_users_count}; conteggi nella risposta della PUT: "
                    f"{added.member_users_count}, occ_token della risposta = token successivo: "
                    f"{added.occ_token == after_add.occ_token}"
                )
                assert user_id in _member_user_ids(after_add)
            finally:
                current = client.admin_manage.workspace_for_edit(workspace_id)
                if user_id in _member_user_ids(current):
                    assert current.occ_token is not None
                    client.admin_manage.edit_workspace(
                        workspace_id, current.occ_token, remove_user_ids=[user_id], **keep
                    )
            final = client.admin_manage.workspace_for_edit(workspace_id)
            print(
                "[06-C22] dopo remove_user_ids: "
                f"utente presente={user_id in _member_user_ids(final)} "
                f"member_users_count={final.member_users_count} "
                f"name invariato={final.name == before.name} "
                f"translations invariate={final.translations == before.translations} "
                f"description invariata={final.description == before.description}"
            )
        assert user_id not in _member_user_ids(final)
        assert final.member_users_count == before.member_users_count
        assert final.name == before.name
