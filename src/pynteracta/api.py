import json
import logging
import os
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta

import jwt
import requests
from requests import Response

from . import urls
from .exceptions import InteractaError, InteractaLoginError, InteractaResponseError
from .schemas.models import (
    GroupMembersOut,
    GroupsOut,
    HashtagsOut,
    PostDetailOut,
    PostIn,
    PostsOut,
    UsersOut,
)
from .schemas.requests import BodyPost

# from .schemas.responses import ResponsePost, ResponsePosts, ResponseUsers
from .utils import (
    PLAYGROUND_SETTINGS,
    format_response_error,
    interactapi,
    mock_validate_kid,
    parse_service_account_file,
)

logger = logging.getLogger(__name__)
jwt.api_jws.PyJWS._validate_kid = mock_validate_kid  # type: ignore


class Api:
    def __init__(self):
        self.access_token = None

    def call_post(
        self, path: str, query_url: str = None, headers: dict = None, data: dict | str = None
    ):
        if data:
            data = data.json()
        else:
            data = json.dumps({})

        return self.call_api("post", path=path, query_url=query_url, headers=headers, data=data)

    def call_get(self, path: str, query_url: str = None, headers: dict = None):
        return self.call_api("get", path=path, query_url=query_url, headers=headers)

    def call_put(
        self, path: str, query_url: str = None, headers: dict = None, data: dict | str = None
    ):
        return self.call_api("put", path=path, query_url=query_url, headers=headers, data=data)

    def call_api(
        self, method: str, path: str, query_url: str = None, headers={}, data: dict | str = None
    ):
        url = f"{self.base_url}/external/v2{path}"
        request_method = getattr(requests, method)
        response = request_method(url, headers=headers, data=data)
        if response.status_code != 200:
            raise InteractaResponseError(format_response_error(response))
        return response


