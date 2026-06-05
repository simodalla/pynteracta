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

from pynteracta.models.facade.attachments import (
    AttachmentDetail,
    AttachmentVisibility,
    PostAttachmentList,
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
from pynteracta.models.facade.tasks import Task
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
