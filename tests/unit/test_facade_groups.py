# SPDX-License-Identifier: Apache-2.0
"""Unit tests for Group, GroupMember, GroupForEdit, Tag, Hashtag facades."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

from pynteracta.models.facade.groups import (
    Group,
    GroupForEdit,
    GroupList,
    GroupMember,
    GroupMembersResult,
    GroupSummary,
    GroupWriteResult,
    Tag,
)
from pynteracta.models.facade.hashtags import Hashtag, HashtagList
from pynteracta.models.generated import external_v2 as generated

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
_CREATE_PAYLOAD = load_payload("create_group_response.json")
_EDIT_PAYLOAD = load_payload("edit_group_response.json")
_MEMBERS_EDIT_PAYLOAD = load_payload("edit_groups_members_response.json")
_CREATED_GROUP_ID = 202
_CREATED_MEMBERS_COUNT = 2
_EDIT_NEXT_OCC_TOKEN = 6
_MEMBERS_NEXT_OCC_TOKEN = 6
_MEMBERS_COUNT_AFTER = 3


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

    # criterio: 05-C06
    def test_occ_token_exposed(self, for_edit: GroupForEdit) -> None:
        assert for_edit.occ_token == _OCC_TOKEN
        assert for_edit.occ_token == for_edit.raw.occToken

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


class TestGroupSummary:
    # criterio: 05-C10
    def test_from_stub_revalidates_group_dto(self) -> None:
        stub = generated.GroupDTO.model_validate(_MEMBERS_EDIT_PAYLOAD["successGroups"][0])
        summary = GroupSummary.from_stub(stub)
        assert summary.id == _GROUP_ID_1
        assert summary.name == "Engineering"
        assert summary.email == "engineering@example.com"
        assert summary.visible is True
        assert summary.deleted is False
        assert summary.members_count == _MEMBERS_COUNT_AFTER
        assert summary.occ_token == _MEMBERS_NEXT_OCC_TOKEN
        assert isinstance(summary.raw, generated.GroupDTOModel)

    def test_from_stub_rejects_non_dict(self) -> None:
        with pytest.raises(ValueError, match="Unexpected stub root type"):
            GroupSummary.from_stub(generated.GroupDTO.model_validate("not-a-group"))


class TestGroupWriteResult:
    # criterio: 05-C07
    def test_from_create_exposes_response_fields(self) -> None:
        result = GroupWriteResult.from_create(_CREATE_PAYLOAD)
        assert result.group_id == _CREATED_GROUP_ID
        assert result.next_occ_token == 1
        assert result.name == "QA"
        assert result.email == "qa@example.com"
        assert result.visible is True
        assert result.members_count == _CREATED_MEMBERS_COUNT
        assert result.raw.groupId == _CREATED_GROUP_ID

    # criterio: 05-C08
    def test_from_edit_uses_given_group_id(self) -> None:
        result = GroupWriteResult.from_edit(_EDIT_PAYLOAD, _GROUP_ID_1)
        assert result.group_id == _GROUP_ID_1
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN
        assert result.name is None
        assert result.members_count is None

    # criterio: 05-C09
    def test_from_member_edit_uses_group_occ_token(self) -> None:
        members = GroupMembersResult.from_dict(_MEMBERS_EDIT_PAYLOAD)
        result = GroupWriteResult.from_member_edit(members.success_groups[0])
        assert result.group_id == _GROUP_ID_1
        assert result.next_occ_token == _MEMBERS_NEXT_OCC_TOKEN
        assert result.name == "Engineering"
        assert result.members_count == _MEMBERS_COUNT_AFTER


class TestGroupMembersResult:
    # criterio: 05-C10
    def test_from_dict_splits_lists(self) -> None:
        result = GroupMembersResult.from_dict(_MEMBERS_EDIT_PAYLOAD)
        assert [g.id for g in result.success_groups] == [_GROUP_ID_1]
        assert [g.id for g in result.concurrency_error_groups] == [_GROUP_ID_2]
        assert all(isinstance(g, GroupSummary) for g in result.success_groups)
        assert result.concurrency_error_groups[0].occ_token == 2  # noqa: PLR2004
        assert result.raw.successGroups is not None

    def test_empty_response_has_empty_lists(self) -> None:
        result = GroupMembersResult.from_dict({})
        assert result.success_groups == []
        assert result.concurrency_error_groups == []
