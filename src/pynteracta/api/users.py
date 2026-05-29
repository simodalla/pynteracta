# SPDX-License-Identifier: Apache-2.0
"""Users resource client (endpoints 3-5)."""

from __future__ import annotations

from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body
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

    def list(
        self,
        *,
        page_token: str | None = None,
        page_size: int | None = None,
        calculate_total_items_count: bool | None = None,
        **filters: Any,
    ) -> SystemUserList:
        """POST ``/admin/data/users`` with explicit filter kwargs."""
        body = build_paginated_body(
            page_token=page_token,
            page_size=page_size,
            calculate_total_items_count=calculate_total_items_count,
            **filters,
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
