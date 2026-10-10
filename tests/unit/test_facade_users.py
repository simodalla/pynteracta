# SPDX-License-Identifier: Apache-2.0
"""Test delle façade degli utenti: form di modifica e risultato delle scritture (spec 05)."""

from __future__ import annotations

import pytest
from api_helpers import load_payload

from pynteracta.models.facade.users import UserForEdit, UserWriteResult

_USER_ID = 42
_USER_OCC_TOKEN = 42
_CREATED_USER_ID = 1043
_CREATED_NEXT_OCC_TOKEN = 1
_EDIT_NEXT_OCC_TOKEN = 43
_CREDENTIALS_NEXT_OCC_TOKEN = 13


# criterio: 05-C06
def test_user_for_edit_exposes_occ_token() -> None:
    user = UserForEdit.from_dict(load_payload("get_user_for_edit_response.json"))
    assert user.occ_token == _USER_OCC_TOKEN
    assert user.occ_token == user.raw.occToken
    assert user.first_name == "Maria"


class TestUserWriteResult:
    # criterio: 05-C01
    def test_from_create_exposes_response_fields(self) -> None:
        payload = load_payload("create_user_response.json")
        result = UserWriteResult.from_create(payload)
        assert result.user_id == _CREATED_USER_ID
        assert result.next_occ_token == _CREATED_NEXT_OCC_TOKEN
        assert result.generated_password == ["Xk7-fake-pw"]
        assert result.expired_credentials is True
        assert result.sent_email_notify is False
        assert result.account_photo_url == payload["accountPhotoUrl"]
        assert result.raw.userId == _CREATED_USER_ID

    # criterio: 05-C01
    # criterio: 05-C26
    def test_from_create_normalizes_string_generated_password(self) -> None:
        """Il tenant restituisce ``generatedPassword`` come stringa, non come lista (T15)."""
        payload = load_payload("create_user_response.json")
        payload["generatedPassword"] = "Xk7-fake-pw"
        result = UserWriteResult.from_create(payload)
        assert result.generated_password == ["Xk7-fake-pw"]
        assert result.raw.generatedPassword == ["Xk7-fake-pw"]
        assert result.user_id == _CREATED_USER_ID

    # criterio: 05-C20
    def test_from_create_invalid_response_hides_values(self) -> None:
        """Una risposta malformata non porta i valori (la password) nel messaggio d'errore."""
        payload = load_payload("create_user_response.json")
        payload["generatedPassword"] = {"nested": "s3cret-value"}
        payload["userId"] = "not-an-int-value"
        with pytest.raises(ValueError, match="generatedPassword") as info:
            UserWriteResult.from_create(payload)
        text = str(info.value)
        assert "s3cret-value" not in text
        assert "not-an-int-value" not in text
        assert "userId" in text
        assert info.value.__context__ is None
        assert info.value.__cause__ is None

    # criterio: 05-C02
    def test_from_edit_uses_given_user_id(self) -> None:
        payload = load_payload("edit_user_response.json")
        result = UserWriteResult.from_edit(payload, _USER_ID)
        assert result.user_id == _USER_ID
        assert result.next_occ_token == _EDIT_NEXT_OCC_TOKEN
        assert result.account_photo_url == payload["accountPhotoUrl"]
        assert result.generated_password is None
        assert result.expired_credentials is None
        assert result.sent_email_notify is None

    # criterio: 05-C04
    def test_from_credentials_uses_given_user_id(self) -> None:
        result = UserWriteResult.from_credentials(
            load_payload("edit_user_credentials_response.json"), _USER_ID
        )
        assert result.user_id == _USER_ID
        assert result.next_occ_token == _CREDENTIALS_NEXT_OCC_TOKEN
        assert result.account_photo_url is None
