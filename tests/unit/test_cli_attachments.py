# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'attachments' command group."""

from __future__ import annotations

import pathlib

import httpx
import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_ATTACH_BASE = "https://api.example.com/portal/api/external/v2/communication/attachments/data"
_POSTS_BASE = "https://api.example.com/portal/api/external/v2/communication/posts/data"

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestAttachmentsList:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/posts/21269/attachments-list",
            load_payload("list_post_attachments_response.json"),
        )
        result = runner.invoke(app, ["attachments", "list", "--post", "21269"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/posts/21269/attachments-list",
            load_payload("list_post_attachments_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "attachments", "list", "--post", "21269"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_table_excludes_temporary_links(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/posts/21269/attachments-list",
            load_payload("list_post_attachments_response.json"),
        )
        result = runner.invoke(app, ["attachments", "list", "--post", "21269"], env=BASE_ENV)
        assert result.exit_code == 0
        assert "temporaryContent" not in result.output
        assert "token=" not in result.output

    @respx.mock
    def test_full_includes_temporary_links(self, runner: CliRunner) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/posts/21269/attachments-list",
            load_payload("list_post_attachments_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "attachments", "list", "--post", "21269", "--full"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        has_link = (
            "temporaryContentViewLink" in result.output
            or "temporary_content_view_link" in result.output
        )
        assert has_link

    @respx.mock
    def test_all_pages(self, runner: CliRunner) -> None:
        page1 = {
            "items": [
                {
                    "id": 3001,
                    "name": "a.pdf",
                    "contentMimeType": "application/pdf",
                    "size": 100,
                    "type": 1,
                },
            ],
            "nextPageToken": "tok",
            "totalItemsCount": 2,
        }
        page2 = {
            "items": [
                {
                    "id": 3002,
                    "name": "b.jpg",
                    "contentMimeType": "image/jpeg",
                    "size": 200,
                    "type": 1,
                },
            ],
            "nextPageToken": None,
            "totalItemsCount": 2,
        }
        respx.post(f"{_ATTACH_BASE}/posts/21269/attachments-list").mock(
            side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)]
        )
        result = runner.invoke(
            app, ["attachments", "list", "--post", "21269", "--all"], env=BASE_ENV
        )
        assert result.exit_code == 0
        assert "a.pdf" in result.output
        assert "b.jpg" in result.output

    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/posts/21269/attachments-list",
            load_payload("list_post_attachments_response.json"),
        )
        out = pathlib.Path(str(tmp_path)) / "out.csv"
        result = runner.invoke(
            app,
            ["attachments", "list", "--post", "21269", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "report.pdf" in content
        # temporary links must NOT appear in default export (curated cols only)
        assert "temporaryContent" not in content


class TestAttachmentsGet:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/attachment-detail-by-id/3001",
            load_payload("get_attachment_detail_response.json"),
        )
        result = runner.invoke(app, ["attachments", "get", "3001"], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "GET",
            "communication/posts/data/attachment-detail-by-id/3001",
            load_payload("get_attachment_detail_response.json"),
        )
        result = runner.invoke(
            app, ["--output", "json", "attachments", "get", "3001"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    def test_no_web_url_option(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["attachments", "get", "--help"], env=BASE_ENV)
        assert "--web-url" not in result.output


class TestAttachmentsCheckVisibility:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/check-visibility",
            load_payload("check_attachment_visibility_response.json"),
        )
        result = runner.invoke(
            app, ["attachments", "check-visibility", "3001", "3002"], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json(
            "POST",
            "communication/attachments/data/check-visibility",
            load_payload("check_attachment_visibility_response.json"),
        )
        result = runner.invoke(
            app,
            ["--output", "json", "attachments", "check-visibility", "3001", "3002"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot
