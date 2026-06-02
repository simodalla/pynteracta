# SPDX-License-Identifier: Apache-2.0
"""Facade models for the pynteracta endpoints."""

from pynteracta.models.facade.auth import (
    CreateAccessTokenByServiceAccountRequestDTO,
    CurrentUserResponse,
    GoogleOAuth2AccessTokenResponse,
    ServiceAccountTokenResponse,
)
from pynteracta.models.facade.catalogs import (
    Catalog,
    CatalogEntry,
    CatalogEntryList,
    CatalogList,
    GetPostDefinitionCatalogsRequestDTO,
    ListPostDefinitionCatalogEntriesRequestDTO,
)
from pynteracta.models.facade.communities import (
    Community,
    CommunityDetail,
    CommunityList,
    FieldType,
    ListCommunitiesRequestDTO,
    PostDefinition,
    PostDefinitionMap,
    PostFieldDefinition,
)
from pynteracta.models.facade.posts import (
    ListCommunityPostsFilteredRequestDTO,
    ListPostCommentsRequestDTO,
    Post,
    PostCommentList,
    PostList,
)
from pynteracta.models.facade.users import (
    ListSystemUsersRequestDTO,
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
