# SPDX-License-Identifier: Apache-2.0
"""Contract tests: generated models must match the pinned Swagger snapshot.

Each test suite covers two concerns:
  1. Schema superset: the generated Pydantic model's fields are a superset of the
     OpenAPI ``properties`` for that DTO.  Fails loudly if a required property
     disappears or is renamed.
  2. Facade smoke: instantiating the facade from a realistic JSON payload parses
     cleanly, ``raw`` is accessible, and narrow facade properties return expected values.
"""

from __future__ import annotations

import pytest

from pynteracta.models.facade.admin_manage import (
    CatalogEntryForEdit,
    CatalogForEdit,
    UserCredentialsForEdit,
    WorkspaceForEdit,
)
from pynteracta.models.facade.attachments import (
    AttachmentDetail,
    AttachmentVisibility,
    PostAttachmentList,
    UploadedAttachment,
    UploadTicket,
)
from pynteracta.models.facade.auth import CurrentUserResponse, ServiceAccountTokenResponse
from pynteracta.models.facade.catalogs import CatalogEntryList, CatalogList
from pynteracta.models.facade.communities import (
    CommunityDetail,
    CommunityList,
    PostDefinition,
    PostDefinitionMap,
)
from pynteracta.models.facade.posts import Post, PostCommentList, PostList
from pynteracta.models.facade.posts_write import (
    PostComment,
    PostForEdit,
    PostWriteResult,
    WorkflowScreen,
)
from pynteracta.models.facade.tasks import Task, TaskWriteResult
from pynteracta.models.facade.users import SystemUserList, UserForEdit, UserProfile
from pynteracta.models.generated import external_v2 as generated

from .conftest import load_payload

pytestmark = pytest.mark.contract

# ---------------------------------------------------------------------------
# Fixture constants  (IDs / counts matching tests/fixtures/payloads/*.json)
# ---------------------------------------------------------------------------

_USER_ID = 1042
_USER2_ID = 1099
_USER_OCC_TOKEN = 42
_POST_ID = 21269
_COMMUNITY_ID = 79
_COMMENT_ID = 5501
_USER_LIST_COUNT = 2
_POST_COMMENTS_COUNT = 2
# M9: community settings + catalogs
_SETTINGS_COMMUNITY_ID_1 = 10
_SETTINGS_COMMUNITY_ID_2 = 20
_SETTINGS_COMMUNITY_COUNT = 2
_CATALOG_ID_1 = 5
_CATALOG_ID_2 = 8
_CATALOG_COUNT = 2
_CATALOG_ENTRY_ID_1 = 100
_CATALOG_ENTRY_COUNT = 2
_POST_DEF_FIELD_COUNT = 2
_ATTACHMENT_ID_1 = 3001
_ATTACHMENT_COUNT = 2
_TASK_ID = 7001
_TASK_OCC_TOKEN = 3
_ATTACHMENT_VISIBLE_IDS = [3001, 3002]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_fields(model_cls: type) -> set[str]:
    """Return the set of field names declared on a Pydantic BaseModel class."""
    return set(model_cls.model_fields.keys())


def assert_superset(
    swagger_definitions: dict,  # type: ignore[type-arg]
    dto_name: str,
    model_cls: type,
    *,
    note: str = "",
) -> None:
    """Assert that ``model_cls`` fields are a superset of the Swagger ``properties``.

    Args:
        swagger_definitions: The ``definitions`` dict from the Swagger snapshot.
        dto_name: Key in ``definitions`` to check against.
        model_cls: Generated Pydantic model class.
        note: Optional context shown in the assertion message.
    """
    swagger_props = set((swagger_definitions[dto_name].get("properties") or {}).keys())
    model_field_names = _model_fields(model_cls)
    missing = swagger_props - model_field_names
    assert not missing, (
        f"{model_cls.__name__} is missing fields from Swagger '{dto_name}': {missing}. {note}"
    )


# ---------------------------------------------------------------------------
# 1. CreateAccessTokenByServiceAccountRequestDTO / ResponseDTO
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CreateAccessTokenByServiceAccountRequestDTO",
            generated.CreateAccessTokenByServiceAccountRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CreateAccessTokenByServiceAccountResponseDTO",
            generated.CreateAccessTokenByServiceAccountResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("create_access_token_response.json")
        facade = ServiceAccountTokenResponse.from_dict(payload)
        assert facade.raw is not None
        assert isinstance(facade.access_token, str)
        assert facade.access_token.startswith("eyJ")

    def test_facade_raw_accessible(self) -> None:
        payload = load_payload("create_access_token_response.json")
        facade = ServiceAccountTokenResponse.from_dict(payload)
        assert facade.raw.accessToken == facade.access_token


# ---------------------------------------------------------------------------
# 2. CurrentUserDataResponseDTO
# ---------------------------------------------------------------------------


