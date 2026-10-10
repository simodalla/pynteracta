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
from pynteracta.exceptions import ConcurrencyError, TransportError, ValidationError
from pynteracta.models.facade.attachments import UploadedAttachment, UploadTicket
from pynteracta.models.facade.posts_write import (
    PostAttachmentsWriteResult,
    PostComment,
    PostForCopy,
    PostForCreate,
    PostForEdit,
    PostWriteResult,
    WorkflowOperationResult,
    WorkflowScreen,
    WorkflowScreenWriteResult,
)
from pynteracta.models.generated import external_v2 as generated

_MANAGE = f"{BASE_URL}/communication/posts/manage"
_COMMUNITY_ID = 79
_POST_ID = 21269
_NEW_POST_ID = 21270
_OCC_TOKEN = 5
_HTTP_400 = 400
_HTTP_409 = 409
_NEXT_OCC_TOKEN_EDIT = 6
_COPY_POST_ID = 21271

_CREATE_PATH = f"{_MANAGE}/create-post/{_COMMUNITY_ID}"
_EDIT_PATH = f"{_MANAGE}/edit-post/{_POST_ID}/{_OCC_TOKEN}"
_CUSTOM_DATA_PATH = f"{_MANAGE}/edit-post-custom-data/{_POST_ID}/{_OCC_TOKEN}"
_COPY_PATH = f"{_MANAGE}/copy-post/{_POST_ID}/{_OCC_TOKEN}"
_WATCHERS_PATH = f"{_MANAGE}/edit-post-watchers/{_POST_ID}"
_ATTACHMENTS_PATH = f"{_MANAGE}/edit-post-attachments/{_POST_ID}"
_DELETE_PATH = f"{_MANAGE}/delete-post/{_POST_ID}"
_ERASABLE_PATH = f"{_MANAGE}/mark-post-as-erasable/{_POST_ID}"
_COMMENT_PATH = f"{_MANAGE}/create-comment/{_POST_ID}"
_COMMENT_ID = 5601
_OPERATION_ID = 12
_SCREEN_OCC_TOKEN = 3
_SCREEN_PATH = f"{_MANAGE}/post-workflow-screen-data-for-edit/{_POST_ID}"
_EXECUTE_PATH = f"{_MANAGE}/execute-post-workflow-operation/{_POST_ID}/{_OPERATION_ID}"
_EDIT_SCREEN_PATH = f"{_MANAGE}/edit-post-workflow-screen-data/{_POST_ID}/{_SCREEN_OCC_TOKEN}"
_PARENT_COMMENT_ID = 5
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
        expected = load_payload("post_for_edit_response.json")["contentData"]["customData"]
        assert form.content_data.customData == expected

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


def _mock_put(path: str, fixture: str) -> respx.Route:
    return respx.put(path).mock(return_value=httpx.Response(200, json=load_payload(fixture)))


class TestPostsEdit:
    # criterio: 03-C04
    @respx.mock
    def test_edit_sends_only_given_fields(self) -> None:
        route = _mock_put(_EDIT_PATH, "edit_post_response.json")
        result = _api().edit(_POST_ID, _OCC_TOKEN, title="T2", remove_watcher_user_ids=[7])
        assert route.call_count == 1
        assert _sent(route) == {"title": "T2", "removeWatcherUserIds": [7]}
        assert result.next_occ_token == _NEXT_OCC_TOKEN_EDIT
        assert result.post is not None
        assert result.post.title == "Procedura di prova (rev. 2)"
        assert result.post_id == _POST_ID

    # criterio: 03-C04
    @respx.mock
    def test_edit_without_fields_sends_empty_body(self) -> None:
        route = _mock_put(_EDIT_PATH, "edit_post_response.json")
        _api().edit(_POST_ID, _OCC_TOKEN)
        assert _sent(route) == {}

    # criterio: 03-C02
    @respx.mock
    def test_edit_raw_equivalent(self) -> None:
        route = _mock_put(_EDIT_PATH, "edit_post_response.json")
        req = generated.EditCustomPostRequestDTO(title="T2", removeWatcherUserIds=[7])
        result = _api().edit_raw(_POST_ID, _OCC_TOKEN, req)
        assert _sent(route) == {"title": "T2", "removeWatcherUserIds": [7]}
        assert result.next_occ_token == _NEXT_OCC_TOKEN_EDIT


