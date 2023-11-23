import json
import logging
from collections import OrderedDict

import jwt
import requests
from pydantic import BaseModel
from requests import Response

from . import urls
from .core import format_response_error, interactapi, mock_validate_kid
from .exceptions import (
    InteractaError,
    InteractaLoginError,
    InteractaResponseError,
    MultipleObjectsReturned,
    ObjectDoesNotFound,
    PostDoesNotFound,
)
from .schemas.models import (
    BaseListPostsElement,
    CreateCustomPostIn,
    EditCustomPostIn,
    GetCommunityDetailsResponse,
    GetCustomPostForEditResponse,
    GetPostWorkflowScreenDataForEditResponse,
    Group,
    InteractaModel,
    Post,
)
from .schemas.requests import (
    CreateGroupIn,
    CreateUserIn,
    EditGroupIn,
    EditUserIn,
    ExecutePostWorkflowOperationIn,
    GetPostDefinitionCatalogsIn,
    ListCommunityPostsIn,
    ListGroupMembersIn,
    ListSystemGroupsIn,
    ListSystemUsersIn,
)
from .schemas.responses import (
    CreateGroupOut,
    CreateUserOut,
    EditGroupOut,
    EditUserOut,
    ExecutePostWorkflowOperationResponse,
    GetGroupForEditOut,
    GetPostDefinitionCatalogsOut,
    GetPostDefinitionOut,
    GetUserForEditOut,
    HashtagsOut,
    ListGroupMembersOut,
    ListPostDefinitionCatalogEntriesOut,
    ListSystemGroupsOut,
    ListSystemUsersElement,
    ListSystemUsersOut,
    PostCreatedOut,
    PostDetailOut,
    PostsOut,
)
from .settings import ApiSettings, InteractaSettings

logger = logging.getLogger(__name__)
jwt.api_jws.PyJWS._validate_kid = mock_validate_kid  # type: ignore


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


