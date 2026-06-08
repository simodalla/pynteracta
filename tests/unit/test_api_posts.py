# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: PLR2004
"""Tests for PostsAPI."""

from __future__ import annotations

import json
from typing import ClassVar

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.posts import PostsAPI
from pynteracta.exceptions import ValidationError
from pynteracta.models.facade.post_filters import FilterType, PostFieldFilter
from pynteracta.models.facade.posts import (
    CheckVisibilityRequestDTO,
    ListCommunityPostsFilteredRequestDTO,
    ListCommunityPostsRequestDTO,
    ListPostCommentsRequestDTO,
    ListPostHistoryEventsRequestDTO,
)

_POST_ID = 21269
_COMMUNITY_ID = 79
_POST_ID2 = 21270


class TestPostsAPI:
    @respx.mock
    def test_get(self) -> None:
        payload = load_payload("get_post_detail_response.json")
        route = respx.get(f"{BASE_URL}/communication/posts/data/post-detail-by-id/21269").mock(
            return_value=httpx.Response(200, json=payload),
        )
        api = PostsAPI(make_transport())
        result = api.get(21269, load_main_attachment=True)
        assert route.called
        assert route.calls[0].request.url.params["loadMainAttachment"] == "true"
        assert result.id == payload["id"]
        assert result.title == payload["title"]

    @respx.mock
    def test_list_in_community(self) -> None:
        payload = load_payload("list_community_posts_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/posts/data/list/community/79",
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        page_size = 25
        result = api.list_in_community(79, page_size=page_size)
        assert route.called
        assert route.calls[0].request.url.params["loadPostDetails"] == "true"
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == page_size
        assert len(result.items_typed) == 1

    @respx.mock
    def test_list_in_community_raw(self) -> None:
        payload = load_payload("list_community_posts_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/posts/data/list/community/79",
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        req = ListCommunityPostsFilteredRequestDTO(pageSize=5)
        result = api.list_in_community_raw(79, req, load_capabilities=True)
        assert route.called
        assert route.calls[0].request.url.params["loadCapabilities"] == "true"
        assert result.items_typed[0].title == payload["items"][0]["title"]

    @respx.mock
    def test_iterate_in_community(self) -> None:
        page1 = {
            "items": [{"id": 1, "communityId": 79, "title": "First"}],
            "nextPageToken": "next",
            "totalItemsCount": 2,
        }
        page2 = {
            "items": [{"id": 2, "communityId": 79, "title": "Second"}],
            "nextPageToken": None,
            "totalItemsCount": 2,
        }
        respx.post(f"{BASE_URL}/communication/posts/data/list/community/79").mock(
            side_effect=[
                httpx.Response(200, json=page1),
                httpx.Response(200, json=page2),
            ],
        )
        api = PostsAPI(make_transport())
        titles = [p.title for p in api.iterate_in_community(79, page_size=1)]
        assert titles == ["First", "Second"]

    @respx.mock
    def test_comments(self) -> None:
        payload = load_payload("list_post_comments_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/posts/data/comments-list/21269",
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        page_size = 10
        result = api.comments(21269, page_size=page_size)
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == page_size
        assert len(result.items_typed) == 1

    @respx.mock
    def test_comments_raw(self) -> None:
        payload = load_payload("list_post_comments_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/posts/data/comments-list/21269",
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        req = ListPostCommentsRequestDTO(pageSize=5)
        result = api.comments_raw(21269, req)
        assert route.called
        assert result.items_typed[0].commentPlainText == payload["items"][0]["commentPlainText"]

    @respx.mock
    def test_iterate_comments(self) -> None:
        page1 = {
            "items": [{"id": 1, "commentPlainText": "A"}],
            "nextPageToken": "t2",
            "totalItemsCount": 2,
        }
        page2 = {
            "items": [{"id": 2, "commentPlainText": "B"}],
            "nextPageToken": None,
            "totalItemsCount": 2,
        }
        respx.post(f"{BASE_URL}/communication/posts/data/comments-list/99").mock(
            side_effect=[
                httpx.Response(200, json=page1),
                httpx.Response(200, json=page2),
            ],
        )
        api = PostsAPI(make_transport())
        texts = [c.commentPlainText for c in api.iterate_comments(99, page_size=1)]
        assert texts == ["A", "B"]

    # --- new M15 endpoints ---

    _PAGE_SIZE_10 = 10
    _PAGE_SIZE_20 = 20
    _HISTORY_ITEMS = 2
    _ONE_ITEM = 1

    @respx.mock
    def test_get_by_client_uid(self) -> None:
        payload = load_payload("get_post_detail_response.json")
        route = respx.get(
            f"{BASE_URL}/communication/posts/data/post-detail-by-client-uid/uid-abc"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        result = api.get_by_client_uid("uid-abc", load_main_attachment=True)
        assert route.called
        assert route.calls[0].request.url.params["loadMainAttachment"] == "true"
        assert result.id == payload["id"]

    @respx.mock
    def test_capabilities(self) -> None:
        payload = load_payload("get_post_capabilities_response.json")
        route = respx.get(f"{BASE_URL}/communication/posts/data/post-capabilities/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        result = api.capabilities(_POST_ID)
        assert route.called
        assert result.can_view_detail is True
        assert result.can_modify is False

    @respx.mock
    def test_history(self) -> None:
        payload = load_payload("list_post_history_response.json")
        route = respx.post(f"{BASE_URL}/communication/posts/data/history-list/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        result = api.history(_POST_ID, page_size=self._PAGE_SIZE_10)
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == self._PAGE_SIZE_10
        assert len(result.items_typed) == self._HISTORY_ITEMS
        assert result.items_typed[0].typeId == 1

    @respx.mock
    def test_history_raw(self) -> None:
        payload = load_payload("list_post_history_response.json")
        respx.post(f"{BASE_URL}/communication/posts/data/history-list/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        req = ListPostHistoryEventsRequestDTO(pageSize=5)
        result = api.history_raw(_POST_ID, req)
        assert result.items_typed[0].id == payload["items"][0]["id"]

    @respx.mock
    def test_history_workflow_screen_data_nullable(self) -> None:
        # Regression: API can return null values inside workflowScreenData dict
        payload = {
            "items": [
                {
                    "id": 1003,
                    "timestamp": 1700002000000,
                    "typeId": 6,
                    "typeDescription": "Executed post workflow operation.",
                    "postId": _POST_ID,
                    "workflowScreenData": {"5139": None, "5170": [{"id": 1, "label": "Cat A"}]},
                }
            ],
            "nextPageToken": None,
            "totalItemsCount": 1,
        }
        respx.post(f"{BASE_URL}/communication/posts/data/history-list/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        result = api.history(_POST_ID)
        item = result.items_typed[0]
        assert item.workflowScreenData == {"5139": None, "5170": [{"id": 1, "label": "Cat A"}]}

    @respx.mock
    def test_iterate_history(self) -> None:
        page1 = {
            "items": [{"id": 1, "typeId": 1, "typeDescription": "Creato", "timestamp": 1000}],
            "nextPageToken": "t2",
            "totalItemsCount": 2,
        }
        page2 = {
            "items": [{"id": 2, "typeId": 2, "typeDescription": "Modificato", "timestamp": 2000}],
            "nextPageToken": None,
            "totalItemsCount": 2,
        }
        respx.post(f"{BASE_URL}/communication/posts/data/history-list/{_POST_ID}").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        api = PostsAPI(make_transport())
        ids = [e.id for e in api.iterate_history(_POST_ID, page_size=1)]
        assert ids == [1, 2]

    @respx.mock
    def test_global_stream(self) -> None:
        payload = load_payload("global_stream_response.json")
        route = respx.post(f"{BASE_URL}/communication/posts/data/global-stream").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        result = api.global_stream(sync_token="tok1")
        assert route.called
        assert route.calls[0].request.url.params["syncToken"] == "tok1"
        assert len(result.items_typed) == self._ONE_ITEM
        assert result.next_sync_token == "sync_abc123"

    @respx.mock
    def test_iterate_global_stream(self) -> None:
        page1 = {
            "items": [{"id": 1, "communityId": _COMMUNITY_ID, "title": "A"}],
            "nextPageToken": "t2",
            "nextSyncToken": None,
        }
        page2 = {
            "items": [{"id": 2, "communityId": _COMMUNITY_ID, "title": "B"}],
            "nextPageToken": None,
            "nextSyncToken": "sync2",
        }
        respx.post(f"{BASE_URL}/communication/posts/data/global-stream").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        api = PostsAPI(make_transport())
        ids = [e.id for e in api.iterate_global_stream()]
        assert ids == [1, 2]

    @respx.mock
    def test_community_list(self) -> None:
        payload = load_payload("list_community_posts_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/posts/data/community-list/{_COMMUNITY_ID}"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        result = api.community_list(_COMMUNITY_ID, page_size=self._PAGE_SIZE_20)
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == self._PAGE_SIZE_20
        assert len(result.items_typed) == self._ONE_ITEM

    @respx.mock
    def test_community_list_raw(self) -> None:
        payload = load_payload("list_community_posts_response.json")
        respx.post(f"{BASE_URL}/communication/posts/data/community-list/{_COMMUNITY_ID}").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        req = ListCommunityPostsRequestDTO(pageSize=5)
        result = api.community_list_raw(_COMMUNITY_ID, req)
        assert result.items_typed[0].title == payload["items"][0]["title"]

    @respx.mock
    def test_iterate_community_list(self) -> None:
        page1 = {
            "items": [{"id": 10, "communityId": _COMMUNITY_ID, "title": "P1"}],
            "nextPageToken": "t2",
        }
        page2 = {
            "items": [{"id": 11, "communityId": _COMMUNITY_ID, "title": "P2"}],
            "nextPageToken": None,
        }
        respx.post(f"{BASE_URL}/communication/posts/data/community-list/{_COMMUNITY_ID}").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        api = PostsAPI(make_transport())
        ids = [p.id for p in api.iterate_community_list(_COMMUNITY_ID)]
        assert ids == [10, 11]

    @respx.mock
    def test_check_visibility(self) -> None:
        payload = load_payload("check_visibility_response.json")
        route = respx.post(f"{BASE_URL}/communication/posts/data/check-visibility").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        result = api.check_visibility([_POST_ID, _POST_ID2])
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["ids"] == [_POST_ID, _POST_ID2]
        typed = result.posts_typed
        assert typed[0].id == _POST_ID
        assert typed[0].canViewComments is True

    @respx.mock
    def test_check_visibility_raw(self) -> None:
        payload = load_payload("check_visibility_response.json")
        respx.post(f"{BASE_URL}/communication/posts/data/check-visibility").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        req = CheckVisibilityRequestDTO(ids=[_POST_ID])
        result = api.check_visibility_raw(req)
        assert result.posts_typed[0].id == _POST_ID

    @respx.mock
    def test_check_visibility_with_comments(self) -> None:
        payload = load_payload("check_visibility_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/posts/data/check-visibility-with-comments"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = PostsAPI(make_transport())
        result = api.check_visibility_with_comments([_POST_ID, _POST_ID2])
        assert route.called
        assert result.posts_typed[1].canViewComments is False

    @respx.mock
    def test_check_visibility_with_comments_raw(self) -> None:
        payload = load_payload("check_visibility_response.json")
        respx.post(f"{BASE_URL}/communication/posts/data/check-visibility-with-comments").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = PostsAPI(make_transport())
        req = CheckVisibilityRequestDTO(ids=[_POST_ID])
        result = api.check_visibility_with_comments_raw(req)
        assert len(result.posts_typed) == self._HISTORY_ITEMS


class TestListInCommunityFilters:
    """Tests for the new filter/sort kwargs on list_in_community."""

    _COMMUNITY_ID = 17
    _PAYLOAD: ClassVar[dict] = {
        "items": [{"id": 1, "communityId": 17, "title": "T"}],
        "nextPageToken": None,
    }
    _URL = f"{BASE_URL}/communication/posts/data/list/community/17"

    @respx.mock
    def test_order_by_sent_in_body(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(
            self._COMMUNITY_ID, order_by="postLastModifyTimestamp", order_desc=True
        )
        body = json.loads(route.calls[0].request.content)
        assert body["orderBy"] == "postLastModifyTimestamp"
        assert body["orderDesc"] is True

    @respx.mock
    def test_pinned_first_sent(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID, pinned_first=True)
        body = json.loads(route.calls[0].request.content)
        assert body["pinnedFirst"] is True

    @respx.mock
    def test_custom_field_order_by(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID, order_by="postCustomField-1954")
        body = json.loads(route.calls[0].request.content)
        assert body["orderBy"] == "postCustomField-1954"

    def test_invalid_order_by_raises(self) -> None:
        api = PostsAPI(make_transport())
        with pytest.raises(ValidationError, match="Invalid order_by"):
            api.list_in_community(self._COMMUNITY_ID, order_by="notAValidField")

    @respx.mock
    def test_community_post_filters_assembled(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(
            self._COMMUNITY_ID,
            title="Report",
            post_types=[1, 2],
            followed_by_me=True,
            only_pinned=False,
        )
        body = json.loads(route.calls[0].request.content)
        cpf = body["communityPostFilters"]
        assert cpf["title"] == "Report"
        assert cpf["postTypes"] == [1, 2]
        assert cpf["followedByMe"] is True
        assert cpf["onlyPinned"] is False
        # SaaS defaults always included when any filter is set
        assert cpf["mentioned"] is False
        assert cpf["hashtagIds"] == []
        assert cpf["currentWorkflowStatusIds"] == []
        assert cpf["postFieldFilters"] == []
        assert cpf["screenFieldFilters"] == []

    @respx.mock
    def test_saas_defaults_included_with_to_manage(self) -> None:
        """Complete communityPostFilters and communityAttachmentFilters always present."""
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID, to_manage=True)
        body = json.loads(route.calls[0].request.content)
        cpf = body["communityPostFilters"]
        assert cpf["toManage"] is True
        assert cpf["mentioned"] is False
        assert cpf["postTypes"] == []
        assert cpf["hashtagIds"] == []
        assert cpf["currentWorkflowStatusIds"] == []
        assert cpf["postFieldFilters"] == []
        assert cpf["screenFieldFilters"] == []
        caf = body["communityAttachmentFilters"]
        assert caf["excludeFilePickers"] is False
        assert caf["hashtagIds"] == []
        assert caf["name"] is None

    @respx.mock
    def test_explicit_mentioned_true_not_overridden(self) -> None:
        """Explicit mentioned=True must not be overridden by the default false."""
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID, mentioned=True)
        body = json.loads(route.calls[0].request.content)
        assert body["communityPostFilters"]["mentioned"] is True

    @respx.mock
    def test_post_field_filters_serialized(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(
            self._COMMUNITY_ID,
            post_field_filters=[
                PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[226]),
                PostFieldFilter(column_id=1957, type_id=FilterType.LIKE, parameters=["aaa"]),
            ],
        )
        body = json.loads(route.calls[0].request.content)
        pff = body["communityPostFilters"]["postFieldFilters"]
        assert pff[0] == {"columnId": 1411, "typeId": 4, "parameters": [226]}
        assert pff[1] == {"columnId": 1957, "typeId": 3, "parameters": ["aaa"]}

    @respx.mock
    def test_date_coercion_iso_string(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(
            self._COMMUNITY_ID,
            creation_timestamp_from="2025-01-01T00:00:00+00:00",
        )
        body = json.loads(route.calls[0].request.content)
        cpf = body["communityPostFilters"]
        assert isinstance(cpf["creationTimestampFrom"], int)
        assert cpf["creationTimestampFrom"] == 1735689600000

    @respx.mock
    def test_date_coercion_int_passthrough(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID, creation_timestamp_from=1780264800000)
        body = json.loads(route.calls[0].request.content)
        assert body["communityPostFilters"]["creationTimestampFrom"] == 1780264800000

    @respx.mock
    def test_community_post_filters_always_present(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID, page_size=10)
        body = json.loads(route.calls[0].request.content)
        cpf = body["communityPostFilters"]
        assert cpf["mentioned"] is False
        assert cpf["postTypes"] == []
        assert cpf["toManage"] is None
        assert cpf["hashtagIds"] == []
        assert body["communityAttachmentFilters"]["excludeFilePickers"] is False
        assert body["communityAttachmentFilters"]["hashtagIds"] == []

    @respx.mock
    def test_order_desc_defaults_to_true(self) -> None:
        """orderDesc and orderBy are always sent with SaaS defaults when not explicitly set."""
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(self._COMMUNITY_ID)
        body = json.loads(route.calls[0].request.content)
        assert body["orderDesc"] is True
        assert body["orderBy"] == "postLastModifyAndCommentTimestamp"
        assert body["pinnedFirst"] is True

    @respx.mock
    def test_post_field_filters_as_dicts(self) -> None:
        route = respx.post(self._URL).mock(return_value=httpx.Response(200, json=self._PAYLOAD))
        api = PostsAPI(make_transport())
        api.list_in_community(
            self._COMMUNITY_ID,
            post_field_filters=[{"columnId": 1411, "typeId": 4, "parameters": [226]}],
        )
        body = json.loads(route.calls[0].request.content)
        assert body["communityPostFilters"]["postFieldFilters"][0]["columnId"] == 1411
