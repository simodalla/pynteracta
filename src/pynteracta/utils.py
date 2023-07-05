import functools
import json
import tomllib
from pathlib import Path
from typing import Any

from jwt.exceptions import InvalidTokenError
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from requests.models import Response

from .exceptions import InteractaError

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

SESSION_ACCESSTK_CACHE_FILENAME = ".pyintercata"


def mock_validate_kid(self, kid) -> None:
    if not isinstance(kid, str) and not isinstance(kid, int):
        raise InvalidTokenError("Key ID header parameter must be a string or an int")


def set_session_access_token(access_token: str):
    try:
        sak_file = Path.home() / SESSION_ACCESSTK_CACHE_FILENAME
        sak_file.write_text(access_token)
    except Exception:
        return False
    return True


def get_session_access_token():
    try:
        sak_file = Path.home() / SESSION_ACCESSTK_CACHE_FILENAME
        token = sak_file.read_text()
    except Exception:
        return None
    return token


def clean_session_access_token():
    try:
        sak_file = Path.home() / SESSION_ACCESSTK_CACHE_FILENAME
        sak_file.unlink()
    except Exception:
        return False
    return True


def format_response_error(response: Response) -> str:
    return (
        f"url: {response.url} - response {response.status_code}"
        f" headers: {response.headers} content: {response.text}"
    )


def parse_service_account_file(file_path: str) -> dict:
    try:
        with open(file_path) as f:
            json_data = json.load(f)
            check_service_account_json_data(data=json_data)
            data = {
                "service_auth_key": str(json_data["private_key"]),
                "service_auth_iss": str(json_data["client_id"]),
                "service_auth_kid": int(json_data["private_key_id"]),
            }
    except Exception as e:
        raise InteractaError(str(e)) from e
    return data


def check_service_account_json_data(data: dict):
    required_keys = ["private_key_id", "private_key", "client_id"]
    not_keys = [key for key in required_keys if key not in data.keys()]
    if not_keys:
        raise InteractaError(
            "Il service account non risulta valido. Non sono presenti tutti parametri necessari."
        )
    not_values = [key for key in required_keys if not data[key]]
    if not_values:
        raise InteractaError(
            "Il service account non risulta valido. Non sono valorizzati tutti parametri necessari."
        )
    return True


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


class TomlConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        env_file = self.config.get("env_file")
        with open(env_file, "rb") as ft:
            file_content_toml = tomllib.load(ft)
            field_value = file_content_toml.get(field_name)
            return field_value, field_name, False

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        d: dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(field, field_name)
            field_value = self.prepare_field_value(field_name, field, field_value, value_is_complex)
            if field_value is not None:
                d[field_key] = field_value

        return d


class TomlSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
            env_settings,
            file_secret_settings,
        )
