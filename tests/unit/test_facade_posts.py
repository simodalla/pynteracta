# SPDX-License-Identifier: Apache-2.0
"""Tests for new M15 post facade classes."""

from __future__ import annotations

import json
from pathlib import Path

from pynteracta.models.facade.posts import (
    GlobalPostStream,
    PostCapabilities,
    PostHistoryEventList,
    VisibilityResult,
)

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "payloads"

_POST_ID = 21269
_POST_ID2 = 21270
_HISTORY_COUNT = 2
_TYPE_CREATED = 1
_TYPE_MODIFIED = 2


def load(name: str) -> dict:  # type: ignore[type-arg]
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


class TestPostCapabilities:
    def test_from_dict(self) -> None:
        data = load("get_post_capabilities_response.json")
        caps = PostCapabilities.from_dict(data)
        assert caps.can_view_detail is True
        assert caps.can_modify is False
        assert caps.can_delete is False
        assert caps.can_view_comment is True
        assert caps.can_add_comment is True
        assert caps.can_edit_like is True
        assert caps.can_edit_follow is True
        assert caps.raw.canEditComment == 1

    def test_raw_escape_hatch(self) -> None:
        data = load("get_post_capabilities_response.json")
        caps = PostCapabilities.from_dict(data)
        assert caps.raw.canEditWorkflowScreenData is False


class TestPostHistoryEventList:
    def test_from_dict(self) -> None:
        data = load("list_post_history_response.json")
        history = PostHistoryEventList.from_dict(data)
        assert history.next_page_token is None
        assert history.total_items_count == _HISTORY_COUNT
        items = history.items_typed
        assert len(items) == _HISTORY_COUNT
        assert items[0].typeId == _TYPE_CREATED
        assert items[0].typeDescription == "Creato post"
        assert items[1].typeId == _TYPE_MODIFIED

    def test_raw_escape_hatch(self) -> None:
        data = load("list_post_history_response.json")
        history = PostHistoryEventList.from_dict(data)
        assert history.raw.totalItemsCount == _HISTORY_COUNT


class TestVisibilityResult:
    def test_from_dict(self) -> None:
        data = load("check_visibility_response.json")
        result = VisibilityResult.from_dict(data)
        posts = result.posts_typed
        assert len(posts) == _HISTORY_COUNT
        assert posts[0].id == _POST_ID
        assert posts[0].canViewComments is True
        assert posts[1].id == _POST_ID2
        assert posts[1].canViewComments is False

    def test_empty_posts(self) -> None:
        result = VisibilityResult.from_dict({"posts": None})
        assert result.posts_typed == []

    def test_raw_escape_hatch(self) -> None:
        data = load("check_visibility_response.json")
        result = VisibilityResult.from_dict(data)
        assert result.raw.posts is not None


class TestGlobalPostStream:
    def test_from_dict(self) -> None:
        data = load("global_stream_response.json")
        stream = GlobalPostStream.from_dict(data)
        assert stream.next_page_token is None
        assert stream.next_sync_token == "sync_abc123"
        items = stream.items_typed
        assert len(items) == 1
        assert items[0].id == _POST_ID
        assert items[0].title == "Stream Post One"

    def test_empty_items(self) -> None:
        stream = GlobalPostStream.from_dict({"items": None, "nextSyncToken": None})
        assert stream.items_typed == []
