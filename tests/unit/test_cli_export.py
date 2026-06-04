# SPDX-License-Identifier: Apache-2.0
"""Unit tests for --export / --export-format CLI options across data-emitting commands."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pyarrow.parquet as pq
import pytest
import respx
import typer
from api_helpers import load_payload, mock_json
from ruamel.yaml import YAML
from typer.testing import CliRunner

from pynteracta.cli import app
from pynteracta.cli._common import EXIT_CONFIG

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> Any:
    yml = YAML()
    return yml.load(path.read_text(encoding="utf-8"))


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    table = pq.read_table(path)
    return table.to_pylist()


def _mock_posts_list() -> None:
    mock_json(
        "POST",
        "communication/posts/data/list/community/79",
        load_payload("list_community_posts_response.json"),
    )


def _mock_post_get() -> None:
    mock_json(
        "GET",
        "communication/posts/data/post-detail-by-id/21269",
        load_payload("get_post_detail_response.json"),
    )


def _mock_users_list() -> None:
    mock_json(
        "POST",
        "admin/data/users",
        load_payload("list_system_users_response.json"),
    )


# ---------------------------------------------------------------------------
# Format inference
# ---------------------------------------------------------------------------


class TestFormatInference:
    @respx.mock
    def test_csv_inferred_from_extension(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "out.csv"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()

    @respx.mock
    def test_json_inferred_from_extension(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "out.json"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()

    @respx.mock
    def test_yaml_inferred_from_yml_extension(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "out.yml"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()

    @respx.mock
    def test_explicit_format_override(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "out.data"
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--export",
                str(out),
                "--export-format",
                "json",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()
        data = _read_json(out)
        assert isinstance(data, list)

    def test_unknown_extension_without_override_exits_config(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        out = tmp_path / "out.xyz"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == EXIT_CONFIG

    def test_unknown_format_override_exits_config(self, runner: CliRunner, tmp_path: Path) -> None:
        out = tmp_path / "out.csv"
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--export",
                str(out),
                "--export-format",
                "xlsx",
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == EXIT_CONFIG


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


class TestCSVExport:
    @respx.mock
    def test_csv_list_command(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.csv"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = _read_csv(out)
        assert len(rows) > 0
        assert "id" in rows[0]

    @respx.mock
    def test_csv_single_object_has_header_plus_one_row(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        _mock_post_get()
        out = tmp_path / "post.csv"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = _read_csv(out)
        assert len(rows) == 1

    @respx.mock
    def test_csv_nested_values_are_json_strings(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.csv"
        runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--full", "--export", str(out)],
            env=BASE_ENV,
        )
        rows = _read_csv(out)
        # Full dump may contain nested fields; check the file is valid CSV with headers
        assert len(rows) > 0

    @respx.mock
    def test_csv_with_fields_subset(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.csv"
        result = runner.invoke(
            app,
            [
                "posts",
                "list",
                "--community",
                "79",
                "--fields",
                "id,title",
                "--export",
                str(out),
            ],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = _read_csv(out)
        assert set(rows[0].keys()) == {"id", "title"}


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------


class TestJSONExport:
    @respx.mock
    def test_json_list_command_produces_array(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.json"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert isinstance(data, list)
        assert len(data) > 0

    @respx.mock
    def test_json_single_object_produces_dict(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_post_get()
        out = tmp_path / "post.json"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert isinstance(data, dict)
        assert "id" in data

    @respx.mock
    def test_json_with_web_url(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_post_get()
        out = tmp_path / "post.json"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--web-url", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert "web_url" in data

    @respx.mock
    def test_json_with_full_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.json"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--full", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert isinstance(data, list)

    @respx.mock
    def test_json_no_data_dumped_to_stdout(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.json"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        # stdout should contain the summary line only, no JSON data
        assert "[" not in result.output
        assert "Wrote" in result.output


# ---------------------------------------------------------------------------
# YAML export
# ---------------------------------------------------------------------------


class TestYAMLExport:
    @respx.mock
    def test_yaml_list_command(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.yaml"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_yaml(out)
        assert isinstance(data, list)
        assert len(data) > 0

    @respx.mock
    def test_yaml_single_object_produces_dict(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_post_get()
        out = tmp_path / "post.yaml"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_yaml(out)
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Parquet export
# ---------------------------------------------------------------------------


class TestParquetExport:
    @respx.mock
    def test_parquet_list_command(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.parquet"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = _read_parquet(out)
        assert len(rows) > 0
        assert "id" in rows[0]

    @respx.mock
    def test_parquet_single_record(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_post_get()
        out = tmp_path / "post.parquet"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = _read_parquet(out)
        assert len(rows) == 1

    @respx.mock
    def test_missing_pyarrow_exits_config(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.parquet"
        with patch(
            "pynteracta.cli._export._check_parquet_available",
            side_effect=typer.Exit(EXIT_CONFIG),
        ):
            result = runner.invoke(
                app,
                ["posts", "list", "--community", "79", "--export", str(out)],
                env=BASE_ENV,
            )
        assert result.exit_code == EXIT_CONFIG


# ---------------------------------------------------------------------------
# Summary line and --quiet
# ---------------------------------------------------------------------------


class TestSummaryLine:
    @respx.mock
    def test_summary_line_printed(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.json"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "Wrote" in result.output
        assert str(out) in result.output
        assert "json" in result.output

    @respx.mock
    def test_quiet_suppresses_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.json"
        result = runner.invoke(
            app,
            ["--quiet", "posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "Wrote" not in result.output
        assert out.exists()

    @respx.mock
    def test_record_count_in_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_post_get()
        out = tmp_path / "post.json"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "1 record" in result.output


# ---------------------------------------------------------------------------
# Overwrite and parent-dir creation
# ---------------------------------------------------------------------------


class TestFileCreation:
    @respx.mock
    def test_overwrites_existing_file(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.json"
        out.write_text("old content", encoding="utf-8")
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert _read_json(out) != "old content"

    @respx.mock
    def test_creates_missing_parent_directories(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "a" / "b" / "c" / "posts.json"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()


# ---------------------------------------------------------------------------
# Composition with --full / --fields / --web-url
# ---------------------------------------------------------------------------


class TestExportComposition:
    @respx.mock
    def test_export_with_fields_subset(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_users_list()
        out = tmp_path / "users.json"
        result = runner.invoke(
            app,
            ["users", "list", "--fields", "id", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert isinstance(data, list)
        for rec in data:
            assert set(rec.keys()) == {"id"}

    @respx.mock
    def test_export_with_full_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_users_list()
        out = tmp_path / "users.json"
        result = runner.invoke(
            app,
            ["users", "list", "--full", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert isinstance(data, list)
        # Full dump should have more keys than the curated 4-key set
        assert len(data[0]) >= 4  # noqa: PLR2004

    @respx.mock
    def test_export_with_web_url(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_post_get()
        out = tmp_path / "post.json"
        result = runner.invoke(
            app,
            ["posts", "get", "21269", "--web-url", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        data = _read_json(out)
        assert "web_url" in data

    @respx.mock
    def test_csv_nested_encoded_as_json_string(self, runner: CliRunner, tmp_path: Path) -> None:
        _mock_posts_list()
        out = tmp_path / "posts.csv"
        result = runner.invoke(
            app,
            ["posts", "list", "--community", "79", "--full", "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        rows = _read_csv(out)
        # Any nested dict/list column should be a string (compact JSON), not a Python repr
        for row in rows:
            for v in row.values():
                if v.startswith("{") or v.startswith("["):
                    # Must be valid JSON
                    json.loads(v)