class TestCurrentUserData:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CurrentUserDataResponseDTO",
            generated.CurrentUserDataResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("current_user_data_response.json")
        facade = CurrentUserResponse.from_dict(payload)
        assert facade.raw is not None
        assert facade.has_google_credentials is False
        assert facade.has_microsoft_credentials is False

    def test_facade_user_data_typed(self) -> None:
        payload = load_payload("current_user_data_response.json")
        facade = CurrentUserResponse.from_dict(payload)
        typed = facade.user_data_typed
        assert typed is not None
        assert typed.firstName == "Maria"
        assert typed.lastName == "Rossi"
        assert typed.id == _USER_ID


# ---------------------------------------------------------------------------
# 3. ListSystemUsersRequestDTO / ResponseDTO
# ---------------------------------------------------------------------------


class TestListSystemUsers:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListSystemUsersRequestDTO",
            generated.ListSystemUsersRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListSystemUsersResponseDTO",
            generated.ListSystemUsersResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("list_system_users_response.json")
        facade = SystemUserList.from_dict(payload)
        assert facade.raw is not None
        assert facade.next_page_token is None
        assert facade.total_items_count == _USER_LIST_COUNT

    def test_facade_items_typed(self) -> None:
        payload = load_payload("list_system_users_response.json")
        facade = SystemUserList.from_dict(payload)
        items = facade.items_typed
        assert len(items) == _USER_LIST_COUNT
        assert items[0].firstName == "Maria"
        assert items[1].firstName == "Luca"

    def test_curated_kwargs_serialize_to_pinned_fields(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
    ) -> None:
        """The camelCase fields the v0.8 curated kwargs map to must exist on the pinned DTO."""
        promoted_fields = {
            "fullTextFilter",
            "statusFilter",
            "workspaceIds",
            "communityIds",
            "creationTimestampFrom",
            "creationTimestampTo",
            "lastAccessTimestampFrom",
            "lastAccessTimestampTo",
            "role",
            "orderTypeId",
            "orderDesc",
        }
        swagger_props = set(
            (swagger_definitions["ListSystemUsersRequestDTO"].get("properties") or {}).keys()
        )
        missing = promoted_fields - swagger_props
        assert not missing, f"Promoted kwargs map to fields absent from the pinned DTO: {missing}"


# ---------------------------------------------------------------------------
# 4. UserProfileInfoDTO  (typed as UserProfileInfoDTO1 in generated code — Q5 surprise)
# ---------------------------------------------------------------------------


