# SPDX-License-Identifier: Apache-2.0
"""Facade models for the groups endpoints.

Letture (elenco, membri, form di modifica) e, dalla spec 05, i risultati delle scritture:
:class:`GroupWriteResult` per ``create``, ``edit`` ed ``edit_members``, :class:`GroupMembersResult`
con le due liste di :class:`GroupSummary` per ``edit_members_bulk``.
"""

from __future__ import annotations

from typing import Any

from pynteracta.models.generated import external_v2 as generated


def _resolve_root(obj: object) -> object:
    """Unwrap a RootModel stub to its inner dict."""
    root = getattr(obj, "root", None)
    return root if root is not None else obj


class Tag:
    """Thin facade over :class:`~generated.TagDTO1`.

    Attributes:
        raw: The underlying typed DTO.
    """

    def __init__(self, raw: generated.TagDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        return self.raw.name

    @property
    def visible(self) -> bool | None:
        return self.raw.visible


class GroupMember:
    """Thin facade over :class:`~generated.UserDTOModel` for a group member.

    ``ListGroupMembersResponseDTO.items`` and ``GetGroupForEditResponseDTO.members`` are typed as
    ``list[UserDTO]`` (``RootModel[Any]`` stubs); this facade wraps the re-validated typed sibling.

    Attributes:
        raw: The underlying typed DTO.
    """

    def __init__(self, raw: generated.UserDTOModel) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def first_name(self) -> str | None:
        return self.raw.firstName

    @property
    def last_name(self) -> str | None:
        return self.raw.lastName

    @property
    def full_name(self) -> str | None:
        parts = [p for p in (self.raw.firstName, self.raw.lastName) if p]
        return " ".join(parts) if parts else None

    @property
    def email(self) -> str | None:
        return self.raw.contactEmail

    @property
    def deleted(self) -> bool | None:
        return self.raw.deleted

    @property
    def blocked(self) -> bool | None:
        return self.raw.blocked

    @classmethod
    def from_stub(cls, stub: generated.UserDTO) -> GroupMember:
        """Re-validate a ``UserDTO`` ``RootModel[Any]`` stub into :class:`GroupMember`."""
        root = _resolve_root(stub)
        if isinstance(root, dict):
            return cls(generated.UserDTOModel.model_validate(root))
        msg = f"Unexpected stub root type: {type(root)}"
        raise ValueError(msg)


class Group:
    """Narrow facade over :class:`~generated.ListSystemGroupsElementDTOModel`.

    ``ListSystemGroupsResponseDTO.items`` are typed as ``ListSystemGroupsElementDTO``
    (``RootModel[Any]`` stubs); bind to the typed ``ListSystemGroupsElementDTOModel``.

    Attributes:
        raw: The underlying typed DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListSystemGroupsElementDTOModel) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        return self.raw.name

    @property
    def email(self) -> str | None:
        return self.raw.email

    @property
    def description(self) -> str | None:
        return self.raw.description

    @property
    def members_count(self) -> int | None:
        return self.raw.membersCount

    @property
    def visible(self) -> bool | None:
        return self.raw.visible

    @property
    def deleted(self) -> bool | None:
        return self.raw.deleted

    @property
    def creation_timestamp(self) -> int | None:
        return self.raw.creationTimestamp

    @property
    def tags_typed(self) -> list[Tag]:
        """Re-validate each opaque ``TagDTO`` stub into :class:`Tag`."""
        if not self.raw.tags:
            return []
        result = []
        for t in self.raw.tags:
            root = _resolve_root(t)
            if isinstance(root, dict):
                result.append(Tag(generated.TagDTO1.model_validate(root)))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> Group:  # type: ignore[type-arg]
        """Parse from a raw dict item."""
        raw = generated.ListSystemGroupsElementDTOModel.model_validate(data)
        return cls(raw)


class GroupList:
    """Narrow facade over :class:`~generated.ListSystemGroupsResponseDTO`.

    ``items`` are ``ListSystemGroupsElementDTO`` (``RootModel[Any]`` stubs); call
    :meth:`items_typed` to get :class:`Group` instances.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListSystemGroupsResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        return self.raw.totalItemsCount

    @property
    def items_typed(self) -> list[Group]:
        """Re-validate each opaque list item into :class:`Group`."""
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = _resolve_root(item)
            if isinstance(root, dict):
                result.append(Group(generated.ListSystemGroupsElementDTOModel.model_validate(root)))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> GroupList:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        raw = generated.ListSystemGroupsResponseDTO.model_validate(data)
        return cls(raw)


class GroupMemberList:
    """Narrow facade over :class:`~generated.ListGroupMembersResponseDTO`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListGroupMembersResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        return self.raw.totalItemsCount

    @property
    def members_typed(self) -> list[GroupMember]:
        """Re-validate each opaque ``UserDTO`` stub into :class:`GroupMember`."""
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = _resolve_root(item)
            if isinstance(root, dict):
                result.append(GroupMember(generated.UserDTOModel.model_validate(root)))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> GroupMemberList:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        raw = generated.ListGroupMembersResponseDTO.model_validate(data)
        return cls(raw)


class GroupForEdit:
    """Narrow facade over :class:`~generated.GetGroupForEditResponseDTO`.

    The ``members`` list contains ``UserDTO`` (``RootModel[Any]`` stubs); call
    :meth:`members_typed` to re-validate them. :attr:`occ_token` è il token di concorrenza da
    passare a ``edit`` ed ``edit_members`` (spec 05).

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetGroupForEditResponseDTO) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        return self.raw.name

    @property
    def email(self) -> str | None:
        return self.raw.email

    @property
    def description(self) -> str | None:
        return self.raw.description

    @property
    def members_count(self) -> int | None:
        return self.raw.membersCount

    @property
    def visible(self) -> bool | None:
        return self.raw.visible

    @property
    def deleted(self) -> bool | None:
        return self.raw.deleted

    @property
    def creation_timestamp(self) -> int | None:
        return self.raw.creationTimestamp

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza da passare a ``edit`` ed ``edit_members`` (spec 05, RF-023a)."""
        return self.raw.occToken

    @property
    def tags_typed(self) -> list[Tag]:
        """Re-validate each opaque ``TagDTO`` stub into :class:`Tag`."""
        if not self.raw.tags:
            return []
        result = []
        for t in self.raw.tags:
            root = _resolve_root(t)
            if isinstance(root, dict):
                result.append(Tag(generated.TagDTO1.model_validate(root)))
        return result

    @property
    def members_typed(self) -> list[GroupMember]:
        """Re-validate each opaque ``UserDTO`` stub into :class:`GroupMember`."""
        if not self.raw.members:
            return []
        result = []
        for item in self.raw.members:
            root = _resolve_root(item)
            if isinstance(root, dict):
                result.append(GroupMember(generated.UserDTOModel.model_validate(root)))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> GroupForEdit:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        raw = generated.GetGroupForEditResponseDTO.model_validate(data)
        return cls(raw)


class GroupSummary:
    """Façade sul ``GroupDTO`` restituito nelle liste di ``edit_members`` (spec 05).

    ``successGroups`` e ``concurrencyErrorGroups`` sono liste di stub ``RootModel[Any]``; la
    façade avvolge il gemello tipizzato ``GroupDTOModel``.

    Attributes:
        raw: Il DTO tipizzato sottostante.
    """

    def __init__(self, raw: generated.GroupDTOModel) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        return self.raw.name

    @property
    def email(self) -> str | None:
        return self.raw.email

    @property
    def visible(self) -> bool | None:
        return self.raw.visible

    @property
    def deleted(self) -> bool | None:
        return self.raw.deleted

    @property
    def members_count(self) -> int | None:
        return self.raw.membersCount

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza del gruppo dopo la scrittura."""
        return self.raw.occToken

    @classmethod
    def from_stub(cls, stub: generated.GroupDTO) -> GroupSummary:
        """Rivalida uno stub ``GroupDTO`` in :class:`GroupSummary`."""
        root = _resolve_root(stub)
        if isinstance(root, dict):
            return cls(generated.GroupDTOModel.model_validate(root))
        msg = f"Unexpected stub root type: {type(root)}"
        raise ValueError(msg)


