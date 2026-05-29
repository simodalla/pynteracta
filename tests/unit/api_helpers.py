# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for API unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from pynteracta.transport import HttpTransport

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "payloads"
BASE_URL = "https://api.example.com/portal/api/external/v2"
FAKE_JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"


def load_payload(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


def make_transport(**kwargs: object) -> HttpTransport:
    defaults: dict[str, object] = {
        "base_url": BASE_URL,
        "token_provider": lambda: FAKE_JWT,
    }
    defaults.update(kwargs)
    return HttpTransport(**defaults)  # type: ignore[arg-type]


def full_url(path: str) -> str:
    return f"{BASE_URL}/{path.lstrip('/')}"


def mock_json(method: str, path: str, payload: dict, *, status: int = 200) -> respx.Route:
    url = full_url(path)
    return getattr(respx, method.lower())(url).mock(  # type: ignore[attr-defined]
        return_value=httpx.Response(status, json=payload),
    )
