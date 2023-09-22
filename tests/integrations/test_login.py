import pytest

from pynteracta.api import InteractaApi
from pynteracta.settings import InteractaSettings

pytestmark = pytest.mark.integration


def test_login_with_service_account(settings: InteractaSettings) -> None:
    api = InteractaApi(settings=settings)
    api.login()
