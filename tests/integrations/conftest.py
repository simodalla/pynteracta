import pytest

from pynteracta.api import InteractaApi
from pynteracta.settings import AppSettings, InteractaSettings


@pytest.fixture(scope="session")
def app_settings() -> AppSettings:
    return AppSettings(_env_file=".envs/integrations/.pyinteracta.toml")


@pytest.fixture(scope="session")
def settings(app_settings: AppSettings) -> InteractaSettings:
    return app_settings.interacta


@pytest.fixture(scope="session")
def logged_api(settings: InteractaSettings) -> InteractaApi:
    api = InteractaApi(settings=settings)
    url, payload = api.prepare_service_login()
    api.login(url, payload)
    return api
