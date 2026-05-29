# SPDX-License-Identifier: Apache-2.0
import builtins

import pytest

from pynteracta.exceptions import (
    AuthenticationError,
    ConcurrencyError,
    CustomFieldValidationError,
    InteractaError,
    NotFoundError,
    PermissionError,
    ServerError,
    TransportError,
    ValidationError,
)

_STATUS_CODE = 500


def test_hierarchy() -> None:
    assert issubclass(AuthenticationError, InteractaError)
    assert issubclass(PermissionError, InteractaError)
    assert issubclass(NotFoundError, InteractaError)
    assert issubclass(ValidationError, InteractaError)
    assert issubclass(CustomFieldValidationError, ValidationError)
    assert issubclass(ConcurrencyError, InteractaError)
    assert issubclass(ServerError, InteractaError)
    assert issubclass(TransportError, InteractaError)


def test_base_fields() -> None:
    err = InteractaError(
        "boom",
        status_code=_STATUS_CODE,
        request_method="GET",
        request_url="https://example.com",
        response_body={"detail": "oops"},
        request_id="req-123",
    )
    assert str(err) == "boom"
    assert err.status_code == _STATUS_CODE
    assert err.request_method == "GET"
    assert err.request_url == "https://example.com"
    assert err.response_body == {"detail": "oops"}
    assert err.request_id == "req-123"


def test_validation_error_has_errors() -> None:
    err = ValidationError("bad", errors=[{"field": "name", "msg": "required"}])
    assert err.errors == [{"field": "name", "msg": "required"}]


def test_validation_error_defaults_empty_list() -> None:
    err = ValidationError("bad")
    assert err.errors == []


def test_permission_error_distinct_from_builtin() -> None:
    assert PermissionError is not builtins.PermissionError
    with pytest.raises(PermissionError):
        raise PermissionError("denied", status_code=403)
