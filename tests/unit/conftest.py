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


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner with mix_stderr=False for separate capture."""
    return CliRunner()
