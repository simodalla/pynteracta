import json

import pytest

from pynteracta.api import InteractaApi
from pynteracta.exceptions import InteractaResponseError
from pynteracta.schemas.models import PostComment
from pynteracta.schemas.requests import CreateCustomPostIn, CreatePostCommentIn
from pynteracta.schemas.responses import (
    ListPostCommentsOut,
)

from .conftest import IntegrationTestData

pytestmark = pytest.mark.integration


def test_list_comment_post(logged_api: InteractaApi, integrations_data: IntegrationTestData):
    titolo = "test-123"
    data = CreateCustomPostIn(
        title=titolo,
        custom_data=integrations_data.comments.default_custom_data,
    )
    post_created = logged_api.create_post(
        community_id=integrations_data.comments.community_id,
        data=data,
    )

    list_comments = logged_api.list_comment_post(post_id=post_created.post_id)

    assert isinstance(list_comments, ListPostCommentsOut)
    assert len(list_comments.items) == 0

    text_comment = "Commento di test"

    data = CreatePostCommentIn(comment=json.dumps([{"insert": text_comment}]))
    result_create_comment = logged_api.create_comment_post(post_id=post_created.post_id, data=data)
    assert text_comment == result_create_comment.comment.comment_plain_text
    assert text_comment in result_create_comment.comment.comment_delta

    list_comments = logged_api.list_comment_post(post_id=post_created.post_id)
    assert isinstance(list_comments, ListPostCommentsOut)
    assert len(list_comments.items) == 1
    assert isinstance(list_comments.items[0], PostComment)
    assert result_create_comment.comment.id == list_comments.items[0].id

    with pytest.raises(InteractaResponseError):
        logged_api.delete_comment_post(comment_id=list_comments.items[0].id)

    logged_api.delete_post(post_created.post_id)
