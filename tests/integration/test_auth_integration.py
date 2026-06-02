# SPDX-License-Identifier: Apache-2.0
"""Opt-in integration tests against a real Interacta tenant."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pynteracta.auth import (
    GoogleOAuth2Credentials,
    GoogleOAuth2TokenManager,
    MemoryTokenCache,
    TokenManager,
    load_service_account_key,
)
from pynteracta.transport import HttpTransport
from pynteracta.urls import build_api_base

pytestmark = pytest.mark.integration


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


@pytest.fixture
def sa_key():
    path = Path(_require_env("PYNTERACTA_SERVICE_ACCOUNT_KEY"))
    if not path.exists():
        pytest.skip(f"Service account key not found: {path}")
    return load_service_account_key(path)


@pytest.fixture
def api_base() -> str:
    base_url = _require_env("PYNTERACTA_BASE_URL")
    base_path = os.environ.get("PYNTERACTA_BASE_PATH", "/portal")
    api_version = int(os.environ.get("PYNTERACTA_API_VERSION", "2"))
    return build_api_base(base_url, base_path, api_version)


def test_service_account_authentication(api_base: str, sa_key) -> None:
    """Manual integration check: obtain a real access token from the cert tenant."""
    transport = HttpTransport(base_url=api_base)
    cache = MemoryTokenCache()
    manager = TokenManager(key=sa_key, cache=cache, transport=transport)
    token = manager.get_token()
    assert token
    assert len(token.split(".")) == 3  # noqa: PLR2004 — JWT has three segments


def test_google_oauth2_authentication(api_base: str) -> None:
    """Manual integration check: exchange a real Google access token for an Interacta token."""
    google_token = _require_env("PYNTERACTA_GOOGLE_OAUTH2_TOKEN")
    base_url = _require_env("PYNTERACTA_BASE_URL")
    base_path = os.environ.get("PYNTERACTA_BASE_PATH", "/portal")
    google_auth_base = f"{base_url.rstrip('/')}/{base_path.strip('/')}/api"
    transport = HttpTransport(base_url=google_auth_base)
    cache = MemoryTokenCache()
    manager = GoogleOAuth2TokenManager(
        GoogleOAuth2Credentials(token=google_token),
        cache,
        transport,
        cache_key="integration",
    )
    token = manager.get_token()
    assert token
    assert len(token.split(".")) == 3  # noqa: PLR2004 — JWT has three segments
