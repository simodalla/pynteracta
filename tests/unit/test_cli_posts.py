# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'posts' command group."""

from __future__ import annotations

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
