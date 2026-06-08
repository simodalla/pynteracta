# SPDX-License-Identifier: Apache-2.0
"""Facade models for the communication settings / communities endpoints.

Endpoints covered:
  GET  /communication/settings/communities                               (endpoint 1)
  GET  /communication/settings/communities/{communityId}/details         (endpoint 2)
  POST /communication/settings/communities/details                       (endpoint 3)
  GET  /communication/settings/communities/{communityId}/post-definition (endpoint 4)
  POST /communication/settings/communities/post-definitions              (endpoint 5)
"""

from __future__ import annotations

from enum import IntEnum

from pynteracta.models.generated import external_v2 as generated

# Re-exported for use by the communities API layer.
ListCommunitiesRequestDTO = generated.ListCommunitiesRequestDTO


class FieldType(IntEnum):
    """Field type identifiers as defined in the CommunicationSettings vendor documentation."""

    INT = 1
    BIGINT = 2
    DECIMAL = 3
    DATE = 4
    DATETIME = 5
    STRING = 6
    ENUM = 7
    ENUM_LIST = 8
    TEXT_AREA = 9
    FLAG = 10
    DELTA_AREA = 11
    FEEDBACK = 12
    HIERARCHICAL_ENUM = 13
    LINK = 14
    GENERIC_ENTITY_LIST = 15


class Community:
    """Narrow facade over :class:`~generated.CommunityDTO1`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.CommunityDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Unique community identifier."""
        return self.raw.id

    @property
    def name(self) -> str | None:
        """Community name."""
        return self.raw.name

    @property
    def description(self) -> str | None:
        """Community description."""
        return self.raw.description

    @classmethod
    def from_raw(cls, raw: generated.CommunityDTO1) -> Community:
        """Wrap a generated DTO."""
        return cls(raw)


