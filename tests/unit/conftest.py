# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures for unit tests."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner with mix_stderr=False for separate capture."""
    return CliRunner()
