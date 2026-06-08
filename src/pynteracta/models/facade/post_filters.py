# SPDX-License-Identifier: Apache-2.0
"""Custom-field filter helpers for community post listing.

Provides:
- :class:`FilterType` — enum of ``typeId`` values accepted by the API.
- :class:`PostFieldFilter` — thin typed wrapper over one ``postFieldFilters`` entry.
- :func:`validate_field_filters` — opt-in client-side validation against a
  :class:`~pynteracta.models.facade.communities.PostDefinition`.
- :class:`PostFieldFilterBuilder` — resolves human-readable field/value labels to
  numeric ids using a :class:`~pynteracta.models.facade.communities.PostDefinition`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any

from pynteracta.exceptions import ValidationError

if TYPE_CHECKING:
    from pynteracta.models.facade.communities import PostDefinition, PostFieldDefinition


class FilterType(IntEnum):
    """``typeId`` values for ``postFieldFilters`` / ``screenFieldFilters``.

    Maps to the API-documented filter semantics:

    - ``EQUAL`` — exact match; ``parameters`` = ``[value]``.
    - ``INTERVAL`` — range; ``parameters`` = ``[from_millis, to_millis]`` (epoch-ms ints).
    - ``LIKE`` — partial text match; ``parameters`` = ``["substring"]``.
    - ``IN`` — one of a set; ``parameters`` = ``[id1, id2, ...]`` (enum / entity ids).
    - ``CONTAINS`` — field contains value; ``parameters`` = ``[value]``.
    - ``IS_NULL_OR_IN`` — null or one of a set; ``parameters`` = ``[id1, ...]``.
    - ``IS_EMPTY`` — field is empty; ``parameters`` omitted or ``[]``.
    """

    EQUAL = 1
    INTERVAL = 2
    LIKE = 3
    IN = 4
    CONTAINS = 5
    IS_NULL_OR_IN = 6
    IS_EMPTY = 7


# FieldType values whose type↔typeId pairing has been confirmed from real production payloads.
# Keys are FieldType int values; values are the confirmed FilterType.
# Only these pairings are enforced by validate_field_filters (D-v0.7-4 permissive policy).
_CONFIRMED_TYPE_PAIRINGS: dict[int, FilterType] = {
    7: FilterType.IN,  # ENUM
    8: FilterType.IN,  # ENUM_LIST
    13: FilterType.IN,  # HIERARCHICAL_ENUM
    15: FilterType.IN,  # GENERIC_ENTITY_LIST
    4: FilterType.INTERVAL,  # DATE
    5: FilterType.INTERVAL,  # DATETIME
    6: FilterType.LIKE,  # STRING
    9: FilterType.LIKE,  # TEXT_AREA
    11: FilterType.LIKE,  # DELTA_AREA
}

# FieldType int values that carry enum_values (used for parameter id validation).
_ENUM_FIELD_TYPES: frozenset[int] = frozenset({7, 8, 13})

_CUSTOM_FIELD_ORDER_RE = re.compile(r"^postCustomField-\d+$")


@dataclass
class PostFieldFilter:
    """One entry in ``postFieldFilters`` / ``screenFieldFilters``.

    Example::

        PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[226])
    """

    column_id: int
    type_id: FilterType | int
    parameters: list[int | str | float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the camelCase dict the API expects."""
        return {
            "columnId": self.column_id,
            "typeId": int(self.type_id),
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PostFieldFilter:
        """Parse from a raw filter dict (camelCase or snake_case keys accepted)."""
        col = data.get("columnId") or data.get("column_id")
        tid = data.get("typeId") or data.get("type_id")
        params = data.get("parameters", [])
        if col is None or tid is None:
            raise ValueError(f"PostFieldFilter requires column_id and type_id, got: {data!r}")
        return cls(column_id=int(col), type_id=int(tid), parameters=list(params))


def _coerce_filter(f: PostFieldFilter | dict[str, Any]) -> PostFieldFilter:
    if isinstance(f, PostFieldFilter):
        return f
    return PostFieldFilter.from_dict(f)


def validate_field_filters(
    filters: list[PostFieldFilter | dict[str, Any]],
    post_definition: PostDefinition,
    *,
    screen: bool = False,
    allow_deleted_enum_values: bool = False,
) -> list[PostFieldFilter]:
    """Validate *filters* against *post_definition*; return coerced :class:`PostFieldFilter` list.

    Checks (fail-fast, raises :class:`~pynteracta.exceptions.ValidationError`):

    1. Each ``column_id`` exists in the community's ``field_definitions``.
    2. For enum-typed fields (ENUM/ENUM_LIST/HIERARCHICAL_ENUM), every ``parameters`` id is a
       known ``enum_values.id``; deleted values are rejected unless *allow_deleted_enum_values*.
    3. For field types with confirmed ``type↔typeId`` pairings, the ``type_id`` must match;
       unconfirmed types are skipped (permissive — D-v0.7-4).

    Args:
        filters: Filters to validate — each may be a :class:`PostFieldFilter` or a raw dict.
        post_definition: The community post-definition to validate against.
        screen: If ``True``, validates as ``screenFieldFilters`` (same rules, different label).
        allow_deleted_enum_values: If ``True``, deleted enum values are accepted as parameters.

    Returns:
        The same filters coerced to :class:`PostFieldFilter` instances.
    """
    kind = "screenFieldFilters" if screen else "postFieldFilters"
    field_map: dict[int, PostFieldDefinition] = {
        fd.id: fd for fd in post_definition.field_definitions if fd.id is not None
    }

    result: list[PostFieldFilter] = []
    for raw in filters:
        pff = _coerce_filter(raw)
        fd = field_map.get(pff.column_id)
        if fd is None:
            raise ValidationError(
                f"{kind}: column_id {pff.column_id} not found in community post-definition "
                f"(community_id={post_definition.community_id})"
            )

        ft_int = fd.type_raw
        if ft_int is not None:
            # Check confirmed type↔typeId pairing
            confirmed = _CONFIRMED_TYPE_PAIRINGS.get(ft_int)
            if confirmed is not None and int(pff.type_id) != int(confirmed):
                raise ValidationError(
                    f"{kind}: column_id {pff.column_id} ({fd.label!r}) has field type "
                    f"{fd.type!r} which requires type_id={confirmed.name} ({confirmed}), "
                    f"got type_id={pff.type_id}"
                )

            # Validate enum parameter ids
            if ft_int in _ENUM_FIELD_TYPES and pff.parameters:
                allowed_ids: set[int] = set()
                for ev in fd.enum_values:
                    if (not ev.deleted or allow_deleted_enum_values) and ev.id is not None:
                        allowed_ids.add(ev.id)
                for param in pff.parameters:
                    if isinstance(param, (int, float)) and int(param) not in allowed_ids:
                        deleted_ids = {ev.id for ev in fd.enum_values if ev.deleted and ev.id}
                        hint = " (it is deleted)" if int(param) in deleted_ids else ""
                        raise ValidationError(
                            f"{kind}: column_id {pff.column_id} ({fd.label!r}): "
                            f"parameter {param!r} is not a valid enum value id{hint}. "
                            f"Allowed ids: {sorted(allowed_ids)}"
                        )

        result.append(pff)
    return result


class PostFieldFilterBuilder:
    """Build :class:`PostFieldFilter` instances using human-readable field and value labels.

    Resolves field ``externalId`` or ``label`` to ``column_id``, and enum value ``label`` to
    numeric ``id``, using a :class:`~pynteracta.models.facade.communities.PostDefinition`.

    Resolution rules (D-v0.7-9, Q-v0.7-5):

    - ``externalId`` is preferred over ``label`` (unambiguous, stable).
    - Deleted enum values are excluded by default (set *include_deleted=True* to include).
    - Duplicate or ambiguous labels raise :class:`~pynteracta.exceptions.ValidationError` — use
      the numeric ``id`` directly in that case.
    - The default ``type_id`` is inferred from the field ``type`` via the confirmed pairing table;
      pass an explicit *type_id* to override.

    Example::

        builder = PostFieldFilterBuilder(post_definition)
        filters = [
            builder.build("assegnatario", [3872]),          # by field externalId, id param
            builder.build("Tipologia", ["Altro"]),           # by field label, value label
            builder.build("data_", [t_from, t_to],          # date INTERVAL
                          type_id=FilterType.INTERVAL),
        ]
    """

    def __init__(
        self,
        post_definition: PostDefinition,
        *,
        include_deleted: bool = False,
    ) -> None:
        self._post_definition = post_definition
        self._include_deleted = include_deleted
        self._field_map = self._build_field_map()

    def _build_field_map(self) -> dict[str, PostFieldDefinition]:
        """Build a lookup: externalId → fd first, then label → fd (with collision detection)."""
        by_external: dict[str, PostFieldDefinition] = {}
        by_label: dict[str, list[PostFieldDefinition]] = {}
        for fd in self._post_definition.field_definitions:
            if fd.external_id:
                by_external[fd.external_id] = fd
            if fd.label:
                by_label.setdefault(fd.label, []).append(fd)
        result: dict[str, PostFieldDefinition] = dict(by_external)
        for label, fds in by_label.items():
            if label not in result:
                result[label] = fds[0]  # collision/ambiguity handled at resolve time
        # store raw by_label for ambiguity detection
        self._by_label = by_label
        return result

    def _resolve_field(self, field_key: str) -> PostFieldDefinition:
        """Resolve field_key (externalId or label) to a PostFieldDefinition."""
        # Check externalId first
        for fd in self._post_definition.field_definitions:
            if fd.external_id == field_key:
                return fd
        # Then label — check for ambiguity
        matches = self._by_label.get(field_key, [])
        if not matches:
            available = [
                fd.external_id or fd.label or str(fd.id)
                for fd in self._post_definition.field_definitions
            ]
            raise ValidationError(
                f"PostFieldFilterBuilder: field {field_key!r} not found in post-definition. "
                f"Available field keys (externalId or label): {available}"
            )
        if len(matches) > 1:
            ids = [fd.id for fd in matches]
            raise ValidationError(
                f"PostFieldFilterBuilder: label {field_key!r} is ambiguous — matched "
                f"column_ids {ids}. Use the numeric column_id directly."
            )
        return matches[0]

    def _resolve_enum_value(self, fd: PostFieldDefinition, value_label: str) -> int:
        """Resolve an enum value label to its numeric id."""
        candidates = [ev for ev in fd.enum_values if (self._include_deleted or not ev.deleted)]
        # Prefer externalId match
        for ev in candidates:
            if ev.external_id and ev.external_id == value_label:
                if ev.id is None:
                    raise ValidationError(
                        f"PostFieldFilterBuilder: enum value externalId={value_label!r} in "
                        f"field {fd.label!r} has no numeric id"
                    )
                return ev.id
        # Then label match
        label_matches = [ev for ev in candidates if ev.label == value_label]
        if not label_matches:
            all_labels = [
                ev.label for ev in fd.enum_values if not ev.deleted or self._include_deleted
            ]
            raise ValidationError(
                f"PostFieldFilterBuilder: enum value {value_label!r} not found in field "
                f"{fd.label!r}. Available labels: {all_labels}"
            )
        if len(label_matches) > 1:
            ids = [ev.id for ev in label_matches]
            raise ValidationError(
                f"PostFieldFilterBuilder: enum value label {value_label!r} is ambiguous in "
                f"field {fd.label!r} — matched ids {ids}. Use the numeric id directly."
            )
        ev = label_matches[0]
        if ev.id is None:
            raise ValidationError(
                f"PostFieldFilterBuilder: enum value {value_label!r} in field "
                f"{fd.label!r} has no numeric id"
            )
        return ev.id

    def build(
        self,
        field_key: str | int,
        parameters: list[int | str | float] | None = None,
        *,
        type_id: FilterType | int | None = None,
    ) -> PostFieldFilter:
        """Build a :class:`PostFieldFilter` for the given field.

        Args:
            field_key: Field ``externalId``, ``label``, or numeric ``column_id``.
            parameters: Filter values. String items are resolved as enum value labels when the
                field type supports it; numeric items pass through unchanged.
            type_id: Override the inferred ``type_id``. If omitted, inferred from the field type
                via the confirmed pairing table.

        Returns:
            A :class:`PostFieldFilter` ready for use in ``post_field_filters``.
        """
        if isinstance(field_key, int):
            # Direct numeric id — look up fd for type inference only
            field_map_by_id = {
                fd.id: fd for fd in self._post_definition.field_definitions if fd.id is not None
            }
            fd = field_map_by_id.get(field_key)
            column_id = field_key
        else:
            fd = self._resolve_field(field_key)
            column_id = fd.id if fd.id is not None else 0

        # Resolve type_id
        resolved_type_id: FilterType | int
        if type_id is not None:
            resolved_type_id = type_id
        elif fd is not None and fd.type_raw is not None:
            inferred = _CONFIRMED_TYPE_PAIRINGS.get(fd.type_raw)
            resolved_type_id = inferred if inferred is not None else FilterType.EQUAL
        else:
            resolved_type_id = FilterType.EQUAL

        # Resolve string parameters to enum ids when applicable
        resolved_params: list[int | str | float] = []
        for param in parameters or []:
            if isinstance(param, str) and fd is not None and fd.type_raw in _ENUM_FIELD_TYPES:
                resolved_params.append(self._resolve_enum_value(fd, param))
            else:
                resolved_params.append(param)

        return PostFieldFilter(
            column_id=column_id,
            type_id=resolved_type_id,
            parameters=resolved_params,
        )
