# SPDX-License-Identifier: Apache-2.0
"""CLI tests for the 'tasks' command group."""

from __future__ import annotations

import pathlib

import pytest
import respx
from api_helpers import load_payload, mock_json
from typer.testing import CliRunner

from pynteracta.cli import app

_TASK_ID = 7001
_POST_ID = 21269

BASE_ENV = {
    "PYNTERACTA_BASE_URL": "https://api.example.com",
}

_TASKS_GET_PATH = f"communication/tasks/data/task-detail-by-id/{_TASK_ID}"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestTasksGet:
    @respx.mock
    def test_table_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(app, ["tasks", "get", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_json_output(self, runner: CliRunner, snapshot: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(
            app, ["--output", "json", "tasks", "get", str(_TASK_ID)], env=BASE_ENV
        )
        assert result.exit_code == 0, result.output
        assert result.output == snapshot

    @respx.mock
    def test_full_includes_raw_fields(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(
            app, ["--output", "json", "tasks", "get", str(_TASK_ID), "--full"], env=BASE_ENV
        )
        assert result.exit_code == 0
        # full JSON exposes all facade properties
        assert "description_plain_text" in result.output or "description" in result.output

    @respx.mock
    def test_fields_option(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(
            app,
            ["tasks", "get", str(_TASK_ID), "--fields", "id,title,state"],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert "id" in result.output
        assert "title" in result.output

    @respx.mock
    def test_web_url_included(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(app, ["tasks", "get", str(_TASK_ID), "--web-url"], env=BASE_ENV)
        assert result.exit_code == 0
        assert f"/post/{_POST_ID}" in result.output

    @respx.mock
    def test_web_url_not_shown_by_default(self, runner: CliRunner) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        result = runner.invoke(app, ["tasks", "get", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == 0
        assert "/post/" not in result.output

    @respx.mock
    def test_export_csv(self, runner: CliRunner, tmp_path: object) -> None:
        mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
        out = pathlib.Path(str(tmp_path)) / "task.csv"
        result = runner.invoke(
            app,
            ["tasks", "get", str(_TASK_ID), "--export", str(out)],
            env=BASE_ENV,
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "Review quarterly report" in content

    def test_help_shows_web_url(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["tasks", "get", "--help"], env=BASE_ENV)
        assert "--web-url" in result.output

    def test_delta_not_in_default_table(self, runner: CliRunner) -> None:
        with respx.mock:
            mock_json("GET", _TASKS_GET_PATH, load_payload("get_task_detail_response.json"))
            result = runner.invoke(app, ["tasks", "get", str(_TASK_ID)], env=BASE_ENV)
        assert result.exit_code == 0
        assert "descriptionDelta" not in result.output
        assert "surveyData" not in result.output
