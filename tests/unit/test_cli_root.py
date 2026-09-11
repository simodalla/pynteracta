# SPDX-License-Identifier: Apache-2.0
"""Tests for root-level CLI options."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pynteracta import __version__
from pynteracta.cli import app
from pynteracta.cli._common import EXIT_CONFIG


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestVersionFlag:
    def test_long_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0, result.output
        assert result.output.strip() == f"pynteracta {__version__}"

    def test_short_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0, result.output
        assert __version__ in result.output

    def test_eager_wins_over_missing_command(self, runner: CliRunner) -> None:
        """--version exits before the 'missing command' handling kicks in."""
        result = runner.invoke(app, ["--version", "--profile", "does-not-exist"])
        assert result.exit_code == 0, result.output
        assert __version__ in result.output


def _root_level() -> int:
    return logging.getLogger("pynteracta").level


class TestLogLevelResolution:
    """--log-level > PYNTERACTA_LOG_LEVEL / profile log_level > INFO."""

    @pytest.fixture
    def config_file(self, tmp_path: Path) -> Path:
        cfg = tmp_path / "config.toml"
        cfg.write_text(
            'current_profile = "default"\n\n[profiles.default]\n'
            'base_url = "https://interacta.example.it"\nlog_level = "DEBUG"\n',
            encoding="utf-8",
        )
        return cfg

    def test_profile_log_level_is_honoured(self, runner: CliRunner, config_file: Path) -> None:
        result = runner.invoke(app, ["--config-file", str(config_file), "config", "list"])
        assert result.exit_code == 0, result.output
        assert _root_level() == logging.DEBUG

    def test_flag_overrides_profile(self, runner: CliRunner, config_file: Path) -> None:
        result = runner.invoke(
            app, ["--config-file", str(config_file), "--log-level", "warning", "config", "list"]
        )
        assert result.exit_code == 0, result.output
        assert _root_level() == logging.WARNING

    def test_env_overrides_profile(
        self, runner: CliRunner, config_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_LOG_LEVEL", "ERROR")
        result = runner.invoke(app, ["--config-file", str(config_file), "config", "list"])
        assert result.exit_code == 0, result.output
        assert _root_level() == logging.ERROR

    def test_default_is_info_without_profile(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["--config-file", str(tmp_path / "missing.toml"), "config", "list"]
        )
        assert result.exit_code == 0, result.output
        assert _root_level() == logging.INFO

    def test_invalid_flag_value_exits_config(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--log-level", "verbose", "config", "list"])
        assert result.exit_code == EXIT_CONFIG
        assert "Invalid --log-level" in result.output
