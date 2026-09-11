# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'posts' command group."""

from __future__ import annotations

import json
from typing import ClassVar

import httpx
import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_STREAM_BASE = "https://api.example.com/portal/api/external/v2/communication/posts/data"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}

_EPOCH_2025_01_01 = 1735689600000
_EPOCH_2025_01_02 = 1735776000000


class TestPostsGet:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(app, ["posts", "get", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(app, ["--output", "json", "posts", "get", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_with_web_url(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(app, ["posts", "get", "21269", "--web-url"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "web_url" in result.output or "/post/21269" in result.output

    @respx.mock
    def test_without_web_url(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-id/21269",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(app, ["posts", "get", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "/post/21269" not in result.output


class TestPostsList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(app, ["posts", "list", "--community", "79"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/list/community/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "posts", "list", "--community", "79"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot


class TestPostsListFilters:
    """Tests for the new filter/sort flags on `posts list`."""

    _LIST_URL = "communication/posts/data/list/community/79"
    _PAYLOAD: ClassVar[dict] = {
        "items": [{"id": 1, "communityId": 79, "title": "T"}],
        "nextPageToken": None,
    }

    @respx.mock
    def test_order_by_flag(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--order-by",
                "postLastModifyTimestamp",
                "--desc",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["orderBy"] == "postLastModifyTimestamp"
        assert body["orderDesc"] is True

    @respx.mock
    def test_asc_flag(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--order-by", "postTitle", "--asc"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["orderDesc"] is False

    @respx.mock
    def test_pinned_first_flag(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app, ["posts", "list", "--community", "79", "--pinned-first"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["pinnedFirst"] is True

    @respx.mock
    def test_title_filter(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app, ["posts", "list", "--community", "79", "--title", "Report"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["communityPostFilters"]["title"] == "Report"

    @respx.mock
    def test_post_type_repeatable(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--post-type", "1", "--post-type", "2"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["communityPostFilters"]["postTypes"] == [1, 2]

    @respx.mock
    def test_field_filter_in(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--field-filter", "1411:4:226,512"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        pff = body["communityPostFilters"]["postFieldFilters"]
        assert pff[0] == {"columnId": 1411, "typeId": 4, "parameters": [226, 512]}

    @respx.mock
    def test_field_filter_like_string(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--field-filter", "1957:3:aaa"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        pff = body["communityPostFilters"]["postFieldFilters"]
        assert pff[0] == {"columnId": 1957, "typeId": 3, "parameters": ["aaa"]}

    @respx.mock
    def test_field_filter_interval(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--field-filter",
                "1954:2:1780264800000,1780955999999",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        pff = body["communityPostFilters"]["postFieldFilters"]
        assert pff[0]["parameters"] == [1780264800000, 1780955999999]

    def test_field_filter_bad_format(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--field-filter", "bad"],
            env=BASE_ENV,
        )
        assert result.exit_code != 0

    @respx.mock
    def test_screen_field_filter_forwarded(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--screen-field-filter", "2001:1:7"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        cpf = body["communityPostFilters"]
        assert cpf["screenFieldFilters"] == [{"columnId": 2001, "typeId": 1, "parameters": [7]}]
        assert not cpf.get("postFieldFilters")

    @respx.mock
    def test_screen_field_filter_repeatable_and_string_tokens(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--screen-field-filter",
                "2001:4:7,9",
                "--screen-field-filter",
                "2002:3:draft",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        sff = body["communityPostFilters"]["screenFieldFilters"]
        assert sff == [
            {"columnId": 2001, "typeId": 4, "parameters": [7, 9]},
            {"columnId": 2002, "typeId": 3, "parameters": ["draft"]},
        ]

    @respx.mock
    def test_screen_and_post_field_filters_combined(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--field-filter",
                "1411:4:226,512",
                "--screen-field-filter",
                "2001:1:7",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        cpf = body["communityPostFilters"]
        assert cpf["postFieldFilters"] == [
            {"columnId": 1411, "typeId": 4, "parameters": [226, 512]}
        ]
        assert cpf["screenFieldFilters"] == [{"columnId": 2001, "typeId": 1, "parameters": [7]}]

    @pytest.mark.parametrize("bad", ["bad", "2001:x:7", "2001:1"])
    def test_screen_field_filter_bad_format(self, runner: CliRunner, bad: str) -> None:
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--screen-field-filter", bad],
            env=BASE_ENV,
        )
        assert result.exit_code == 1
        assert "--screen-field-filter" in result.output

    @respx.mock
    def test_remaining_curated_flags_land_on_cpf(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--description",
                "quarterly",
                "--created-by-group",
                "12",
                "--created-by-group",
                "13",
                "--modified-from",
                "2025-01-01T00:00:00+00:00",
                "--modified-to",
                "1735776000000",
                "--hashtag",
                "3",
                "--hashtags-and",
                "--visibility",
                "1",
                "--mentioned",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        cpf = json.loads(route.calls[0].request.content)["communityPostFilters"]
        assert cpf["description"] == "quarterly"
        assert cpf["createdByGroupIds"] == [12, 13]
        assert cpf["modifiedTimestampFrom"] == _EPOCH_2025_01_01
        assert cpf["modifiedTimestampTo"] == _EPOCH_2025_01_02
        assert cpf["hashtagsLogicalAnd"] is True
        assert cpf["visibility"] == 1
        assert cpf["mentioned"] is True

    @respx.mock
    def test_negated_bool_flags(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--no-mentioned", "--no-hashtags-and"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        cpf = json.loads(route.calls[0].request.content)["communityPostFilters"]
        assert cpf["mentioned"] is False
        assert cpf["hashtagsLogicalAnd"] is False

    @respx.mock
    def test_generic_filter_passthrough(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--filter", "containsText=hello"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["communityPostFilters"]["containsText"] == "hello"

    @respx.mock
    def test_order_desc_always_sent(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(app, ["posts", "list", "--community", "79"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["orderDesc"] is True
        assert body["orderBy"] == "postLastModifyAndCommentTimestamp"

    @respx.mock
    def test_asc_without_order_by(self, runner: CliRunner) -> None:
        route = mock_json("POST", self._LIST_URL, self._PAYLOAD)
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--asc"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        body = json.loads(route.calls[0].request.content)
        assert body["orderDesc"] is False
        assert body["orderBy"] == "postLastModifyAndCommentTimestamp"


class TestPostsComments:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/comments-list/21269",
            load_payload("list_post_comments_response.json"),
        )
        result = runner.invoke(app, ["posts", "comments", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot


class TestPostsGetByClientUid:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-client-uid/uid-abc",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(app, ["posts", "get-by-client-uid", "uid-abc"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-client-uid/uid-abc",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "posts", "get-by-client-uid", "uid-abc"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_with_web_url(self, runner: CliRunner) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-detail-by-client-uid/uid-abc",
            load_payload("get_post_detail_response.json"),
        )
        result = runner.invoke(
            app, ["posts", "get-by-client-uid", "uid-abc", "--web-url"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "web_url" in result.output or "/post/" in result.output


class TestPostsCapabilities:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-capabilities/21269",
            load_payload("get_post_capabilities_response.json"),
        )
        result = runner.invoke(app, ["posts", "capabilities", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/post-capabilities/21269",
            load_payload("get_post_capabilities_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "posts", "capabilities", "21269"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert result.output == snapshot


class TestPostsHistory:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/history-list/21269",
            load_payload("list_post_history_response.json"),
        )
        result = runner.invoke(app, ["posts", "history", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/history-list/21269",
            load_payload("list_post_history_response.json"),
        )
        result = runner.invoke(app, ["--output", "json", "posts", "history", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_all_pages(self, runner: CliRunner) -> None:
        page1 = {
            "items": [{"id": 1, "typeId": 1, "typeDescription": "C", "timestamp": 1000}],
            "nextPageToken": "t2",
        }
        page2 = {
            "items": [{"id": 2, "typeId": 2, "typeDescription": "M", "timestamp": 2000}],
            "nextPageToken": None,
        }
        respx.post(f"{_STREAM_BASE}/history-list/21269").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        result = runner.invoke(app, ["posts", "history", "21269", "--all"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "1" in result.output
        assert "2" in result.output


class TestPostsGlobalStream:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/global-stream",
            load_payload("global_stream_response.json"),
        )
        result = runner.invoke(app, ["posts", "global-stream"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/global-stream",
            load_payload("global_stream_response.json"),
        )
        result = runner.invoke(app, ["--output", "json", "posts", "global-stream"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_all_pages(self, runner: CliRunner) -> None:
        page1 = {
            "items": [{"id": 1, "communityId": 79, "title": "A"}],
            "nextPageToken": "t2",
        }
        page2 = {
            "items": [{"id": 2, "communityId": 79, "title": "B"}],
            "nextPageToken": None,
        }
        respx.post(f"{_STREAM_BASE}/global-stream").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        result = runner.invoke(app, ["posts", "global-stream", "--all"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "A" in result.output
        assert "B" in result.output


class TestPostsCommunityList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/community-list/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(app, ["posts", "community-list", "--community", "79"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/community-list/79",
            load_payload("list_community_posts_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "community-list", "--community", "79"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_all_pages(self, runner: CliRunner) -> None:
        page1 = {
            "items": [{"id": 10, "communityId": 79, "title": "P1"}],
            "nextPageToken": "t2",
        }
        page2 = {
            "items": [{"id": 11, "communityId": 79, "title": "P2"}],
            "nextPageToken": None,
        }
        respx.post(f"{_STREAM_BASE}/community-list/79").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        result = runner.invoke(
            app, ["posts", "community-list", "--community", "79", "--all"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "P1" in result.output
        assert "P2" in result.output


class TestPostsCheckVisibility:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/check-visibility",
            load_payload("check_visibility_response.json"),
        )
        result = runner.invoke(app, ["posts", "check-visibility", "21269", "21270"], env=BASE_ENV)
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/posts/data/check-visibility",
            load_payload("check_visibility_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "posts", "check-visibility", "21269", "21270"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert result.output == snapshot

    @respx.mock
    def test_with_comments(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/posts/data/check-visibility-with-comments",
            load_payload("check_visibility_response.json"),
        )
        result = runner.invoke(
            app,
            ["posts", "check-visibility", "21269", "--with-comments"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
