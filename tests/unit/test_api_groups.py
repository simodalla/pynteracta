# SPDX-License-Identifier: Apache-2.0
"""Tests for GroupsAPI."""

from __future__ import annotations

import json
from typing import ClassVar

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport, mock_json

from pynteracta.api.groups import GroupsAPI
from pynteracta.exceptions import ConcurrencyError, InteractaError, NotFoundError, TransportError
from pynteracta.models.generated import external_v2 as generated

_GROUP_ID_1 = 201
_GROUP_ID_2 = 202
_GROUP_COUNT = 2
_MEMBER_ID_1 = 1042
_MEMBER_ID_2 = 1099
_MEMBER_COUNT = 2
_OCC_TOKEN = 5
_TAG_ID = 10
_PAGE_SIZE = 10


class TestGroupsList:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("list_groups_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/groups").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.list_groups()
        assert route.called
        items = result.items_typed
        assert len(items) == _GROUP_COUNT
        assert items[0].id == _GROUP_ID_1
        assert items[1].id == _GROUP_ID_2

    @respx.mock
    def test_full_text_filter_in_body(self) -> None:
        payload = load_payload("list_groups_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/groups").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        api.list_groups(
            full_text_filter="eng", page_size=_PAGE_SIZE, order_type_id="name", order_desc=False
        )
        body = json.loads(route.calls[0].request.content)
        assert body["fullTextFilter"] == "eng"
        assert body["pageSize"] == _PAGE_SIZE
        assert body["orderTypeId"] == "name"
        assert body["orderDesc"] is False

    @respx.mock
    def test_tags_typed(self) -> None:
        payload = load_payload("list_groups_response.json")
        respx.post(f"{BASE_URL}/admin/data/groups").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.list_groups()
        tags = result.items_typed[0].tags_typed
        assert len(tags) == 1
        assert tags[0].id == _TAG_ID
        assert tags[0].name == "dev"


class TestGroupsListMembers:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("list_group_members_response.json")
        route = respx.post(f"{BASE_URL}/admin/data/groups/{_GROUP_ID_1}/members").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.list_members(_GROUP_ID_1)
        assert route.called
        members = result.members_typed
        assert len(members) == _MEMBER_COUNT
        assert members[0].id == _MEMBER_ID_1
        assert members[0].first_name == "Alice"
        assert members[0].last_name == "Rossi"
        assert members[0].full_name == "Alice Rossi"
        assert members[0].email == "alice@example.com"
        assert members[1].id == _MEMBER_ID_2


