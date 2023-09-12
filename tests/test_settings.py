from pynteracta.models import ServiceAccountModel
from pynteracta.settings import ApiSettings


def test_service_acconunt_data_in_settings():
    servive_file_path = "tests/fake_service_account.json"
    settings = ApiSettings(base_url="https://example.com")
    assert settings.service_account is None

    settings = ApiSettings(base_url="https://example.com", service_file_path=servive_file_path)
    assert isinstance(settings.service_account, ServiceAccountModel)

    assert settings.service_account.token_expiration == 9
    assert settings.service_account.alg == "RS512"
    assert settings.service_account.aud == "injenia/portal-authenticator"
    assert settings.service_account.private_key_id == 1
    assert settings.service_account.client_id == 1234
    assert settings.service_account.private_key.startswith("-----BEGIN PRIVATE KEY")
    assert "1234567890" in settings.service_account.private_key
