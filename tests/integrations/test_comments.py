from devtools import debug  # noqa

from pynteracta.api import InteractaApi
from pynteracta.exceptions import InteractaResponseError
from pynteracta.schemas.responses import (
    ListPostCommentsOut,
)
from .conftest import IntegrationTestData
from pynteracta.schemas.requests import CreateCustomPostIn, CreatePostCommentIn
import json

import pytest


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

    data = CreatePostCommentIn(comment=json.dumps([{"insert": "Commento di test"}]))
    result_crate_comment = logged_api.create_comment_post(post_id=post_created.post_id, data=data)

    debug(result_crate_comment)

    list_comments = logged_api.list_comment_post(post_id=post_created.post_id)
    debug(list_comments)
    assert isinstance(list_comments, ListPostCommentsOut)
    assert len(list_comments.items) == 1

    with pytest.raises(InteractaResponseError):
        logged_api.delete_comment_post(comment_id=list_comments.items[0].id)

    logged_api.delete_post(post_created.post_id)