class TestGroupsGetForEdit:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_group_for_edit_response.json")
        route = respx.get(f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.get_for_edit(_GROUP_ID_1)
        assert route.called
        assert result.id == _GROUP_ID_1
        assert result.name == "Engineering"
        assert result.members_count == _MEMBER_COUNT
        assert result.raw.occToken == _OCC_TOKEN

    @respx.mock
    def test_members_typed(self) -> None:
        payload = load_payload("get_group_for_edit_response.json")
        respx.get(f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.get_for_edit(_GROUP_ID_1)
        members = result.members_typed
        assert len(members) == _MEMBER_COUNT
        assert members[0].id == _MEMBER_ID_1
        assert members[1].id == _MEMBER_ID_2

    # criterio: 05-C06
    @respx.mock
    def test_get_for_edit_exposes_occ_token(self) -> None:
        payload = load_payload("get_group_for_edit_response.json")
        respx.get(f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}/edit").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = GroupsAPI(make_transport())
        result = api.get_for_edit(_GROUP_ID_1)
        assert result.occ_token == _OCC_TOKEN
        assert result.raw.occToken == _OCC_TOKEN


# ---------------------------------------------------------------------------
# Scritture (spec 05)
# ---------------------------------------------------------------------------

_CREATED_GROUP_ID = 202
_CREATED_MEMBERS_COUNT = 2
_EDIT_NEXT_OCC_TOKEN = 6
_MEMBERS_NEXT_OCC_TOKEN = 6
_MEMBERS_COUNT_AFTER = 3
_CREATE_URL = f"{BASE_URL}/admin/manage/groups"
_EDIT_URL = f"{BASE_URL}/admin/manage/groups/{_GROUP_ID_1}"
_MEMBERS_URL = f"{BASE_URL}/admin/manage/groups/members"
_HTTP_CONFLICT = 409


def _body(route: respx.Route) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[0].request.content)  # type: ignore[no-any-return]


class TestGroupsCreate:
    # criterio: 05-C07
    @respx.mock
    def test_create_sends_only_given_fields_and_wraps_response(self) -> None:
        route = mock_json("POST", "admin/manage/groups", load_payload("create_group_response.json"))
        result = GroupsAPI(make_transport()).create(name="G", visible=True, member_ids=[1, 2])
        assert route.call_count == 1
        assert _body(route) == {"name": "G", "visible": True, "memberIds": [1, 2]}
        assert result.group_id == _CREATED_GROUP_ID
        assert result.next_occ_token == 1
        assert result.name == "QA"
        assert result.visible is True
        assert result.members_count == _CREATED_MEMBERS_COUNT
        assert result.raw.groupId == _CREATED_GROUP_ID

    # criterio: 05-C07
    @respx.mock
    def test_create_raw_equivalent(self) -> None:
        route = mock_json("POST", "admin/manage/groups", load_payload("create_group_response.json"))
        req = generated.CreateGroupRequestDTO(name="G", visible=True, memberIds=[1, 2])
        result = GroupsAPI(make_transport()).create_raw(req)
        assert _body(route) == {"name": "G", "visible": True, "memberIds": [1, 2]}
        assert result.group_id == _CREATED_GROUP_ID

    # criterio: 05-C21
    @respx.mock
    def test_create_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(_CREATE_URL).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(TransportError):
            GroupsAPI(make_transport()).create(name="G")
        assert route.call_count == 1


class TestGroupsEdit:
    # criterio: 05-C08
    @respx.mock
    def test_edit_sends_given_fields_and_occ_token(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(200, json=load_payload("edit_group_response.json"))
        )
        result = GroupsAPI(make_transport()).edit(_GROUP_ID_1, _OCC_TOKEN, name="G2")
        assert route.call_count == 1
        assert _body(route) == {"name": "G2", "occToken": _OCC_TOKEN}
        assert result.group_id == _GROUP_ID_1
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN

    # criterio: 05-C08
    @respx.mock
    def test_edit_raw_equivalent(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(200, json=load_payload("edit_group_response.json"))
        )
        req = generated.EditGroupRequestDTO(name="G2", memberIds=[1], occToken=_OCC_TOKEN)
        result = GroupsAPI(make_transport()).edit_raw(_GROUP_ID_1, req)
        assert _body(route) == {"name": "G2", "memberIds": [1], "occToken": _OCC_TOKEN}
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN

    # criterio: 05-C05
    @respx.mock
    def test_edit_409_raises_concurrency_error_once(self) -> None:
        route = respx.put(_EDIT_URL).mock(
            return_value=httpx.Response(409, json={"message": "Concurrency error"})
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            GroupsAPI(make_transport()).edit(_GROUP_ID_1, _OCC_TOKEN, name="G2")
        assert exc_info.value.status_code == _HTTP_CONFLICT
        assert route.call_count == 1


class TestGroupsDelete:
    # criterio: 05-C08
    @respx.mock
    def test_delete_sends_one_request_and_returns_none(self) -> None:
        route = respx.delete(_EDIT_URL).mock(return_value=httpx.Response(200))
        assert GroupsAPI(make_transport()).delete(_GROUP_ID_1) is None
        assert route.call_count == 1

    # criterio: 05-C08
    @respx.mock
    def test_delete_404_raises_not_found(self) -> None:
        route = respx.delete(_EDIT_URL).mock(
            return_value=httpx.Response(404, json={"message": "Gruppo non esistente"})
        )
        with pytest.raises(NotFoundError):
            GroupsAPI(make_transport()).delete(_GROUP_ID_1)
        assert route.call_count == 1


def _members_payload(*, conflict: bool = False, missing: bool = False) -> dict:  # type: ignore[type-arg]
    payload = load_payload("edit_groups_members_response.json")
    if missing:
        return {"successGroups": [], "concurrencyErrorGroups": []}
    if conflict:
        group = payload["successGroups"][0]
        return {"successGroups": [], "concurrencyErrorGroups": [group]}
    return payload


class TestGroupsEditMembers:
    _BODY: ClassVar[dict] = {  # type: ignore[type-arg]
        "groupMembers": [
            {
                "id": _GROUP_ID_1,
                "occToken": _OCC_TOKEN,
                "addUserIds": [_MEMBER_ID_1],
                "deleteUserIds": [_MEMBER_ID_2],
            }
        ]
    }

    # criterio: 05-C09
    @respx.mock
    def test_success_returns_group_with_next_occ_token(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload())
        )
        result = GroupsAPI(make_transport()).edit_members(
            _GROUP_ID_1, _OCC_TOKEN, add_user_ids=[_MEMBER_ID_1], remove_user_ids=[_MEMBER_ID_2]
        )
        assert route.call_count == 1
        assert _body(route) == self._BODY
        assert result.group_id == _GROUP_ID_1
        assert result.next_occ_token == _MEMBERS_NEXT_OCC_TOKEN
        assert result.members_count == _MEMBERS_COUNT_AFTER
        assert result.name == "Engineering"

    # criterio: 05-C09
    @respx.mock
    def test_only_given_keys_are_sent(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload())
        )
        GroupsAPI(make_transport()).edit_members(_GROUP_ID_1, _OCC_TOKEN, add_user_ids=[1])
        assert _body(route) == {
            "groupMembers": [{"id": _GROUP_ID_1, "occToken": _OCC_TOKEN, "addUserIds": [1]}]
        }

    # criterio: 05-C09
    @respx.mock
    def test_conflict_raises_concurrency_error(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload(conflict=True))
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            GroupsAPI(make_transport()).edit_members(_GROUP_ID_1, _OCC_TOKEN, add_user_ids=[1])
        assert exc_info.value.status_code == 200  # noqa: PLR2004
        assert exc_info.value.request_method == "PUT"
        assert exc_info.value.response_body is not None
        assert route.call_count == 1

    # criterio: 05-C09
    @respx.mock
    def test_missing_group_raises_interacta_error(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload(missing=True))
        )
        with pytest.raises(InteractaError) as exc_info:
            GroupsAPI(make_transport()).edit_members(_GROUP_ID_1, _OCC_TOKEN, add_user_ids=[1])
        assert not isinstance(exc_info.value, ConcurrencyError)
        assert exc_info.value.status_code == 200  # noqa: PLR2004
        assert route.call_count == 1