class TestPostsCustomData:
    # criterio: 03-C05
    @respx.mock
    def test_edit_custom_data_body_and_result(self) -> None:
        route = _mock_put(_CUSTOM_DATA_PATH, "edit_post_response.json")
        result = _api().edit_custom_data(_POST_ID, _OCC_TOKEN, custom_data={"1411": 226})
        assert route.call_count == 1
        assert _sent(route) == {"customData": {"1411": 226}}
        assert isinstance(result, PostWriteResult)
        assert result.next_occ_token == _NEXT_OCC_TOKEN_EDIT

    # criterio: 03-C02
    @respx.mock
    def test_raw_equivalent(self) -> None:
        route = _mock_put(_CUSTOM_DATA_PATH, "edit_post_response.json")
        req = generated.EditPostCustomDataRequestDTO(customData={"1411": 226})
        _api().edit_custom_data_raw(_POST_ID, _OCC_TOKEN, req)
        assert _sent(route) == {"customData": {"1411": 226}}


class TestPostsCopy:
    # criterio: 03-C06
    @respx.mock
    def test_copy_body_and_result(self) -> None:
        route = _mock_put(_COPY_PATH, "copy_post_response.json")
        result = _api().copy(_POST_ID, _OCC_TOKEN, title="Copia")
        assert route.call_count == 1
        assert _sent(route) == {"title": "Copia"}
        assert result.post_id == _COPY_POST_ID
        assert result.next_occ_token == 1

    # criterio: 03-C02
    @respx.mock
    def test_raw_equivalent(self) -> None:
        route = _mock_put(_COPY_PATH, "copy_post_response.json")
        req = generated.CopyCustomPostRequestDTO(title="Copia", announcement=True)
        result = _api().copy_raw(_POST_ID, _OCC_TOKEN, req)
        assert _sent(route) == {"title": "Copia", "announcement": True}
        assert result.post_id == _COPY_POST_ID


class TestPostsWatchersAttachments:
    # criterio: 03-C08
    @respx.mock
    def test_edit_watchers_body_and_none(self) -> None:
        route = respx.put(_WATCHERS_PATH).mock(return_value=httpx.Response(200))
        result = _api().edit_watchers(_POST_ID, add_user_ids=[7], remove_user_ids=[8])
        assert result is None
        assert route.call_count == 1
        assert _sent(route) == {"addWatcherUserIds": [7], "removeWatcherUserIds": [8]}

    # criterio: 03-C08
    @respx.mock
    def test_edit_attachments_body_and_result(self) -> None:
        route = _mock_put(_ATTACHMENTS_PATH, "edit_post_attachments_response.json")
        result = _api().edit_attachments(_POST_ID, remove_ids=[3])
        assert route.call_count == 1
        assert _sent(route) == {"removeAttachmentIds": [3]}
        assert isinstance(result, PostAttachmentsWriteResult)
        assert result.post_id == _POST_ID
        assert [a.id for a in result.added] == [4]
        assert result.updated == []
        assert result.removed_ids == [3]

    # criterio: 03-C02
    @respx.mock
    def test_raw_equivalents(self) -> None:
        watchers = respx.put(_WATCHERS_PATH).mock(return_value=httpx.Response(200))
        attachments = _mock_put(_ATTACHMENTS_PATH, "edit_post_attachments_response.json")
        api = _api()
        api.edit_watchers_raw(_POST_ID, generated.EditPostWatchersRequestDTO(addWatcherUserIds=[7]))
        api.edit_attachments_raw(
            _POST_ID, generated.EditPostAttachmentsRequestDTO(removeAttachmentIds=[3])
        )
        assert _sent(watchers) == {"addWatcherUserIds": [7]}
        assert _sent(attachments) == {"removeAttachmentIds": [3]}


