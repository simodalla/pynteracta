# SPDX-License-Identifier: Apache-2.0
"""Admin manage edit (read-form) resource client.

The admin/manage *edit* endpoints return the full entity state plus an ``occToken`` (optimistic
concurrency control) for the write surface. This client exposes the four read-form helpers; the
user credentials write lives on ``client.users`` (``get_credentials_for_edit``,
``edit_credentials``, spec 05), the others arrive with their write spec.
"""

from __future__ import annotations

from pynteracta.api._base import ResourceClient
from pynteracta.models.facade.admin_manage import (
    CatalogEntryForEdit,
    CatalogForEdit,
    UserCredentialsForEdit,
    WorkspaceForEdit,
)
from pynteracta.transport import HttpTransport

_WORKSPACE_FOR_EDIT_PATH = "admin/manage/workspaces/{workspace_id}/edit"
_CATALOG_FOR_EDIT_PATH = "admin/manage/catalogs/{catalog_id}/edit"
_CATALOG_ENTRY_FOR_EDIT_PATH = "admin/manage/catalogs/{catalog_id}/entries/{entry_id}/edit"
_USER_CREDENTIALS_FOR_EDIT_PATH = "admin/manage/users/{user_id}/credentials/edit"


class AdminManageAPI(ResourceClient):
    """Client for the admin/manage edit (read-form) endpoints.

    These are admin-only read helpers, propaedeutic to the write surface. Each returns the
    entity's editable state and an ``occToken`` (``UserCredentialsForEdit.occ_token``; on ``.raw``
    for the others).
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

        Args:
            catalog_id: The catalog ID to fetch.
        """
        path = _CATALOG_FOR_EDIT_PATH.format(catalog_id=catalog_id)
        return CatalogForEdit.from_dict(self._get(path))

    def catalog_entry_for_edit(self, catalog_id: int, entry_id: int) -> CatalogEntryForEdit:
        """GET ``/admin/manage/catalogs/{catalogId}/entries/{entryId}/edit``.

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