class InteractaAPI(Api):
    def __init__(
        self,
        base_url: str | None = None,
        service_auth_key: str | bytes | None = None,
        service_auth_jti: str | None = None,
        service_auth_iss: str | None = None,
        service_auth_kid: int = 0,
        service_auth_alg: str = "RS512",
        service_auth_token_expiration: int = 9,
        log_calls: bool = False,
        log_call_responses: bool = False,
    ) -> None:
        self.base_url = base_url
        self.service_auth_key = service_auth_key
        self.service_auth_jti = service_auth_jti
        self.service_auth_iss = service_auth_iss
        self.service_auth_kid = service_auth_kid
        self.service_auth_alg = service_auth_alg
        self.service_auth_token_expiration = service_auth_token_expiration
        # self.access_token = None
        self._log_calls = log_calls
        self._log_call_responses = log_call_responses
        self._call_stack = OrderedDict()

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        url = value if value else os.getenv("INTERACTA_BASEURL", "")
        if url:
            if url.endswith("/"):
                url = url.rstrip("/")
            if not url.endswith(urls.PORTAL_PATH):
                url = f"{url}{urls.PORTAL_PATH}"
        self._base_url = url

    # SERVICE AUTH PAYLOAD PROPS
    @property
    def service_auth_key(self) -> str:
        return self._service_auth_key

    @service_auth_key.setter
    def service_auth_key(self, value: bytes) -> None:
        self._service_auth_key = (
            value if value else os.getenv("INTERACTA_SERVICE_AUTH_KEY", "").encode()
        )

    @property
    def service_auth_jti(self):
        return self._service_auth_jti

    @service_auth_jti.setter
    def service_auth_jti(self, value):
        self._service_auth_jti = (
            value if value else os.getenv("INTERACTA_SERVICE_AUTH_JTI", str(uuid.uuid4()))
        )

    @property
    def service_auth_iss(self):
        return self._service_auth_iss

    @service_auth_iss.setter
    def service_auth_iss(self, value):
        self._service_auth_iss = value if value else os.getenv("INTERACTA_SERVICE_AUTH_ISS", None)

    # END SERVICE AUTH PAYLOAD PROPS

    # SERVICE AUTH HEADERS PROPS
    @property
    def service_auth_kid(self):
        return self._service_auth_kid

    @service_auth_kid.setter
    def service_auth_kid(self, value):
        self._service_auth_kid = value
        if not self._service_auth_kid:
            try:
                self._service_auth_kid = int(os.getenv("INTERACTA_SERVICE_AUTH_KID", 0))
            except ValueError:
                self._service_auth_kid = 0

    # END SERVICE AUTH HEADERS PROPS

    @property
    def authorized_header(self):
        return {
            "authorization": f"Bearer {self.access_token}",
            "content-type": "application/json",
        }

    def _record_log_call(self, url: str, kwargs: dict = {}, response=None):
        log_data = {
            "url": url,
            "kwargs": kwargs,
            "status_code": response.status_code,
        }
        if self._log_call_responses:
            log_data["content"] = response.content
        self._call_stack[len(self._call_stack) + 1] = log_data

    def prepare_credentials_login(self, username: str = "", password: str = ""):
        username = username if username else os.getenv("INTERACTA_USERNAME", "")
        password = password if password else os.getenv("INTERACTA_PASSWORD", "")
        login_url = f"{self.base_url}{urls.LOGIN_CREDENTIAL}"
        data = json.dumps({"username": username, "password": password})
        return login_url, data

    def prepare_service_login(
        self,
        service_auth_key: str | None = None,
        service_auth_jti: str | None = None,
        service_auth_iss: str | None = None,
        service_auth_kid: int = 0,
    ):
        if service_auth_key:
            self.service_auth_key = service_auth_key
        if service_auth_jti:
            self.service_auth_jti = service_auth_jti
        if service_auth_iss:
            self.service_auth_iss = service_auth_iss
        if service_auth_kid:
            self.service_auth_kid = service_auth_kid

        login_url = f"{self.base_url}{urls.LOGIN_SERVICE}"
        now = datetime.now()
        current_timestamp = time.mktime(now.timetuple())
        expiration_timestamp = time.mktime(
            (now + timedelta(seconds=60 * self.service_auth_token_expiration)).timetuple()
        )
        payload = {
            "jti": self.service_auth_jti,
            "aud": "injenia/portal-authenticator",
            "iss": self.service_auth_iss,
            "iat": current_timestamp,
            "exp": expiration_timestamp,
        }
        headers = {"kid": self.service_auth_kid, "typ": None}
        try:
            token = jwt.encode(
                payload,
                self.service_auth_key,
                algorithm=self.service_auth_alg,
                headers=headers,
            )
        except Exception as e:
            raise e
        data = json.dumps({"jwtAssertion": token})
        return login_url, data

    def prepare_service_login_from_file(self, file_path: str) -> tuple:
        try:
            data = parse_service_account_file(file_path)
        except InteractaError as e:
            raise e
        return self.prepare_service_login(**data)

    def login(self, url, data):
        try:
            response = self.call_request(
                "post",
                url,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=data,
            )
        except InteractaResponseError as e:
            raise InteractaLoginError(str(e))
        result = response.json()
        if "accessToken" not in result:
            raise InteractaLoginError(f"{format_response_error(response)} - No accessToken")
        self.access_token = result["accessToken"]
        return self.access_token

    def call_request(self, method: str, url: str, **kwargs):
        if method not in ["get", "post"]:
            return False
        request_method = getattr(requests, method)
        # print("______________________________________-")
        # print(url, kwargs)
        # print("______________________________________-")

        response = request_method(url, **kwargs)
        if self._log_calls:
            self._record_log_call(url, kwargs, response)
        if response.status_code != 200:
            raise InteractaResponseError(format_response_error(response))
        return response

    @interactapi(schema_out=PostsOut)
    def post_list(
        self, community_id: str | int, query_url=None, headers: dict = {}, data: BodyPost = None
    ) -> PostsOut | Response:
        path = f"/communication/posts/data/community-list/{community_id}"
        return self.call_post(path=path, query_url=query_url, headers=headers, data=data)

    @interactapi(schema_out=PostDetailOut)
    def post_detail(
        self, post_id: str | int, query_url=None, headers: dict = {}
    ) -> PostDetailOut | Response:
        path = f"/communication/posts/data/post-detail-by-id/{post_id}"
        return self.call_get(path=path, query_url=query_url, headers=headers)

    @interactapi(schema_out=UsersOut)
    def user_list(
        self, query_url=None, headers: dict = {}, data: dict = None
    ) -> UsersOut | Response:
        path = "/admin/data/users"
        return self.call_post(path=path, query_url=query_url, headers=headers, data=data)

    @interactapi(schema_out=GroupMembersOut)
    def group_member_list(
        self, group_id: str | int, query_url=None, headers: dict = {}, data: dict = {}
    ) -> GroupMembersOut | Response:
        path = f"/admin/data/groups/{group_id}/members"
        return self.call_post(path=path, query_url=query_url, headers=headers, data=data)

    @interactapi(schema_out=GroupsOut)
    def group_list(
        self, query_url=None, headers: dict = {}, data: dict = {}
    ) -> GroupsOut | Response:
        path = "/admin/data/groups"
        return self.call_post(path=path, query_url=query_url, headers=headers, data=data)

    @interactapi(schema_out=HashtagsOut)
    def hashtag_list(
        self, community_id: str | int, query_url=None, headers: dict = {}, data: dict = {}
    ) -> GroupsOut | Response:
        path = f"/admin/data/communities/{community_id}/hashtags"
        return self.call_post(path=path, query_url=query_url, headers=headers, data=data)

    @interactapi
    def community_post_definition_detail(
        self, community_id: str | int, query_url=None, headers: dict = {}
    ):
        path = f"/communication/settings/communities/{community_id}/post-definition"
        return self.call_get(path=path, query_url=query_url, headers=headers)

    def create_post(self, community_id, payload: PostIn) -> Response:
        url = f"{self.base_url}/external/v2/communication/posts/manage/create-post/{community_id}"
        headers = self.authorized_header
        response = requests.get(url, headers=headers)
        data = payload.json()
        response = self.call_request("post", url, headers=headers, data=data)
        return response.json()


class PlaygroundApi(InteractaAPI):
    def __init__(
        self,
        log_calls: bool = False,
        log_call_responses: bool = False,
    ):
        super().__init__(
            base_url=PLAYGROUND_SETTINGS["base_url"],
            log_calls=log_calls,
            log_call_responses=log_call_responses,
        )

    def bootstrap_token(self):
        url, data = self.prepare_credentials_login(
            username=PLAYGROUND_SETTINGS["username"],
            password=PLAYGROUND_SETTINGS["password"],
        )
        token = self.login(url, data)
        return token

    def get_posts(self):
        return super().get_posts(community_id=PLAYGROUND_SETTINGS["community"]["id"])