class TestPostsDelete:
    # criterio: 03-C09
    @respx.mock
    def test_delete_returns_post_id(self) -> None:
        route = respx.delete(_DELETE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("delete_post_response.json"))
        )
        assert _api().delete(_POST_ID) == _POST_ID
        assert route.call_count == 1

    # criterio: 03-C09
    @respx.mock
    def test_mark_as_erasable_puts_without_body_and_returns_post_id(self) -> None:
        route = _mock_put(_ERASABLE_PATH, "mark_post_erasable_response.json")
        assert _api().mark_as_erasable(_POST_ID) == _POST_ID
        assert route.call_count == 1
        assert route.calls[0].request.content == b""

    # criterio: 03-C38
    @respx.mock
    def test_mark_as_erasable_returns_server_value_zero(self) -> None:
        respx.put(_ERASABLE_PATH).mock(return_value=httpx.Response(200, json={"postId": 0}))
        assert _api().mark_as_erasable(_POST_ID) == 0


class TestPostsComment:
    # criterio: 03-C10
    @respx.mock
    def test_add_comment_body_and_facade(self) -> None:
        route = respx.post(_COMMENT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_comment_response.json"))
        )
        comment = _api().add_comment(
            _POST_ID, comment="Ciao", comment_format=2, parent_comment_id=_PARENT_COMMENT_ID
        )
        assert route.call_count == 1
        assert _sent(route) == {
            "comment": "Ciao",
            "commentFormat": 2,
            "parentCommentId": _PARENT_COMMENT_ID,
        }
        assert isinstance(comment, PostComment)
        assert comment.id == _COMMENT_ID
        assert comment.comment_plain_text == "Ciao"
        assert comment.creator_user is not None
        assert comment.parent_comment_id == _PARENT_COMMENT_ID
        assert comment.raw is not None

    # criterio: 03-C02
    @respx.mock
    def test_add_comment_raw_equivalent(self) -> None:
        route = respx.post(_COMMENT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_comment_response.json"))
        )
        req = generated.CreatePostCommentRequestDTO(comment="Ciao", commentFormat=2)
        assert _api().add_comment_raw(_POST_ID, req).id == _COMMENT_ID
        assert _sent(route) == {"comment": "Ciao", "commentFormat": 2}