class TestGroupsEditMembersBulk:
    _GROUPS: ClassVar[list[dict]] = [  # type: ignore[type-arg]
        {"id": _GROUP_ID_1, "occToken": _OCC_TOKEN, "addUserIds": [1]},
        {"id": _GROUP_ID_2, "occToken": 1, "deleteUserIds": [2]},
    ]

    # criterio: 05-C10
    @respx.mock
    def test_returns_both_lists_without_raising(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload())
        )
        result = GroupsAPI(make_transport()).edit_members_bulk(self._GROUPS)
        assert route.call_count == 1
        assert _body(route) == {"groupMembers": self._GROUPS}
        assert [g.id for g in result.success_groups] == [_GROUP_ID_1]
        assert [g.id for g in result.concurrency_error_groups] == [_GROUP_ID_2]

    # criterio: 05-C10
    @respx.mock
    def test_bulk_raw_equivalent(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload())
        )
        req = generated.EditMultipleGroupsMembersRequestDTO(groupMembers=self._GROUPS)
        result = GroupsAPI(make_transport()).edit_members_bulk_raw(req)
        assert _body(route) == {"groupMembers": self._GROUPS}
        assert len(result.success_groups) == 1

    # criterio: 05-C10
    @respx.mock
    def test_empty_list_is_sent_as_is(self) -> None:
        route = respx.put(_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_members_payload(missing=True))
        )
        result = GroupsAPI(make_transport()).edit_members_bulk([])
        assert _body(route) == {"groupMembers": []}
        assert result.success_groups == []
