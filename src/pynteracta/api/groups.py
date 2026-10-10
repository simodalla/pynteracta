# SPDX-License-Identifier: Apache-2.0
"""Groups resource client: letture e scritture admin (spec 05)."""

from __future__ import annotations

from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.api._utils import build_paginated_body, build_write_body
from pynteracta.exceptions import ConcurrencyError, InteractaError
from pynteracta.models.facade.groups import (
    Group,
    GroupForEdit,
    GroupList,
    GroupMember,
    GroupMemberList,
    GroupMembersResult,
    GroupWriteResult,
)
from pynteracta.models.generated import external_v2 as generated
from pynteracta.pagination import PageIterator
from pynteracta.transport import HttpTransport

_LIST_PATH = "admin/data/groups"
_LIST_MEMBERS_PATH = "admin/data/groups/{group_id}/members"
_GET_FOR_EDIT_PATH = "admin/manage/groups/{group_id}/edit"
_CREATE_PATH = "admin/manage/groups"
_EDIT_PATH = "admin/manage/groups/{group_id}"
_MEMBERS_PATH = "admin/manage/groups/members"

# Elemento di edit_members_bulk: dict nella forma di EditGroupMembersRequestDTO o il DTO.
MembersEdit = dict[str, Any] | generated.EditGroupMembersRequestDTO


class GroupsAPI(ResourceClient):
    """Client for group listing, member listing, group-for-edit and admin write endpoints.

    Le scritture (spec 05) inviano **solo i campi passati**, in una sola richiesta: un errore del
    server o di rete risale al chiamante, mai un nuovo tentativo (ADR 0001). Il token di
    concorrenza lo fornisce il chiamante, letto da ``GroupForEdit.occ_token``; un ``409`` è
    ``ConcurrencyError``.
    """

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

    # --- scritture admin (spec 05) -------------------------------------------------------

    def create(
        self,
        *,
        name: str | None = None,
        email: str | None = None,
        external_id: str | None = None,
        visible: bool | None = None,
        member_ids: list[int] | None = None,
    ) -> GroupWriteResult:
        """POST ``/admin/manage/groups``: crea un gruppo.

        Args:
            name: Nome del gruppo.
            email: Email del gruppo.
            external_id: Riferimento esterno.
            visible: ``True`` = visibile per le menzioni; ``False`` = gruppo di sistema.
            member_ids: Id degli utenti membri.
        """
        body = build_write_body(
            name=name, email=email, external_id=external_id, visible=visible, member_ids=member_ids
        )
        return GroupWriteResult.from_create(self._post(_CREATE_PATH, json=body))

    def create_raw(self, req: generated.CreateGroupRequestDTO) -> GroupWriteResult:
        """POST ``/admin/manage/groups`` da un DTO già costruito."""
        return GroupWriteResult.from_create(
            self._post(_CREATE_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )

    def edit(  # noqa: PLR0913
        self,
        group_id: int,
        occ_token: int,
        *,
        name: str | None = None,
        email: str | None = None,
        external_id: str | None = None,
        visible: bool | None = None,
        member_ids: list[int] | None = None,
    ) -> GroupWriteResult:
        """PUT ``/admin/manage/groups/{groupId}``: modifica un gruppo.

        Il corpo contiene solo i campi passati più l'``occToken``. ``member_ids``, se passato, è
        la lista **completa** dei membri; per aggiungere o togliere singoli utenti si usa
        :meth:`edit_members`. I campi omessi non vengono inviati: cosa ne fa il server è scritto
        in ``docs/api/groups.md``.

        Args:
            group_id: Il gruppo da modificare.
            occ_token: Token di concorrenza letto da ``GroupForEdit.occ_token``.
            name: Nome del gruppo.
            email: Email del gruppo.
            external_id: Riferimento esterno.
            visible: Visibilità per le menzioni.
            member_ids: Lista completa degli id dei membri.
        """
        body = build_write_body(
            name=name,
            email=email,
            external_id=external_id,
            visible=visible,
            member_ids=member_ids,
            occ_token=occ_token,
        )
        path = _EDIT_PATH.format(group_id=group_id)
        return GroupWriteResult.from_edit(self._put(path, json=body), group_id)

    def edit_raw(self, group_id: int, req: generated.EditGroupRequestDTO) -> GroupWriteResult:
        """PUT ``/admin/manage/groups/{groupId}`` da un DTO già costruito, ``occToken`` compreso."""
        path = _EDIT_PATH.format(group_id=group_id)
        return GroupWriteResult.from_edit(
            self._put(path, json=req.model_dump(mode="json", exclude_none=True)), group_id
        )

    def delete(self, group_id: int) -> None:
        """DELETE ``/admin/manage/groups/{groupId}``: elimina un gruppo; la risposta è vuota."""
        self._delete(_EDIT_PATH.format(group_id=group_id))

    def edit_members(
        self,
        group_id: int,
        occ_token: int,
        *,
        add_user_ids: list[int] | None = None,
        remove_user_ids: list[int] | None = None,
    ) -> GroupWriteResult:
        """PUT ``/admin/manage/groups/members`` per un solo gruppo.

        Il server risponde ``200`` con due liste: se il gruppo è in ``successGroups`` il risultato
        porta il suo nuovo ``next_occ_token``; se è in ``concurrencyErrorGroups`` la chiamata
        solleva ``ConcurrencyError`` (stato ``200``, corpo allegato); se non è in nessuna delle
        due solleva ``InteractaError``. Una sola richiesta in ogni caso.

        Args:
            group_id: Il gruppo.
            occ_token: Token di concorrenza letto da ``GroupForEdit.occ_token``.
            add_user_ids: Id degli utenti da aggiungere.
            remove_user_ids: Id degli utenti da togliere.
        """
        item = build_write_body(
            id=group_id,
            occ_token=occ_token,
            add_user_ids=add_user_ids,
            delete_user_ids=remove_user_ids,
        )
        body = self._put(_MEMBERS_PATH, json={"groupMembers": [item]})
        result = GroupMembersResult.from_dict(body)
        if any(g.id == group_id for g in result.concurrency_error_groups):
            msg = f"Group {group_id} changed since it was read: members not changed"
            raise ConcurrencyError(
                msg,
                status_code=200,
                request_method="PUT",
                request_url=_MEMBERS_PATH,
                response_body=body,
            )
        for summary in result.success_groups:
            if summary.id == group_id:
                return GroupWriteResult.from_member_edit(summary)
        msg = f"Group {group_id} missing from the members edit response"
        raise InteractaError(
            msg,
            status_code=200,
            request_method="PUT",
            request_url=_MEMBERS_PATH,
            response_body=body,
        )

    def edit_members_bulk(self, groups: list[MembersEdit]) -> GroupMembersResult:
        """PUT ``/admin/manage/groups/members`` per più gruppi in una sola richiesta.

        Ogni elemento è ``{"id", "occToken", "addUserIds", "deleteUserIds"}`` (dict o DTO). Il
        risultato riporta ``success_groups`` e ``concurrency_error_groups``; **non solleva** per i
        conflitti: decide il chiamante.
        """
        body = build_write_body(group_members=groups)
        return GroupMembersResult.from_dict(self._put(_MEMBERS_PATH, json=body))

    def edit_members_bulk_raw(
        self, req: generated.EditMultipleGroupsMembersRequestDTO
    ) -> GroupMembersResult:
        """PUT ``/admin/manage/groups/members`` da un DTO già costruito."""
        return GroupMembersResult.from_dict(
            self._put(_MEMBERS_PATH, json=req.model_dump(mode="json", exclude_none=True))
        )
