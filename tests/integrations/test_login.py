from pynteracta.api import InteractaApi
from pynteracta.settings import InteractaSettings


def test_login_with_service_account(settings: InteractaSettings) -> None:
    api = InteractaApi(settings=settings)
    url, payload = api.prepare_service_login()
    api.login(url, payload)
