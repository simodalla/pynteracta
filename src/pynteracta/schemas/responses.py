from .core import PagedItemsOut, SchemaOut
from .models import (
    BaseListPostsElement,
    Group,
    Hashtag,
    ListSystemGroupsElement,
    ListSystemUsersElement,
    Post,
    PostDefinition,
    PostDetail,
    PostWorkflowDefinitionState,
    User,
)


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


class PostDetailOut(SchemaOut, Post):
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


class PostCreatedOut(SchemaOut):
    # CreatePostResponseDTO
    post_id: int
    next_occ_token: int | None = None
    post_data: PostDetail | None = None


class GetPostDefinitionOut(SchemaOut, PostDefinition):
    # -- GetPostDefinitionResponseDTO
    pass
