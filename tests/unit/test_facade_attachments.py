# SPDX-License-Identifier: Apache-2.0
"""Tests for attachment facade classes."""

from __future__ import annotations

import json
from pathlib import Path

from pynteracta.models.facade.attachments import (
    AttachmentDetail,
    AttachmentVisibility,
    PostAttachment,
    PostAttachmentList,
)

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "payloads"

_ATTACHMENT_ID = 3001
_ATTACHMENT_COUNT = 2
_ATTACHMENT_SIZE = 204800
_POST_ID = 21269


def load(name: str) -> dict:  # type: ignore[type-arg]
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


class TestPostAttachmentList:
    def test_from_dict(self) -> None:
        data = load("list_post_attachments_response.json")
        result = PostAttachmentList.from_dict(data)
        assert result.total_items_count == _ATTACHMENT_COUNT
        assert result.next_page_token is None
        assert result.can_add_attachment is True
        assert result.image_attachments_count == data["imageAttachmentsCount"]
        assert result.documents_attachments_count == data["documentsAttachmentsCount"]

    def test_items_typed(self) -> None:
        data = load("list_post_attachments_response.json")
        result = PostAttachmentList.from_dict(data)
        items = result.items_typed
        assert len(items) == _ATTACHMENT_COUNT
        first = items[0]
        assert isinstance(first, PostAttachment)
        assert first.id == _ATTACHMENT_ID
        assert first.name == data["items"][0]["name"]
        assert first.content_mime_type == data["items"][0]["contentMimeType"]
        assert first.size == _ATTACHMENT_SIZE
        assert first.type == data["items"][0]["type"]
        assert first.downloadable is True
        assert first.version_number == 1

    def test_raw_escape_hatch(self) -> None:
        data = load("list_post_attachments_response.json")
        result = PostAttachmentList.from_dict(data)
        assert result.raw is not None
        assert result.raw.totalItemsCount == _ATTACHMENT_COUNT

    def test_temporary_links_on_item(self) -> None:
        data = load("list_post_attachments_response.json")
        result = PostAttachmentList.from_dict(data)
        items = result.items_typed
        assert items[0].temporary_content_view_link is not None
        assert items[0].temporary_content_download_link is not None
        # photo has preview link
        assert items[1].temporary_content_preview_image_link is not None


class TestAttachmentDetail:
    def test_from_dict(self) -> None:
        data = load("get_attachment_detail_response.json")
        result = AttachmentDetail.from_dict(data)
        assert result.id == _ATTACHMENT_ID
        assert result.name == data["attachmentData"]["name"]
        assert result.content_mime_type == data["attachmentData"]["contentMimeType"]
        assert result.size == _ATTACHMENT_SIZE
        assert result.type == data["attachmentData"]["type"]
        assert result.downloadable is True

    def test_post_info(self) -> None:
        data = load("get_attachment_detail_response.json")
        result = AttachmentDetail.from_dict(data)
        assert result.post is not None
        assert result.post.id == _POST_ID

    def test_temporary_links(self) -> None:
        data = load("get_attachment_detail_response.json")
        result = AttachmentDetail.from_dict(data)
        assert result.temporary_content_view_link is not None
        assert result.temporary_content_download_link is not None

    def test_raw_escape_hatch(self) -> None:
        data = load("get_attachment_detail_response.json")
        result = AttachmentDetail.from_dict(data)
        assert result.raw is not None
        assert result.attachment_data is not None


class TestAttachmentVisibility:
    def test_from_dict(self) -> None:
        data = load("check_attachment_visibility_response.json")
        result = AttachmentVisibility.from_dict(data)
        assert result.ids == [3001, 3002]

    def test_empty_ids(self) -> None:
        result = AttachmentVisibility.from_dict({"ids": None})
        assert result.ids == []

    def test_raw_escape_hatch(self) -> None:
        data = load("check_attachment_visibility_response.json")
        result = AttachmentVisibility.from_dict(data)
        assert result.raw.ids == [3001, 3002]
