# SPDX-License-Identifier: Apache-2.0
"""Tests for communities and catalogs facade models."""

from __future__ import annotations

import pytest

from pynteracta.models.facade.catalogs import CatalogEntryList, CatalogList
from pynteracta.models.facade.communities import (
    CommunityDetail,
    CommunityList,
    FieldType,
    PostDefinition,
    PostDefinitionMap,
    PostFieldDefinition,
)
from pynteracta.models.generated import external_v2 as generated

_UNKNOWN_TYPE = 999
_COMMUNITY_ID_A = 10
_COMMUNITY_ID_B = 20
_CATALOG_ID_A = 5
_CATALOG_ENTRY_ID = 100
_CATALOG_ENTRY_TOTAL = 10


class TestFieldType:
    def test_all_values_defined(self) -> None:
        expected = {
            FieldType.INT: "INT",
            FieldType.BIGINT: "BIGINT",
            FieldType.DECIMAL: "DECIMAL",
            FieldType.DATE: "DATE",
            FieldType.DATETIME: "DATETIME",
            FieldType.STRING: "STRING",
            FieldType.ENUM: "ENUM",
            FieldType.ENUM_LIST: "ENUM_LIST",
            FieldType.TEXT_AREA: "TEXT_AREA",
            FieldType.FLAG: "FLAG",
            FieldType.DELTA_AREA: "DELTA_AREA",
            FieldType.FEEDBACK: "FEEDBACK",
            FieldType.HIERARCHICAL_ENUM: "HIERARCHICAL_ENUM",
            FieldType.LINK: "LINK",
            FieldType.GENERIC_ENTITY_LIST: "GENERIC_ENTITY_LIST",
        }
        for ft, name in expected.items():
            assert ft.name == name

    def test_unknown_type_returns_none_via_facade(self) -> None:
        raw = generated.PostFieldDefinitionDTO1(id=1, name="x", label="X", type=_UNKNOWN_TYPE)
        fd = PostFieldDefinition(raw)
        assert fd.type is None
        assert fd.type_raw == _UNKNOWN_TYPE

    def test_none_type_returns_none(self) -> None:
        raw = generated.PostFieldDefinitionDTO1(id=1, name="x", label="X", type=None)
        fd = PostFieldDefinition(raw)
        assert fd.type is None
        assert fd.type_raw is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(FieldType.FEEDBACK, FieldType.FEEDBACK), (FieldType.ENUM, FieldType.ENUM)],
    )
    def test_typed_field_type(self, value: FieldType, expected: FieldType) -> None:
        raw = generated.PostFieldDefinitionDTO1(id=1, name="x", label="X", type=value.value)
        fd = PostFieldDefinition(raw)
        assert fd.type == expected


class TestCommunityList:
    def test_from_dict_empty(self) -> None:
        result = CommunityList.from_dict({"communities": []})
        assert result.items_typed == []

    def test_from_dict_with_items(self) -> None:
        data = {"communities": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
        result = CommunityList.from_dict(data)
        assert len(result.items_typed) == 2  # noqa: PLR2004
        assert result.items_typed[0].id == 1
        assert result.items_typed[1].name == "B"

    def test_items_typed_raw_accessible(self) -> None:
        data = {"communities": [{"id": _CATALOG_ID_A, "name": "X", "description": "desc"}]}
        result = CommunityList.from_dict(data)
        community = result.items_typed[0]
        assert community.raw.id == _CATALOG_ID_A


class TestCommunityDetail:
    def test_from_dict_with_community(self) -> None:
        data = {
            "community": {
                "id": _COMMUNITY_ID_A,
                "name": "Engineering",
                "description": "Eng team",
            }
        }
        result = CommunityDetail.from_dict(data)
        assert result.community is not None
        assert result.community.id == _COMMUNITY_ID_A

    def test_from_dict_null_community(self) -> None:
        result = CommunityDetail.from_dict({"community": None})
        assert result.community is None


class TestPostDefinition:
    def test_field_definitions_typed(self) -> None:
        data = {
            "communityId": _COMMUNITY_ID_A,
            "fieldDefinitions": [
                {"id": 1, "name": "col_1", "label": "Field 1", "type": 6, "required": False}
            ],
            "hashtags": [],
        }
        defn = PostDefinition.from_dict(data)
        assert defn.community_id == _COMMUNITY_ID_A
        assert len(defn.field_definitions) == 1
        fd = defn.field_definitions[0]
        assert fd.label == "Field 1"
        assert fd.type == FieldType.STRING

    def test_hashtags_typed(self) -> None:
        data = {
            "communityId": _COMMUNITY_ID_A,
            "fieldDefinitions": [],
            "hashtags": [{"id": 1, "name": "tag1", "deleted": False}],
        }
        defn = PostDefinition.from_dict(data)
        hashtags = defn.hashtags
        assert hashtags is not None
        assert hashtags[0].name == "tag1"

    def test_empty_hashtags_returns_none(self) -> None:
        data = {"communityId": _COMMUNITY_ID_A, "fieldDefinitions": [], "hashtags": []}
        defn = PostDefinition.from_dict(data)
        assert defn.hashtags is None


class TestPostDefinitionMap:
    def test_integer_keys(self) -> None:
        data = {
            "communityPostDefinitionMap": {
                "10": {"communityId": _COMMUNITY_ID_A, "fieldDefinitions": [], "hashtags": []},
                "20": {"communityId": _COMMUNITY_ID_B, "fieldDefinitions": [], "hashtags": []},
            }
        }
        defn_map = PostDefinitionMap.from_dict(data)
        defs = defn_map.definitions
        assert _COMMUNITY_ID_A in defs
        assert _COMMUNITY_ID_B in defs
        assert isinstance(next(iter(defs.keys())), int)

    def test_empty_map(self) -> None:
        defn_map = PostDefinitionMap.from_dict({"communityPostDefinitionMap": None})
        assert defn_map.definitions == {}


class TestCatalogFacades:
    def test_catalog_list_from_dict(self) -> None:
        data = {
            "catalogs": [
                {"id": _CATALOG_ID_A, "name": "Departments", "paged": False},
                {"id": 8, "name": "Locations", "paged": True},
            ]
        }
        result = CatalogList.from_dict(data)
        assert len(result.items_typed) == 2  # noqa: PLR2004
        assert result.items_typed[0].id == _CATALOG_ID_A
        assert result.items_typed[1].paged is True

    def test_catalog_entry_list_pagination(self) -> None:
        data = {
            "items": [{"id": _CATALOG_ENTRY_ID, "label": "Eng", "externalId": "ENG"}],
            "nextPageToken": "tok",
            "totalItemsCount": _CATALOG_ENTRY_TOTAL,
        }
        result = CatalogEntryList.from_dict(data)
        assert result.next_page_token == "tok"
        assert result.total_items_count == _CATALOG_ENTRY_TOTAL
        assert len(result.items_typed) == 1
        entry = result.items_typed[0]
        assert entry.id == _CATALOG_ENTRY_ID
        assert entry.label == "Eng"
        assert entry.external_id == "ENG"

    def test_catalog_entry_list_empty(self) -> None:
        result = CatalogEntryList.from_dict({"items": [], "nextPageToken": None})
        assert result.items_typed == []
        assert result.next_page_token is None