class InteractaApi(Api):
    def __init__(
        self,
        settings: InteractaSettings,
        log_calls: bool = False,
        log_call_responses: bool = False,
    ) -> None:
        self.settings = settings
        self._log_calls = log_calls
        self._log_call_responses = log_call_responses
        self._call_stack = OrderedDict()

    @property
    def authorized_header(self):
        return {
            "authorization": f"Bearer {self.access_token}",
            "content-type": "application/json",  # charset=UTF-8",
        }

    def prepare_credentials_login(self):
        login_path = urls.LOGIN_CREDENTIAL
        data = json.dumps(
            {
                "username": self.settings.auth_username,
                "password": self.settings.auth_password.get_secret_value(),
            }
        )
        return login_path, data

    def prepare_service_login(self):
        if not self.settings.auth_service_account:
            raise InteractaError("Problemi con service account")

        login_path = urls.LOGIN_SERVICE
        payload = self.settings.auth_service_account.jwt_token_payload
        headers = self.settings.auth_service_account.jwt_token_headers

        try:
            token = jwt.encode(
                payload,
                self.settings.auth_service_account.private_key.get_secret_value(),
                algorithm=self.settings.auth_service_account.algorithm,
                headers=headers,
            )
        except Exception as e:
            raise e
        data = json.dumps({"jwtAssertion": token})
        return login_path, data

    def login(self):
        try:
            path, data = (
                self.prepare_service_login()
                if self.settings.auth_service_account
                else self.prepare_credentials_login()
            )
        except Exception as e:
            raise InteractaError(f"Error on prepare login: {e}") from e

        try:
            response = self.call_api(
                "post",
                path=path,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                },
                data=data,
            )
        except InteractaResponseError as e:
            raise InteractaLoginError(str(e)) from e
        result = response.json()
        if "accessToken" not in result:
            raise InteractaLoginError(f"{format_response_error(response)} - No accessToken")
        self.access_token = result["accessToken"]
        return self.access_token

    @interactapi(schema_out=PostsOut)
    def list_posts(
        self,
        community_id: str | int,
        params: dict = None,
        headers: dict = None,
        data: ListCommunityPostsIn = None,
    ) -> PostsOut | Response:
        path = f"/communication/posts/data/community-list/{community_id}"
        return self.call_post(path=path, params=params, headers=headers, data=data)

    @interactapi(schema_out=PostDetailOut)
    def get_post_detail(
        self, post_id: str | int, parms: dict = None, headers: dict = None
    ) -> PostDetailOut | Response:
        path = f"/communication/posts/data/post-detail-by-id/{post_id}"
        try:
            return self.call_get(path=path, params=parms, headers=headers)
        except InteractaResponseError as e:
            raise PostDoesNotFound(f"Post with id '{post_id}' non found: {e}") from e

    @interactapi(schema_out=PostCreatedOut)
    def create_post(
        self, community_id, headers: dict = None, data: CreateCustomPostIn = None
    ) -> PostCreatedOut | Response:
        path = f"/communication/posts/manage/create-post/{community_id}"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=GetCustomPostForEditResponse)
    def get_post_data_for_edit(
        self, post_id, headers: dict = None
    ) -> GetCustomPostForEditResponse | Response:
        path = f"/communication/posts/manage/post-data-for-edit/{post_id}"
        return self.call_get(path=path, headers=headers)

    @interactapi()
    def edit_post(
        self,
        post_id,
        occ_token,
        headers: dict = None,
        data: EditCustomPostIn = None,
    ) -> Response:
        path = f"/communication/posts/manage/edit-post/{post_id}/{occ_token}"
        return self.call_put(path=path, headers=headers, data=data)

    @interactapi(schema_out=ListSystemUsersOut)
    def list_users(
        self, headers: dict = None, data: ListSystemUsersIn | None = None
    ) -> ListSystemUsersOut | Response:
        path = "/admin/data/users"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=CreateUserOut)
    def create_user(
        self, headers: dict = None, data: CreateUserIn | None = None
    ) -> CreateUserOut | Response:
        path = "/admin/manage/users"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=GetUserForEditOut)
    def get_user_data_for_edit(self, user_id, headers: dict = None) -> GetUserForEditOut | Response:
        path = f"/admin/manage/users/{user_id}/edit"
        return self.call_get(path=path, headers=headers)

    @interactapi(schema_out=EditUserOut)
    def edit_user(
        self, user_id, headers: dict = None, data: EditUserIn | None = None
    ) -> EditUserOut | Response:
        path = f"/admin/manage/users/{user_id}"
        return self.call_put(path=path, headers=headers, data=data)

    @interactapi()
    def delete_user(self, user_id: int, headers: dict = None) -> Response:
        path = f"/admin/manage/users/{user_id}"
        return self.call_delete(path=path, headers=headers)

    @interactapi(schema_out=ListSystemGroupsOut)
    def list_groups(
        self, headers: dict = None, data: ListSystemGroupsIn | None = None
    ) -> ListSystemGroupsOut | Response:
        path = "/admin/data/groups"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=CreateGroupOut)
    def create_group(
        self, headers: dict = None, data: CreateGroupIn | None = None
    ) -> CreateGroupOut | Response:
        path = "/admin/manage/groups"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=ListGroupMembersOut)
    def list_group_members(
        self,
        group_id: str | int,
        headers: dict = None,
        data: ListGroupMembersIn | None = None,
    ) -> ListGroupMembersOut | Response:
        path = f"/admin/data/groups/{group_id}/members"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=GetGroupForEditOut)
    def get_group_data_for_edit(
        self, group_id, headers: dict = None
    ) -> GetGroupForEditOut | Response:
        path = f"/admin/manage/groups/{group_id}/edit"
        return self.call_get(path=path, headers=headers)

    @interactapi(schema_out=EditGroupOut)
    def edit_group(
        self,
        group_id: str | int,
        headers: dict = None,
        data: EditGroupIn | None = None,
    ) -> EditGroupOut | Response:
        path = f"/admin/manage/groups/{group_id}"
        return self.call_put(path=path, headers=headers, data=data)

    @interactapi()
    def delete_group(self, group_id: int, headers: dict = None) -> Response:
        path = f"/admin/manage/groups/{group_id}"
        return self.call_delete(path=path, headers=headers)

    @interactapi(schema_out=HashtagsOut)
    def list_hashtags(
        self, community_id: str | int, headers: dict = None, data: dict = None
    ) -> ListSystemGroupsOut | Response:
        path = f"/admin/data/communities/{community_id}/hashtags"
        return self.call_post(path=path, headers=headers, data=data)

    @interactapi(schema_out=GetPostDefinitionOut)
    def get_post_definition_detail(
        self, community_id: str | int, headers: dict = None
    ) -> GetPostDefinitionOut | Response:
        path = f"/communication/settings/communities/{community_id}/post-definition"
        return self.call_get(path=path, headers=headers)

    @interactapi(schema_out=GetCommunityDetailsResponse)
    def get_community_detail(
        self, community_id: str | int, headers: dict = None
    ) -> GetCommunityDetailsResponse | Response:
        path = f"/communication/settings/communities/{community_id}/details"
        return self.call_get(path=path, headers=headers)

    @interactapi()
    def list_business_units(self, headers: dict = None) -> Response:
        path = "/admin/data/business-units"
        return self.call_get(path=path, headers=headers)

    @interactapi(schema_out=GetPostDefinitionCatalogsOut)
    def list_catalogs(
        self,
        catalog_ids: set[int],
        load_entries: bool = False,
        headers: dict = None,
    ) -> GetPostDefinitionCatalogsOut | Response:
        path = "/communication/settings/post-definition/catalogs"
        params = {"loadEntries": load_entries}
        data = GetPostDefinitionCatalogsIn(catalog_ids=list(catalog_ids))
        return self.call_post(path=path, headers=headers, data=data, params=params)

    @interactapi(schema_out=ListPostDefinitionCatalogEntriesOut)
    def list_catalog_entries(
        self, catalog_id: int | str, headers: dict = None, data: dict = None
    ) -> ListPostDefinitionCatalogEntriesOut | Response:
        path = f"/communication/settings/post-definition/catalogs/{catalog_id}/entries"
        return self.call_post(path=path, headers=headers, data=data)

    ### worflow operations

    @interactapi(schema_out=GetPostWorkflowScreenDataForEditResponse)
    def get_post_workflow_screen_data_for_edit(
        self, post_id: int, workflow_operation_id: int | None = None, headers: dict = None
    ) -> GetPostWorkflowScreenDataForEditResponse | Response:
        path = f"/communication/posts/manage/post-workflow-screen-data-for-edit/{post_id}"
        params = (
            {"workflowOperationId": str(workflow_operation_id)} if workflow_operation_id else None
        )
        return self.call_get(path=path, params=params, headers=headers)

    @interactapi(schema_out=ExecutePostWorkflowOperationResponse)
    def execute_post_workflow_operation(
        self,
        post_id: int,
        workflow_operation_id: int,
        headers: dict | None = None,
        data: ExecutePostWorkflowOperationIn | None = None,
    ):
        path = (
            "/communication/posts/manage/execute-post-workflow-operation/"
            f"{post_id}/{workflow_operation_id}"
        )
        return self.call_post(path=path, headers=headers, data=data)

    ### end worflow operations

    def get_post_by_title(self, community_id: int, title: str) -> Post:
        search = ListCommunityPostsIn(title=title)
        result = self.list_posts(community_id, data=search)
        posts = [post for post in result.items if title.lower() in post.title.strip().lower()]
        if len(posts) == 0:
            raise PostDoesNotFound(f"Post with '{title}' in title non found in interacta")
        elif len(posts) > 1:
            raise MultipleObjectsReturned(
                f"Multiple post with '{title}' in title founded in interacta"
            )
        return posts[0]

    def get_post_by_exact_title(self, community_id: int, title: str) -> Post | None:
        search = ListCommunityPostsIn(title=title)
        result = self.list_posts(community_id, data=search)
        posts = [post for post in result.items if title.lower() == post.title.strip().lower()]
        if len(posts) == 0:
            raise PostDoesNotFound(f"Post with title '{title}' non found in interacta")
        elif len(posts) > 1:
            raise MultipleObjectsReturned(
                f"Multiple post with title '{title}' founded in interacta"
            )
        return posts[0]

    def list_all_posts(
        self,
        community_id: str | int,
        data: ListCommunityPostsIn = None,
    ) -> list[BaseListPostsElement]:
        all_posts = []
        page_token = None
        data = data if data else ListCommunityPostsIn()
        while True:
            data.page_token = page_token
            posts = self.list_posts(
                community_id=community_id,
                data=data,
            )
            all_posts += posts.items
            if not posts.next_page_token:
                break
            page_token = posts.next_page_token
        return all_posts

    def all_users(self, data: ListSystemUsersIn | None = None) -> list[ListSystemUsersElement]:
        all_items = []
        page_token = None
        counter = 1
        data = data if data else ListSystemUsersIn(page_size=100)
        while True:
            data.page_token = page_token
            list_results = self.list_users(data=data)
            all_items += list_results.items
            if not list_results.next_page_token:
                break
            page_token = list_results.next_page_token
            counter += 1
        return all_items

    def get_group(self, name: str | None, filter: ListSystemGroupsIn | None = None) -> Group | None:
        if not filter:
            filter = ListSystemGroupsIn()
            filter.page_size = 100
            filter.calculate_total_items_count = True
            filter.full_text_filter = name
            filter.status_filter = [0]
        else:
            filter.full_text_filter = name
        result = self.list_groups(data=filter)
        groups = [group for group in result.items if group.name == name]

        if len(groups) == 0:
            raise ObjectDoesNotFound(f"Group with name '{name}' non found in interacta")
        elif len(groups) > 1:
            raise MultipleObjectsReturned(
                f"Multiple groups with name '{name}' founded in interacta"
            )
        return groups[0]

    def get_user(
        self,
        email_external_auth_service: str | None = None,
        data: ListSystemUsersIn | None = None,
    ) -> ListSystemUsersElement:
        if not data:
            data = ListSystemUsersIn()
            data.calculate_total_items_count = True
        if email_external_auth_service:
            data.external_auth_service_email_full_text_filter = email_external_auth_service

        result = self.list_users(data=data)

        json_data = data.model_dump_json(exclude_unset=True, exclude={"page_size"})
        if len(result.items) == 0:
            raise ObjectDoesNotFound(f"User with data '{json_data}' non found in interacta")
        elif len(result.items) > 1:
            raise MultipleObjectsReturned(
                f"Multiple users with data '{json_data}' founded in interacta"
            )
        return result.items[0]

    @classmethod
    def swap_type_model(cls, post: Post, PostModel: BaseModel):
        return PostModel.model_validate(post.model_dump(by_alias=True))
