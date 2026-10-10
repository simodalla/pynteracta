# SPDX-License-Identifier: Apache-2.0
"""Test delle façade degli utenti: form di modifica e risultato delle scritture (spec 05)."""

from __future__ import annotations

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
