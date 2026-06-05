# SPDX-License-Identifier: Apache-2.0
"""Groups resource client."""

from __future__ import annotations

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body
from pynteracta.models.facade.groups import (
    Group,
    GroupForEdit,
    GroupList,
    GroupMember,
    GroupMemberList,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_PATH = "admin/data/groups"
_LIST_MEMBERS_PATH = "admin/data/groups/{group_id}/members"
_GET_FOR_EDIT_PATH = "admin/manage/groups/{group_id}/edit"


class GroupsAPI(ResourceClient):
    """Client for group listing, member listing, and group-for-edit endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list_groups(  # noqa: PLR0913
        self,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        full_text_filter: str | None = None,
        status_filter: list[int] | None = None,
        workspace_ids: list[int] | None = None,
        order_type_id: str | None = None,
        order_desc: bool | None = None,
    ) -> GroupList:
        """POST ``/admin/data/groups``.

        Args:
            page_token: Pagination cursor from a previous response.
            page_size: Maximum items per page.
            full_text_filter: Full-text filter on group name and email.
            status_filter: Filter by group status codes.
            workspace_ids: Filter by workspace IDs.
            order_type_id: Sort field. Valid values: ``'name'``, ``'email'``.
            order_desc: ``True`` for descending, ``False`` for ascending (default: ``True``).
        """
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            full_text_filter=full_text_filter,
            status_filter=status_filter,
            workspace_ids=workspace_ids,
            order_type_id=order_type_id,
            order_desc=order_desc,
        )
        req = generated.ListSystemGroupsRequestDTO.model_validate(body)
        return self.list_groups_raw(req)

    def list_groups_raw(self, req: generated.ListSystemGroupsRequestDTO) -> GroupList:
        """POST group list with a pre-built request DTO (escape hatch)."""
        return GroupList.from_dict(
            self._post(_LIST_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_groups(  # noqa: PLR0913
        self,
        *,
        page_size: int | None = None,
        full_text_filter: str | None = None,
        status_filter: list[int] | None = None,
        workspace_ids: list[int] | None = None,
        order_type_id: str | None = None,
        order_desc: bool | None = None,
    ) -> PageIterator[Group]:
        """Lazy iterator over all pages of :meth:`list_groups`."""

        def fetch(page_token: str | None) -> GroupList:
            return self.list_groups(
                page_token=page_token,
                page_size=page_size,
                full_text_filter=full_text_filter,
                status_filter=status_filter,
                workspace_ids=workspace_ids,
                order_type_id=order_type_id,
                order_desc=order_desc,
            )

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def list_members(
        self,
        group_id: int,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
    ) -> GroupMemberList:
        """POST ``/admin/data/groups/{groupId}/members``.

        Args:
            group_id: The group whose members to list.
            page_token: Pagination cursor.
            page_size: Maximum items per page.
        """
        body = build_paginated_body(page_token=page_token, page_size=page_size)
        req = generated.ListGroupMembersRequestDTO.model_validate(body)
        path = _LIST_MEMBERS_PATH.format(group_id=group_id)
        return GroupMemberList.from_dict(
            self._post(path, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate_members(
        self,
        group_id: int,
        *,
        page_size: int | None = None,
    ) -> PageIterator[GroupMember]:
        """Lazy iterator over all pages of :meth:`list_members`."""

        def fetch(page_token: str | None) -> GroupMemberList:
            return self.list_members(group_id, page_token=page_token, page_size=page_size)

        return PageIterator(fetch, items_getter=lambda page: page.members_typed)

    def get_for_edit(self, group_id: int) -> GroupForEdit:
        """GET ``/admin/manage/groups/{groupId}/edit``.

        Args:
            group_id: The group ID to fetch.
        """
        path = _GET_FOR_EDIT_PATH.format(group_id=group_id)
        return GroupForEdit.from_dict(self._get(path))
