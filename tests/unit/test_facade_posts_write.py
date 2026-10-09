# SPDX-License-Identifier: Apache-2.0
"""Test delle façade di scrittura dei post (spec 03, T03)."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

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

_POST_ID = 21269
_NEW_POST_ID = 21270
_COPY_POST_ID = 21271
_COMMUNITY_ID = 79
_OCC_TOKEN = 5
_NEXT_OCC_TOKEN_EDIT = 6
_SCREEN_OCC_TOKEN = 3
_NEXT_SCREEN_OCC_TOKEN = 4
_COMMENT_ID = 5601
_PARENT_COMMENT_ID = 5
_CREATOR_ID = 1042
_ADDED_ATTACHMENT_ID = 4
_REMOVED_ATTACHMENT_ID = 3
_OPERATION_ID = 12


class TestPostWriteResult:
    # criterio: 03-C29
    def test_from_create(self) -> None:
        result = PostWriteResult.from_create(load_payload("create_post_response.json"))
        assert isinstance(result.raw, generated.CreatePostResponseDTO)
        assert result.post_id == _NEW_POST_ID
        assert result.next_occ_token == 1
        assert isinstance(result.post, generated.PostDetailDTO1)
        assert result.post.title == "Procedura di prova"
        assert result.post.customData == {"1411": 226, "1413": True}

    # criterio: 03-C29
    def test_from_edit_takes_post_id_from_post_data(self) -> None:
        result = PostWriteResult.from_edit(load_payload("edit_post_response.json"))
        assert result.post_id == _POST_ID
        assert result.next_occ_token == _NEXT_OCC_TOKEN_EDIT
        assert result.post is not None
        assert result.post.title == "Procedura di prova (rev. 2)"

    # criterio: 03-C29
    def test_from_copy(self) -> None:
        result = PostWriteResult.from_copy(load_payload("copy_post_response.json"))
        assert result.post_id == _COPY_POST_ID
        assert result.post is not None
        assert result.post.title == "Copia della procedura"

    def test_without_post_data(self) -> None:
        result = PostWriteResult.from_edit({"nextOccToken": 2})
        assert result.post is None
        assert result.post_id is None
        assert result.next_occ_token == 2  # noqa: PLR2004


class TestPostForms:
    # criterio: 03-C29
    def test_for_create(self) -> None:
        form = PostForCreate.from_dict(load_payload("post_for_create_response.json"))
        assert isinstance(form.raw, generated.GetCustomPostForCreateResponseDTO)
        assert isinstance(form.content_data, generated.PostEditableContentDataDTO1)
        assert form.content_data.customData == {}

    # criterio: 03-C29
    def test_for_edit(self) -> None:
        form = PostForEdit.from_dict(load_payload("post_for_edit_response.json"))
        assert form.occ_token == _OCC_TOKEN
        assert form.community_id == _COMMUNITY_ID
        assert form.custom_id == "POST-21269"
        assert form.current_workflow_state is not None
        assert form.current_workflow_state.name == "In revisione"
        assert form.content_data is not None
        assert form.content_data.title == "Procedura di prova"
        expected = load_payload("post_for_edit_response.json")["contentData"]["customData"]
        assert form.content_data.customData == expected

    # criterio: 03-C29
    def test_for_copy(self) -> None:
        form = PostForCopy.from_dict(load_payload("post_for_copy_response.json"))
        assert form.occ_token == _OCC_TOKEN
        assert form.content_data is not None
        assert form.content_data.visibility == 1

    def test_missing_nested_data_is_none(self) -> None:
        form = PostForEdit.from_dict({"occToken": 1})
        assert form.content_data is None
        assert form.current_workflow_state is None
        assert PostForCreate.from_dict({}).content_data is None


class TestPostComment:
    # criterio: 03-C29
    def test_from_dict(self) -> None:
        comment = PostComment.from_dict(load_payload("create_post_comment_response.json"))
        assert isinstance(comment.raw, generated.CreatePostCommentResponseDTO)
        assert comment.id == _COMMENT_ID
        assert comment.comment_plain_text == "Ciao"
        assert comment.comment_delta is not None
        assert comment.creator_user is not None
        assert comment.creator_user.id == _CREATOR_ID
        assert comment.creation_timestamp == 1748002000000  # noqa: PLR2004
        assert comment.parent_comment_id == _PARENT_COMMENT_ID

    def test_without_parent_or_comment(self) -> None:
        payload = load_payload("create_post_comment_response.json")
        payload["comment"]["parentComment"] = None
        assert PostComment.from_dict(payload).parent_comment_id is None
        empty = PostComment.from_dict({})
        assert empty.id is None
        assert empty.creator_user is None
        assert empty.parent_comment_id is None


class TestPostAttachmentsWriteResult:
    # criterio: 03-C29
    def test_from_dict(self) -> None:
        result = PostAttachmentsWriteResult.from_dict(
            load_payload("edit_post_attachments_response.json")
        )
        assert result.post_id == _POST_ID
        assert [a.id for a in result.added] == [_ADDED_ATTACHMENT_ID]
        assert result.updated == []
        assert result.removed_ids == [_REMOVED_ATTACHMENT_ID]

    def test_empty(self) -> None:
        result = PostAttachmentsWriteResult.from_dict({})
        assert result.added == []
        assert result.updated == []
        assert result.removed_ids == []


class TestWorkflowFacades:
    # criterio: 03-C29
    def test_screen(self) -> None:
        screen = WorkflowScreen.from_dict(load_payload("workflow_screen_response.json"))
        assert screen.screen_data == load_payload("workflow_screen_response.json")["screenData"]
        assert screen.screen_occ_token == _SCREEN_OCC_TOKEN
        assert screen.screen is not None
        assert screen.screen.name == "Approvazione"
        assert screen.current_workflow_state is not None
        assert screen.current_workflow_state.name == "In revisione"

    # criterio: 03-C29
    def test_operation_result(self) -> None:
        payload = load_payload("execute_workflow_operation_response.json")
        payload["newCurrentWorkflowPermittedOperations"] = [{"id": _OPERATION_ID, "name": "Riapri"}]
        result = WorkflowOperationResult.from_dict(payload)
        assert result.new_current_state is not None
        assert result.new_current_state.name == "Approvato"
        assert result.new_screen_data == {"5": "x", "6": 1}
        assert [op.id for op in result.new_permitted_operations] == [_OPERATION_ID]
        assert result.new_can_edit_workflow_screen_data is False
        assert result.post_data_has_changed is True

    # criterio: 03-C29
    def test_screen_write_result(self) -> None:
        result = WorkflowScreenWriteResult.from_dict(
            load_payload("edit_workflow_screen_response.json")
        )
        assert result.next_screen_occ_token == _NEXT_SCREEN_OCC_TOKEN
        assert result.new_screen_data == {"5": "x", "6": 1}
        assert result.post_data_has_changed is False

    @pytest.mark.parametrize("cls", [WorkflowScreen, WorkflowOperationResult])
    def test_empty_workflow_payloads(self, cls: type) -> None:
        facade = cls.from_dict({})  # type: ignore[attr-defined]
        assert facade.raw is not None
        if isinstance(facade, WorkflowScreen):
            assert facade.screen is None
            assert facade.current_workflow_state is None
        else:
            assert facade.new_current_state is None
            assert facade.new_permitted_operations == []
