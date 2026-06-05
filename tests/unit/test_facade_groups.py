# SPDX-License-Identifier: Apache-2.0
"""Unit tests for Group, GroupMember, GroupForEdit, Tag, Hashtag facades."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

from pynteracta.models.facade.groups import Group, GroupForEdit, GroupList, GroupMember, Tag
from pynteracta.models.facade.hashtags import Hashtag, HashtagList

_GROUP_PAYLOAD = load_payload("list_groups_response.json")
_MEMBERS_PAYLOAD = load_payload("list_group_members_response.json")
_FOR_EDIT_PAYLOAD = load_payload("get_group_for_edit_response.json")
_HASHTAGS_PAYLOAD = load_payload("list_community_hashtags_response.json")

_GROUP_ID_1 = 201
_GROUP_ID_2 = 202
_GROUP_COUNT = 2
_MEMBER_ID_1 = 1042
_MEMBER_ID_2 = 1099
_MEMBER_COUNT = 2
_GROUP_MEMBERS_COUNT = 12
_HASHTAG_ID_1 = 301
_HASHTAG_COUNT = 2
_TAG_ID = 10
_OCC_TOKEN = 5
_COMMUNITY_ID = 79


@pytest.fixture
def group_list() -> GroupList:
    return GroupList.from_dict(_GROUP_PAYLOAD)


@pytest.fixture
def for_edit() -> GroupForEdit:
    return GroupForEdit.from_dict(_FOR_EDIT_PAYLOAD)


@pytest.fixture
def hashtag_list() -> HashtagList:
    return HashtagList.from_dict(_HASHTAGS_PAYLOAD)


class TestGroupList:
    def test_total_items_count(self, group_list: GroupList) -> None:
        assert group_list.total_items_count == _GROUP_COUNT

    def test_items_typed(self, group_list: GroupList) -> None:
        items = group_list.items_typed
        assert len(items) == _GROUP_COUNT
        assert all(isinstance(g, Group) for g in items)

    def test_group_fields(self, group_list: GroupList) -> None:
        g = group_list.items_typed[0]
        assert g.id == _GROUP_ID_1
        assert g.name == "Engineering"
        assert g.email == "engineering@example.com"
        assert g.members_count == _GROUP_MEMBERS_COUNT
        assert g.visible is True
        assert g.deleted is False

    def test_tags_typed(self, group_list: GroupList) -> None:
        tags = group_list.items_typed[0].tags_typed
        assert len(tags) == 1
        assert isinstance(tags[0], Tag)
        assert tags[0].id == _TAG_ID
        assert tags[0].name == "dev"
        assert tags[0].visible is True

    def test_raw_accessible(self, group_list: GroupList) -> None:
        assert group_list.raw is not None


class TestGroupForEdit:
    def test_fields(self, for_edit: GroupForEdit) -> None:
        assert for_edit.id == _GROUP_ID_1
        assert for_edit.name == "Engineering"
        assert for_edit.members_count == _MEMBER_COUNT

    def test_occ_token_only_on_raw(self, for_edit: GroupForEdit) -> None:
        assert not hasattr(for_edit, "occ_token")
        assert for_edit.raw.occToken == _OCC_TOKEN

    def test_members_typed(self, for_edit: GroupForEdit) -> None:
        members = for_edit.members_typed
        assert len(members) == _MEMBER_COUNT
        assert all(isinstance(m, GroupMember) for m in members)
        assert members[0].id == _MEMBER_ID_1
        assert members[0].full_name == "Alice Rossi"
        assert members[0].email == "alice@example.com"
        assert members[1].id == _MEMBER_ID_2

    def test_tags_typed(self, for_edit: GroupForEdit) -> None:
        tags = for_edit.tags_typed
        assert len(tags) == 1
        assert tags[0].id == _TAG_ID


class TestHashtagList:
    def test_total_items_count(self, hashtag_list: HashtagList) -> None:
        assert hashtag_list.total_items_count == _HASHTAG_COUNT

    def test_items_typed(self, hashtag_list: HashtagList) -> None:
        items = hashtag_list.items_typed
        assert len(items) == _HASHTAG_COUNT
        assert all(isinstance(h, Hashtag) for h in items)

    def test_hashtag_fields(self, hashtag_list: HashtagList) -> None:
        h = hashtag_list.items_typed[0]
        assert h.id == _HASHTAG_ID_1
        assert h.name == "engineering"
        assert h.community_id == _COMMUNITY_ID
        assert h.external_id == "ht-301"
        assert h.deleted is False

    def test_raw_accessible(self, hashtag_list: HashtagList) -> None:
        h = hashtag_list.items_typed[0]
        assert h.raw is not None
        assert h.raw.id == _HASHTAG_ID_1
