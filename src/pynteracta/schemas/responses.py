from datetime import datetime

from pydantic import HttpUrl

from .core import InteractaOut, ItemCreatedEditedOut, PaginatedOut
from .models import (
    BaseListPostsElement,
    Catalog,
    CatalogEntry,
    Community,
    Group,
    Hashtag,
    ListSystemGroupsElement,
    ListSystemUsersElement,
    Post,
    PostComment,
    PostDefinition,
    PostDetail,
    PostEditableContentData,
    PostWorkflowDefinitionState,
    PostWorkflowDefinitionTransition,
    Tag,
    User,
    UserInfo,
    WorkflowDefinitionScreen,
)
from .requests import UserEditBase, UserSettingsIn


class GetCommunityDetailsOut(InteractaOut):
    community: Community | None = None


class GetCustomPostForEditOut(InteractaOut):
    # -- GetCustomPostForEditResponseDTO
    content_data: PostEditableContentData | None = None
    occ_token: int
    community_id: int
    custom_id: str | None = None
    current_workflow_state: PostWorkflowDefinitionState | None = None
    creator_user: User | None = None
    creation_timestamp: datetime | None = None
    last_modify_user: User | None = None
    last_modify_timestamp: datetime | None = None
    last_operation_timestamp: datetime | None = None


class ListSystemGroupsOut(PaginatedOut):
    # ListSystemGroupsResponseDTO
    items: list[ListSystemGroupsElement] | None = []


class ListSystemUsersOut(PaginatedOut):
    # ListSystemUsersResponseDTO
    items: list[ListSystemUsersElement] | None


class ListUsersOut(PaginatedOut):
    # ListUsersResponseDTO ##OK##
    items: list[User] | None


class ListGroupMembersOut(PaginatedOut):
    # ListGroupMembersResponseDTO
    items: list[User] | None = []


class ListPostDefinitionCatalogEntriesOut(PaginatedOut):
    # ListPostDefinitionCatalogEntriesResponseDTO
    items: list[CatalogEntry] | None = []


class PostDetailOut(InteractaOut, Post):
    # GetPostDetailResponseDTO
    current_workflow_state: PostWorkflowDefinitionState | None = None
    current_workflow_screen_data: dict | None = None
    mentions: list[User] | None = None
    comment_mentions: ListUsersOut | None = None
    watchers: list[User] | None = None
    watcher_users: list[User] | None = None
    watcher_groups: list[Group] | None = None
    hashtags: list[Hashtag] | None = None


class PostsOut(PaginatedOut):
    # PagedListPostsResponseDTO
    items: list[BaseListPostsElement] | None = []


class HashtagsOut(PaginatedOut):
    items: list[Hashtag] | None = []


class PostCreatedOut(InteractaOut):
    # CreatePostResponseDTO
    post_id: int
    next_occ_token: int | None = None
    post_data: PostDetail | None = None


class GetPostDefinitionOut(InteractaOut, PostDefinition):
    # -- GetPostDefinitionResponseDTO
    pass


class GetPostWorkflowScreenDataForEditOut(InteractaOut):
    # GetPostWorkflowScreenDataForEditResponseDTO
    screen_data: dict | None = None
    screen_occ_token: int | None = None
    screen: WorkflowDefinitionScreen | None = None
    current_workflow_state: PostWorkflowDefinitionState | None = None


class EditPostWorkflowOut(InteractaOut):
    new_screen_data: dict | None = None
    new_last_modify_timestamp: int | None = None
    post_data_has_changed: bool | None = None


class ExecutePostWorkflowOperationOut(EditPostWorkflowOut):
    # ExecutePostWorkflowOperationResponseDTO
    new_current_state: PostWorkflowDefinitionState | None = None
    new_current_workflow_permitted_operations: list[PostWorkflowDefinitionTransition] | None = None
    new_can_edit_workflow_screen_data: bool | None = None


class EditPostWorkflowScreenDataOut(EditPostWorkflowOut):
    # EditPostWorkflowScreenDataResponseDTO
    next_screen_occ_token: int | None = None


class CreateUserOut(InteractaOut):
    # CreateUserResponseDTO
    # ID dell'utente creato.
    user_id: int
    # Url dell'immagine utente.
    account_photo_url: HttpUrl | None = None
    # Nel caso in cui sono state create delle crenziali custom (username / password) riporta
    # la password generata.
    generated_password: list[str] | None = None
    # Nel caso in cui sono state create delle crenziali custom (username / password) indica se le
    # credenziali devono essere cambiate al prossimo login.
    expired_credentials: bool | None = None
    # Nel caso in cui sono state create delle crenziali custom (username / password) indica se è
    # stata spedita un'email di notifica.
    sent_email_notify: bool | None = None
    # Token per il controllo della conconcorrenza
    next_occ_token: int | None = None


class UserSettingsOut(UserSettingsIn):
    # UserSettingsResponseDTO
    edit_private_email_enabled: bool | None = None


class GetUserForEditOut(InteractaOut, UserEditBase):
    # GetUserForEditResponseDTO
    private_email_verified: bool | None = None
    occ_token: int | None = None
    blocked: bool | None = None
    user_settings: UserSettingsOut | None = None
    user_info: UserInfo | None = None


class EditUserOut(ItemCreatedEditedOut):
    # EditUserResponseDTO
    account_photo_url: str | None = None


class CreateGroupOut(Group, ItemCreatedEditedOut):
    # CreateGroupResponseDTO
    tags: list[dict] | None = None
    group_id: int | None = None


class EditGroupOut(ItemCreatedEditedOut):
    # EditGroupResponseDTO
    pass


class GetGroupForEditOut(InteractaOut, Group):
    # GetGroupForEditResponseDTO
    members: list[User] | None = None
    tags: list[Tag] | None = None


class GetPostDefinitionCatalogsOut(InteractaOut):
    # GetPostDefinitionCatalogsResponseDTO
    catalogs: list[Catalog] | None = None


class DeletePostOut(InteractaOut):
    # DeletePostResponseDTO
    post_id: int


class ListPostCommentsOut(PaginatedOut):
    # ListPostCommentsResponseDTO
    items: list[PostComment] | None = []


class CreatePostCommentOut(InteractaOut):
    # CreatePostCommentResponseDTO
    comment: PostComment
