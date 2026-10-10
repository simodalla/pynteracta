# SPDX-License-Identifier: Apache-2.0
"""Users resource client: letture (endpoint 3-5) e scritture admin (spec 05)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_write_body, to_epoch_millis
from pynteracta.models.facade.admin_manage import UserCredentialsForEdit
from pynteracta.models.facade.auth import CurrentUserResponse
from pynteracta.models.facade.users import (
    ListSystemUsersRequestDTO,
    SystemUserList,
    UserForEdit,
    UserProfile,
    UserWriteResult,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_USERS_PATH = "admin/data/users"
_PROFILE_PATH = "core/user-profile/info"
_GET_FOR_EDIT_PATH = "admin/manage/users/{user_id}/edit"
_CURRENT_USER_PATH = "core/auth/current-user-data"
_CREATE_PATH = "admin/manage/users"
_EDIT_PATH = "admin/manage/users/{user_id}"
_DELETE_PATH = "admin/manage/users/{user_id}"
_CREDENTIALS_PATH = "admin/manage/users/{user_id}/credentials"
_CREDENTIALS_FOR_EDIT_PATH = "admin/manage/users/{user_id}/credentials/edit"

# Blocco annidato di una scrittura: dict nella forma del DTO (chiavi camelCase) o DTO generato.
WriteBlock = dict[str, Any] | BaseModel | None


class UsersAPI(ResourceClient):
    """Client for user listing, profile, admin lookup and admin write endpoints.

    Le scritture (spec 05) inviano **solo i campi passati**, in una sola richiesta: un errore del
    server o di rete risale al chiamante, mai un nuovo tentativo (ADR 0001). Il token di
    concorrenza lo fornisce il chiamante, letto da ``UserForEdit.occ_token`` o
    ``UserCredentialsForEdit.occ_token``; un ``409`` è ``ConcurrencyError``. La semantica del
    server sui campi omessi in ``edit`` ed ``edit_credentials`` è documentata in
    ``docs/api/users.md``.
    """

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

    # --- scritture admin (spec 05) -------------------------------------------------------

    def create(  # noqa: PLR0913
        self,
        *,
        firstname: str | None = None,
        lastname: str | None = None,
        contact_email: str | None = None,
        private_email: str | None = None,
        external_id: str | None = None,
        user_preferences: WriteBlock = None,
        user_info: WriteBlock = None,
        user_settings: WriteBlock = None,
        user_credentials_configuration: WriteBlock = None,
        reset_user_custom_credentials_command: WriteBlock = None,
    ) -> UserWriteResult:
        """POST ``/admin/manage/users``: crea un utente.

        Il corpo contiene solo i campi passati, in camelCase. I blocchi annidati sono dict nella
        forma del DTO o DTO generati. La password custom si imposta o si fa generare solo qui,
        con ``reset_user_custom_credentials_command`` (``generatePassword`` oppure ``password``).

        Args:
            firstname: Nome.
            lastname: Cognome.
            contact_email: Email di contatto.
            private_email: Email privata.
            external_id: Riferimento esterno.
            user_preferences: ``AdminUserPreferencesDTO`` (lingua, fuso, notifiche email).
            user_info: ``UserInfoDTO`` (area, business unit, email privata).
            user_settings: ``UserSettingsRequestDTO`` (sezione persone, profilo ridotto…).
            user_credentials_configuration: ``UserCredentialsConfigurationDTO`` (``google``,
                ``microsoft``, ``custom``).
            reset_user_custom_credentials_command: ``ResetUserCustomCredentialsCommandDTO``.
        """
        body = build_write_body(
            firstname=firstname,
            lastname=lastname,
            contact_email=contact_email,
            private_email=private_email,
            external_id=external_id,
            user_preferences=user_preferences,
            user_info=user_info,
            user_settings=user_settings,
            user_credentials_configuration=user_credentials_configuration,
            reset_user_custom_credentials_command=reset_user_custom_credentials_command,
        )
        return UserWriteResult.from_create(self._post(_CREATE_PATH, json=body))

    def create_raw(self, req: generated.CreateUserRequestDTO) -> UserWriteResult:
        """POST ``/admin/manage/users`` da un DTO già costruito."""
        return UserWriteResult.from_create(
            self._post(_CREATE_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def edit(  # noqa: PLR0913
        self,
        user_id: int,
        occ_token: int,
        *,
        firstname: str | None = None,
        lastname: str | None = None,
        contact_email: str | None = None,
        private_email: str | None = None,
        external_id: str | None = None,
        user_preferences: WriteBlock = None,
        user_info: WriteBlock = None,
        user_settings: WriteBlock = None,
    ) -> UserWriteResult:
        """PUT ``/admin/manage/users/{userId}``: modifica un utente.

        Il corpo contiene solo i campi passati più l'``occToken``. I campi omessi non vengono
        inviati: cosa ne fa il server è scritto in ``docs/api/users.md``.

        Args:
            user_id: L'utente da modificare.
            occ_token: Token di concorrenza letto da ``UserForEdit.occ_token``.
            firstname: Nome.
            lastname: Cognome.
            contact_email: Email di contatto.
            private_email: Email privata.
            external_id: Riferimento esterno.
            user_preferences: ``AdminUserPreferencesDTO``.
            user_info: ``UserInfoDTO``.
            user_settings: ``UserSettingsRequestDTO``.
        """
        body = build_write_body(
            firstname=firstname,
            lastname=lastname,
            contact_email=contact_email,
            private_email=private_email,
            external_id=external_id,
            user_preferences=user_preferences,
            user_info=user_info,
            user_settings=user_settings,
            occ_token=occ_token,
        )
        path = _EDIT_PATH.format(user_id=user_id)
        return UserWriteResult.from_edit(self._put(path, json=body), user_id)

    def edit_raw(self, user_id: int, req: generated.EditUserRequestDTO) -> UserWriteResult:
        """PUT ``/admin/manage/users/{userId}`` da un DTO già costruito (``occToken`` compreso)."""
        path = _EDIT_PATH.format(user_id=user_id)
        return UserWriteResult.from_edit(
            self._put(path, json=req.model_dump(mode="json", exclude_none=True)), user_id
        )

    def delete(self, user_id: int) -> None:
        """DELETE ``/admin/manage/users/{userId}``: elimina un utente. La risposta non ha corpo."""
        self._delete(_DELETE_PATH.format(user_id=user_id))

    def edit_credentials(
        self,
        user_id: int,
        occ_token: int,
        *,
        google: WriteBlock = None,
        microsoft: WriteBlock = None,
        custom: WriteBlock = None,
    ) -> UserWriteResult:
        """PUT ``/admin/manage/users/{userId}/credentials``: modifica le credenziali.

        ``userCredentialsConfiguration`` contiene solo i blocchi passati. La password custom non
        si cambia da qui: il DTO non la prevede (solo alla creazione).

        Args:
            user_id: L'utente.
            occ_token: Token letto da ``UserCredentialsForEdit.occ_token``.
            google: ``GoogleUserCredentialsConfigurationDTO`` (``googleAccountId``, ``enabled``).
            microsoft: ``MicrosoftUserCredentialsConfigurationDTO``.
            custom: ``CustomUserCredentialsConfigurationDTO`` (``username``, ``active``…).
        """
        body = {
            "userCredentialsConfiguration": build_write_body(
                google=google, microsoft=microsoft, custom=custom
            ),
            "occToken": occ_token,
        }
        path = _CREDENTIALS_PATH.format(user_id=user_id)
        return UserWriteResult.from_credentials(self._put(path, json=body), user_id)

    def edit_credentials_raw(
        self, user_id: int, req: generated.EditUserCredentialsRequestDTO
    ) -> UserWriteResult:
        """PUT ``/admin/manage/users/{userId}/credentials`` da un DTO già costruito."""
        path = _CREDENTIALS_PATH.format(user_id=user_id)
        return UserWriteResult.from_credentials(
            self._put(path, json=req.model_dump(mode="json", exclude_none=True)), user_id
        )

    def get_credentials_for_edit(self, user_id: int) -> UserCredentialsForEdit:
        """GET ``/admin/manage/users/{userId}/credentials/edit``.

        Alias di :meth:`~pynteracta.api.admin_manage.AdminManageAPI.user_credentials_for_edit`:
        stessa richiesta, stessa façade, con ``occ_token`` per :meth:`edit_credentials`.
        """
        path = _CREDENTIALS_FOR_EDIT_PATH.format(user_id=user_id)
        return UserCredentialsForEdit.from_dict(self._get(path))
