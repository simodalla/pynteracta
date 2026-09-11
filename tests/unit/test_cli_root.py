# SPDX-License-Identifier: Apache-2.0
"""Tests for root-level CLI options."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from pynteracta import __version__
from pynteracta.cli import app


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