class TestUserProfileInfo:
    def test_swagger_def_exists(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert "UserProfileInfoDTO" in swagger_definitions

    def test_typed_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        # UserProfileInfoDTO is RootModel[Any] in the generated code; the typed model is
        # UserProfileInfoDTO1.  We verify the typed model covers the swagger properties.
        assert_superset(
            swagger_definitions,
            "UserProfileInfoDTO",
            generated.UserProfileInfoDTO1,
            note=(
                "UserProfileInfoDTO generates as RootModel[Any]; "
                "UserProfileInfoDTO1 is the typed equivalent."
            ),
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("user_profile_info_response.json")
        facade = UserProfile.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _USER_ID
        assert facade.first_name == "Maria"
        assert facade.last_name == "Rossi"
        assert facade.contact_email == "m.rossi@example.it"

    def test_facade_raw_accessible(self) -> None:
        payload = load_payload("user_profile_info_response.json")
        facade = UserProfile.from_dict(payload)
        assert facade.raw.biography == "Senior developer at Example S.r.l."


# ---------------------------------------------------------------------------
# 5. GetUserForEditResponseDTO
# ---------------------------------------------------------------------------


class TestGetUserForEdit:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetUserForEditResponseDTO",
            generated.GetUserForEditResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_user_for_edit_response.json")
        facade = UserForEdit.from_dict(payload)
        assert facade.raw is not None
        assert facade.first_name == "Maria"
        assert facade.last_name == "Rossi"
        assert facade.blocked is False
        assert facade.external_id == "EXT-1042"

    def test_facade_raw_accessible(self) -> None:
        payload = load_payload("get_user_for_edit_response.json")
        facade = UserForEdit.from_dict(payload)
        assert facade.raw.occToken == _USER_OCC_TOKEN


# ---------------------------------------------------------------------------
# 6. GetPostDetailResponseDTO
# ---------------------------------------------------------------------------


class TestGetPostDetail:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetPostDetailResponseDTO",
            generated.GetPostDetailResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_post_detail_response.json")
        facade = Post.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _POST_ID
        assert facade.community_id == _COMMUNITY_ID
        assert facade.title == "Aggiornamento procedure sicurezza Q2 2026"
        assert facade.comments_count == _POST_COMMENTS_COUNT
        assert facade.likes_count == 1

    def test_facade_raw_accessible(self) -> None:
        payload = load_payload("get_post_detail_response.json")
        facade = Post.from_dict(payload)
        assert facade.raw.attachmentsCount == 0


# ---------------------------------------------------------------------------
# 7. ListCommunityPostsFilteredRequestDTO / PagedListPostsResponseDTO
# ---------------------------------------------------------------------------


class TestListCommunityPosts:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListCommunityPostsFilteredRequestDTO",
            generated.ListCommunityPostsFilteredRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "PagedListPostsResponseDTO",
            generated.PagedListPostsResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("list_community_posts_response.json")
        facade = PostList.from_dict(payload)
        assert facade.raw is not None
        assert facade.next_page_token is None
        assert facade.total_items_count == 1

    def test_facade_items_typed(self) -> None:
        payload = load_payload("list_community_posts_response.json")
        facade = PostList.from_dict(payload)
        items = facade.items_typed
        assert len(items) == 1
        assert items[0].id == _POST_ID
        assert items[0].title == "Aggiornamento procedure sicurezza Q2 2026"


# ---------------------------------------------------------------------------
# 8. ListPostCommentsRequestDTO / ListPostCommentsResponseDTO
# ---------------------------------------------------------------------------


class TestListPostComments:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostCommentsRequestDTO",
            generated.ListPostCommentsRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostCommentsResponseDTO",
            generated.ListPostCommentsResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("list_post_comments_response.json")
        facade = PostCommentList.from_dict(payload)
        assert facade.raw is not None
        assert facade.next_page_token is None
        assert facade.total_items_count == 1

    def test_facade_items_typed(self) -> None:
        payload = load_payload("list_post_comments_response.json")
        facade = PostCommentList.from_dict(payload)
        items = facade.items_typed
        assert len(items) == 1
        assert items[0].id == _COMMENT_ID
        assert items[0].commentPlainText == "Ottimo aggiornamento, grazie!"


# ---------------------------------------------------------------------------
# 9. ListCommunitiesRequestDTO / ListCommunitiesResponseDTO
# ---------------------------------------------------------------------------


class TestListCommunities:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListCommunitiesRequestDTO",
            generated.ListCommunitiesRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListCommunitiesResponseDTO",
            generated.ListCommunitiesResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("communities_list.json")
        facade = CommunityList.from_dict(payload)
        assert facade.raw is not None
        items = facade.items_typed
        assert len(items) == _SETTINGS_COMMUNITY_COUNT
        assert items[0].id == _SETTINGS_COMMUNITY_ID_1
        assert items[0].name == "Engineering"


# ---------------------------------------------------------------------------
# 10. GetCommunityDetailsResponseDTO
# ---------------------------------------------------------------------------


class TestGetCommunityDetails:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetCommunityDetailsResponseDTO",
            generated.GetCommunityDetailsResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("community_details.json")
        facade = CommunityDetail.from_dict(payload)
        assert facade.community is not None
        assert facade.community.id == _SETTINGS_COMMUNITY_ID_1


# ---------------------------------------------------------------------------
# 11. GetPostDefinitionResponseDTOModel / ListPostDefinitionsResponseDTO
# ---------------------------------------------------------------------------


class TestGetPostDefinition:
    def test_response_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetPostDefinitionResponseDTO",
            generated.GetPostDefinitionResponseDTOModel,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("post_definition.json")
        facade = PostDefinition.from_dict(payload)
        assert facade.community_id == _SETTINGS_COMMUNITY_ID_1
        assert len(facade.field_definitions) == _POST_DEF_FIELD_COUNT

    def test_list_response_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostDefinitionsResponseDTO",
            generated.ListPostDefinitionsResponseDTO,
        )

    def test_post_definition_map_facade(self) -> None:
        payload = load_payload("post_definitions_map.json")
        facade = PostDefinitionMap.from_dict(payload)
        defs = facade.definitions
        assert _SETTINGS_COMMUNITY_ID_1 in defs
        assert defs[_SETTINGS_COMMUNITY_ID_1].community_id == _SETTINGS_COMMUNITY_ID_1


# ---------------------------------------------------------------------------
# 12. GetPostDefinitionCatalogsRequestDTO / ResponseDTO
# ---------------------------------------------------------------------------


class TestGetPostDefinitionCatalogs:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetPostDefinitionCatalogsRequestDTO",
            generated.GetPostDefinitionCatalogsRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetPostDefinitionCatalogsResponseDTO",
            generated.GetPostDefinitionCatalogsResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("catalogs.json")
        facade = CatalogList.from_dict(payload)
        assert facade.raw is not None
        items = facade.items_typed
        assert len(items) == _CATALOG_COUNT
        assert items[0].id == _CATALOG_ID_1
        assert items[0].name == "Departments"


# ---------------------------------------------------------------------------
# 13. ListPostDefinitionCatalogEntriesRequestDTO / ResponseDTO
# ---------------------------------------------------------------------------


class TestListCatalogEntries:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostDefinitionCatalogEntriesRequestDTO",
            generated.ListPostDefinitionCatalogEntriesRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostDefinitionCatalogEntriesResponseDTO",
            generated.ListPostDefinitionCatalogEntriesResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("catalog_entries.json")
        facade = CatalogEntryList.from_dict(payload)
        assert facade.raw is not None
        assert facade.next_page_token is None
        assert facade.total_items_count == _CATALOG_ENTRY_COUNT

    def test_facade_items_typed(self) -> None:
        payload = load_payload("catalog_entries.json")
        facade = CatalogEntryList.from_dict(payload)
        items = facade.items_typed
        assert len(items) == _CATALOG_ENTRY_COUNT
        assert items[0].id == _CATALOG_ENTRY_ID_1
        assert items[0].label == "Engineering"
        assert items[0].external_id == "ENG"


# ---------------------------------------------------------------------------
# 14. Attachments — M16
# ---------------------------------------------------------------------------


class TestListPostAttachments:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostAttachmentsByPostIdRequestDTO",
            generated.ListPostAttachmentsByPostIdRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostAttachmentsResponseDTO",
            generated.ListPostAttachmentsResponseDTO,
        )

    def test_element_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListPostAttachmentsElementDTO",
            generated.ListPostAttachmentsElementDTOModel,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("list_post_attachments_response.json")
        facade = PostAttachmentList.from_dict(payload)
        assert facade.raw is not None
        assert facade.total_items_count == _ATTACHMENT_COUNT
        items = facade.items_typed
        assert len(items) == _ATTACHMENT_COUNT
        assert items[0].id == _ATTACHMENT_ID_1
        assert items[0].name == "report.pdf"


