# SPDX-License-Identifier: Apache-2.0
"""Test delle scritture dei post in libreria (spec 03): ``client.posts`` via ``PostsWriteAPI``."""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.posts import PostsAPI
from pynteracta.exceptions import TransportError, ValidationError
from pynteracta.models.facade.posts_write import (
    PostForCopy,
    PostForCreate,
    PostForEdit,
    PostWriteResult,
)
from pynteracta.models.generated import external_v2 as generated

_MANAGE = f"{BASE_URL}/communication/posts/manage"
_COMMUNITY_ID = 79
_POST_ID = 21269
_NEW_POST_ID = 21270
_OCC_TOKEN = 5
_HTTP_400 = 400

_CREATE_PATH = f"{_MANAGE}/create-post/{_COMMUNITY_ID}"
_SCHEDULED = datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome"))
_SCHEDULED_BODY = {"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"}


def _api() -> PostsAPI:
    return PostsAPI(make_transport())


def _sent(route: respx.Route, index: int = 0) -> dict:  # type: ignore[type-arg]
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


class TestPostsPrep:
    # criterio: 03-C11
    @respx.mock
    def test_get_for_create(self) -> None:
        route = respx.get(f"{_MANAGE}/post-data-for-create/{_COMMUNITY_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("post_for_create_response.json"))
        )
        form = _api().get_for_create(_COMMUNITY_ID)
        assert isinstance(form, PostForCreate)
        assert form.content_data is not None
        assert route.call_count == 1

    # criterio: 03-C11
    @respx.mock
    def test_get_for_edit_no_query_and_occ_token(self) -> None:
        route = respx.get(f"{_MANAGE}/post-data-for-edit/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("post_for_edit_response.json"))
        )
        form = _api().get_for_edit(_POST_ID)
        assert isinstance(form, PostForEdit)
        assert route.calls[0].request.url.query == b""
        assert form.occ_token == _OCC_TOKEN
        assert form.community_id == _COMMUNITY_ID
        assert form.current_workflow_state is not None
        assert form.content_data is not None
        assert form.content_data.title == "Procedura di prova"
        assert form.content_data.customData == {"1411": 226, "1413": True}

    # criterio: 03-C11
    @respx.mock
    def test_get_for_edit_load_attachments_false_in_query(self) -> None:
        route = respx.get(f"{_MANAGE}/post-data-for-edit/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("post_for_edit_response.json"))
        )
        _api().get_for_edit(_POST_ID, load_attachments=False)
        assert route.calls[0].request.url.params["loadAttachments"] == "false"

    # criterio: 03-C11
    @respx.mock
    def test_get_for_copy(self) -> None:
        route = respx.get(f"{_MANAGE}/post-data-for-copy/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("post_for_copy_response.json"))
        )
        form = _api().get_for_copy(_POST_ID, load_attachments=True)
        assert isinstance(form, PostForCopy)
        assert form.occ_token == _OCC_TOKEN
        assert form.content_data is not None
        assert route.calls[0].request.url.params["loadAttachments"] == "true"


class TestPostsCreate:
    # criterio: 03-C01
    @respx.mock
    def test_create_sends_only_given_fields_and_wraps_response(self) -> None:
        payload = load_payload("create_post_response.json")
        route = respx.post(_CREATE_PATH).mock(return_value=httpx.Response(200, json=payload))
        result = _api().create(
            _COMMUNITY_ID,
            title="T",
            description="D",
            description_format=2,
            custom_data={"1411": 226},
            watcher_user_ids=[7],
        )
        assert route.call_count == 1
        assert _sent(route) == {
            "announcement": False,
            "title": "T",
            "description": "D",
            "descriptionFormat": 2,
            "customData": {"1411": 226},
            "watcherUserIds": [7],
        }
        assert isinstance(result, PostWriteResult)
        assert result.post_id == _NEW_POST_ID
        assert result.next_occ_token == payload["nextOccToken"]
        assert result.post is not None
        assert result.post.title == payload["postData"]["title"]
        assert isinstance(result.raw, generated.CreatePostResponseDTO)

    # criterio: 03-C01
    @respx.mock
    def test_create_without_kwargs_sends_announcement_only(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_response.json"))
        )
        _api().create(_COMMUNITY_ID)
        assert _sent(route) == {"announcement": False}

    # criterio: 03-C02
    @respx.mock
    def test_create_raw_equivalent(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_response.json"))
        )
        result = _api().create_raw(
            _COMMUNITY_ID, generated.CreateCustomPostRequest(announcement=False, title="T")
        )
        assert _sent(route) == {"announcement": False, "title": "T"}
        assert result.post_id == _NEW_POST_ID

    # criterio: 03-C03
    @respx.mock
    def test_scheduled_publication_zoneinfo_in_body(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_response.json"))
        )
        _api().create(_COMMUNITY_ID, scheduled_publication=_SCHEDULED, draft=True)
        assert _sent(route)["scheduledPublication"] == _SCHEDULED_BODY
        assert _sent(route)["draft"] is True

    # criterio: 03-C03
    @respx.mock
    def test_naive_scheduled_publication_raises_before_request(self) -> None:
        route = respx.post(_CREATE_PATH).mock(return_value=httpx.Response(200, json={}))
        with pytest.raises(ValueError, match="timezone-aware"):
            _api().create(_COMMUNITY_ID, scheduled_publication=datetime(2026, 12, 31, 18, 0))
        assert route.call_count == 0


class TestPostsErrors:
    # criterio: 03-C16
    @respx.mock
    def test_400_custom_field_validation_error_readable(self) -> None:
        body = load_payload("custom_field_validation_error_response.json")
        route = respx.post(_CREATE_PATH).mock(return_value=httpx.Response(_HTTP_400, json=body))
        with pytest.raises(ValidationError) as exc_info:
            _api().create(_COMMUNITY_ID, custom_data={"1411": "bad"})
        assert exc_info.value.status_code == _HTTP_400
        assert "validationErrors" in str(exc_info.value.response_body)
        assert route.call_count == 1

    # criterio: 03-C17
    @respx.mock
    def test_create_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(_CREATE_PATH).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(TransportError):
            _api().create(_COMMUNITY_ID, title="T")
        assert route.call_count == 1
