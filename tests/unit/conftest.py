# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures for unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point config loading at an isolated, non-existent file.

    Without this, any test that resolves a profile without an explicit ``--config-file`` reads
    the developer's real ``user_config_dir("pynteracta")/config.toml`` (e.g. a ``default``
    profile carrying a ``service_account_key``), which pollutes the run. Tests that pass
    ``--config-file`` are unaffected (flag/path takes precedence over the env var).
    """
    monkeypatch.setenv("PYNTERACTA_CONFIG_FILE", str(tmp_path / "isolated_config.toml"))


@pytest.fixture(autouse=True)
def _no_forced_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise terminal colour forcing so CLI snapshots are environment-independent.

    Some shells and agent harnesses export ``FORCE_COLOR`` (or ``CLICOLOR_FORCE``), which makes
    Rich emit ANSI escapes inside ``CliRunner`` output and breaks every snapshot test.

    ``GITHUB_ACTIONS`` needs the same treatment: Rich treats it as a CI environment that supports
    colour and emits escapes regardless of ``NO_COLOR``, which splits an option name into
    per-segment styles (``--web-url`` becomes ``ESC[1;36m-ESC[0mESC[1;36m-webESC[0m…``) and breaks
    substring assertions on ``--help`` output.
    """
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("CLICOLOR_FORCE", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner with mix_stderr=False for separate capture."""
    return CliRunner()