class GroupWriteResult:
    """Façade sulla risposta di ``create``, ``edit`` ed ``edit_members`` di un gruppo (spec 05).

    I DTO non hanno gli stessi campi: le proprietà assenti valgono ``None``. ``group_id`` viene
    da ``groupId`` (creazione) o ``id`` (membri), altrimenti è quello passato dal chiamante;
    ``next_occ_token`` viene da ``nextOccToken`` o, per il gruppo restituito da ``edit_members``,
    dal suo ``occToken``.

    Attributes:
        raw: Il DTO generato sottostante (``CreateGroupResponseDTO``, ``EditGroupResponseDTO`` o
            ``GroupDTOModel``).
    """

    def __init__(
        self,
        raw: (
            generated.CreateGroupResponseDTO
            | generated.EditGroupResponseDTO
            | generated.GroupDTOModel
        ),
        *,
        group_id: int | None = None,
    ) -> None:
        self.raw = raw
        self._group_id = group_id

    @property
    def group_id(self) -> int | None:
        """Id del gruppo scritto: dalla risposta, altrimenti quello passato."""
        for attr in ("groupId", "id"):
            value = getattr(self.raw, attr, None)
            if value is not None:
                return int(value)
        return self._group_id

    @property
    def next_occ_token(self) -> int | None:
        """Token di concorrenza da usare per la modifica successiva."""
        value: int | None = getattr(self.raw, "nextOccToken", None)
        if value is not None:
            return value
        occ: int | None = getattr(self.raw, "occToken", None)
        return occ

    @property
    def name(self) -> str | None:
        value: str | None = getattr(self.raw, "name", None)
        return value

    @property
    def email(self) -> str | None:
        value: str | None = getattr(self.raw, "email", None)
        return value

    @property
    def visible(self) -> bool | None:
        value: bool | None = getattr(self.raw, "visible", None)
        return value

    @property
    def members_count(self) -> int | None:
        value: int | None = getattr(self.raw, "membersCount", None)
        return value

    @classmethod
    def from_create(cls, data: dict[str, Any]) -> GroupWriteResult:
        """Legge la risposta di ``POST admin/manage/groups``."""
        return cls(generated.CreateGroupResponseDTO.model_validate(data))

    @classmethod
    def from_edit(cls, data: dict[str, Any], group_id: int) -> GroupWriteResult:
        """Legge la risposta di ``PUT admin/manage/groups/{groupId}``."""
        return cls(generated.EditGroupResponseDTO.model_validate(data), group_id=group_id)

    @classmethod
    def from_member_edit(cls, summary: GroupSummary) -> GroupWriteResult:
        """Avvolge il gruppo restituito in ``successGroups`` da ``edit_members``."""
        return cls(summary.raw, group_id=summary.id)


class GroupMembersResult:
    """Façade sulla risposta di ``PUT admin/manage/groups/members`` (spec 05).

    Il server risponde ``200`` anche con conflitti: :attr:`success_groups` e
    :attr:`concurrency_error_groups` dicono com'è andata gruppo per gruppo.

    Attributes:
        raw: Il DTO generato sottostante.
    """

    def __init__(self, raw: generated.EditMultipleGroupsMembersResponseDTO) -> None:
        self.raw = raw

    @staticmethod
    def _summaries(items: list[generated.GroupDTO] | None) -> list[GroupSummary]:
        return [GroupSummary.from_stub(item) for item in items or []]

    @property
    def success_groups(self) -> list[GroupSummary]:
        """Gruppi modificati, con il nuovo ``occ_token``."""
        return self._summaries(self.raw.successGroups)

    @property
    def concurrency_error_groups(self) -> list[GroupSummary]:
        """Gruppi non modificati perché cambiati dopo la lettura dell'``occToken``."""
        return self._summaries(self.raw.concurrencyErrorGroups)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GroupMembersResult:
        """Parse from a raw API response dict."""
        return cls(generated.EditMultipleGroupsMembersResponseDTO.model_validate(data))
