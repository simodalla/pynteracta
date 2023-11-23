from pydantic import HttpUrl

from .core import InteractaOut, ItemCreatedEditedOut, PagedItemsOut
from .models import (
    BaseListPostsElement,
    Catalog,
    CatalogEntry,
    Group,
    Hashtag,
    ListSystemGroupsElement,
    ListSystemUsersElement,
    Post,
    PostDefinition,
    PostDetail,
    PostWorkflowDefinitionState,
    PostWorkflowDefinitionTransition,
    Tag,
    User,
    UserInfo,
)
from .requests import UserEditBase, UserSettingsIn


class ListSystemGroupsOut(PagedItemsOut):
    # ListSystemGroupsResponseDTO
    items: list[ListSystemGroupsElement] | None = []


class ListSystemUsersOut(PagedItemsOut):
    # ListSystemUsersResponseDTO
    items: list[ListSystemUsersElement] | None


class ListUsersOut(PagedItemsOut):
    # ListUsersResponseDTO ##OK##
    items: list[User] | None


class ListGroupMembersOut(PagedItemsOut):
    # ListGroupMembersResponseDTO
    items: list[User] | None = []


class ListPostDefinitionCatalogEntriesOut(PagedItemsOut):
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


class PostsOut(PagedItemsOut):
    # PagedListPostsResponseDTO
    items: list[BaseListPostsElement] | None = []


class HashtagsOut(PagedItemsOut):
    items: list[Hashtag] | None = []


class PostCreatedOut(InteractaOut):
    # CreatePostResponseDTO
    post_id: int
    next_occ_token: int | None = None
    post_data: PostDetail | None = None


class GetPostDefinitionOut(InteractaOut, PostDefinition):
    # -- GetPostDefinitionResponseDTO
    pass


class ExecutePostWorkflowOperationResponse(InteractaOut):
    # ExecutePostWorkflowOperationResponseDTO
    new_current_state: PostWorkflowDefinitionState | None = None
    new_screen_data: dict | None = None
    new_current_workflow_permitted_operations: list[PostWorkflowDefinitionTransition] | None = None
    new_can_edit_workflow_screen_data: bool | None = None
    new_last_modify_timestamp: int | None = None
    post_data_has_changed: bool | None = None


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
