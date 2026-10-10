# SPDX-License-Identifier: Apache-2.0
"""Tests for AttachmentsAPI."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, BinaryIO

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.attachments import AttachmentsAPI
from pynteracta.exceptions import TransportError, UploadError
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


# ---------------------------------------------------------------------------
# Spec 04: upload in due passi
# ---------------------------------------------------------------------------

_UPLOAD_PATH = f"{BASE_URL}/core/storage/upload-new-attachment"
_STORAGE_URL = "https://storage.example.com/bucket-test"
_HTTP_204 = 204
_HTTP_400 = 400


def _mock_upload(
    storage: httpx.Response | Exception | None = None,
) -> tuple[respx.Route, respx.Route]:
    payload = load_payload("upload_new_attachment_response.json")
    ticket_route = respx.post(_UPLOAD_PATH).mock(return_value=httpx.Response(200, json=payload))
    storage_route = respx.post(_STORAGE_URL)
    if isinstance(storage, Exception):
        storage_route.mock(side_effect=storage)
    else:
        storage_route.mock(return_value=storage or httpx.Response(_HTTP_204))
    return ticket_route, storage_route


def _file_part(route: respx.Route) -> bytes:
    body = route.calls[0].request.content
    return body[body.index(b'name="file"') :]


class TestRequestUploadUrl:
    # criterio: 04-C06
    @respx.mock
    def test_returns_ticket(self) -> None:
        ticket_route, storage_route = _mock_upload()
        ticket = AttachmentsAPI(make_transport()).request_upload_url()
        assert ticket_route.call_count == 1
        assert ticket_route.calls[0].request.content == b""
        assert storage_route.call_count == 0
        payload = load_payload("upload_new_attachment_response.json")
        assert ticket.content_ref == payload["contentRef"]
        assert ticket.upload_url == _STORAGE_URL
        assert ticket.form_params == payload["uploadMultipartRequestBodyParams"]
        assert ticket.temporary_download_url == payload["temporaryDownloadUrl"]
        assert ticket.raw.contentRef == payload["contentRef"]


class TestUpload:
    # criterio: 04-C01
    @respx.mock
    def test_path_two_requests_in_order_no_authorization(self, tmp_path: Path) -> None:
        ticket_route, storage_route = _mock_upload()
        path = tmp_path / "nota.txt"
        path.write_bytes(b"testo della nota")
        uploaded = AttachmentsAPI(make_transport()).upload(path)
        assert [call.request.url for call in respx.calls] == [_UPLOAD_PATH, _STORAGE_URL]
        assert "Authorization" in ticket_route.calls[0].request.headers
        storage_request = storage_route.calls[0].request
        assert "Authorization" not in storage_request.headers
        body = storage_request.content
        for name in ("GoogleAccessId", "key", "policy", "signature"):
            assert body.index(f'name="{name}"'.encode()) < body.index(b'name="file"')
        part = _file_part(storage_route)
        assert b'filename="nota.txt"' in part
        assert b"Content-Type: text/plain" in part
        assert b"testo della nota" in part
        payload = load_payload("upload_new_attachment_response.json")
        assert uploaded.content_ref == payload["contentRef"]
        assert uploaded.name == "nota.txt"
        assert uploaded.mime_type == "text/plain"
        assert uploaded.temporary_download_url == payload["temporaryDownloadUrl"]
        assert uploaded.raw.contentRef == payload["contentRef"]

    # criterio: 04-C01
    @respx.mock
    def test_string_path_is_accepted(self, tmp_path: Path) -> None:
        _, storage_route = _mock_upload()
        path = tmp_path / "b.pdf"
        path.write_bytes(b"%PDF-1.4")
        uploaded = AttachmentsAPI(make_transport()).upload(str(path))
        assert uploaded.mime_type == "application/pdf"
        assert b'filename="b.pdf"' in _file_part(storage_route)

    # criterio: 04-C01
    @respx.mock
    def test_empty_file_is_uploaded(self, tmp_path: Path) -> None:
        _, storage_route = _mock_upload()
        path = tmp_path / "vuoto.txt"
        path.write_bytes(b"")
        uploaded = AttachmentsAPI(make_transport()).upload(path)
        assert storage_route.call_count == 1
        assert uploaded.name == "vuoto.txt"

    # criterio: 04-C02
    @respx.mock
    def test_bytes_with_name_octet_stream(self) -> None:
        _, storage_route = _mock_upload()
        uploaded = AttachmentsAPI(make_transport()).upload(b"\x00\x01", name="dati.bin")
        part = _file_part(storage_route)
        assert b'filename="dati.bin"' in part
        assert b"Content-Type: application/octet-stream" in part
        assert uploaded.mime_type == "application/octet-stream"

    # criterio: 04-C02
    @respx.mock
    def test_fileobj_with_name_is_not_closed(self) -> None:
        _, storage_route = _mock_upload()
        fileobj = io.BytesIO(b"contenuto")
        uploaded = AttachmentsAPI(make_transport()).upload(fileobj, name="dati.bin")
        assert b"contenuto" in _file_part(storage_route)
        assert uploaded.name == "dati.bin"
        assert not fileobj.closed

    # criterio: 04-C02
    @respx.mock
    def test_mime_type_override(self, tmp_path: Path) -> None:
        _, storage_route = _mock_upload()
        path = tmp_path / "nota.txt"
        path.write_bytes(b"x")
        uploaded = AttachmentsAPI(make_transport()).upload(path, mime_type="image/png")
        assert b"Content-Type: image/png" in _file_part(storage_route)
        assert uploaded.mime_type == "image/png"

    # criterio: 04-C02
    @respx.mock
    def test_name_override_for_path(self, tmp_path: Path) -> None:
        _, storage_route = _mock_upload()
        path = tmp_path / "nota.txt"
        path.write_bytes(b"x")
        uploaded = AttachmentsAPI(make_transport()).upload(path, name="altro.pdf")
        part = _file_part(storage_route)
        assert b'filename="altro.pdf"' in part
        assert b"Content-Type: application/pdf" in part
        assert uploaded.name == "altro.pdf"

    # criterio: 04-C02
    @respx.mock
    def test_unknown_extension_octet_stream(self, tmp_path: Path) -> None:
        _, storage_route = _mock_upload()
        path = tmp_path / "dati.sconosciuto"
        path.write_bytes(b"x")
        AttachmentsAPI(make_transport()).upload(path)
        assert b"Content-Type: application/octet-stream" in _file_part(storage_route)

    # criterio: 04-C02
    @respx.mock
    def test_bytes_without_name_raises_before_requests(self) -> None:
        _mock_upload()
        with pytest.raises(ValueError, match="name"):
            AttachmentsAPI(make_transport()).upload(b"x")
        assert len(respx.calls) == 0

    # criterio: 04-C03
    @respx.mock
    def test_missing_path_raises_without_requests(self, tmp_path: Path) -> None:
        _mock_upload()
        with pytest.raises(FileNotFoundError):
            AttachmentsAPI(make_transport()).upload(tmp_path / "manca.txt")
        assert len(respx.calls) == 0

    # criterio: 04-C03
    @respx.mock
    def test_directory_raises_without_requests(self, tmp_path: Path) -> None:
        _mock_upload()
        with pytest.raises(IsADirectoryError):
            AttachmentsAPI(make_transport()).upload(tmp_path)
        assert len(respx.calls) == 0

    # criterio: 04-C04
    @respx.mock
    def test_storage_400_raises_upload_error_once(self, tmp_path: Path) -> None:
        error_xml = "<?xml version='1.0'?><Error><Code>InvalidPolicy</Code></Error>"
        ticket_route, storage_route = _mock_upload(httpx.Response(_HTTP_400, text=error_xml))
        path = tmp_path / "nota.txt"
        path.write_bytes(b"x")
        with pytest.raises(UploadError) as exc_info:
            AttachmentsAPI(make_transport()).upload(path)
        err = exc_info.value
        assert err.status_code == _HTTP_400
        assert err.request_url == _STORAGE_URL
        assert err.response_body == error_xml
        assert err.file_name == "nota.txt"
        assert ticket_route.call_count == 1
        assert storage_route.call_count == 1

    # criterio: 04-C05
    @respx.mock
    def test_storage_timeout_raises_transport_error_once(self, tmp_path: Path) -> None:
        ticket_route, storage_route = _mock_upload(httpx.ReadTimeout("timed out"))
        path = tmp_path / "nota.txt"
        path.write_bytes(b"x")
        with pytest.raises(TransportError):
            AttachmentsAPI(make_transport()).upload(path)
        assert ticket_route.call_count == 1
        assert storage_route.call_count == 1

    # criterio: 04-C01
    @respx.mock
    def test_library_closes_file_it_opened(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _mock_upload(httpx.Response(_HTTP_400, text="<Error/>"))
        opened: list[BinaryIO] = []
        real_open = Path.open

        def spy_open(self: Path, *args: Any, **kwargs: Any) -> Any:
            handle = real_open(self, *args, **kwargs)
            opened.append(handle)
            return handle

        monkeypatch.setattr(Path, "open", spy_open)
        path = tmp_path / "nota.txt"
        path.write_bytes(b"x")
        with pytest.raises(UploadError):
            AttachmentsAPI(make_transport()).upload(path)
        assert opened
        assert all(handle.closed for handle in opened)
