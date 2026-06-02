# SPDX-License-Identifier: Apache-2.0
"""Tests for hooks.py — dataclasses and ClientHooks Protocol."""

from __future__ import annotations

import inspect

from pynteracta.hooks import ClientHooks, RequestInfo, ResponseInfo


class _RecordingHooks:
    def __init__(self) -> None:
        self.requests: list[RequestInfo] = []
        self.responses: list[ResponseInfo] = []
        self.errors: list[BaseException] = []

    def on_request(self, req: RequestInfo) -> None:
        self.requests.append(req)

    def on_response(self, resp: ResponseInfo) -> None:
        self.responses.append(resp)

    def on_error(self, exc: BaseException) -> None:
        self.errors.append(exc)


def test_recording_hooks_satisfies_protocol() -> None:
    assert isinstance(_RecordingHooks(), ClientHooks)


def test_request_info_frozen() -> None:
    req = RequestInfo(method="GET", url="https://example.com", headers={"User-Agent": "x"})
    try:
        req.method = "POST"  # type: ignore[misc]
        raise AssertionError("should have raised")
    except AttributeError:
        pass


def test_request_info_body_defaults_none() -> None:
    req = RequestInfo(method="GET", url="https://example.com", headers={})
    assert req.body is None


def test_request_info_body_stored() -> None:
    req = RequestInfo(method="POST", url="https://example.com", headers={}, body={"key": "val"})
    assert req.body == {"key": "val"}


def test_response_info_frozen() -> None:
    resp = ResponseInfo(
        status_code=200,
        url="https://example.com",
        headers={},
        elapsed_ms=42.0,
        request_id=None,
    )
    try:
        resp.status_code = 404  # type: ignore[misc]
        raise AssertionError("should have raised")
    except AttributeError:
        pass


def test_response_info_body_defaults_none() -> None:
    resp = ResponseInfo(
        status_code=200,
        url="https://example.com",
        headers={},
        elapsed_ms=10.0,
        request_id=None,
    )
    assert resp.body is None


def test_response_info_body_stored() -> None:
    resp = ResponseInfo(
        status_code=200,
        url="https://example.com",
        headers={},
        elapsed_ms=10.0,
        request_id="req-1",
        body={"result": "ok"},
    )
    assert resp.body == {"result": "ok"}


def test_request_info_no_httpx_types() -> None:
    sig = inspect.signature(RequestInfo)
    for param in sig.parameters.values():
        ann = param.annotation
        if ann is not inspect.Parameter.empty:
            assert "httpx" not in repr(ann), f"httpx leaked into RequestInfo.{param.name}"


def test_response_info_no_httpx_types() -> None:
    sig = inspect.signature(ResponseInfo)
    for param in sig.parameters.values():
        ann = param.annotation
        if ann is not inspect.Parameter.empty:
            assert "httpx" not in repr(ann), f"httpx leaked into ResponseInfo.{param.name}"
