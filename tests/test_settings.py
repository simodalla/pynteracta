import pytest
from pydantic import ValidationError

from pynteracta.models import ServiceAccountModel
from pynteracta.settings import ApiSettings


def test_api_settings_init_with_service_file(service_account_path):
    settings = ApiSettings(
        base_url="https://example.com", auth_service_file_path=service_account_path
    )
    assert isinstance(settings.auth_service_account, ServiceAccountModel)

    assert settings.auth_service_account.token_expiration == 9
    assert settings.auth_service_account.algorithm == "RS512"
    assert settings.auth_service_account.aud == "injenia/portal-authenticator"
    assert settings.auth_service_account.private_key_id == 1
    assert settings.auth_service_account.client_id == 1234
    assert settings.auth_service_account.private_key.startswith("-----BEGIN PRIVATE KEY")
    assert "1234567890" in settings.auth_service_account.private_key


def test_api_settings_without_service_and_user_pwd_raise_exception():
    with pytest.raises(ValidationError) as exc_info:
        ApiSettings(base_url="https://example.com")

    assert "No authentication settings is set" in str(exc_info.value)


def test_api_settings_with_service_path_dont_exist():
    # with pytest.raises(ValidationError) as exc_info:
    with pytest.raises(ValidationError) as exc_info:
        ApiSettings(base_url="https://example.com", auth_service_file_path="__wrong__")

    assert "Wrong service account settings" in str(exc_info.value)
