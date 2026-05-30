# SPDX-License-Identifier: Apache-2.0
"""Tests for PostsAPI."""

from __future__ import annotations

import json

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.posts import PostsAPI
from pynteracta.models.facade.posts import (
    ListCommunityPostsFilteredRequestDTO,
    ListPostCommentsRequestDTO,
)


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
