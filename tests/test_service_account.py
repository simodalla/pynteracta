import json

from devtools import debug

from pynteracta.models import ServiceAccountModel


def test_service_account_model_from_json_file():
    with open("tests/fake_service_account.json") as f:
        json_data = json.load(f)
        service_account = ServiceAccountModel(**json_data)

    assert service_account.token_expiration == 9
    assert service_account.alg == "RS512"
    assert service_account.aud == "injenia/portal-authenticator"
    assert service_account.private_key_id == 1
    assert service_account.client_id == 1234
    assert service_account.private_key.startswith("-----BEGIN PRIVATE KEY")
    assert "1234567890" in service_account.private_key

    service_account_dump = service_account.model_dump(mode="json", by_alias=True)

    assert service_account_dump["kid"] == 1
    assert service_account_dump["iis"] == 1234


def test_service_account_jwt_token_payload():
    with open("tests/fake_service_account.json") as f:
        service_account = ServiceAccountModel(**json.load(f))

    jwt_token_payload = service_account.jwt_token_payload
    assert jwt_token_payload["iis"] == 1234
    for key in ["jti", "aud", "iat", "exp"]:
        assert key in jwt_token_payload


def test_service_account_jwt_token_headers():
    with open("tests/fake_service_account.json") as f:
        service_account = ServiceAccountModel(**json.load(f))

    jwt_token_headers = service_account.jwt_token_headers
    debug(jwt_token_headers)
    assert jwt_token_headers["kid"] == 1
    assert jwt_token_headers["typ"] is None
