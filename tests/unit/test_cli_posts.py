# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'posts' command group."""

from __future__ import annotations

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app


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
