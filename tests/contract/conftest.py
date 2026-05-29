# SPDX-License-Identifier: Apache-2.0
"""Contract test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SWAGGER_PATH = FIXTURES_DIR / "swagger.json"
PAYLOADS_DIR = FIXTURES_DIR / "payloads"


@pytest.fixture(scope="session")
def swagger() -> dict:  # type: ignore[type-arg]
    """Load the pinned Swagger 2.0 snapshot from tests/fixtures/swagger.json."""
    return json.loads(SWAGGER_PATH.read_bytes())


@pytest.fixture(scope="session")
def swagger_definitions(swagger: dict) -> dict:  # type: ignore[type-arg]
    """Return the ``definitions`` section of the pinned Swagger snapshot."""
    return swagger["definitions"]


def load_payload(filename: str) -> dict:  # type: ignore[type-arg]
    """Load a JSON payload fixture by filename.

    Args:
        filename: Filename relative to ``tests/fixtures/payloads/``.

    Returns:
        Parsed JSON dict.
    """
    return json.loads((PAYLOADS_DIR / filename).read_bytes())
