# SPDX-License-Identifier: Apache-2.0
"""Facade models for the groups endpoints."""

from __future__ import annotations

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
    :meth:`members_typed` to re-validate them. ``occToken`` is only on ``.raw`` — it is the
    propaedeutic edit token for the future write surface.

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
