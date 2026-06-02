# SPDX-License-Identifier: Apache-2.0
"""Tests for redaction utilities in logging.py."""

from __future__ import annotations

import pytest

from pynteracta.logging import redact_body, redact_headers, redact_string

_REDACTED = "***REDACTED***"
_FAKE_JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
_PLAIN_INT = 42


class TestRedactString:
    def test_jwt_is_redacted(self) -> None:
        assert redact_string(_FAKE_JWT) == _REDACTED

    def test_jwt_embedded_in_text(self) -> None:
        result = redact_string(f"token: {_FAKE_JWT} end")
        assert _FAKE_JWT not in result
        assert _REDACTED in result

    def test_plain_string_unchanged(self) -> None:
        assert redact_string("hello world") == "hello world"

    def test_empty_string(self) -> None:
        assert redact_string("") == ""


class TestRedactHeaders:
    def test_authorization_always_redacted(self) -> None:
        result = redact_headers({"Authorization": "some-token", "Content-Type": "application/json"})
        assert result["Authorization"] == _REDACTED
        assert result["Content-Type"] == "application/json"

    def test_authorization_case_insensitive(self) -> None:
        result = redact_headers({"authorization": "tok"})
        assert result["authorization"] == _REDACTED

    def test_bearer_token_redacted(self) -> None:
        result = redact_headers({"Authorization": f"Bearer {_FAKE_JWT}"})
        assert result["Authorization"] == _REDACTED

    def test_jwt_in_other_header_redacted(self) -> None:
        result = redact_headers({"X-Custom": _FAKE_JWT})
        assert _FAKE_JWT not in result["X-Custom"]

    def test_non_sensitive_headers_preserved(self) -> None:
        result = redact_headers({"Content-Type": "application/json", "Accept": "application/json"})
        assert result == {"Content-Type": "application/json", "Accept": "application/json"}

    def test_returns_new_dict(self) -> None:
        original = {"Authorization": "tok"}
        result = redact_headers(original)
        assert result is not original


class TestRedactBody:
    @pytest.mark.parametrize(
        "key",
        ["token", "password", "secret", "privateKey", "TOKEN", "PASSWORD", "myToken"],
    )
    def test_sensitive_key_redacted(self, key: str) -> None:
        result = redact_body({key: "sensitive-value"})
        assert isinstance(result, dict)
        assert result[key] == _REDACTED

    def test_non_sensitive_key_preserved(self) -> None:
        result = redact_body({"username": "alice", "email": "alice@example.com"})
        assert result == {"username": "alice", "email": "alice@example.com"}

    def test_non_dict_string_unchanged(self) -> None:
        assert redact_body("hello") == "hello"

    def test_non_dict_int_unchanged(self) -> None:
        assert redact_body(_PLAIN_INT) == _PLAIN_INT

    def test_non_dict_none_unchanged(self) -> None:
        assert redact_body(None) is None

    def test_list_of_ints_unchanged(self) -> None:
        assert redact_body([1, 2]) == [1, 2]

    def test_nested_dict_sensitive_key_redacted(self) -> None:
        body = {"user": {"password": "secret123", "email": "a@b.com"}}
        result = redact_body(body)
        assert isinstance(result, dict)
        assert result["user"]["password"] == _REDACTED
        assert result["user"]["email"] == "a@b.com"

    def test_list_of_dicts_redacted(self) -> None:
        body = [{"token": "abc"}, {"name": "alice"}]
        result = redact_body(body)
        assert isinstance(result, list)
        assert result[0]["token"] == _REDACTED
        assert result[1]["name"] == "alice"

    def test_jwt_in_string_value_redacted(self) -> None:
        fake_jwt = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
        body = {"description": f"auth={fake_jwt}"}
        result = redact_body(body)
        assert isinstance(result, dict)
        assert fake_jwt not in result["description"]
        assert _REDACTED in result["description"]

    def test_deeply_nested_sensitive_key(self) -> None:
        body = {"outer": {"inner": {"secret": "xyz"}}}
        result = redact_body(body)
        assert result["outer"]["inner"]["secret"] == _REDACTED

    def test_string_with_jwt_redacted(self) -> None:
        fake_jwt = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.signature"
        assert fake_jwt not in redact_body(fake_jwt)
        assert _REDACTED in redact_body(fake_jwt)