class TestGetPostAttachmentDetail:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetPostAttachmentDetailResponseDTO",
            generated.GetPostAttachmentDetailResponseDTO,
        )

    def test_attachment_data_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "PostAttachmentDataDTO",
            generated.PostAttachmentDataDTO1,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_attachment_detail_response.json")
        facade = AttachmentDetail.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _ATTACHMENT_ID_1
        assert facade.name == "report.pdf"
        assert facade.post is not None
        assert facade.post.id == _POST_ID


class TestCheckAttachmentVisibility:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CheckVisibilityRequestDTO",
            generated.CheckVisibilityRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CheckVisibilityResponseDTO",
            generated.CheckVisibilityResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("check_attachment_visibility_response.json")
        facade = AttachmentVisibility.from_dict(payload)
        assert facade.raw is not None
        assert facade.ids == _ATTACHMENT_VISIBLE_IDS


# ---------------------------------------------------------------------------
# 17. GetTaskDetailResponseDTO (M17)
# ---------------------------------------------------------------------------


class TestGetTaskDetail:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetTaskDetailResponseDTO",
            generated.GetTaskDetailResponseDTO,
        )

    def test_sub_task_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "SubTaskDTO",
            generated.SubTaskDTO1,
            note="typed variant of RootModel stub",
        )

    def test_task_capabilities_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "TaskCapabilitiesDTO",
            generated.TaskCapabilitiesDTO1,
            note="typed variant of RootModel stub",
        )

    def test_task_reminder_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "TaskReminderDTO",
            generated.TaskReminderDTO1,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        facade = Task.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _TASK_ID
        assert facade.post_id == _POST_ID
        assert facade.title == "Review quarterly report"

    def test_facade_raw_accessible(self) -> None:
        payload = load_payload("get_task_detail_response.json")
        facade = Task.from_dict(payload)
        assert facade.raw.occToken == _TASK_OCC_TOKEN
        assert facade.raw.descriptionDelta is not None


# ---------------------------------------------------------------------------
# 17b. Task write DTOs (spec 02)
# ---------------------------------------------------------------------------

_CREATED_TASK_ID_CONTRACT = 7002
_EDIT_NEXT_OCC_TOKEN_CONTRACT = 4


class TestTaskWriteDTOs:
    # criterio: 02-C14
    @pytest.mark.parametrize(
        ("definition", "model"),
        [
            ("CreateTaskRequestDTO", generated.CreateTaskRequestDTO),
            ("CreateTaskResponseDTO", generated.CreateTaskResponseDTO),
            ("EditTaskRequestDTO", generated.EditTaskRequestDTO),
            ("EditTaskResponseDTO", generated.EditTaskResponseDTO),
            ("DeleteTaskResponseDTO", generated.DeleteTaskResponseDTO),
        ],
    )
    def test_write_dto_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(swagger_definitions, definition, model)

    # criterio: 02-C14
    @pytest.mark.parametrize(
        ("definition", "model"),
        [
            ("ZonedDatetimeInputDTO", generated.ZonedDatetimeInputDTO1),
            ("TaskDetailDTO", generated.TaskDetailDTO1),
        ],
    )
    def test_typed_stub_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(
            swagger_definitions, definition, model, note="typed variant of RootModel stub"
        )

    # criterio: 02-C14
    def test_facade_smoke_create(self) -> None:
        facade = TaskWriteResult.from_create(load_payload("create_task_response.json"))
        assert facade.raw is not None
        assert facade.task_id == _CREATED_TASK_ID_CONTRACT
        assert facade.next_occ_token == 1
        assert facade.task is not None
        assert facade.task.title == "Prepare the quarterly report"
        assert facade.capabilities is not None
        assert facade.capabilities.can_modify is True

    # criterio: 02-C14
    def test_facade_smoke_edit(self) -> None:
        facade = TaskWriteResult.from_edit(load_payload("edit_task_response.json"))
        assert facade.task_id == _TASK_ID
        assert facade.next_occ_token == _EDIT_NEXT_OCC_TOKEN_CONTRACT
        assert facade.task is not None
        assert facade.task.title.endswith("(updated)")  # type: ignore[union-attr]

    # criterio: 02-C14
    def test_delete_response_fixture_parses(self) -> None:
        dto = generated.DeleteTaskResponseDTO.model_validate(
            load_payload("delete_task_response.json")
        )
        assert dto.postId == _POST_ID


