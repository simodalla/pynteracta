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
from .exceptions import (
    InteractaError,
    InteractaLoginError,
    InteractaResponseError,
    MultipleObjectsReturned,
    PostDoesNotFound,
)
from .schemas.models import (
    EditCustomPostIn,
    GetCustomPostForEditResponse,
    GroupMembersOut,
    GroupsOut,
    HashtagsOut,
    Post,
    PostCreatedOut,
    PostDefinitionOut,
    PostDetailOut,
    PostIn,
    PostsOut,
    UsersOut,
)
from .schemas.requests import BodyPost
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
        self._log_calls = False

    def call_get(self, path: str, query_url: str = None, headers: dict = None):
        return self.call_api("get", path=path, query_url=query_url, headers=headers)

    def call_post(
        self,
        path: str,
        query_url: str = None,
        headers: dict = None,
        data: dict | None = None,
        payload: dict | None = None,
    ):
        return self.call_api(
            "post", path=path, query_url=query_url, headers=headers, data=data, payload=payload
        )

    def call_put(
        self,
        path: str,
        query_url: str = None,
        headers: dict = None,
        data: dict | None = None,
        payload: dict | None = None,
    ):
        return self.call_api(
            "put", path=path, query_url=query_url, headers=headers, data=data, payload=payload
        )

    def call_api(
        self,
        method: str,
        path: str,
        query_url: str | None = None,
        headers: dict | None = None,
        data: dict | None = None,
        payload: dict | None = None,
    ):
        url = f"{self.base_url}{path}"
        request_method = getattr(requests, method)
        if self._log_calls:
            log_msg = f"API CALL: URL [{url}] HEADERS [{headers}] DATA [{data}]"
            logger.info(log_msg)
        response = request_method(url, headers=headers, data=data, json=payload)
        if response.status_code != 200:
            raise InteractaResponseError(format_response_error(response), response=response)
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
            if not url.endswith(urls.API_ENDPOINT_PATH):
                url = f"{url}{urls.API_ENDPOINT_PATH}"
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

    def prepare_credentials_login(self, username: str = "", password: str = ""):
        username = username if username else os.getenv("INTERACTA_USERNAME", "")
        password = password if password else os.getenv("INTERACTA_PASSWORD", "")
        login_path = urls.LOGIN_CREDENTIAL
        data = {"username": username, "password": password}
        return login_path, data

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

        login_path = urls.LOGIN_SERVICE
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
        data = {"jwtAssertion": token}
        return login_path, data

    def prepare_service_login_from_file(self, file_path: str) -> tuple:
        try:
            data = parse_service_account_file(file_path)
        except InteractaError as e:
            raise e
        return self.prepare_service_login(**data)

    def login(self, path, payload):
        try:
            response = self.call_post(
                path=path,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                payload=payload,
            )
        except InteractaResponseError as e:
            raise InteractaLoginError(str(e))
        result = response.json()
        if "accessToken" not in result:
            raise InteractaLoginError(f"{format_response_error(response)} - No accessToken")
        self.access_token = result["accessToken"]
        return self.access_token

    @interactapi(schema_out=PostsOut)
    def post_list(
        self, community_id: str | int, query_url=None, headers: dict = {}, payload: BodyPost = None
    ) -> PostsOut | Response:
        path = f"/communication/posts/data/community-list/{community_id}"
        return self.call_post(path=path, query_url=query_url, headers=headers, payload=payload)

    @interactapi(schema_out=PostDetailOut)
    def post_detail(
        self, post_id: str | int, query_url=None, headers: dict = {}
    ) -> PostDetailOut | Response:
        path = f"/communication/posts/data/post-detail-by-id/{post_id}"
        try:
            return self.call_get(path=path, query_url=query_url, headers=headers)
        except InteractaResponseError as e:
            raise PostDoesNotFound(f"Post with id '{post_id}' non found in interacta: {e}")

    @interactapi(schema_out=PostCreatedOut)
    def create_post(
        self, community_id, query_url=None, headers: dict = {}, payload: PostIn = None
    ) -> PostCreatedOut | Response:
        path = f"/communication/posts/manage/create-post/{community_id}"
        return self.call_post(path=path, query_url=query_url, headers=headers, payload=payload)

    @interactapi(schema_out=GetCustomPostForEditResponse)
    def post_data_for_edit(
        self, post_id, query_url=None, headers: dict = {}
    ) -> GetCustomPostForEditResponse | Response:
        path = f"/communication/posts/manage/post-data-for-edit/{post_id}"
        return self.call_get(path=path, query_url=query_url, headers=headers)

    @interactapi()
    def edit_post(
        self,
        post_id,
        occ_token,
        query_url=None,
        headers: dict = {},
        payload: EditCustomPostIn = None,
    ) -> Response:
        path = f"/communication/posts/manage/edit-post/{post_id}/{occ_token}"
        return self.call_put(path=path, query_url=query_url, headers=headers, payload=payload)

    def get_post_by_title(self, community_id: int, title: str) -> Post | None:
        search = BodyPost(title=title)
        result = self.post_list(community_id, payload=search)
        posts = [post for post in result.items if title.lower() in post.title.strip().lower()]
        if len(posts) == 0:
            raise PostDoesNotFound(f"Post with '{title}' in title non found in interacta")
        elif len(posts) > 1:
            raise MultipleObjectsReturned(
                f"Multiple post with '{title}' in title founded in interacta"
            )
        return posts[0]

    def get_post_by_exact_title(self, community_id: int, title: str) -> Post | None:
        search = BodyPost(title=title)
        result = self.post_list(community_id, payload=search)
        posts = [post for post in result.items if title.lower() == post.title.strip().lower()]
        if len(posts) == 0:
            raise PostDoesNotFound(f"Post with title '{title}' non found in interacta")
        elif len(posts) > 1:
            raise MultipleObjectsReturned(
                f"Multiple post with title '{title}' founded in interacta"
            )
        return posts[0]

    @interactapi(schema_out=UsersOut)
    def user_list(
        self, query_url=None, headers: dict = {}, payload: dict = None
    ) -> UsersOut | Response:
        path = "/admin/data/users"
        return self.call_post(path=path, query_url=query_url, headers=headers, payload=payload)

    @interactapi(schema_out=GroupMembersOut)
    def group_member_list(
        self, group_id: str | int, query_url=None, headers: dict = {}, payload: dict = {}
    ) -> GroupMembersOut | Response:
        path = f"/admin/data/groups/{group_id}/members"
        return self.call_post(path=path, query_url=query_url, headers=headers, payload=payload)

    @interactapi(schema_out=GroupsOut)
    def group_list(
        self, query_url=None, headers: dict = {}, payload: dict = {}
    ) -> GroupsOut | Response:
        path = "/admin/data/groups"
        return self.call_post(path=path, query_url=query_url, headers=headers, payload=payload)

    @interactapi(schema_out=HashtagsOut)
    def hashtag_list(
        self, community_id: str | int, query_url=None, headers: dict = {}, payload: dict = {}
    ) -> GroupsOut | Response:
        path = f"/admin/data/communities/{community_id}/hashtags"
        return self.call_post(path=path, query_url=query_url, headers=headers, payload=payload)

    @interactapi(schema_out=PostDefinitionOut)
    def community_post_definition_detail(
        self, community_id: str | int, query_url=None, headers: dict = {}
    ) -> PostDefinitionOut | Response:
        path = f"/communication/settings/communities/{community_id}/post-definition"
        return self.call_get(path=path, query_url=query_url, headers=headers)

    def catalog_for_edit_detail(
        self, catalog_id: str | int, query_url=None, headers: dict = {}
    ) -> PostDefinitionOut | Response:
        path = f"/admin/manage/catalogs/{catalog_id}/edit"
        return self.call_get(path=path, query_url=query_url, headers=headers)


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
