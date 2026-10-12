# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests for the admin/manage edit (read-form) endpoints."""

from __future__ import annotations

import os

import pytest

from pynteracta.client import InteractaClient

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
            token = before.occ_token
            # Il server vuole il nome in ogni modifica (T14): si ripassano i campi letti.
            keep = {
                "name": before.name,
                "translations": before.translations,
                "description": before.description,
            }
            added = None
            try:
                added = client.admin_manage.edit_workspace(
                    workspace_id, token, add_user_ids=[user_id], **keep
                )
                assert added.occ_token is not None
                token = added.occ_token
                print(
                    f"\n[06-C22] edit_workspace(add_user_ids) con nome, traduzioni e descrizione "
                    "letti: "
                    f"name invariato={added.name == before.name} "
                    f"description invariata={added.description == before.description} "
                    f"member_users_count {before.member_users_count} -> "
                    f"{added.member_users_count}"
                )
            finally:
                final = added or before
                # Se l'utente di prova era già membro il conteggio non cresce: non lo si toglie.
                if added is not None and added.member_users_count != before.member_users_count:
                    final = client.admin_manage.edit_workspace(
                        workspace_id, token, remove_user_ids=[user_id], **keep
                    )
                if final.name != before.name or final.description != before.description:
                    assert final.occ_token is not None
                    final = client.admin_manage.edit_workspace(
                        workspace_id, final.occ_token, **keep
                    )
        assert final.member_users_count == before.member_users_count
        assert final.name == before.name