# ---------------------------------------------------------------------------
# 18. Groups & Hashtags (M18)
# ---------------------------------------------------------------------------

_GROUP_ID_CONTRACT = 201
_GROUP_COUNT_CONTRACT = 2
_GROUP_OCC_TOKEN_CONTRACT = 5
_HASHTAG_ID_CONTRACT = 301
_HASHTAG_COUNT_CONTRACT = 2


class TestListSystemGroups:
    from pynteracta.models.facade.groups import GroupList  # noqa: PLC0415

    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListSystemGroupsRequestDTO",
            generated.ListSystemGroupsRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListSystemGroupsResponseDTO",
            generated.ListSystemGroupsResponseDTO,
        )

    def test_element_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListSystemGroupsElementDTO",
            generated.ListSystemGroupsElementDTOModel,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        from pynteracta.models.facade.groups import GroupList  # noqa: PLC0415

        payload = load_payload("list_groups_response.json")
        facade = GroupList.from_dict(payload)
        assert facade.raw is not None
        assert facade.total_items_count == _GROUP_COUNT_CONTRACT
        items = facade.items_typed
        assert len(items) == _GROUP_COUNT_CONTRACT
        assert items[0].id == _GROUP_ID_CONTRACT


class TestListGroupMembers:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListGroupMembersRequestDTO",
            generated.ListGroupMembersRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "ListGroupMembersResponseDTO",
            generated.ListGroupMembersResponseDTO,
        )


class TestGetGroupForEdit:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetGroupForEditResponseDTO",
            generated.GetGroupForEditResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        from pynteracta.models.facade.groups import GroupForEdit  # noqa: PLC0415

        payload = load_payload("get_group_for_edit_response.json")
        facade = GroupForEdit.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _GROUP_ID_CONTRACT
        assert facade.raw.occToken == _GROUP_OCC_TOKEN_CONTRACT

    def test_tag_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "TagDTO",
            generated.TagDTO1,
            note="typed variant of RootModel stub",
        )


class TestAdminListHashtags:
    def test_request_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "AdminListHashtagsRequestDTO",
            generated.AdminListHashtagsRequestDTO,
        )

    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "AdminListHashtagsResponseDTO",
            generated.AdminListHashtagsResponseDTO,
        )

    def test_hashtag_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "AdminHashtagDTO",
            generated.AdminHashtagDTO,
        )

    def test_facade_smoke(self) -> None:
        from pynteracta.models.facade.hashtags import HashtagList  # noqa: PLC0415

        payload = load_payload("list_community_hashtags_response.json")
        facade = HashtagList.from_dict(payload)
        assert facade.raw is not None
        assert facade.total_items_count == _HASHTAG_COUNT_CONTRACT
        items = facade.items_typed
        assert len(items) == _HASHTAG_COUNT_CONTRACT
        assert items[0].id == _HASHTAG_ID_CONTRACT


# ---------------------------------------------------------------------------
# 19. Admin manage edits (M19)
# ---------------------------------------------------------------------------

_WORKSPACE_ID_CONTRACT = 88
_WORKSPACE_OCC_TOKEN_CONTRACT = 17
_CATALOG_ID_CONTRACT = 5
_CATALOG_OCC_TOKEN_CONTRACT = 9
_ENTRY_ID_CONTRACT = 100
_ENTRY_OCC_TOKEN_CONTRACT = 4
_USER_CREDS_OCC_TOKEN_CONTRACT = 12


class TestGetWorkspaceForEdit:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetWorkspaceForEditResponseDTO",
            generated.GetWorkspaceForEditResponseDTO,
        )

    def test_content_data_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "WorkspaceEditableContentDataDTO",
            generated.WorkspaceEditableContentDataDTO1,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_workspace_for_edit_response.json")
        facade = WorkspaceForEdit.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _WORKSPACE_ID_CONTRACT
        assert facade.name == "Operations"
        assert facade.raw.occToken == _WORKSPACE_OCC_TOKEN_CONTRACT


class TestGetCatalogForEdit:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetCatalogForEditResponseDTO",
            generated.GetCatalogForEditResponseDTO,
        )

    def test_content_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CatalogEditableContentDTO",
            generated.CatalogEditableContentDTOModel,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_catalog_for_edit_response.json")
        facade = CatalogForEdit.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _CATALOG_ID_CONTRACT
        assert facade.deleted is False
        assert facade.raw.occToken == _CATALOG_OCC_TOKEN_CONTRACT


class TestGetCatalogEntryForEdit:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetCatalogEntryForEditResponseDTO",
            generated.GetCatalogEntryForEditResponseDTO,
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_catalog_entry_for_edit_response.json")
        facade = CatalogEntryForEdit.from_dict(payload)
        assert facade.raw is not None
        assert facade.id == _ENTRY_ID_CONTRACT
        assert facade.external_id == "ENG"
        assert facade.raw.occToken == _ENTRY_OCC_TOKEN_CONTRACT


