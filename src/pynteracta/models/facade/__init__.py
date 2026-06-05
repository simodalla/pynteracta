# SPDX-License-Identifier: Apache-2.0
"""Facade models for the pynteracta endpoints."""

from pynteracta.models.facade.attachments import (
    AttachmentDetail,
    AttachmentVisibility,
    PostAttachment,
    PostAttachmentList,
)
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
    CheckVisibilityRequestDTO,
    GlobalPostStream,
    ListCommunityPostsFilteredRequestDTO,
    ListCommunityPostsRequestDTO,
    ListPostCommentsRequestDTO,
    ListPostHistoryEventsRequestDTO,
    Post,
    PostCapabilities,
    PostCommentList,
    PostHistoryEventList,
    PostList,
    VisibilityResult,
)
from pynteracta.models.facade.tasks import (
    SubTask,
    Task,
    TaskCapabilities,
    TaskReminder,
)
from pynteracta.models.facade.users import (
    ListSystemUsersRequestDTO,
    SystemUserList,
    UserForEdit,
    UserProfile,
)

__all__ = [
    "AttachmentDetail",
    "AttachmentVisibility",
    "Catalog",
    "CatalogEntry",
    "CatalogEntryList",
    "CatalogList",
    "CheckVisibilityRequestDTO",
    "Community",
    "CommunityDetail",
    "CommunityList",
    "CreateAccessTokenByServiceAccountRequestDTO",
    "CurrentUserResponse",
    "FieldType",
    "GetPostDefinitionCatalogsRequestDTO",
    "GlobalPostStream",
    "GoogleOAuth2AccessTokenResponse",
    "ListCommunitiesRequestDTO",
    "ListCommunityPostsFilteredRequestDTO",
    "ListCommunityPostsRequestDTO",
    "ListPostCommentsRequestDTO",
    "ListPostDefinitionCatalogEntriesRequestDTO",
    "ListPostHistoryEventsRequestDTO",
    "ListSystemUsersRequestDTO",
    "Post",
    "PostAttachment",
    "PostAttachmentList",
    "PostCapabilities",
    "PostCommentList",
    "PostDefinition",
    "PostDefinitionMap",
    "PostFieldDefinition",
    "PostHistoryEventList",
    "PostList",
    "ServiceAccountTokenResponse",
    "SubTask",
    "SystemUserList",
    "Task",
    "TaskCapabilities",
    "TaskReminder",
    "UserForEdit",
    "UserProfile",
    "VisibilityResult",
]
