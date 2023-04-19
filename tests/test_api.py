import datetime as dt
import json
import os
import time
import uuid
from zoneinfo import ZoneInfo

import pytest
import time_machine

from pynteracta import urls as intercta_urls
from pynteracta.api import InteractaAPI
from pynteracta.exceptions import InteractaLoginError

rome_tz = ZoneInfo("Europe/Rome")


class TestInteractaAPI:
    def test_init_without_params_no_envs(self, mocker):
        mocker.patch.dict(os.environ, {}, clear=True)

        api = InteractaAPI()

        assert api.base_url is None
        assert api.service_auth_key == b""
        try:
            uuid.UUID(str(api.service_auth_jti))
        except ValueError:
            pytest.fail(f"api.service_auth_jti '{api.service_auth_jti}' is not a valid uuid")
        assert api.service_auth_iss is None
        assert api.service_auth_kid == 0
        assert api.service_auth_alg == "RS512"
        assert api.service_auth_token_expiration == 9

    def test_init_without_params_with_env(self, mocker, environment_params):
        mocker.patch.dict(os.environ, environment_params)

        api = InteractaAPI()

        assert (
            api.base_url
            == f'{environment_params["INTERACTA_BASEURL"]}{intercta_urls.API_ENDPOINT_PATH}'
        )
        assert api.service_auth_key == environment_params["INTERACTA_SERVICE_AUTH_KEY"].encode()
        assert api.service_auth_jti == environment_params["INTERACTA_SERVICE_AUTH_JTI"]
        assert api.service_auth_iss == environment_params["INTERACTA_SERVICE_AUTH_ISS"]
        assert api.service_auth_kid == int(environment_params["INTERACTA_SERVICE_AUTH_KID"])

    def test_base_url_setter_(self, mocker):
        url = "https://example.org/"

        mocker.patch.dict(os.environ, {"INTERACTA_BASEURL": url}, clear=True)
        api = InteractaAPI()
        assert api.base_url == f"https://example.org{intercta_urls.API_ENDPOINT_PATH}"

        mocker.patch.dict(os.environ, {}, clear=True)
        api = InteractaAPI(base_url=url)
        assert api.base_url == f"https://example.org{intercta_urls.API_ENDPOINT_PATH}"

    @pytest.mark.parametrize(
        "env,expected",
        [
            ({"INTERACTA_SERVICE_AUTH_KID": "5"}, 5),
            ({"INTERACTA_SERVICE_AUTH_KID": "abc"}, 0),
            ({}, 0),
        ],
    )
    def test_service_auth_kid_setter(self, mocker, env, expected):
        mocker.patch.dict(os.environ, env, clear=True)
        api = InteractaAPI()
        assert api.service_auth_kid == expected

    def test_prepare_credentials_login(self):
        url = "http://example.org"
        username = "user1"
        pwd = "test1234"

        api = InteractaAPI(base_url=url)

        login_url, data = api.prepare_credentials_login(username=username, password=pwd)
        data = json.loads(data)

        assert (
            login_url == f"{url}{intercta_urls.API_ENDPOINT_PATH}{intercta_urls.LOGIN_CREDENTIAL}"
        )
        assert data["username"] == username
        assert data["password"] == pwd

    @time_machine.travel(dt.datetime(2022, 9, 10, 12, 0, tzinfo=rome_tz))
    def test_prepare_service_login(self, mocker, environment_params):
        auth_token_expiration = 9
        token = "1234"
        now = dt.datetime.now()
        mocker.patch.dict(os.environ, environment_params)
        mock_jwt = mocker.patch("jwt.encode", return_value=token)

        api = InteractaAPI(service_auth_token_expiration=auth_token_expiration)

        login_url, data = api.prepare_service_login()
        data = json.loads(data)

        assert login_url == (
            f"{environment_params['INTERACTA_BASEURL']}"
            f"{intercta_urls.API_ENDPOINT_PATH}{intercta_urls.LOGIN_SERVICE}"
        )
        assert "jwtAssertion" in data
        assert data["jwtAssertion"] == token

        mock_jwt.assert_called_once_with(
            {
                "jti": environment_params["INTERACTA_SERVICE_AUTH_JTI"],
                "aud": "injenia/portal-authenticator",
                "iss": environment_params["INTERACTA_SERVICE_AUTH_ISS"],
                "iat": time.mktime(now.timetuple()),
                "exp": time.mktime(
                    (now + dt.timedelta(seconds=60 * auth_token_expiration)).timetuple()
                ),
            },
            environment_params["INTERACTA_SERVICE_AUTH_KEY"].encode(),
            algorithm="RS512",
            headers={"kid": int(environment_params["INTERACTA_SERVICE_AUTH_KID"]), "typ": None},
        )

    def test_login_raise_exception_if_return_code_is_not_200(self, faker, mocked_responses):
        url = faker.url()
        mocked_responses.post(url, status=404)

        with pytest.raises(InteractaLoginError) as excinfo:
            api = InteractaAPI(base_url=url)
            api.login(url=url, payload={})

        assert f"url: {url}" in str(excinfo.value)

    def test_login_raise_exception_if_return_code_not_have_accessToken(
        self, faker, mocked_responses
    ):
        url = faker.url()
        fake_json = {"wrong_key": 123}
        mocked_responses.post(url, status=200, json=fake_json)
        with pytest.raises(InteractaLoginError) as excinfo:
            api = InteractaAPI(base_url=url)
            api.login(url=url, payload={})

        assert f"url: {url}" in str(excinfo.value)
        assert "No accessToken" in str(excinfo.value)