class TestPostsWorkflow:
    # criterio: 03-C12
    @respx.mock
    def test_get_workflow_screen_without_operation(self) -> None:
        route = respx.get(_SCREEN_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("workflow_screen_response.json"))
        )
        screen = _api().get_workflow_screen(_POST_ID)
        assert route.calls[0].request.url.query == b""
        assert isinstance(screen, WorkflowScreen)
        assert screen.screen_data == load_payload("workflow_screen_response.json")["screenData"]
        assert screen.screen_occ_token == _SCREEN_OCC_TOKEN
        assert screen.screen is not None
        assert screen.screen.name == "Approvazione"
        assert screen.current_workflow_state is not None
        assert screen.current_workflow_state.name == "In revisione"

    # criterio: 03-C12
    @respx.mock
    def test_get_workflow_screen_with_operation_query(self) -> None:
        route = respx.get(_SCREEN_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("workflow_screen_response.json"))
        )
        _api().get_workflow_screen(_POST_ID, operation_id=_OPERATION_ID)
        assert route.calls[0].request.url.params["workflowOperationId"] == str(_OPERATION_ID)

    # criterio: 03-C13
    @respx.mock
    def test_execute_operation_body_and_result(self) -> None:
        route = respx.post(_EXECUTE_PATH).mock(
            return_value=httpx.Response(
                200, json=load_payload("execute_workflow_operation_response.json")
            )
        )
        result = _api().execute_workflow_operation(
            _POST_ID, _OPERATION_ID, screen_data={"5": "x"}, screen_occ_token=_SCREEN_OCC_TOKEN
        )
        assert route.call_count == 1
        assert _sent(route) == {"screenData": {"5": "x"}, "screenOccToken": _SCREEN_OCC_TOKEN}
        assert isinstance(result, WorkflowOperationResult)
        assert result.new_current_state is not None
        assert result.new_current_state.name == "Approvato"
        assert result.new_screen_data == {"5": "x", "6": 1}
        assert result.new_permitted_operations == []
        assert result.post_data_has_changed is True

    # criterio: 03-C13
    @respx.mock
    def test_execute_operation_without_kwargs_sends_empty_body(self) -> None:
        route = respx.post(_EXECUTE_PATH).mock(
            return_value=httpx.Response(
                200, json=load_payload("execute_workflow_operation_response.json")
            )
        )
        _api().execute_workflow_operation(_POST_ID, _OPERATION_ID)
        assert _sent(route) == {}

    # criterio: 03-C14
    @respx.mock
    def test_edit_workflow_screen_body_and_result(self) -> None:
        route = _mock_put(_EDIT_SCREEN_PATH, "edit_workflow_screen_response.json")
        result = _api().edit_workflow_screen(_POST_ID, _SCREEN_OCC_TOKEN, screen_data={"5": "x"})
        assert route.call_count == 1
        assert _sent(route) == {"screenData": {"5": "x"}}
        assert isinstance(result, WorkflowScreenWriteResult)
        assert result.next_screen_occ_token == _SCREEN_OCC_TOKEN + 1
        assert result.new_screen_data == {"5": "x", "6": 1}

    # criterio: 03-C02
    @respx.mock
    def test_raw_equivalents(self) -> None:
        execute = respx.post(_EXECUTE_PATH).mock(
            return_value=httpx.Response(
                200, json=load_payload("execute_workflow_operation_response.json")
            )
        )
        edit = _mock_put(_EDIT_SCREEN_PATH, "edit_workflow_screen_response.json")
        api = _api()
        api.execute_workflow_operation_raw(
            _POST_ID,
            _OPERATION_ID,
            generated.ExecutePostWorkflowOperationRequestDTO(screenData={"5": "x"}),
        )
        api.edit_workflow_screen_raw(
            _POST_ID,
            _SCREEN_OCC_TOKEN,
            generated.EditPostWorkflowScreenDataRequestDTO(screenData={"5": "x"}),
        )
        assert _sent(execute) == {"screenData": {"5": "x"}}
        assert _sent(edit) == {"screenData": {"5": "x"}}


# criterio: 03-C03
@pytest.mark.parametrize(
    ("method", "path", "fixture"),
    [
        ("edit", _EDIT_PATH, "edit_post_response.json"),
        ("copy", _COPY_PATH, "copy_post_response.json"),
    ],
)
class TestScheduledPublicationOnEditAndCopy:
    @respx.mock
    def test_zoneinfo_in_body(self, method: str, path: str, fixture: str) -> None:
        route = _mock_put(path, fixture)
        getattr(_api(), method)(_POST_ID, _OCC_TOKEN, scheduled_publication=_SCHEDULED)
        assert _sent(route) == {"scheduledPublication": _SCHEDULED_BODY}

    @respx.mock
    def test_naive_raises_before_request(self, method: str, path: str, fixture: str) -> None:
        route = _mock_put(path, fixture)
        with pytest.raises(ValueError, match="timezone-aware"):
            getattr(_api(), method)(
                _POST_ID, _OCC_TOKEN, scheduled_publication=datetime(2026, 12, 31, 18, 0)
            )
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

    # criterio: 03-C07
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("edit", _EDIT_PATH),
            ("edit_custom_data", _CUSTOM_DATA_PATH),
            ("copy", _COPY_PATH),
        ],
    )
    @respx.mock
    def test_409_raises_concurrency_error_once(self, method: str, path: str) -> None:
        route = respx.put(path).mock(
            return_value=httpx.Response(_HTTP_409, json={"message": "occToken mismatch"})
        )
        with pytest.raises(ConcurrencyError) as exc_info:
            getattr(_api(), method)(_POST_ID, _OCC_TOKEN)
        assert exc_info.value.status_code == _HTTP_409
        assert route.call_count == 1

    # criterio: 03-C17
    @respx.mock
    def test_add_comment_timeout_raises_transport_error_once(self) -> None:
        route = respx.post(_COMMENT_PATH).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(TransportError):
            _api().add_comment(_POST_ID, comment="Ciao")
        assert route.call_count == 1

    # criterio: 03-C07
    @respx.mock
    def test_409_on_workflow_raises_concurrency_error_once(self) -> None:
        conflict = httpx.Response(_HTTP_409, json={"message": "occToken mismatch"})
        execute = respx.post(_EXECUTE_PATH).mock(return_value=conflict)
        edit = respx.put(_EDIT_SCREEN_PATH).mock(return_value=conflict)
        api = _api()
        with pytest.raises(ConcurrencyError):
            api.execute_workflow_operation(_POST_ID, _OPERATION_ID, screen_data={"5": "x"})
        with pytest.raises(ConcurrencyError):
            api.edit_workflow_screen(_POST_ID, _SCREEN_OCC_TOKEN, screen_data={"5": "x"})
        assert execute.call_count == 1
        assert edit.call_count == 1


