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
    UploadedAttachment,
    UploadTicket,
)
from pynteracta.models.generated import external_v2 as generated

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


class TestUploadTicket:
    # criterio: 04-C06
    def test_properties_from_fixture(self) -> None:
        data = load("upload_new_attachment_response.json")
        ticket = UploadTicket.from_dict(data)
        assert isinstance(ticket.raw, generated.GetTemporaryImageUploadUrlBaseResponseDTO)
        assert ticket.content_ref == data["contentRef"]
        assert ticket.upload_url == "https://storage.example.com/bucket-test"
        assert ticket.form_params == data["uploadMultipartRequestBodyParams"]
        assert ticket.temporary_download_url == data["temporaryDownloadUrl"]

    # criterio: 04-C06
    def test_form_params_is_a_copy(self) -> None:
        ticket = UploadTicket.from_dict(load("upload_new_attachment_response.json"))
        ticket.form_params["policy"] = "changed"
        assert ticket.raw.uploadMultipartRequestBodyParams is not None
        assert ticket.raw.uploadMultipartRequestBodyParams["policy"] != "changed"

    # criterio: 04-C06
    def test_form_params_empty_without_params(self) -> None:
        ticket = UploadTicket.from_dict({"contentRef": "abc", "uploadUrl": "https://s"})
        assert ticket.form_params == {}
        assert ticket.temporary_download_url is None


class TestUploadedAttachment:
    def _uploaded(self) -> UploadedAttachment:
        ticket = UploadTicket.from_dict(load("upload_new_attachment_response.json"))
        return UploadedAttachment(ticket, name="nota.txt", mime_type="text/plain")

    # criterio: 04-C06
    def test_properties(self) -> None:
        data = load("upload_new_attachment_response.json")
        uploaded = self._uploaded()
        assert uploaded.raw.contentRef == data["contentRef"]
        assert uploaded.content_ref == data["contentRef"]
        assert uploaded.name == "nota.txt"
        assert uploaded.mime_type == "text/plain"
        assert uploaded.temporary_download_url == data["temporaryDownloadUrl"]

    # criterio: 04-C07
    def test_as_write_input_and_as_version_of(self) -> None:
        uploaded = self._uploaded()
        ref = uploaded.content_ref
        assert uploaded.as_write_input() == {"name": "nota.txt", "contentRef": ref}
        assert uploaded.as_version_of(7) == {
            "attachmentId": 7,
            "contentRef": ref,
            "name": "nota.txt",
        }