class TestGetUserCredentialsForEdit:
    def test_response_dto_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetUserCredentialsForEditResponseDTO",
            generated.GetUserCredentialsForEditResponseDTO,
        )

    def test_configuration_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "UserCredentialsConfigurationDTO",
            generated.UserCredentialsConfigurationDTO1,
            note="typed variant of RootModel stub",
        )

    def test_custom_credentials_dto_model_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "CustomUserCredentialsConfigurationDTO",
            generated.CustomUserCredentialsConfigurationDTOModel,
            note="typed variant of RootModel stub",
        )

    def test_facade_smoke(self) -> None:
        payload = load_payload("get_user_credentials_for_edit_response.json")
        facade = UserCredentialsForEdit.from_dict(payload)
        assert facade.raw is not None
        assert facade.has_google_credentials is True
        assert facade.has_custom_credentials is True
        assert facade.custom_username == "m.rossi"
        assert facade.raw.occToken == _USER_CREDS_OCC_TOKEN_CONTRACT


# ---------------------------------------------------------------------------
# Spec 03: post write DTOs (custom posts, comments, workflow)
# ---------------------------------------------------------------------------

_POST_WRITE_DTOS = [
    ("Create Custom Post Request", generated.CreateCustomPostRequest),
    ("EditCustomPostRequestDTO", generated.EditCustomPostRequestDTO),
    ("EditPostCustomDataRequestDTO", generated.EditPostCustomDataRequestDTO),
    ("CopyCustomPostRequestDTO", generated.CopyCustomPostRequestDTO),
    ("EditPostWatchersRequestDTO", generated.EditPostWatchersRequestDTO),
    ("EditPostAttachmentsRequestDTO", generated.EditPostAttachmentsRequestDTO),
    ("CreatePostCommentRequestDTO", generated.CreatePostCommentRequestDTO),
    ("ExecutePostWorkflowOperationRequestDTO", generated.ExecutePostWorkflowOperationRequestDTO),
    ("EditPostWorkflowScreenDataRequestDTO", generated.EditPostWorkflowScreenDataRequestDTO),
    ("CreatePostResponseDTO", generated.CreatePostResponseDTO),
    ("EditPostResponseDTO", generated.EditPostResponseDTO),
    ("CopyPostResponseDTO", generated.CopyPostResponseDTO),
    ("EditPostAttachmentsResponseDTO", generated.EditPostAttachmentsResponseDTO),
    ("MarkPostAsErasableResponseDTO", generated.MarkPostAsErasableResponseDTO),
    ("DeletePostResponseDTO", generated.DeletePostResponseDTO),
    ("CreatePostCommentResponseDTO", generated.CreatePostCommentResponseDTO),
    ("ExecutePostWorkflowOperationResponseDTO", generated.ExecutePostWorkflowOperationResponseDTO),
    ("EditPostWorkflowScreenDataResponseDTO", generated.EditPostWorkflowScreenDataResponseDTO),
    (
        "GetPostWorkflowScreenDataForEditResponseDTO",
        generated.GetPostWorkflowScreenDataForEditResponseDTO,
    ),
    ("GetCustomPostForCreateResponseDTO", generated.GetCustomPostForCreateResponseDTO),
    ("GetCustomPostForEditResponseDTO", generated.GetCustomPostForEditResponseDTO),
    ("GetCustomPostForCopyResponseDTO", generated.GetCustomPostForCopyResponseDTO),
]

_POST_WRITE_TYPED_STUBS = [
    ("PostDetailDTO", generated.PostDetailDTO1),
    ("PostEditableContentDataDTO", generated.PostEditableContentDataDTO1),
    ("PostCommentDTO", generated.PostCommentDTO1),
    ("PostWorkflowDefinitionStateDTO", generated.PostWorkflowDefinitionStateDTO1),
    ("PostWorkflowDefinitionTransitionDTO", generated.PostWorkflowDefinitionTransitionDTO1),
    ("WorkflowDefinitionScreenDTO", generated.WorkflowDefinitionScreenDTO1),
    ("InputPostAttachmentDTO", generated.InputPostAttachmentDTO1),
    ("InputPostCommentAttachmentDTO", generated.InputPostCommentAttachmentDTO1),
]

_POST_WRITE_FIXTURES = [
    ("create_post_response.json", generated.CreatePostResponseDTO),
    ("edit_post_response.json", generated.EditPostResponseDTO),
    ("copy_post_response.json", generated.CopyPostResponseDTO),
    ("delete_post_response.json", generated.DeletePostResponseDTO),
    ("mark_post_erasable_response.json", generated.MarkPostAsErasableResponseDTO),
    ("edit_post_attachments_response.json", generated.EditPostAttachmentsResponseDTO),
    ("create_post_comment_response.json", generated.CreatePostCommentResponseDTO),
    ("post_for_create_response.json", generated.GetCustomPostForCreateResponseDTO),
    ("post_for_edit_response.json", generated.GetCustomPostForEditResponseDTO),
    ("post_for_copy_response.json", generated.GetCustomPostForCopyResponseDTO),
    ("workflow_screen_response.json", generated.GetPostWorkflowScreenDataForEditResponseDTO),
    (
        "execute_workflow_operation_response.json",
        generated.ExecutePostWorkflowOperationResponseDTO,
    ),
    ("edit_workflow_screen_response.json", generated.EditPostWorkflowScreenDataResponseDTO),
    (
        "custom_field_validation_error_response.json",
        generated.CustomFieldValidationErrorResponseDTO,
    ),
]