# ---------------------------------------------------------------------------
# Spec 04: UploadedAttachment nelle scritture dei post
# ---------------------------------------------------------------------------


def _uploaded() -> UploadedAttachment:
    ticket = UploadTicket.from_dict(load_payload("upload_new_attachment_response.json"))
    return UploadedAttachment(ticket, name="nota.txt", mime_type="text/plain")


def _ref() -> dict[str, str]:
    return {
        "name": "nota.txt",
        "contentRef": load_payload("upload_new_attachment_response.json")["contentRef"],
    }


class TestPostsUploadedAttachments:
    # criterio: 04-C07
    @respx.mock
    def test_create_attachments(self) -> None:
        route = respx.post(_CREATE_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_response.json"))
        )
        _api().create(_COMMUNITY_ID, attachments=[{"attachmentId": 3}, _uploaded()])
        assert _sent(route)["attachments"] == [{"attachmentId": 3}, _ref()]

    # criterio: 04-C07
    @respx.mock
    def test_add_comment_attachments(self) -> None:
        route = respx.post(_COMMENT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("create_post_comment_response.json"))
        )
        _api().add_comment(_POST_ID, comment="c", attachments=[_uploaded()])
        assert _sent(route)["attachments"] == [_ref()]

    # criterio: 04-C07
    @respx.mock
    def test_edit_add_attachments(self) -> None:
        route = respx.put(_EDIT_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("edit_post_response.json"))
        )
        _api().edit(_POST_ID, _OCC_TOKEN, add_attachments=[_uploaded()])
        assert _sent(route)["addAttachments"] == [_ref()]

    # criterio: 04-C07
    @respx.mock
    def test_copy_add_attachments(self) -> None:
        route = respx.put(_COPY_PATH).mock(
            return_value=httpx.Response(200, json=load_payload("copy_post_response.json"))
        )
        _api().copy(_POST_ID, _OCC_TOKEN, add_attachments=[_uploaded()])
        assert _sent(route)["addAttachments"] == [_ref()]

    # criterio: 04-C07
    @respx.mock
    def test_edit_attachments_add_and_update_version(self) -> None:
        route = respx.put(_ATTACHMENTS_PATH).mock(
            return_value=httpx.Response(
                200, json=load_payload("edit_post_attachments_response.json")
            )
        )
        uploaded = _uploaded()
        _api().edit_attachments(
            _POST_ID,
            add=[{"attachmentId": 3}, uploaded],
            update=[uploaded.as_version_of(7)],
            remove_ids=[9],
        )
        assert _sent(route) == {
            "addAttachments": [{"attachmentId": 3}, _ref()],
            "updateAttachments": [{"attachmentId": 7, **_ref()}],
            "removeAttachmentIds": [9],
        }