class CommunityList:
    """Facade over :class:`~generated.ListCommunitiesResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.ListCommunitiesResponseDTO) -> None:
        self.raw = raw

    @property
    def items(self) -> list[generated.CommunityDTO]:
        """Raw community items (generated stubs)."""
        return self.raw.communities or []

    @property
    def items_typed(self) -> list[Community]:
        """Community items re-validated as typed :class:`Community` facades."""
        result = []
        for item in self.items:
            typed = generated.CommunityDTO1.model_validate(item.root)
            result.append(Community(typed))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> CommunityList:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.ListCommunitiesResponseDTO.model_validate(data))


class CommunityDetail:
    """Facade over :class:`~generated.GetCommunityDetailsResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.GetCommunityDetailsResponseDTO) -> None:
        self.raw = raw

    @property
    def community(self) -> Community | None:
        """The community detail, or ``None`` if absent in the response."""
        if self.raw.community is None:
            return None
        typed = generated.CommunityDTO1.model_validate(self.raw.community.root)
        return Community(typed)

    @classmethod
    def from_dict(cls, data: dict) -> CommunityDetail:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.GetCommunityDetailsResponseDTO.model_validate(data))


class FieldEnumValue:
    """Facade over :class:`~generated.PostFieldConfigEnumValueDTO`.

    Represents one allowed value for an ENUM / ENUM_LIST / HIERARCHICAL_ENUM field.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.PostFieldConfigEnumValueDTO) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Numeric identifier used in ``postFieldFilters`` ``parameters``."""
        return self.raw.id

    @property
    def label(self) -> str | None:
        """Human-readable label."""
        return self.raw.label

    @property
    def external_id(self) -> str | None:
        """Stable external identifier (preferred over ``label`` for resolution)."""
        return self.raw.externalId

    @property
    def parent_ids(self) -> list[int]:
        """Parent ids for hierarchical enums; empty list for flat enums."""
        return self.raw.parentIds or []

    @property
    def deleted(self) -> bool:
        """``True`` if this value has been deleted (soft-deleted, still returned by API)."""
        return bool(self.raw.deleted)

    @classmethod
    def from_raw(cls, raw: generated.PostFieldConfigEnumValueDTO) -> FieldEnumValue:
        """Wrap a generated DTO."""
        return cls(raw)


class PostFieldDefinition:
    """Facade over :class:`~generated.PostFieldDefinitionDTO1`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.PostFieldDefinitionDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Field identifier."""
        return self.raw.id

    @property
    def name(self) -> str | None:
        """Internal field name (e.g. ``column_1459``)."""
        return self.raw.name

    @property
    def label(self) -> str | None:
        """Human-readable field label."""
        return self.raw.label

    @property
    def description(self) -> str | None:
        """Field description / compilation instructions."""
        return self.raw.description

    @property
    def type(self) -> FieldType | None:
        """Typed field type. Returns ``None`` if the raw value is absent or unknown."""
        if self.raw.type is None:
            return None
        try:
            return FieldType(self.raw.type)
        except ValueError:
            return None

    @property
    def type_raw(self) -> int | None:
        """Raw integer field type value, for unknown/future types."""
        return self.raw.type

    @property
    def required(self) -> bool | None:
        """Whether the field is required."""
        return self.raw.required

    @property
    def readonly(self) -> bool | None:
        """Whether the field is read-only."""
        return self.raw.readonly

    @property
    def external_id(self) -> str | None:
        """Stable external identifier set by the API consumer (preferred over label)."""
        return self.raw.externalId

    @property
    def metadata(self) -> dict[str, str] | None:
        """Vendor metadata dict (e.g. ``feedback_max_value``, ``decimal_digits``)."""
        return self.raw.metadata

    @property
    def searchable(self) -> bool | None:
        """Whether the field can be used in ``postFieldFilters``."""
        return self.raw.searchable

    @property
    def sortable(self) -> bool | None:
        """Whether the field can be used in ``orderBy`` (``postCustomField-{id}`` form)."""
        return self.raw.sortable

    @property
    def enum_values(self) -> list[FieldEnumValue]:
        """Allowed enum values for ENUM / ENUM_LIST / HIERARCHICAL_ENUM fields.

        Returns an empty list for non-enum field types.
        Use the ``id`` of each entry as the ``parameters`` value in ``postFieldFilters``.
        """
        result = []
        for raw_val in self.raw.enumValues or []:
            typed = generated.PostFieldConfigEnumValueDTO.model_validate(raw_val.root)
            result.append(FieldEnumValue(typed))
        return result

    @property
    def validations(self) -> list[generated.PostFieldValidationDTO] | None:
        """Validation rules attached to this field."""
        return self.raw.validations

    @classmethod
    def from_raw(cls, raw: generated.PostFieldDefinitionDTO1) -> PostFieldDefinition:
        """Wrap a generated DTO."""
        return cls(raw)


class PostDefinition:
    """Facade over :class:`~generated.GetPostDefinitionResponseDTOModel`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.GetPostDefinitionResponseDTOModel) -> None:
        self.raw = raw

    @property
    def community_id(self) -> int | None:
        """Community identifier this definition belongs to."""
        return self.raw.communityId

    @property
    def field_definitions(self) -> list[PostFieldDefinition]:
        """Custom field definitions, re-validated as typed facades."""
        result = []
        for stub in self.raw.fieldDefinitions or []:
            typed = generated.PostFieldDefinitionDTO1.model_validate(stub.root)
            result.append(PostFieldDefinition(typed))
        return result

    @property
    def hashtags(self) -> list[generated.HashtagDTO] | None:
        """Hashtags configured for this community (typed variants)."""
        result = []
        for stub in self.raw.hashtags or []:
            result.append(generated.HashtagDTO.model_validate(stub.root))
        return result or None

    @property
    def custom_fields_enabled(self) -> bool | None:
        """Whether custom fields are enabled."""
        return self.raw.customFieldsEnabled

    @classmethod
    def from_dict(cls, data: dict) -> PostDefinition:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        raw = generated.GetPostDefinitionResponseDTOModel.model_validate(data)
        return cls(raw)


class PostDefinitionMap:
    """Facade over :class:`~generated.ListPostDefinitionsResponseDTO`.

    The vendor returns a ``communityPostDefinitionMap`` keyed by community ID as a string;
    this facade exposes it with integer keys.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.ListPostDefinitionsResponseDTO) -> None:
        self.raw = raw

    @property
    def definitions(self) -> dict[int, PostDefinition]:
        """Post definitions keyed by community ID (integer)."""
        result: dict[int, PostDefinition] = {}
        if self.raw.communityPostDefinitionMap is None:
            return result
        for str_key, stub in self.raw.communityPostDefinitionMap.items():
            typed = generated.GetPostDefinitionResponseDTOModel.model_validate(stub.root)
            result[int(str_key)] = PostDefinition(typed)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> PostDefinitionMap:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.ListPostDefinitionsResponseDTO.model_validate(data))