# Stub annidati delle fixture da rivalidare nelle varianti tipizzate: (fixture, chiave, modello).
_POST_WRITE_NESTED = [
    ("create_post_response.json", "postData", generated.PostDetailDTO1),
    ("edit_post_response.json", "postData", generated.PostDetailDTO1),
    ("copy_post_response.json", "postData", generated.PostDetailDTO1),
    ("create_post_comment_response.json", "comment", generated.PostCommentDTO1),
    ("post_for_create_response.json", "contentData", generated.PostEditableContentDataDTO1),
    ("post_for_edit_response.json", "contentData", generated.PostEditableContentDataDTO1),
    ("post_for_copy_response.json", "contentData", generated.PostEditableContentDataDTO1),
    ("workflow_screen_response.json", "screen", generated.WorkflowDefinitionScreenDTO1),
]


class TestPostWriteDTOs:
    # criterio: 03-C29
    @pytest.mark.parametrize(("definition", "model"), _POST_WRITE_DTOS)
    def test_write_dto_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(swagger_definitions, definition, model)

    # criterio: 03-C29
    @pytest.mark.parametrize(("definition", "model"), _POST_WRITE_TYPED_STUBS)
    def test_typed_stub_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(
            swagger_definitions, definition, model, note="typed variant of RootModel stub"
        )

    # criterio: 03-C29
    @pytest.mark.parametrize(("fixture", "model"), _POST_WRITE_FIXTURES)
    def test_response_fixtures_parse(self, fixture: str, model: type) -> None:
        assert model.model_validate(load_payload(fixture)) is not None  # type: ignore[attr-defined]

    # criterio: 03-C29
    @pytest.mark.parametrize(("fixture", "key", "model"), _POST_WRITE_NESTED)
    def test_response_fixtures_nested_typed(self, fixture: str, key: str, model: type) -> None:
        assert model.model_validate(load_payload(fixture)[key]) is not None  # type: ignore[attr-defined]

    # criterio: 03-C29
    @pytest.mark.parametrize(
        ("model", "field"),
        [
            (generated.GetPostWorkflowScreenDataForEditResponseDTO, "screenData"),
            (generated.ExecutePostWorkflowOperationRequestDTO, "screenData"),
            (generated.ExecutePostWorkflowOperationResponseDTO, "newScreenData"),
            (generated.EditPostWorkflowScreenDataRequestDTO, "screenData"),
            (generated.EditPostWorkflowScreenDataResponseDTO, "newScreenData"),
        ],
    )
    def test_screen_data_accepts_scalar_values(self, model: type, field: str) -> None:
        values = {"5": "x", "6": 1, "7": None, "8": [1, 2], "9": {"a": 1}}
        parsed = model.model_validate({field: values})  # type: ignore[attr-defined]
        assert getattr(parsed, field) == values

    # criterio: 03-C29
    def test_facade_smoke_write_result(self) -> None:
        facade = PostWriteResult.from_create(load_payload("create_post_response.json"))
        assert facade.raw is not None
        assert facade.post is not None
        assert facade.post_id == facade.raw.postId

    # criterio: 03-C29
    def test_facade_smoke_for_edit(self) -> None:
        facade = PostForEdit.from_dict(load_payload("post_for_edit_response.json"))
        assert facade.occ_token is not None
        assert facade.content_data is not None

    # criterio: 03-C29
    def test_facade_smoke_comment(self) -> None:
        facade = PostComment.from_dict(load_payload("create_post_comment_response.json"))
        assert facade.id is not None
        assert facade.creator_user is not None

    # criterio: 03-C29
    def test_facade_smoke_workflow_screen(self) -> None:
        facade = WorkflowScreen.from_dict(load_payload("workflow_screen_response.json"))
        assert facade.screen_occ_token is not None
        assert facade.screen is not None


# ---------------------------------------------------------------------------
# Spec 04: upload degli allegati
# ---------------------------------------------------------------------------


class TestUploadNewAttachment:
    # criterio: 04-C16
    def test_schema_superset(self, swagger_definitions: dict) -> None:  # type: ignore[type-arg]
        assert_superset(
            swagger_definitions,
            "GetTemporaryImageUploadUrlBaseResponseDTO",
            generated.GetTemporaryImageUploadUrlBaseResponseDTO,
        )

    # criterio: 04-C16
    def test_fixture_parses(self) -> None:
        payload = load_payload("upload_new_attachment_response.json")
        dto = generated.GetTemporaryImageUploadUrlBaseResponseDTO.model_validate(payload)
        assert dto.contentRef == payload["contentRef"]
        assert dto.uploadMultipartRequestBodyParams is not None
        assert set(dto.uploadMultipartRequestBodyParams) == {
            "GoogleAccessId",
            "key",
            "policy",
            "signature",
        }

    # criterio: 04-C16
    def test_facade_smoke(self) -> None:
        payload = load_payload("upload_new_attachment_response.json")
        ticket = UploadTicket.from_dict(payload)
        assert ticket.raw is not None
        assert ticket.content_ref == payload["contentRef"]
        uploaded = UploadedAttachment(ticket, name="nota.txt", mime_type="text/plain")
        assert uploaded.raw is ticket.raw
        assert uploaded.as_write_input()["contentRef"] == payload["contentRef"]


