import pytest
import responses


@pytest.fixture()
def environment_params():
    return {
        "INTERACTA_BASEURL": "https://example.org",
        "INTERACTA_SERVICE_AUTH_KEY": "fake_key12345",
        "INTERACTA_SERVICE_AUTH_JTI": "fake_jti",
        "INTERACTA_SERVICE_AUTH_ISS": "fake_iss",
        "INTERACTA_SERVICE_AUTH_KID": "1",
    }.copy()


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps
