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
