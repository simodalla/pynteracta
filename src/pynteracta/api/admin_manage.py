# SPDX-License-Identifier: Apache-2.0
"""Admin manage edit (read-form) resource client.

The admin/manage *edit* endpoints return the full entity state plus an ``occToken`` (optimistic
concurrency control) used by the future write line (deferred to v1.0+). This client exposes the
four read-form helpers only; the ``occToken`` is carried through each facade's ``.raw``.
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

    These are admin-only read helpers, propaedeutic to the future write surface. Each returns the
    entity's editable state and an ``occToken`` (only on the facade ``.raw``).
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

        Args:
            user_id: The user ID whose credentials to fetch.
        """
        path = _USER_CREDENTIALS_FOR_EDIT_PATH.format(user_id=user_id)
        return UserCredentialsForEdit.from_dict(self._get(path))
