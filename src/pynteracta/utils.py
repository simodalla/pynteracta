import functools

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
    "auth_username": "interacta-test-api@interacta-prod",
    "auth_password": "MyInteractaPl@yground!",
    "playground_community": {
        "community_id": 1142,
    },
}


def mock_validate_kid(self, kid) -> None:
    if not isinstance(kid, str) and not isinstance(kid, int):
        raise InvalidTokenError("Key ID header parameter must be a string or an int")


def format_response_error(response: Response) -> str:
    return (
        f"url: {response.url} - response {response.status_code}"
        f" headers: {response.headers} content: {response.text}"
    )


def to_camel(string: str) -> str:
    words = string.split("_")
    if len(words) == 1:
        return string
    return f"{words[0]}{''.join(word.capitalize() for ix, word in enumerate(words[0:]) if ix > 0)}"


def interactapi(func=None, *, schema_out=None):
    if func is None:
        return functools.partial(interactapi, schema_out=schema_out)

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if "headers" not in kwargs:
            kwargs["headers"] = self.authorized_header
        else:
            kwargs["headers"].update(self.authorized_header)
        response = func(self, *args, **kwargs)
        if not schema_out:
            return response
        result = schema_out.model_validate(response.json())
        result._response = response
        return result

    return wrapper
