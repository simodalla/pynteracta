import functools
import json
import logging

import requests
from jwt.exceptions import InvalidTokenError
from requests import Response

from pydantic import BaseModel

from .exceptions import InteractaResponseError
from .schemas.models import InteractaModel
from .settings import ApiSettings

logger = logging.getLogger(__name__)


class Api:
    def __init__(self, settings: ApiSettings):
        self.access_token = None
        self._log_calls = False
        self.settings = settings

    def call_post(
        self, path: str, params: dict = None, headers: dict = None, data: dict | str = None
    ):
        return self.call_api(
            "post", path=path, params=params, headers=headers, data=prepare_data(data)
        )

    def call_get(self, path: str, params: str = None, headers: dict = None):
        return self.call_api("get", path=path, params=params, headers=headers)

    def call_put(
        self, path: str, params: str = None, headers: dict = None, data: dict | str = None
    ):
        return self.call_api(
            "put", path=path, params=params, headers=headers, data=prepare_data(data)
        )

    def call_delete(self, path: str, headers: dict = None, **kwargs):
        return self.call_api("delete", path=path, headers=headers, **kwargs)

    def call_api(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        headers: dict | None = None,
        data: dict | str | None = None,
        **kwargs,
    ):
        url = f"{self.settings.api_url}{path}"
        request_method = getattr(requests, method)
        if self._log_calls:
            log_msg = f"API CALL: URL [{url}] HEADERS [{headers}] DATA [{data}]"
            logger.info(log_msg)
        response = request_method(url, headers=headers, data=data, params=params, **kwargs)
        if response.status_code != 200:
            raise InteractaResponseError(format_response_error(response), response=response)
        return response


def mock_validate_kid(self, kid) -> None:
    if not isinstance(kid, str) and not isinstance(kid, int):
        raise InvalidTokenError("Key ID header parameter must be a string or an int")


def prepare_data(data=None):
    if not data:
        return json.dumps({})
    if isinstance(data, BaseModel):
        if isinstance(data, InteractaModel):
            data = data.model_dump_json(by_alias=True)
        else:
            data = data.model_dump_json()
    else:
        data = json.dumps(data)
    return data.encode("utf-8")


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


def format_response_error(response: Response) -> str:
    return (
        f"url: {response.url} - response {response.status_code}"
        f" headers: {response.headers} content: {response.text}"
    )
