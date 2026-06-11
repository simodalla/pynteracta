# SPDX-License-Identifier: Apache-2.0
"""Users resource client (endpoints 3-5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, to_epoch_millis
from pynteracta.models.facade.auth import CurrentUserResponse
from pynteracta.models.facade.users import (
    ListSystemUsersRequestDTO,
    SystemUserList,
    UserForEdit,
    UserProfile,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_USERS_PATH = "admin/data/users"
_PROFILE_PATH = "core/user-profile/info"
_GET_FOR_EDIT_PATH = "admin/manage/users/{user_id}/edit"
_CURRENT_USER_PATH = "core/auth/current-user-data"


class UsersAPI(ResourceClient):
    """Client for user listing, profile, and admin lookup endpoints."""

    def __init__(self, transport: HttpTransport) -> None:
        super().__init__(transport)

    def list(  # noqa: PLR0913
        self,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        # --- curated filters ---
        full_text_filter: str | None = None,
        status_filter: list[int] | None = None,
        workspace_ids: list[int] | None = None,
        community_ids: list[int] | None = None,
        creation_timestamp_from: int | float | str | datetime | None = None,
        creation_timestamp_to: int | float | str | datetime | None = None,
        last_access_timestamp_from: int | float | str | datetime | None = None,
        last_access_timestamp_to: int | float | str | datetime | None = None,
        role: str | None = None,
        # --- ordering ---
        order_by: str | None = None,
        order_desc: bool | None = None,
        # --- escape hatch ---
        **filters: Any,
    ) -> SystemUserList:
        """POST ``/admin/data/users`` with curated filter and ordering kwargs.

        Args:
            page_token: Opaque token for the page to fetch.
            page_size: Items per page.
            calculate_total_items_count: Ask the API to populate ``totalItemsCount``.
            full_text_filter: Full-text filter on name, surname, and email
                (``fullTextFilter``).
            status_filter: Filter by user status ids (``statusFilter``).
            workspace_ids: Filter by workspace ids (``workspaceIds``).
            community_ids: Filter by community ids (``communityIds``).
            creation_timestamp_from: Lower bound on creation date — epoch-ms ``int``,
                :class:`~datetime.datetime`, or ISO-8601 ``str`` (``creationTimestampFrom``).
            creation_timestamp_to: Upper bound on creation date (``creationTimestampTo``).
            last_access_timestamp_from: Lower bound on last-access date
                (``lastAccessTimestampFrom``).
            last_access_timestamp_to: Upper bound on last-access date
                (``lastAccessTimestampTo``).
            role: Filter by role (``role``).
            order_by: Sort field id — mapped to ``orderTypeId`` (passthrough, no client-side
                validation).
            order_desc: Descending sort (``True``) or ascending (``False``) — ``orderDesc``.
            **filters: Additional snake_case fields forwarded to the request body (converted to
                camelCase). Escape hatch for the long-tail ``ListSystemUsersRequestDTO`` fields
                not promoted to explicit kwargs (e.g. ``business_unit_ids``, ``area_ids``,
                ``manager_ids``, ``lang``, ``login_provider_filter``, name/email prefixes).
        """
        curated: dict[str, Any] = {
            "full_text_filter": full_text_filter,
            "status_filter": status_filter,
            "workspace_ids": workspace_ids,
            "community_ids": community_ids,
            "creation_timestamp_from": to_epoch_millis(creation_timestamp_from),
            "creation_timestamp_to": to_epoch_millis(creation_timestamp_to),
            "last_access_timestamp_from": to_epoch_millis(last_access_timestamp_from),
            "last_access_timestamp_to": to_epoch_millis(last_access_timestamp_to),
            "role": role,
            "order_type_id": order_by,
            "order_desc": order_desc,
        }
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **{**curated, **filters},
        )
        req = ListSystemUsersRequestDTO.model_validate(body)
        return self.list_raw(req)

    def list_raw(self, req: ListSystemUsersRequestDTO) -> SystemUserList:
        """POST ``/admin/data/users`` with a pre-built request DTO (escape hatch)."""
        return SystemUserList.from_dict(
            self._post(_LIST_USERS_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def iterate(
        self,
        *,
        page_size: int | None = None,
        **filters: Any,
    ) -> PageIterator[generated.ListSystemUsersElementDTOModel]:
        """Lazy iterator over all pages of :meth:`list`."""

        def fetch(page_token: str | None) -> SystemUserList:
            return self.list(page_token=page_token, page_size=page_size, **filters)

        return PageIterator(fetch, items_getter=lambda page: page.items_typed)

    def me(self) -> CurrentUserResponse:
        """GET ``/core/auth/current-user-data`` — alias for :meth:`AuthAPI.current_user_data`."""
        return CurrentUserResponse.from_dict(self._get(_CURRENT_USER_PATH))

    def profile(self) -> UserProfile:
        """GET ``/core/user-profile/info`` — own profile (distinct from :meth:`me`)."""
        return UserProfile.from_dict(self._get(_PROFILE_PATH))

    def get_for_edit(self, user_id: int) -> UserForEdit:
        """GET ``/admin/manage/users/{userId}/edit`` — requires admin permissions."""
        path = _GET_FOR_EDIT_PATH.format(user_id=user_id)
        return UserForEdit.from_dict(self._get(path))
