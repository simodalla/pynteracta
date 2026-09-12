# SPDX-License-Identifier: Apache-2.0
"""Tests for HttpTransport: error mapping, redaction, hooks, User-Agent, auth schemes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from structlog.testing import capture_logs

from pynteracta import __version__
from pynteracta.exceptions import (
    AuthenticationError,
    ConcurrencyError,
    CustomFieldValidationError,
    InteractaError,
    NotFoundError,
    ServerError,
    TransportError,
    ValidationError,
)
from pynteracta.exceptions import PermissionError as InteractaPermissionError
from pynteracta.hooks import RequestInfo, ResponseInfo
from pynteracta.transport import _DEFAULT_USER_AGENT, HttpTransport

_BASE = "https://api.example.com/portal/api/external/v2"
_PATH = "/core/auth/current-user-data"
_FULL_URL = f"{_BASE}{_PATH}"
_FAKE_JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
_REDACTED = "***REDACTED***"
_HTTP_200 = 200
_HTTP_404 = 404


def _make_transport(**kwargs: Any) -> HttpTransport:
    return HttpTransport(base_url=_BASE, **kwargs)


# ---------------------------------------------------------------------------
# Error mapping — parametrized by status code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "exc_class"),
    [
        (401, AuthenticationError),
        (403, InteractaPermissionError),
        (404, NotFoundError),
        (409, ConcurrencyError),
        (500, ServerError),
        (503, ServerError),
        (418, InteractaError),  # other 4xx → base InteractaError
        (422, InteractaError),
    ],
)
@respx.mock
def test_error_mapping_by_status(status: int, exc_class: type[InteractaError]) -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(status))
    with pytest.raises(exc_class):
        _make_transport().request("GET", _PATH)


@respx.mock
def test_400_with_validation_errors() -> None:
    body = {"validationErrors": [{"field": "x", "msg": "required"}]}
    respx.get(_FULL_URL).mock(return_value=httpx.Response(400, json=body))
    with pytest.raises(ValidationError) as exc_info:
        _make_transport().request("GET", _PATH)
    assert exc_info.value.errors == [{"field": "x", "msg": "required"}]
    assert not isinstance(exc_info.value, CustomFieldValidationError)


@respx.mock
def test_400_with_custom_field_validation_errors() -> None:
    body = {"customFieldValidationErrors": [{"fieldId": 1}]}
    respx.get(_FULL_URL).mock(return_value=httpx.Response(400, json=body))
    with pytest.raises(CustomFieldValidationError):
        _make_transport().request("GET", _PATH)


@respx.mock
def test_400_other() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(400, json={"detail": "bad"}))
    with pytest.raises(ValidationError) as exc_info:
        _make_transport().request("GET", _PATH)
    assert exc_info.value.errors == []


def test_timeout_maps_to_transport_error() -> None:
    with respx.mock:
        respx.get(_FULL_URL).mock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(TransportError):
            _make_transport().request("GET", _PATH)


def test_network_error_maps_to_transport_error() -> None:
    with respx.mock:
        respx.get(_FULL_URL).mock(side_effect=httpx.NetworkError("connection refused"))
        with pytest.raises(TransportError):
            _make_transport().request("GET", _PATH)


# ---------------------------------------------------------------------------
# Carried fields on exceptions
# ---------------------------------------------------------------------------


@respx.mock
def test_exception_carries_status_method_url_body_request_id() -> None:
    respx.get(_FULL_URL).mock(
        return_value=httpx.Response(
            _HTTP_404,
            json={"detail": "not found"},
            headers={"X-Request-Id": "req-abc"},
        )
    )
    with pytest.raises(NotFoundError) as exc_info:
        _make_transport().request("GET", _PATH)
    err = exc_info.value
    assert err.status_code == _HTTP_404
    assert err.request_method == "GET"
    assert err.request_url is not None
    assert err.response_body == {"detail": "not found"}
    assert err.request_id == "req-abc"


@respx.mock
def test_exception_url_does_not_contain_raw_token() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(AuthenticationError) as exc_info:
        _make_transport(token_provider=lambda: _FAKE_JWT).request("GET", _PATH)
    assert _FAKE_JWT not in (exc_info.value.request_url or "")


# ---------------------------------------------------------------------------
# Successful response
# ---------------------------------------------------------------------------


@respx.mock
def test_success_returns_response() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={"ok": True}))
    resp = _make_transport().request("GET", _PATH)
    assert resp.status_code == _HTTP_200
    assert resp.json() == {"ok": True}


# ---------------------------------------------------------------------------
# User-Agent
# ---------------------------------------------------------------------------


@respx.mock
def test_user_agent_header() -> None:
    route = respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    _make_transport().request("GET", _PATH)
    sent_ua = route.calls[0].request.headers.get("user-agent")
    assert sent_ua == _DEFAULT_USER_AGENT
    assert f"pynteracta/{__version__}" in sent_ua
    assert "python/" in sent_ua
    assert "httpx/" in sent_ua


@respx.mock
def test_user_agent_override() -> None:
    route = respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    _make_transport(user_agent="custom-agent/1.0").request("GET", _PATH)
    assert route.calls[0].request.headers.get("user-agent") == "custom-agent/1.0"


# ---------------------------------------------------------------------------
# Auth scheme
# ---------------------------------------------------------------------------


@respx.mock
def test_auth_scheme_default_bearer() -> None:
    route = respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    _make_transport(token_provider=lambda: "rawtoken").request("GET", _PATH)
    assert route.calls[0].request.headers.get("authorization") == "Bearer rawtoken"


@respx.mock
def test_auth_scheme_none_sends_raw_token() -> None:
    route = respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    _make_transport(token_provider=lambda: "rawtoken", auth_scheme=None).request("GET", _PATH)
    assert route.calls[0].request.headers.get("authorization") == "rawtoken"


@respx.mock
def test_auth_scheme_bearer() -> None:
    route = respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    _make_transport(token_provider=lambda: "rawtoken", auth_scheme="Bearer").request("GET", _PATH)
    assert route.calls[0].request.headers.get("authorization") == "Bearer rawtoken"


@respx.mock
def test_no_token_provider_no_auth_header() -> None:
    route = respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    _make_transport().request("GET", _PATH)
    assert "authorization" not in route.calls[0].request.headers


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


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


@respx.mock
def test_hooks_on_success() -> None:
    respx.get(_FULL_URL).mock(
        return_value=httpx.Response(_HTTP_200, json={}, headers={"X-Request-Id": "rid-1"})
    )
    recorder = _RecordingHooks()
    _make_transport(hooks=recorder).request("GET", _PATH)
    assert len(recorder.requests) == 1
    assert len(recorder.responses) == 1
    assert len(recorder.errors) == 0
    req = recorder.requests[0]
    assert req.method == "GET"
    resp = recorder.responses[0]
    assert resp.status_code == _HTTP_200
    assert resp.request_id == "rid-1"
    assert resp.elapsed_ms >= 0.0


@respx.mock
def test_hooks_on_error() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_404))
    recorder = _RecordingHooks()
    with pytest.raises(NotFoundError):
        _make_transport(hooks=recorder).request("GET", _PATH)
    assert len(recorder.errors) == 1
    assert isinstance(recorder.errors[0], NotFoundError)


def test_hooks_on_network_error() -> None:
    with respx.mock:
        respx.get(_FULL_URL).mock(side_effect=httpx.NetworkError("fail"))
        recorder = _RecordingHooks()
        with pytest.raises(TransportError):
            _make_transport(hooks=recorder).request("GET", _PATH)
    assert len(recorder.errors) == 1
    assert isinstance(recorder.errors[0], TransportError)


@respx.mock
def test_hooks_no_httpx_types_in_request_info() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    recorder = _RecordingHooks()
    _make_transport(hooks=recorder).request("GET", _PATH)
    req = recorder.requests[0]
    assert not any("httpx" in type(v).__module__ for v in [req.method, req.url, req.headers])


# ---------------------------------------------------------------------------
# Redaction in hooks / logs
# ---------------------------------------------------------------------------


@respx.mock
def test_authorization_header_redacted_in_request_info() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    recorder = _RecordingHooks()
    _make_transport(token_provider=lambda: _FAKE_JWT, hooks=recorder).request("GET", _PATH)
    req = recorder.requests[0]
    headers = dict(req.headers)
    auth_value = headers.get("Authorization", headers.get("authorization", ""))
    assert _FAKE_JWT not in auth_value
    assert auth_value == _REDACTED


@respx.mock
def test_jwt_redacted_in_logs() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with capture_logs() as logs:
        _make_transport(token_provider=lambda: _FAKE_JWT).request("GET", _PATH)
    for entry in logs:
        for val in entry.values():
            if isinstance(val, str):
                assert _FAKE_JWT not in val, f"JWT leaked into log entry: {entry}"


@respx.mock
def test_token_invalidator_called_on_401() -> None:
    called: list[str] = []
    respx.get(_FULL_URL).mock(return_value=httpx.Response(401))
    with pytest.raises(AuthenticationError):
        _make_transport(token_invalidator=lambda: called.append("yes")).request("GET", _PATH)
    assert called == ["yes"]


@respx.mock
def test_401_invalid_auth_token_header_calls_invalidator() -> None:
    called: list[str] = []
    respx.get(_FULL_URL).mock(
        return_value=httpx.Response(401, headers={"WWW-Authenticate": "INVALID_AUTH_TOKEN"})
    )
    with pytest.raises(AuthenticationError):
        _make_transport(token_invalidator=lambda: called.append("yes")).request("GET", _PATH)
    assert called == ["yes"]


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@respx.mock
def test_context_manager() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with _make_transport() as t:
        resp = t.request("GET", _PATH)
    assert resp.status_code == _HTTP_200


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


@respx.mock
def test_audit_disabled_emits_no_audit_events() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with capture_logs() as logs:
        _make_transport(audit=False).request("GET", _PATH)
    audit_events = [e for e in logs if "audit" in e.get("event", "")]
    assert audit_events == []


@respx.mock
def test_audit_enabled_emits_request_and_response_events() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={"id": 1}))
    with capture_logs() as logs:
        _make_transport(audit=True).request("GET", _PATH)
    events = [e["event"] for e in logs]
    assert "audit.request" in events
    assert "audit.response" in events


@respx.mock
def test_audit_request_contains_headers() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with capture_logs() as logs:
        _make_transport(audit=True, token_provider=lambda: "tok").request("GET", _PATH)
    req_entry = next(e for e in logs if e.get("event") == "audit.request")
    assert "headers" in req_entry


@respx.mock
def test_audit_bodies_false_no_body_in_events() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={"id": 1}))
    with capture_logs() as logs:
        _make_transport(audit=True, audit_bodies=False).request("GET", _PATH)
    for e in logs:
        if "audit" in e.get("event", ""):
            assert e.get("body") is None


@respx.mock
def test_audit_bodies_true_includes_response_body() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={"id": 1}))
    with capture_logs() as logs:
        _make_transport(audit=True, audit_bodies=True).request("GET", _PATH)
    resp_entry = next(e for e in logs if e.get("event") == "audit.response")
    assert resp_entry.get("body") == {"id": 1}


@respx.mock
def test_audit_bodies_true_includes_request_body() -> None:
    respx.post(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with capture_logs() as logs:
        _make_transport(audit=True, audit_bodies=True).request("POST", _PATH, json={"name": "test"})
    req_entry = next(e for e in logs if e.get("event") == "audit.request")
    assert req_entry.get("body") == {"name": "test"}


@respx.mock
def test_audit_authorization_redacted_in_audit_headers() -> None:
    respx.get(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with capture_logs() as logs:
        _make_transport(audit=True, token_provider=lambda: _FAKE_JWT).request("GET", _PATH)
    req_entry = next(e for e in logs if e.get("event") == "audit.request")
    headers = req_entry.get("headers", {})
    auth = headers.get("Authorization", headers.get("authorization", ""))
    assert _FAKE_JWT not in auth
    assert auth == _REDACTED


@respx.mock
def test_audit_sensitive_body_key_redacted() -> None:
    respx.post(_FULL_URL).mock(return_value=httpx.Response(_HTTP_200, json={}))
    with capture_logs() as logs:
        _make_transport(audit=True, audit_bodies=True).request(
            "POST", _PATH, json={"token": "secret-value", "name": "test"}
        )
    req_entry = next(e for e in logs if e.get("event") == "audit.request")
    body = req_entry.get("body", {})
    assert body.get("token") == _REDACTED
    assert body.get("name") == "test"


class TestResponseRedaction:
    """Finding A (v0.9.3): the response side must be redacted inside the transport.

    The hooks channel is the reason this cannot live in a structlog processor: a consumer's
    ``ClientHooks.on_response`` receives ``ResponseInfo`` directly, and the library deliberately
    never calls ``setup_default_logging()`` on their behalf, so no logging configuration can
    scrub it. None of these tests installs the redaction processor.
    """

    _JWT = "eyJhbGciOiJSUzUxMiJ9.eyJzdWIiOiIxMDAxIn0.c2lnbmF0dXJlLXNlY3JldA"

    def _auth_transport(self, hooks: Any = None) -> HttpTransport:
        return HttpTransport(base_url=_BASE, audit=True, audit_bodies=True, hooks=hooks)

    @respx.mock
    def test_hooks_channel_never_sees_raw_token(self) -> None:
        captured: list[ResponseInfo] = []

        class _Capture:
            def on_request(self, info: RequestInfo) -> None: ...
            def on_response(self, info: ResponseInfo) -> None:
                captured.append(info)

            def on_error(self, err: Exception) -> None: ...

        respx.post(f"{_BASE}/core/auth/create-access-token-by-service-account").mock(
            return_value=httpx.Response(200, json={"accessToken": self._JWT})
        )
        transport = self._auth_transport(hooks=_Capture())
        transport.request("POST", "core/auth/create-access-token-by-service-account", json={})

        assert captured, "on_response was not called"
        body = captured[0].body
        assert isinstance(body, dict)
        assert body["accessToken"] == "***REDACTED***"
        assert self._JWT not in str(body)

    @respx.mock
    def test_audit_event_never_carries_raw_token(self) -> None:
        respx.post(f"{_BASE}/core/auth/create-access-token-by-service-account").mock(
            return_value=httpx.Response(200, json={"accessToken": self._JWT})
        )
        transport = self._auth_transport()
        with capture_logs() as logs:
            transport.request("POST", "core/auth/create-access-token-by-service-account", json={})

        events = [e for e in logs if e.get("event") == "audit.response"]
        assert events, "audit.response was not emitted"
        assert self._JWT not in str(events[0])
        assert events[0]["body"]["accessToken"] == "***REDACTED***"

    @respx.mock
    def test_response_headers_are_redacted_in_both_channels(self) -> None:
        captured: list[ResponseInfo] = []

        class _Capture:
            def on_request(self, info: RequestInfo) -> None: ...
            def on_response(self, info: ResponseInfo) -> None:
                captured.append(info)

            def on_error(self, err: Exception) -> None: ...

        respx.get(f"{_BASE}/ping").mock(
            return_value=httpx.Response(
                200,
                json={"ok": True},
                headers={"authorization": f"Bearer {self._JWT}", "set-cookie": "sid=abc123"},
            )
        )
        transport = self._auth_transport(hooks=_Capture())
        with capture_logs() as logs:
            transport.request("GET", "ping")

        headers = captured[0].headers
        assert self._JWT not in str(headers)
        events = [e for e in logs if e.get("event") == "audit.response"]
        assert self._JWT not in str(events[0]["headers"])

    @respx.mock
    def test_ordinary_payload_is_not_over_redacted(self) -> None:
        """Guards the fix against scrubbing legitimate business fields."""
        payload = {"id": 42, "title": "Quarterly report", "description": "no secrets here"}
        captured: list[ResponseInfo] = []

        class _Capture:
            def on_request(self, info: RequestInfo) -> None: ...
            def on_response(self, info: ResponseInfo) -> None:
                captured.append(info)

            def on_error(self, err: Exception) -> None: ...

        respx.get(f"{_BASE}/posts/42").mock(return_value=httpx.Response(200, json=payload))
        transport = self._auth_transport(hooks=_Capture())
        transport.request("GET", "posts/42")

        assert captured[0].body == payload

    @respx.mock
    def test_oversized_body_still_round_trips(self) -> None:
        """A truncated body is a str, not a dict; redaction must not raise on it."""
        respx.get(f"{_BASE}/big").mock(
            return_value=httpx.Response(200, json={"blob": "x" * 200_000})
        )
        transport = self._auth_transport()
        response = transport.request("GET", "big")
        assert response.status_code == _HTTP_200
