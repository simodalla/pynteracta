import functools

from jwt.exceptions import InvalidTokenError
from requests import Response


def mock_validate_kid(self, kid) -> None:
    if not isinstance(kid, str) and not isinstance(kid, int):
        raise InvalidTokenError("Key ID header parameter must be a string or an int")


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