# ---------------------------------------------------------------------------
# 22. Admin write: users and groups (spec 05)
# ---------------------------------------------------------------------------

_CREATED_USER_ID_CONTRACT = 1043
_CREATED_GROUP_ID_CONTRACT = 202
_CONFLICT_GROUP_ID_CONTRACT = 202


class TestAdminUsersWriteDTOs:
    # criterio: 05-C22
    @pytest.mark.parametrize(
        ("definition", "model"),
        [
            ("CreateUserRequestDTO", generated.CreateUserRequestDTO),
            ("CreateUserResponseDTO", generated.CreateUserResponseDTO),
            ("EditUserRequestDTO", generated.EditUserRequestDTO),
            ("EditUserResponseDTO", generated.EditUserResponseDTO),
            ("EditUserCredentialsRequestDTO", generated.EditUserCredentialsRequestDTO),
            ("EditUserCredentialsResponseDTO", generated.EditUserCredentialsResponseDTO),
        ],
    )
    def test_schema_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(swagger_definitions, definition, model)

    # criterio: 05-C22
    @pytest.mark.parametrize(
        ("definition", "model"),
        [
            ("UserCredentialsConfigurationDTO", generated.UserCredentialsConfigurationDTO1),
            (
                "ResetUserCustomCredentialsCommandDTO",
                generated.ResetUserCustomCredentialsCommandDTO1,
            ),
            ("AdminUserPreferencesDTO", generated.AdminUserPreferencesDTO),
            ("UserInfoDTO", generated.UserInfoDTO1),
            ("UserSettingsRequestDTO", generated.UserSettingsRequestDTO1),
            (
                "CustomUserCredentialsConfigurationDTO",
                generated.CustomUserCredentialsConfigurationDTOModel,
            ),
        ],
    )
    def test_typed_stub_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(
            swagger_definitions, definition, model, note="typed variant of RootModel stub"
        )

    # criterio: 05-C22
    def test_fixtures_parse(self) -> None:
        created = generated.CreateUserResponseDTO.model_validate(
            load_payload("create_user_response.json")
        )
        assert created.userId == _CREATED_USER_ID_CONTRACT
        assert created.generatedPassword == ["Xk7-fake-pw"]
        edited = generated.EditUserResponseDTO.model_validate(
            load_payload("edit_user_response.json")
        )
        assert edited.nextOccToken is not None
        credentials = generated.EditUserCredentialsResponseDTO.model_validate(
            load_payload("edit_user_credentials_response.json")
        )
        assert credentials.nextOccToken is not None


class TestAdminGroupsWriteDTOs:
    # criterio: 05-C22
    @pytest.mark.parametrize(
        ("definition", "model"),
        [
            ("CreateGroupRequestDTO", generated.CreateGroupRequestDTO),
            ("CreateGroupResponseDTO", generated.CreateGroupResponseDTO),
            ("EditGroupRequestDTO", generated.EditGroupRequestDTO),
            ("EditGroupResponseDTO", generated.EditGroupResponseDTO),
            ("EditMultipleGroupsMembersRequestDTO", generated.EditMultipleGroupsMembersRequestDTO),
            ("EditGroupMembersRequestDTO", generated.EditGroupMembersRequestDTO),
            (
                "EditMultipleGroupsMembersResponseDTO",
                generated.EditMultipleGroupsMembersResponseDTO,
            ),
        ],
    )
    def test_schema_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
        definition: str,
        model: type,
    ) -> None:
        assert_superset(swagger_definitions, definition, model)

    # criterio: 05-C22
    def test_typed_stub_superset(
        self,
        swagger_definitions: dict,  # type: ignore[type-arg]
    ) -> None:
        assert_superset(
            swagger_definitions,
            "GroupDTO",
            generated.GroupDTOModel,
            note="typed variant of RootModel stub",
        )

    # criterio: 05-C22
    def test_fixtures_parse(self) -> None:
        created = generated.CreateGroupResponseDTO.model_validate(
            load_payload("create_group_response.json")
        )
        assert created.groupId == _CREATED_GROUP_ID_CONTRACT
        edited = generated.EditGroupResponseDTO.model_validate(
            load_payload("edit_group_response.json")
        )
        assert edited.nextOccToken is not None
        members = generated.EditMultipleGroupsMembersResponseDTO.model_validate(
            load_payload("edit_groups_members_response.json")
        )
        assert members.successGroups is not None
        assert members.concurrencyErrorGroups is not None
        conflict = generated.GroupDTOModel.model_validate(members.concurrencyErrorGroups[0].root)
        assert conflict.id == _CONFLICT_GROUP_ID_CONTRACT
