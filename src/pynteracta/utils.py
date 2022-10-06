from pathlib import Path

from jwt.exceptions import InvalidTokenError
from requests.models import Response

# ref https://injenia.atlassian.net/wiki/spaces/IEAD/pages/3624075265/Autenticazione#Costruzione-del-jwtAssertion # noqa: E501
SERVICE_AUTH_HEADERS = {
    # Sostituire con il valore "private_key_id" recuperato dal JSON delle credenziali
    # (Service Account). Attenzione che è un tipo JSON number, non una stringa.
    "kid": 0,
    "typ": None,
}

SERVICE_AUTH_PAYLOAD = {
    # jti - Sostituire con un identificativo univoco, esempio UUID
    "jti": "",
    # aud - Fisso al valore injenia/portal-authenticator
    "aud": "injenia/portal-authenticator",
    # iss - Sostituire con il valore "client_id" recuperato dal JSON delle credenziali
    # (Service Account)
    "iss": "",
    # iat- Unix timestamp dell'ora corrente
    "iat": "",
    # unit - Unix timestamp dell'ora di scadenza dell'assertion
    "exp": "",
}

PLAYGROUND_SETTINGS = {
    "base_url": "https://prod.development.lab.interacta.space",
    "username": "interacta-test-api@interacta-prod",
    "password": "MyInteractaPl@yground!",
    "community": {
        "nome": "Interacta Playground",
        "id": 1142,
    },
}

SESSION_ACCESS_TOKEN_FILENAME = ".pyintercata"


def mock_validate_kid(self, kid) -> None:
    if not isinstance(kid, str) and not isinstance(kid, int):
        raise InvalidTokenError("Key ID header parameter must be a string or an int")


def set_session_access_token(access_token: str):
    try:
        sak_file = Path.home() / SESSION_ACCESS_TOKEN_FILENAME
        sak_file.write_text(access_token)
    except Exception:
        return False
    return True


def get_session_access_token():
    try:
        sak_file = Path.home() / SESSION_ACCESS_TOKEN_FILENAME
        token = sak_file.read_text()
    except Exception:
        return None
    return token


def clean_session_access_token():
    try:
        sak_file = Path.home() / SESSION_ACCESS_TOKEN_FILENAME
        sak_file.unlink()
    except Exception:
        return False
    return True


def format_response_error(response: Response) -> str:
    return (
        f"url: {response.url} - response {response.status_code}"
        f" headers: {response.headers} content: {response.text}"
    )
