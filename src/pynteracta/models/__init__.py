# SPDX-License-Identifier: Apache-2.0
"""Public model re-exports.

Consumers import from ``pynteracta.models``, not from ``generated/`` directly.
Generated models remain accessible via ``pynteracta.models.generated.external_v2``
as the documented escape hatch.
"""

from pynteracta.models.facade import (
    Catalog,
    CatalogEntry,
    CatalogEntryList,
    CatalogList,
    Community,
    CommunityDetail,
    CommunityList,
    CreateAccessTokenByServiceAccountRequestDTO,
    CurrentUserResponse,
    FieldType,
    GetPostDefinitionCatalogsRequestDTO,
    GoogleOAuth2AccessTokenResponse,
    ListCommunitiesRequestDTO,
    ListCommunityPostsFilteredRequestDTO,
    ListPostCommentsRequestDTO,
    ListPostDefinitionCatalogEntriesRequestDTO,
    ListSystemUsersRequestDTO,
    Post,
    PostCommentList,
    PostDefinition,
    PostDefinitionMap,
    PostFieldDefinition,
    PostList,
    ServiceAccountTokenResponse,
    SystemUserList,
    UserForEdit,
    UserProfile,
)

__all__ = [
    "Catalog",
    "CatalogEntry",
    "CatalogEntryList",
    "CatalogList",
    "Community",
    "CommunityDetail",
    "CommunityList",
    "CreateAccessTokenByServiceAccountRequestDTO",
    "CurrentUserResponse",
    "FieldType",
    "GetPostDefinitionCatalogsRequestDTO",
    "GoogleOAuth2AccessTokenResponse",
    "ListCommunitiesRequestDTO",
    "ListCommunityPostsFilteredRequestDTO",
    "ListPostCommentsRequestDTO",
    "ListPostDefinitionCatalogEntriesRequestDTO",
    "ListSystemUsersRequestDTO",
    "Post",
    "PostCommentList",
    "PostDefinition",
    "PostDefinitionMap",
    "PostFieldDefinition",
    "PostList",
    "ServiceAccountTokenResponse",
    "SystemUserList",
    "UserForEdit",
    "UserProfile",
]
