# SPDX-License-Identifier: Apache-2.0
"""Admin manage edit (read-form) resource client.

The admin/manage *edit* endpoints return the full entity state plus an ``occToken`` (optimistic
concurrency control) for the write surface. This client exposes the four read-form helpers; the
user credentials write lives on ``client.users`` (``get_credentials_for_edit``,
``edit_credentials``, spec 05), the catalog and entry writes on ``client.catalogs``
(``get_for_edit``, ``get_entry_for_edit`` sono alias dei form, spec 06).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_write_body
from pynteracta.models.facade.admin_manage import (
    CatalogEntryForEdit,
    CatalogForEdit,
    UserCredentialsForEdit,
    WorkspaceForEdit,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.transport import HttpTransport

_WORKSPACE_FOR_EDIT_PATH = "admin/manage/workspaces/{workspace_id}/edit"
_CATALOG_FOR_EDIT_PATH = "admin/manage/catalogs/{catalog_id}/edit"
_CATALOG_ENTRY_FOR_EDIT_PATH = "admin/manage/catalogs/{catalog_id}/entries/{entry_id}/edit"
_USER_CREDENTIALS_FOR_EDIT_PATH = "admin/manage/users/{user_id}/credentials/edit"
_WORKSPACE_EDIT_PATH = "admin/manage/workspaces/{workspace_id}/{occ_token}"

# Associazioni di ruolo del workspace: dict nella forma del DTO (``{"userId": 1, "roleId": 2}``,
# ``{"groupId": 3, "roleId": 2}``) o DTO generati.
RoleAssociations = list[dict[str, Any] | BaseModel] | None


class AdminManageAPI(ResourceClient):
    """Client for the admin/manage edit (read-form) endpoints.

    These are admin-only read helpers, propaedeutic to the write surface. Each returns the
    entity's editable state and an ``occToken``, esposto come ``occ_token`` da tutte le façade.
    :meth:`edit_workspace` è l'unica scrittura di questo client (spec 06): una sola richiesta, mai
    ripetuta; un ``409`` è ``ConcurrencyError``.
    """

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def workspace_for_edit(self, workspace_id: int) -> WorkspaceForEdit:
        """GET ``/admin/manage/workspaces/{workspaceId}/edit``.

        Args:
            workspace_id: The workspace ID to fetch.
        """
        path = _WORKSPACE_FOR_EDIT_PATH.format(workspace_id=workspace_id)
        return WorkspaceForEdit.from_dict(self._get(path))

    def catalog_for_edit(self, catalog_id: int) -> CatalogForEdit:
        """GET ``/admin/manage/catalogs/{catalogId}/edit``.

        Stessa richiesta di :meth:`~pynteracta.api.catalogs.CatalogsAPI.get_for_edit`; la
        scrittura è :meth:`~pynteracta.api.catalogs.CatalogsAPI.edit` (spec 06).

        Args:
            catalog_id: The catalog ID to fetch.
        """
        path = _CATALOG_FOR_EDIT_PATH.format(catalog_id=catalog_id)
        return CatalogForEdit.from_dict(self._get(path))

    def catalog_entry_for_edit(self, catalog_id: int, entry_id: int) -> CatalogEntryForEdit:
        """GET ``/admin/manage/catalogs/{catalogId}/entries/{entryId}/edit``.

        Stessa richiesta di :meth:`~pynteracta.api.catalogs.CatalogsAPI.get_entry_for_edit`; la
        scrittura è :meth:`~pynteracta.api.catalogs.CatalogsAPI.edit_entry` (spec 06).

        Args:
            catalog_id: The catalog ID owning the entry.
            entry_id: The catalog entry ID to fetch.
        """
        path = _CATALOG_ENTRY_FOR_EDIT_PATH.format(catalog_id=catalog_id, entry_id=entry_id)
        return CatalogEntryForEdit.from_dict(self._get(path))

    def user_credentials_for_edit(self, user_id: int) -> UserCredentialsForEdit:
        """GET ``/admin/manage/users/{userId}/credentials/edit``.

        Stessa richiesta di :meth:`~pynteracta.api.users.UsersAPI.get_credentials_for_edit`;
        la scrittura è :meth:`~pynteracta.api.users.UsersAPI.edit_credentials` (spec 05).

        Args:
            user_id: The user ID whose credentials to fetch.
        """
        path = _USER_CREDENTIALS_FOR_EDIT_PATH.format(user_id=user_id)
        return UserCredentialsForEdit.from_dict(self._get(path))

    def edit_workspace(  # noqa: PLR0913
        self,
        workspace_id: int,
        occ_token: int,
        *,
        name: str | None = None,
        translations: dict[str, str] | None = None,
        description: dict[str, str] | None = None,
        new_cover_image_content_ref: str | None = None,
        new_logo_content_ref: str | None = None,
        add_user_ids: list[int] | None = None,
        remove_user_ids: list[int] | None = None,
        add_group_ids: list[int] | None = None,
        remove_group_ids: list[int] | None = None,
        add_user_role_associations: RoleAssociations = None,
        add_group_role_associations: RoleAssociations = None,
        remove_role_association_ids: list[int] | None = None,
    ) -> WorkspaceForEdit:
        """PUT ``/admin/manage/workspaces/{workspaceId}/{occToken}``: modifica un workspace.

        L'``occToken`` sta nel path, non nel corpo; il corpo contiene solo i campi passati. La
        risposta è il form del workspace: il suo ``occ_token`` vale per la modifica successiva.
        I campi omessi non vengono inviati (semantica del server in ``docs/api/admin_manage.md``).

        Args:
            workspace_id: Il workspace da modificare.
            occ_token: Token letto da ``WorkspaceForEdit.occ_token``.
            name: Nome del workspace.
            translations: Traduzioni del nome per lingua.
            description: Descrizione per lingua.
            new_cover_image_content_ref: ``contentRef`` della copertina, da
                ``client.attachments.upload`` (spec 04).
            new_logo_content_ref: ``contentRef`` del logo.
            add_user_ids: Utenti da aggiungere come membri.
            remove_user_ids: Utenti da togliere.
            add_group_ids: Gruppi da aggiungere come membri.
            remove_group_ids: Gruppi da togliere.
            add_user_role_associations: Ruoli da dare a utenti (``{"userId", "roleId"}``).
            add_group_role_associations: Ruoli da dare a gruppi (``{"groupId", "roleId"}``).
            remove_role_association_ids: Associazioni di ruolo da togliere.
        """
        body = build_write_body(
            name=name,
            translations=translations,
            description=description,
            new_cover_image_content_ref=new_cover_image_content_ref,
            new_logo_content_ref=new_logo_content_ref,
            add_user_ids=add_user_ids,
            remove_user_ids=remove_user_ids,
            add_group_ids=add_group_ids,
            remove_group_ids=remove_group_ids,
            add_user_role_associations=add_user_role_associations,
            add_group_role_associations=add_group_role_associations,
            remove_role_association_ids=remove_role_association_ids,
        )
        path = _WORKSPACE_EDIT_PATH.format(workspace_id=workspace_id, occ_token=occ_token)
        return WorkspaceForEdit.from_dict(self._put(path, json=body))

    def edit_workspace_raw(
        self, workspace_id: int, occ_token: int, req: generated.EditWorkspaceRequestDTO
    ) -> WorkspaceForEdit:
        """PUT ``/admin/manage/workspaces/{workspaceId}/{occToken}`` da un DTO già costruito."""
        path = _WORKSPACE_EDIT_PATH.format(workspace_id=workspace_id, occ_token=occ_token)
        return WorkspaceForEdit.from_dict(
            self._put(path, json=req.model_dump(mode="json", exclude_none=True))
        )
