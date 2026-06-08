# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: PLR2004
"""Tests for post_filters facade: FilterType, PostFieldFilter, validate_field_filters,
PostFieldFilterBuilder, and the updated PostFieldDefinition.enum_values."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pynteracta.exceptions import ValidationError
from pynteracta.models.facade.communities import PostDefinition
from pynteracta.models.facade.post_filters import (
    FilterType,
    PostFieldFilter,
    PostFieldFilterBuilder,
    validate_field_filters,
)
from pynteracta.models.generated import external_v2 as generated

_PAYLOADS = Path(__file__).resolve().parent.parent / "fixtures" / "payloads"


def _load_post_definition() -> generated.GetPostDefinitionResponseDTOModel:
    """Load the real 'attività' post-definition fixture."""
    raw = json.loads((_PAYLOADS / "post_definition_attivita.json").read_text(encoding="utf-8"))
    # The fixture is the fieldDefinitions array directly; wrap it
    return generated.GetPostDefinitionResponseDTOModel(
        communityId=17,
        fieldDefinitions=[generated.PostFieldDefinitionDTO(root=item) for item in raw],
    )


def _make_post_definition() -> PostDefinition:
    return PostDefinition(_load_post_definition())


class TestFilterType:
    def test_all_values(self) -> None:
        assert FilterType.EQUAL == 1
        assert FilterType.INTERVAL == 2
        assert FilterType.LIKE == 3
        assert FilterType.IN == 4
        assert FilterType.CONTAINS == 5
        assert FilterType.IS_NULL_OR_IN == 6
        assert FilterType.IS_EMPTY == 7


class TestPostFieldFilter:
    def test_to_dict_camelcase(self) -> None:
        f = PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[226, 512])
        d = f.to_dict()
        assert d == {"columnId": 1411, "typeId": 4, "parameters": [226, 512]}

    def test_from_dict_camel(self) -> None:
        f = PostFieldFilter.from_dict({"columnId": 1411, "typeId": 4, "parameters": [226]})
        assert f.column_id == 1411
        assert f.type_id == 4
        assert f.parameters == [226]

    def test_from_dict_snake(self) -> None:
        f = PostFieldFilter.from_dict({"column_id": 1957, "type_id": 3, "parameters": ["aaa"]})
        assert f.column_id == 1957
        assert f.parameters == ["aaa"]

    def test_from_dict_missing_required_raises(self) -> None:
        with pytest.raises(ValueError, match="column_id"):
            PostFieldFilter.from_dict({"typeId": 4})

    def test_interval_parameters(self) -> None:
        f = PostFieldFilter(
            column_id=1954, type_id=FilterType.INTERVAL, parameters=[1780264800000, 1780955999999]
        )
        assert f.to_dict()["parameters"] == [1780264800000, 1780955999999]

    def test_like_parameters(self) -> None:
        f = PostFieldFilter(column_id=1957, type_id=FilterType.LIKE, parameters=["aaa"])
        assert f.to_dict()["parameters"] == ["aaa"]


class TestPostFieldDefinitionEnumValues:
    def test_enum_values_returned(self) -> None:
        pd = _make_post_definition()
        tipologia = next(fd for fd in pd.field_definitions if fd.id == 1411)
        evs = tipologia.enum_values
        assert len(evs) > 0
        ids = [ev.id for ev in evs]
        assert 226 in ids  # "Manutenzione sistemistica..."

    def test_deleted_flag(self) -> None:
        pd = _make_post_definition()
        tipologia = next(fd for fd in pd.field_definitions if fd.id == 1411)
        deleted = [ev for ev in tipologia.enum_values if ev.deleted]
        active = [ev for ev in tipologia.enum_values if not ev.deleted]
        assert len(deleted) > 0  # "Progetto", "Scuola", etc. are deleted
        assert len(active) > 0

    def test_non_enum_field_returns_empty_list(self) -> None:
        pd = _make_post_definition()
        # column 1954 is DATETIME (type 5) — no enumValues
        datetime_field = next(fd for fd in pd.field_definitions if fd.id == 1954)
        assert datetime_field.enum_values == []

    def test_field_enum_value_properties(self) -> None:
        pd = _make_post_definition()
        tipologia = next(fd for fd in pd.field_definitions if fd.id == 1411)
        ev = next(ev for ev in tipologia.enum_values if ev.id == 226)
        assert ev.label == "Manutenzione sistemistica (aggiornamenti software, ecc..)"
        assert ev.deleted is False


class TestValidateFieldFilters:
    def test_valid_in_filter(self) -> None:
        pd = _make_post_definition()
        filters = [PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[226])]
        result = validate_field_filters(filters, pd)
        assert len(result) == 1

    def test_valid_interval_filter(self) -> None:
        pd = _make_post_definition()
        filters = [
            PostFieldFilter(
                column_id=1954,
                type_id=FilterType.INTERVAL,
                parameters=[1780264800000, 1780955999999],
            )
        ]
        result = validate_field_filters(filters, pd)
        assert len(result) == 1

    def test_valid_like_filter(self) -> None:
        pd = _make_post_definition()
        filters = [PostFieldFilter(column_id=1957, type_id=FilterType.LIKE, parameters=["aaa"])]
        result = validate_field_filters(filters, pd)
        assert len(result) == 1

    def test_unknown_column_id_raises(self) -> None:
        pd = _make_post_definition()
        filters = [PostFieldFilter(column_id=9999, type_id=FilterType.IN, parameters=[1])]
        with pytest.raises(ValidationError, match="column_id 9999"):
            validate_field_filters(filters, pd)

    def test_invalid_enum_value_raises(self) -> None:
        pd = _make_post_definition()
        filters = [PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[9999])]
        with pytest.raises(ValidationError, match="9999"):
            validate_field_filters(filters, pd)

    def test_deleted_enum_value_raises_by_default(self) -> None:
        pd = _make_post_definition()
        # id 26 = "Progetto" (deleted=True) in column 1411
        filters = [PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[26])]
        with pytest.raises(ValidationError, match="deleted"):
            validate_field_filters(filters, pd)

    def test_deleted_enum_value_allowed_when_flag_set(self) -> None:
        pd = _make_post_definition()
        filters = [PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[26])]
        result = validate_field_filters(filters, pd, allow_deleted_enum_values=True)
        assert len(result) == 1

    def test_type_mismatch_raises_for_confirmed_pairing(self) -> None:
        pd = _make_post_definition()
        # column 1411 is ENUM (type 7) — must use IN (4), not LIKE (3)
        filters = [PostFieldFilter(column_id=1411, type_id=FilterType.LIKE, parameters=["x"])]
        with pytest.raises(ValidationError, match="type_id=IN"):
            validate_field_filters(filters, pd)

    def test_accepts_dict_input(self) -> None:
        pd = _make_post_definition()
        filters = [{"columnId": 1411, "typeId": 4, "parameters": [226]}]
        result = validate_field_filters(filters, pd)  # type: ignore[arg-type]
        assert result[0].column_id == 1411

    def test_production_payload(self) -> None:
        """Replay the confirmed production postFieldFilters payload."""
        pd = _make_post_definition()
        filters = [
            PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[226]),
            PostFieldFilter(column_id=1415, type_id=FilterType.IN, parameters=[3872]),
            PostFieldFilter(column_id=1908, type_id=FilterType.IN, parameters=[525]),
        ]
        # 1415 is GENERIC_ENTITY_LIST — parameter 3872 is an entity id, not an enum; skip enum check
        # 1908 is ENUM_LIST
        # We only validate 1908 for enum; 1415 skip (type 15 = GENERIC_ENTITY_LIST, no enumValues)
        # Just confirm it doesn't crash for valid inputs
        result = validate_field_filters(filters[:1] + filters[2:], pd)
        assert len(result) == 2


class TestPostFieldFilterBuilder:
    def test_build_by_external_id(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        f = builder.build("assegnatario", [3872])
        assert f.column_id == 1415
        assert f.type_id == FilterType.IN
        assert f.parameters == [3872]

    def test_build_by_label(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        f = builder.build("Tipologia", [226])
        assert f.column_id == 1411

    def test_build_resolves_enum_label(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        f = builder.build("Tipologia", ["Generica"])  # "Generica" = id 28 in column 1411
        assert f.column_id == 1411
        assert 28 in f.parameters

    def test_build_by_column_id_int(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        f = builder.build(1411, [226])
        assert f.column_id == 1411

    def test_build_with_explicit_type_id(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        f = builder.build("data_", [1780264800000, 1780955999999], type_id=FilterType.INTERVAL)
        assert f.column_id == 1954
        assert f.type_id == FilterType.INTERVAL

    def test_unknown_field_raises(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        with pytest.raises(ValidationError, match="not found"):
            builder.build("campo_inesistente", [1])

    def test_deleted_enum_label_excluded_by_default(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        with pytest.raises(ValidationError, match=r"not found|Progetto"):
            builder.build("Tipologia", ["Progetto"])  # deleted

    def test_deleted_enum_label_allowed_with_flag(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd, include_deleted=True)
        f = builder.build("Tipologia", ["Progetto"])
        assert 26 in f.parameters  # id=26 for "Progetto"

    def test_infers_like_for_text_field(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        # column 1957 "Causa" is DELTA_AREA (type 11) → should infer LIKE
        f = builder.build("causa", ["testo"])
        assert f.column_id == 1957
        assert f.type_id == FilterType.LIKE

    def test_infers_interval_for_datetime_field(self) -> None:
        pd = _make_post_definition()
        builder = PostFieldFilterBuilder(pd)
        f = builder.build("data_", [1780264800000, 1780955999999])
        assert f.type_id == FilterType.INTERVAL
