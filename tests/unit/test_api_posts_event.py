# SPDX-License-Identifier: Apache-2.0
"""Test delle scritture dei post evento in libreria (spec 08): ``client.posts`` via
``PostsEventAPI``."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from api_helpers import BASE_URL, load_payload, make_transport

from pynteracta.api.posts import PostsAPI
from pynteracta.api.posts_event import PostsEventAPI, build_event_block
from pynteracta.api.posts_write import PostsWriteAPI
from pynteracta.exceptions import (
    ConcurrencyError,
    NotFoundError,
    PermissionError,
    TransportError,
    ValidationError,
)
from pynteracta.models.facade.attachments import UploadedAttachment, UploadTicket
from pynteracta.models.facade.posts_event import (
    EventPostForCopy,
    EventPostForCreate,
    EventPostForEdit,
    ParticipationAnswer,
)
from pynteracta.models.facade.posts_write import PostWriteResult
from pynteracta.models.generated import external_v2 as generated

_MANAGE = f"{BASE_URL}/communication/posts/manage"
_COMMUNITY_ID = 79
_POST_ID = 21269
_NEW_POST_ID = 21270
_OCC_TOKEN = 5
_HTTP_400 = 400
_ROME = ZoneInfo("Europe/Rome")
_START = datetime(2026, 11, 5, 10, 0, tzinfo=_ROME)
_END = datetime(2026, 11, 5, 12, 0, tzinfo=_ROME)
_START_BLOCK = {"localDatetime": "2026-11-05T10:00:00"}
_END_BLOCK = {"localDatetime": "2026-11-05T12:00:00"}

_CREATE_PATH = f"{_MANAGE}/create-event-post/{_COMMUNITY_ID}"
_EDIT_PATH = f"{_MANAGE}/edit-event-post/{_POST_ID}/{_OCC_TOKEN}"
_COPY_PATH = f"{_MANAGE}/copy-event-post/{_POST_ID}/{_OCC_TOKEN}"
_COPY_POST_ID = 21271
_NEXT_OCC_TOKEN_EDIT = 6
_HTTP_409 = 409
_HTTP_403 = 403
_HTTP_404 = 404
_PARTICIPATE_PATH = f"{_MANAGE}/post-event/{_POST_ID}/partecipate"


def _api() -> PostsAPI:
    return PostsAPI(make_transport())


def _sent(route: respx.Route, index: int = 0) -> dict[str, Any]:
    return json.loads(route.calls[index].request.content)  # type: ignore[no-any-return]


def _mock_create() -> respx.Route:
    return respx.post(_CREATE_PATH).mock(
        return_value=httpx.Response(200, json=load_payload("create_event_post_response.json"))
    )


class TestPostsApiShape:
    def test_posts_api_exposes_event_methods_and_keeps_custom_ones(self) -> None:
        assert issubclass(PostsAPI, PostsEventAPI)
        for name in ("create_event", "get_event_for_create", "get_event_for_edit"):
            assert getattr(PostsAPI, name) is getattr(PostsEventAPI, name)
        for name in ("create", "edit", "copy", "get_for_edit"):
            assert getattr(PostsAPI, name) is getattr(PostsWriteAPI, name)


class TestBuildEventBlock:
    # criterio: 08-C05
    def test_nothing_gives_empty_dict(self) -> None:
        assert build_event_block() == {}

    # criterio: 08-C01
    def test_full_block(self) -> None:
        assert build_event_block(
            start_at=_START,
            end_at=_END,
            all_day=False,
            location="Sala A",
            invited_user_ids=[7],
            invited_group_ids=[3],
            invitation_type_id=2,
            send_edit_post_notifications=True,
        ) == {
            "startAt": _START_BLOCK,
            "endAt": _END_BLOCK,
            "timezone": "Europe/Rome",
            "allDay": False,
            "location": "Sala A",
            "invitations": {
                "users": [{"id": 7, "typeId": 2}],
                "groups": [{"id": 3, "typeId": 2}],
                "sendEditPostNotifications": True,
            },
        }

    # criterio: 08-C02
    def test_invitations_without_type(self) -> None:
        assert build_event_block(invited_group_ids=[3]) == {"invitations": {"groups": [{"id": 3}]}}
        assert build_event_block(send_edit_post_notifications=False) == {
            "invitations": {"sendEditPostNotifications": False}
        }


class TestEventPrep:
    # criterio: 08-C11
    @respx.mock
    def test_get_event_for_create(self) -> None:
        route = respx.get(f"{_MANAGE}/event-post-data-for-create/{_COMMUNITY_ID}").mock(
            return_value=httpx.Response(
                200, json=load_payload("event_post_for_create_response.json")
            )
        )
        form = _api().get_event_for_create(_COMMUNITY_ID)
        assert isinstance(form, EventPostForCreate)
        assert form.content_data is not None
        assert route.call_count == 1

    # criterio: 08-C11
    @respx.mock
    def test_get_event_for_edit_no_query_occ_token_and_event(self) -> None:
        route = respx.get(f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("event_post_for_edit_response.json"))
        )
        form = _api().get_event_for_edit(_POST_ID)
        assert isinstance(form, EventPostForEdit)
        assert route.calls[0].request.url.query == b""
        assert form.occ_token == _OCC_TOKEN
        assert form.community_id == _COMMUNITY_ID
        assert form.content_data is not None
        assert form.content_data.title == "Riunione di prova"
        assert form.content_data.coverImageContentRef == "ref-1"
        event = form.event
        assert event is not None
        assert event.start_at == _START
        assert event.end_at == _END
        assert event.timezone == "Europe/Rome"
        assert event.all_day is False
        assert event.location == "Sala A"
        assert event.participants_count == 3  # noqa: PLR2004
        assert event.my_answer is ParticipationAnswer.YES
        assert event.invited_users[0].id == 7  # noqa: PLR2004
        assert event.invited_users[0].type_id == 2  # noqa: PLR2004
        assert event.invited_groups[0].id == 3  # noqa: PLR2004
        assert event.send_edit_post_notifications is False

    # criterio: 08-C11
    @respx.mock
    def test_get_event_for_edit_load_attachments_false_in_query(self) -> None:
        route = respx.get(f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("event_post_for_edit_response.json"))
        )
        _api().get_event_for_edit(_POST_ID, load_attachments=False)
        assert route.calls[0].request.url.params["loadAttachments"] == "false"

    # criterio: 08-C11
    @respx.mock
    def test_get_event_for_copy(self) -> None:
        route = respx.get(f"{_MANAGE}/event-post-data-for-copy/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("event_post_for_copy_response.json"))
        )
        form = _api().get_event_for_copy(_POST_ID)
        assert isinstance(form, EventPostForCopy)
        assert form.occ_token == _OCC_TOKEN
        assert form.content_data is not None
        assert form.event is not None
        assert route.calls[0].request.url.query == b""

    # criterio: 08-C11
    @respx.mock
    def test_event_none_when_missing(self) -> None:
        data = load_payload("event_post_for_edit_response.json")
        del data["contentData"]["event"]
        respx.get(f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=data)
        )
        assert _api().get_event_for_edit(_POST_ID).event is None


class TestEventCreate:
    # criterio: 08-C01
    @respx.mock
    def test_create_event_sends_only_given_fields_and_wraps_response(self) -> None:
        route = _mock_create()
        result = _api().create_event(
            _COMMUNITY_ID,
            start_at=_START,
            end_at=_END,
            location="Sala A",
            invited_user_ids=[7],
            invited_group_ids=[3],
            invitation_type_id=2,
            send_edit_post_notifications=True,
            title="T",
            description="D",
            description_format=2,
            cover_image_content_ref="ref-1",
            watcher_user_ids=[8],
            watcher_group_ids=[4],
            pinned=True,
            announcement=False,
            client_uid="uid-1",
        )
        assert route.call_count == 1
        assert _sent(route) == {
            "title": "T",
            "description": "D",
            "descriptionFormat": 2,
            "coverImageContentRef": "ref-1",
            "watcherUserIds": [8],
            "watcherGroupIds": [4],
            "announcement": False,
            "clientUid": "uid-1",
            "pinned": True,
            "event": {
                "startAt": _START_BLOCK,
                "endAt": _END_BLOCK,
                "timezone": "Europe/Rome",
                "location": "Sala A",
                "invitations": {
                    "users": [{"id": 7, "typeId": 2}],
                    "groups": [{"id": 3, "typeId": 2}],
                    "sendEditPostNotifications": True,
                },
            },
        }
        assert isinstance(result, PostWriteResult)
        assert isinstance(result.raw, generated.CreatePostResponseDTO)
        assert result.post_id == _NEW_POST_ID
        assert result.next_occ_token == 1
        assert result.post is not None
        assert result.post.title == "Riunione di prova"

    # criterio: 08-C02
    @respx.mock
    def test_create_event_start_only_sends_event_block_without_announcement(self) -> None:
        route = _mock_create()
        _api().create_event(_COMMUNITY_ID, start_at=_START)
        assert _sent(route) == {"event": {"startAt": _START_BLOCK, "timezone": "Europe/Rome"}}

    # criterio: 08-C02
    @respx.mock
    def test_invited_user_without_type_sends_id_only(self) -> None:
        route = _mock_create()
        _api().create_event(_COMMUNITY_ID, start_at=_START, invited_user_ids=[7])
        assert _sent(route)["event"]["invitations"] == {"users": [{"id": 7}]}

    # criterio: 08-C02
    @respx.mock
    def test_end_at_converted_into_start_zone(self) -> None:
        route = _mock_create()
        end = datetime(2026, 11, 5, 11, 0, tzinfo=ZoneInfo("UTC"))
        _api().create_event(_COMMUNITY_ID, start_at=_START, end_at=end)
        event = _sent(route)["event"]
        assert event["endAt"] == _END_BLOCK
        assert event["timezone"] == "Europe/Rome"

    # criterio: 08-C02
    @respx.mock
    def test_fixed_offset_sends_utc(self) -> None:
        route = _mock_create()
        start = datetime(2026, 11, 5, 10, 0, tzinfo=timezone(timedelta(hours=2)))
        _api().create_event(_COMMUNITY_ID, start_at=start)
        assert _sent(route)["event"] == {
            "startAt": {"localDatetime": "2026-11-05T08:00:00"},
            "timezone": "UTC",
        }

    # criterio: 08-C04
    @respx.mock
    def test_create_event_raw_equivalent(self) -> None:
        route = _mock_create()
        event = {"startAt": _START_BLOCK, "timezone": "Europe/Rome"}
        req = generated.CreateEventPostRequestDTO(title="T", event=event)  # type: ignore[arg-type]
        result = _api().create_event_raw(_COMMUNITY_ID, req)
        assert route.call_count == 1
        assert _sent(route) == {"title": "T", "event": event}
        assert result.post_id == _NEW_POST_ID

    @respx.mock
    def test_scheduled_publication_and_link_preview(self) -> None:
        route = _mock_create()
        _api().create_event(
            _COMMUNITY_ID,
            start_at=_START,
            scheduled_publication=_END,
            link_preview={"url": "https://example.org"},
            draft=True,
            visibility=2,
            all_day=True,
            attachments=[{"attachmentId": 3}],
        )
        body = _sent(route)
        assert body["scheduledPublication"] == {
            "datetime": "2026-11-05T12:00:00",
            "timezone": "Europe/Rome",
        }
        assert body["linkPreview"] == {"url": "https://example.org"}
        assert body["draft"] is True
        assert body["visibility"] == 2  # noqa: PLR2004
        assert body["event"]["allDay"] is True
        assert body["attachments"] == [{"attachmentId": 3}]


def _mock_edit() -> respx.Route:
    return respx.put(_EDIT_PATH).mock(
        return_value=httpx.Response(200, json=load_payload("edit_event_post_response.json"))
    )


def _mock_copy() -> respx.Route:
    return respx.put(_COPY_PATH).mock(
        return_value=httpx.Response(200, json=load_payload("copy_event_post_response.json"))
    )


class TestEventEdit:
    # criterio: 08-C05
    @respx.mock
    def test_edit_event_sends_only_given_fields(self) -> None:
        route = _mock_edit()
        result = _api().edit_event(
            _POST_ID,
            _OCC_TOKEN,
            location="Sala B",
            add_watcher_group_ids=[4],
            remove_watcher_user_ids=[8],
            pinned=False,
            cover_image_content_ref="ref-2",
        )
        assert route.call_count == 1
        assert _sent(route) == {
            "coverImageContentRef": "ref-2",
            "addWatcherGroupIds": [4],
            "removeWatcherUserIds": [8],
            "pinned": False,
            "event": {"location": "Sala B"},
        }
        assert isinstance(result.raw, generated.EditPostResponseDTO)
        assert result.next_occ_token == _NEXT_OCC_TOKEN_EDIT
        assert result.post_id == _POST_ID
        assert result.post is not None
        assert result.post.title == "Riunione di prova (rev. 2)"

    # criterio: 08-C05
    @respx.mock
    def test_edit_event_end_only_sends_end_and_timezone(self) -> None:
        route = _mock_edit()
        _api().edit_event(_POST_ID, _OCC_TOKEN, end_at=_END)
        assert _sent(route) == {"event": {"endAt": _END_BLOCK, "timezone": "Europe/Rome"}}

    # criterio: 08-C05
    @respx.mock
    def test_edit_event_without_fields_sends_empty_body(self) -> None:
        route = _mock_edit()
        _api().edit_event(_POST_ID, _OCC_TOKEN)
        assert _sent(route) == {}

    @respx.mock
    def test_edit_event_other_fields(self) -> None:
        route = _mock_edit()
        _api().edit_event(
            _POST_ID,
            _OCC_TOKEN,
            title="T2",
            description="D",
            description_format=2,
            add_attachments=[{"attachmentId": 4}],
            update_attachments=[{"attachmentId": 5, "contentRef": "r"}],
            remove_attachment_ids=[3],
            add_watcher_user_ids=[7],
            remove_watcher_group_ids=[5],
            visibility=1,
            link_preview={"url": "https://example.org"},
            draft=False,
            scheduled_publication=_END,
            invited_user_ids=[9],
        )
        body = _sent(route)
        assert body["addAttachments"] == [{"attachmentId": 4}]
        assert body["removeWatcherGroupIds"] == [5]
        assert body["scheduledPublication"]["timezone"] == "Europe/Rome"
        assert body["event"] == {"invitations": {"users": [{"id": 9}]}}

    # criterio: 08-C04
    @respx.mock
    def test_raw_equivalent(self) -> None:
        route = _mock_edit()
        req = generated.EditEventPostRequestDTO(event={"location": "Sala B"})  # type: ignore[arg-type]
        result = _api().edit_event_raw(_POST_ID, _OCC_TOKEN, req)
        assert _sent(route) == {"event": {"location": "Sala B"}}
        assert result.next_occ_token == _NEXT_OCC_TOKEN_EDIT


class TestEventCopy:
    # criterio: 08-C06
    @respx.mock
    def test_copy_event_body_and_result(self) -> None:
        route = _mock_copy()
        result = _api().copy_event(
            _POST_ID,
            _OCC_TOKEN,
            title="Copia",
            announcement=True,
            client_uid="uid-2",
            start_at=_START,
        )
        assert route.call_count == 1
        assert _sent(route) == {
            "title": "Copia",
            "announcement": True,
            "clientUid": "uid-2",
            "event": {"startAt": _START_BLOCK, "timezone": "Europe/Rome"},
        }
        assert isinstance(result.raw, generated.CopyPostResponseDTO)
        assert result.post_id == _COPY_POST_ID
        assert result.next_occ_token == 1

    # criterio: 08-C04
    @respx.mock
    def test_raw_equivalent(self) -> None:
        route = _mock_copy()
        req = generated.CopyEventPostRequestDTO(title="Copia", announcement=True)
        result = _api().copy_event_raw(_POST_ID, _OCC_TOKEN, req)
        assert _sent(route) == {"title": "Copia", "announcement": True}
        assert result.post_id == _COPY_POST_ID


def _mock_participate() -> respx.Route:
    return respx.put(_PARTICIPATE_PATH).mock(return_value=httpx.Response(200))


class TestParticipate:
    # criterio: 08-C29
    @respx.mock
    def test_participate_body_and_none(self) -> None:
        route = _mock_participate()
        result = _api().participate(_POST_ID, ParticipationAnswer.YES, notes="Arrivo tardi")
        assert result is None
        assert route.call_count == 1
        assert _sent(route) == {"typeId": 1, "notes": '[{"insert":"Arrivo tardi\\n"}]'}

    # criterio: 08-C29
    @respx.mock
    def test_participate_int_answer(self) -> None:
        route = _mock_participate()
        _api().participate(_POST_ID, 3)
        assert _sent(route) == {"typeId": 3}

    # criterio: 08-C29
    @pytest.mark.parametrize("answer", [0, 4])
    @respx.mock
    def test_participate_invalid_answer_raises_before_request(self, answer: int) -> None:
        route = _mock_participate()
        with pytest.raises(ValueError, match=str(answer)):
            _api().participate(_POST_ID, answer)
        assert route.call_count == 0

    # criterio: 08-C04
    # criterio: 08-C29
    @respx.mock
    def test_raw_equivalent(self) -> None:
        route = _mock_participate()
        req = generated.EditPostEventPartecipateRequestDTO(typeId=2, notes="Forse")
        assert _api().participate_raw(_POST_ID, req) is None
        assert _sent(route) == {"typeId": 2, "notes": "Forse"}


class TestEventErrors:
    # criterio: 08-C03
    @pytest.mark.parametrize("field", ["start_at", "end_at"])
    @respx.mock
    def test_naive_datetime_raises_before_request_on_create(self, field: str) -> None:
        route = _mock_create()
        kwargs: dict[str, Any] = {"start_at": _START, "end_at": _END}
        kwargs[field] = datetime(2026, 11, 5, 10, 0)
        with pytest.raises(ValueError, match=f"{field} must be a timezone-aware datetime"):
            _api().create_event(_COMMUNITY_ID, **kwargs)
        assert route.call_count == 0

    # criterio: 08-C09
    @respx.mock
    def test_create_400_custom_field_validation_readable(self) -> None:
        body = load_payload("custom_field_validation_error_response.json")
        route = respx.post(_CREATE_PATH).mock(return_value=httpx.Response(_HTTP_400, json=body))
        with pytest.raises(ValidationError) as exc_info:
            _api().create_event(_COMMUNITY_ID, start_at=_START, title="T")
        assert exc_info.value.status_code == _HTTP_400
        assert "validationErrors" in str(exc_info.value.response_body)
        assert route.call_count == 1

    # criterio: 08-C10
    @respx.mock
    def test_create_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(_CREATE_PATH).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(TransportError):
            _api().create_event(_COMMUNITY_ID, start_at=_START)
        assert route.call_count == 1

    # criterio: 08-C03
    @pytest.mark.parametrize("method", ["edit_event", "copy_event"])
    @pytest.mark.parametrize("field", ["start_at", "end_at"])
    @respx.mock
    def test_naive_datetime_raises_before_request_on_edit_and_copy(
        self, method: str, field: str
    ) -> None:
        edit = _mock_edit()
        copy = _mock_copy()
        with pytest.raises(ValueError, match=f"{field} must be a timezone-aware datetime"):
            getattr(_api(), method)(_POST_ID, _OCC_TOKEN, **{field: datetime(2026, 11, 5, 10)})
        assert edit.call_count == 0
        assert copy.call_count == 0

    # criterio: 08-C08
    @pytest.mark.parametrize(
        ("method", "path"), [("edit_event", _EDIT_PATH), ("copy_event", _COPY_PATH)]
    )
    @respx.mock
    def test_409_raises_concurrency_error_once(self, method: str, path: str) -> None:
        route = respx.put(path).mock(
            return_value=httpx.Response(_HTTP_409, json={"message": "occToken mismatch"})
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            getattr(_api(), method)(_POST_ID, _OCC_TOKEN, location="Sala B")
        assert exc_info.value.status_code == _HTTP_409
        assert route.call_count == 1

    # criterio: 08-C09
    @respx.mock
    def test_participate_404_not_found_once(self) -> None:
        route = respx.put(_PARTICIPATE_PATH).mock(
            return_value=httpx.Response(_HTTP_404, json={"message": "Post evento non esistente"})
        )
        with pytest.raises(NotFoundError) as exc_info:
            _api().participate(_POST_ID, ParticipationAnswer.NO)
        assert exc_info.value.status_code == _HTTP_404
        assert route.call_count == 1

    # criterio: 08-C09
    @respx.mock
    def test_participate_403_permission_once(self) -> None:
        route = respx.put(_PARTICIPATE_PATH).mock(
            return_value=httpx.Response(_HTTP_403, json={"message": "Forbidden"})
        )
        with pytest.raises(PermissionError):
            _api().participate(_POST_ID, ParticipationAnswer.MAYBE)
        assert route.call_count == 1

    # criterio: 08-C10
    @respx.mock
    def test_participate_timeout_raises_transport_error_once(self) -> None:
        route = respx.put(_PARTICIPATE_PATH).mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(TransportError):
            _api().participate(_POST_ID, ParticipationAnswer.YES)
        assert route.call_count == 1


_ALL_DAY_BLOCK = {
    "startAt": {"localDatetime": "2026-11-05"},
    "endAt": {"localDatetime": "2026-11-06"},
    "allDay": True,
}


class TestAllDay:
    # criterio: 08-C26
    @respx.mock
    def test_create_all_day_dates(self) -> None:
        route = _mock_create()
        _api().create_event(
            _COMMUNITY_ID, start_at=date(2026, 11, 5), end_at=date(2026, 11, 6), all_day=True
        )
        assert _sent(route) == {"event": _ALL_DAY_BLOCK}

    # criterio: 08-C26
    def test_aware_datetime_all_day_uses_local_date(self) -> None:
        late = datetime(2026, 11, 5, 23, 30, tzinfo=_ROME)
        assert build_event_block(start_at=late, all_day=True) == {
            "startAt": {"localDatetime": "2026-11-05"},
            "allDay": True,
        }

    # criterio: 08-C26
    def test_naive_datetime_all_day_accepted(self) -> None:
        naive = datetime(2026, 11, 5, 10, 0)
        assert build_event_block(end_at=naive, all_day=True) == {
            "endAt": {"localDatetime": "2026-11-05"},
            "allDay": True,
        }

    # criterio: 08-C26
    @pytest.mark.parametrize("method", ["create_event", "edit_event", "copy_event"])
    @pytest.mark.parametrize("all_day", [None, False])
    @respx.mock
    def test_date_without_all_day_raises(self, method: str, all_day: bool | None) -> None:
        create, edit, copy = _mock_create(), _mock_edit(), _mock_copy()
        args: tuple[int, ...] = (
            (_COMMUNITY_ID,)
            if method == "create_event"
            else (
                _POST_ID,
                _OCC_TOKEN,
            )
        )
        with pytest.raises(ValueError, match="all_day"):
            getattr(_api(), method)(*args, start_at=date(2026, 11, 5), all_day=all_day)
        assert create.call_count == edit.call_count == copy.call_count == 0

    # criterio: 08-C26
    @pytest.mark.parametrize("method", ["edit_event", "copy_event"])
    @respx.mock
    def test_edit_and_copy_all_day(self, method: str) -> None:
        route = _mock_edit() if method == "edit_event" else _mock_copy()
        getattr(_api(), method)(
            _POST_ID, _OCC_TOKEN, start_at=date(2026, 11, 5), end_at=date(2026, 11, 6), all_day=True
        )
        assert _sent(route) == {"event": _ALL_DAY_BLOCK}

    # criterio: 08-C28
    @respx.mock
    def test_edit_with_read_start_keeps_zone(self) -> None:
        respx.get(f"{_MANAGE}/event-post-data-for-edit/{_POST_ID}").mock(
            return_value=httpx.Response(200, json=load_payload("event_post_for_edit_response.json"))
        )
        route = _mock_edit()
        api = _api()
        form = api.get_event_for_edit(_POST_ID)
        assert form.event is not None
        api.edit_event(_POST_ID, _OCC_TOKEN, start_at=form.event.start_at)
        assert _sent(route) == {"event": {"startAt": _START_BLOCK, "timezone": "Europe/Rome"}}


# ---------------------------------------------------------------------------
# Spec 09: allegati non scaricabili nei post evento
# ---------------------------------------------------------------------------


class TestEventNotDownloadableAttachments:
    # criterio: 09-C12
    @respx.mock
    def test_create_event(self) -> None:
        ticket = UploadTicket.from_dict(load_payload("upload_new_attachment_response.json"))
        uploaded = UploadedAttachment(
            ticket, name="nota.txt", mime_type="text/plain", downloadable=False
        )
        route = _mock_create()
        _api().create_event(_COMMUNITY_ID, start_at=_START, attachments=[uploaded])
        assert _sent(route)["attachments"] == [
            {"name": "nota.txt", "contentRef": uploaded.content_ref, "downloadable": False}
        ]
