# SPDX-License-Identifier: Apache-2.0
"""Tests for redaction utilities in logging.py."""

from __future__ import annotations

import httpx
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

    # Caratterizzazione (04-T02): una query senza nomi sensibili resta identica.
    # criterio: 04-C08
    def test_url_query_without_sensitive_names_untouched(self) -> None:
        url = "https://x.example.com/p?loadViewLink=true&pageSize=10"
        assert redact_string(url) == url


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

    # criterio: 01-C05
    @pytest.mark.parametrize(
        "name",
        ["Authorization", "authorization", "Proxy-Authorization", "PROXY-AUTHORIZATION"],
    )
    def test_auth_headers_redacted_by_name(self, name: str) -> None:
        """Il valore è redatto per nome, anche se non ha la forma di un JWT (Basic user:pass)."""
        result = redact_headers({name: "Basic dXNlcjpwYXNz"})
        assert result[name] == _REDACTED

    # criterio: 01-C06
    @pytest.mark.parametrize(
        "name",
        [
            "X-Api-Key",
            "x-api-key",
            "X_API_KEY",
            "X-Auth-Token",
            "X-Refresh-Token",
            "X-Secret",
            "X-Password",
        ],
    )
    @pytest.mark.parametrize("value", ["opaque-value-1234", ""])
    def test_sensitive_header_names_redacted(self, name: str, value: str) -> None:
        result = redact_headers({name: value})
        assert result[name] == _REDACTED

    # criterio: 01-C07
    def test_non_sensitive_headers_untouched(self) -> None:
        headers = {
            "Content-Type": "application/json",
            "X-Request-Id": "abc-123",
            "WWW-Authenticate": 'Bearer error="invalid_token"',
            "Date": "Thu, 02 Jul 2026 16:06:04 GMT",
            "User-Agent": "pynteracta/0.9.4",
        }
        assert redact_headers(headers) == headers

    # criterio: 01-C08
    def test_jwt_embedded_in_other_header_only_jwt_redacted(self) -> None:
        result = redact_headers({"X-Custom": f"before {_FAKE_JWT} after"})
        assert result["X-Custom"] == f"before {_REDACTED} after"

    # criterio: 01-C01
    def test_set_cookie_value_redacted_attributes_kept(self) -> None:
        result = redact_headers({"Set-Cookie": "a=1; Secure; HttpOnly"})
        assert result["Set-Cookie"] == f"a={_REDACTED}; Secure; HttpOnly"

    # criterio: 01-C01
    def test_set_cookie_empty_value_redacted_attributes_kept(self) -> None:
        result = redact_headers({"Set-Cookie": "a=; Path=/"})
        assert result["Set-Cookie"] == f"a={_REDACTED}; Path=/"

    # criterio: 01-C02
    def test_set_cookie_joined_pair_with_expires_comma(self) -> None:
        """Due Set-Cookie come li unisce httpx (``, ``), con la virgola dentro ``Expires``."""
        expires = "Expires=Thu, 02-Jul-2026 16:06:04 GMT"
        first = f"first=val-1; Secure; HttpOnly; SameSite=Strict; Path=/p; {expires}"
        joined = httpx.Headers([("set-cookie", first), ("set-cookie", "second=val-2; Path=/")])[
            "set-cookie"
        ]
        assert ", second=" in joined  # il formato unito è davvero quello di httpx

        result = redact_headers({"set-cookie": joined})["set-cookie"]
        assert "val-1" not in result
        assert "val-2" not in result
        assert result == (
            f"first={_REDACTED}; Secure; HttpOnly; SameSite=Strict; Path=/p; {expires}, "
            f"second={_REDACTED}; Path=/"
        )

    # criterio: 01-C03
    def test_cookie_request_header_all_values_redacted(self) -> None:
        result = redact_headers({"Cookie": "a=1; b=2"})
        assert result["Cookie"] == f"a={_REDACTED}; b={_REDACTED}"

    # criterio: 01-C04
    @pytest.mark.parametrize("name", ["Cookie", "Set-Cookie"])
    @pytest.mark.parametrize("value", ["garbage", 'a="x,y"; Path=/'])
    def test_cookie_header_without_equals_or_quoted_fully_redacted(
        self, name: str, value: str
    ) -> None:
        result = redact_headers({name: value})
        assert result[name] == _REDACTED


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
