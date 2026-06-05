# SPDX-License-Identifier: Apache-2.0
"""Tests for AttachmentsAPI."""

from __future__ import annotations

import json

import httpx
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.attachments import AttachmentsAPI
from pynteracta.models.facade.attachments import (
    CheckVisibilityRequestDTO,
    ListPostAttachmentsByPostIdRequestDTO,
)

_POST_ID = 21269
_ATTACHMENT_ID = 3001
_ATTACHMENT_ID_2 = 3002
_PAGE_SIZE = 10
_ATTACHMENT_COUNT = 2


class TestListForPost:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("list_post_attachments_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/attachments/data/posts/{_POST_ID}/attachments-list"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AttachmentsAPI(make_transport())
        result = api.list_for_post(_POST_ID)
        assert route.called
        items = result.items_typed
        assert len(items) == _ATTACHMENT_COUNT
        assert items[0].id == _ATTACHMENT_ID
        assert items[0].name == payload["items"][0]["name"]
        assert items[1].id == _ATTACHMENT_ID_2

    @respx.mock
    def test_camel_case_body_filters(self) -> None:
        payload = load_payload("list_post_attachments_response.json")
        route = respx.post(
            f"{BASE_URL}/communication/attachments/data/posts/{_POST_ID}/attachments-list"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AttachmentsAPI(make_transport())
        api.list_for_post(
            _POST_ID,
            page_size=_PAGE_SIZE,
            types=[1],
            entity_types=[1, 4],
            mime_types=["application/pdf"],
            mime_type_category="other",
            order_by="name",
            order_desc=False,
        )
        body = json.loads(route.calls[0].request.content)
        assert body["pageSize"] == _PAGE_SIZE
        assert body["types"] == [1]
        assert body["entityTypes"] == [1, 4]
        assert body["mimeTypes"] == ["application/pdf"]
        assert body["mimeTypeCategory"] == "other"
        assert body["orderBy"] == "name"
        assert body["orderDesc"] is False

    @respx.mock
    def test_list_for_post_raw(self) -> None:
        payload = load_payload("list_post_attachments_response.json")
        respx.post(
            f"{BASE_URL}/communication/attachments/data/posts/{_POST_ID}/attachments-list"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AttachmentsAPI(make_transport())
        req = ListPostAttachmentsByPostIdRequestDTO(pageSize=5)
        result = api.list_for_post_raw(_POST_ID, req)
        assert len(result.items_typed) == _ATTACHMENT_COUNT

    @respx.mock
    def test_iterate_for_post_pagination(self) -> None:
        page1 = {
            "items": [
                {
                    "id": _ATTACHMENT_ID,
                    "name": "a.pdf",
                    "contentMimeType": "application/pdf",
                    "size": 100,
                    "type": 1,
                },
            ],
            "nextPageToken": "tok",
            "totalItemsCount": _ATTACHMENT_COUNT,
        }
        page2 = {
            "items": [
                {
                    "id": _ATTACHMENT_ID_2,
                    "name": "b.jpg",
                    "contentMimeType": "image/jpeg",
                    "size": 200,
                    "type": 1,
                },
            ],
            "nextPageToken": None,
            "totalItemsCount": _ATTACHMENT_COUNT,
        }
        call_count = 0

        def _side_effect(request: httpx.Request, *_: object) -> httpx.Response:
            nonlocal call_count
            body = json.loads(request.content)
            if call_count == 0:
                call_count += 1
                assert "pageToken" not in body
                return httpx.Response(200, json=page1)
            assert body.get("pageToken") == "tok"
            return httpx.Response(200, json=page2)

        respx.post(
            f"{BASE_URL}/communication/attachments/data/posts/{_POST_ID}/attachments-list"
        ).mock(side_effect=_side_effect)

        api = AttachmentsAPI(make_transport())
        items = list(api.iterate_for_post(_POST_ID))
        assert len(items) == _ATTACHMENT_COUNT
        assert items[0].id == _ATTACHMENT_ID
        assert items[1].id == _ATTACHMENT_ID_2

    @respx.mock
    def test_aggregate_counts(self) -> None:
        payload = load_payload("list_post_attachments_response.json")
        respx.post(
            f"{BASE_URL}/communication/attachments/data/posts/{_POST_ID}/attachments-list"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AttachmentsAPI(make_transport())
        result = api.list_for_post(_POST_ID)
        assert result.can_add_attachment is True
        assert result.image_attachments_count == 1
        assert result.documents_attachments_count == 1


class TestGet:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("get_attachment_detail_response.json")
        route = respx.get(
            f"{BASE_URL}/communication/posts/data/attachment-detail-by-id/{_ATTACHMENT_ID}"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AttachmentsAPI(make_transport())
        result = api.get(_ATTACHMENT_ID)
        assert route.called
        assert result.id == payload["attachmentData"]["id"]
        assert result.name == payload["attachmentData"]["name"]
        assert result.content_mime_type == payload["attachmentData"]["contentMimeType"]
        assert result.size == payload["attachmentData"]["size"]
        assert result.post is not None
        assert result.post.id == payload["post"]["id"]

    @respx.mock
    def test_temporary_links_accessible(self) -> None:
        payload = load_payload("get_attachment_detail_response.json")
        respx.get(
            f"{BASE_URL}/communication/posts/data/attachment-detail-by-id/{_ATTACHMENT_ID}"
        ).mock(return_value=httpx.Response(200, json=payload))
        api = AttachmentsAPI(make_transport())
        result = api.get(_ATTACHMENT_ID)
        assert result.temporary_content_view_link is not None
        assert "token=xyz" in (result.temporary_content_view_link or "")


class TestCheckVisibility:
    @respx.mock
    def test_url_and_response(self) -> None:
        payload = load_payload("check_attachment_visibility_response.json")
        route = respx.post(f"{BASE_URL}/communication/attachments/data/check-visibility").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = AttachmentsAPI(make_transport())
        result = api.check_visibility([3001, 3002])
        assert route.called
        body = json.loads(route.calls[0].request.content)
        assert body["ids"] == [3001, 3002]
        assert result.ids == [3001, 3002]

    @respx.mock
    def test_check_visibility_raw(self) -> None:
        payload = load_payload("check_attachment_visibility_response.json")
        respx.post(f"{BASE_URL}/communication/attachments/data/check-visibility").mock(
            return_value=httpx.Response(200, json=payload)
        )
        api = AttachmentsAPI(make_transport())
        req = CheckVisibilityRequestDTO(ids=[3001])
        result = api.check_visibility_raw(req)
        assert result.ids == [3001, 3002]
