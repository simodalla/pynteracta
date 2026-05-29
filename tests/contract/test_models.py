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

from pynteracta.models.facade.auth import CurrentUserResponse, ServiceAccountTokenResponse
from pynteracta.models.facade.posts import Post, PostCommentList, PostList
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
