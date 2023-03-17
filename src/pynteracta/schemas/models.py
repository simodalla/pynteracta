from datetime import datetime

from pydantic import BaseModel, PrivateAttr
from pydantic.typing import Any

from ..utils import to_camel


class InteractaModel(BaseModel):
    class Config:
        alias_generator = to_camel


class Link(BaseModel):
    label: str = ""
    url: str = ""


class SchemaOut(InteractaModel):
    _response: Any = PrivateAttr(None)


class BusinessUnit(InteractaModel):
    id: int
    name: str
    external_id: str | None = None


class Area(InteractaModel):
    id: int
    name: str
    external_id: str | None


class Language(InteractaModel):
    code: str | None
    description: str | None


class Timezone(InteractaModel):
    id: int | None
    code: str | None
    zone_id: str | None
    description: str | None


class Group(InteractaModel):
    id: int
    name: str = ""
    email: str | None
    visible: bool | None
    deleted: bool | None
    external_id: str | None
    occ_token: int | None
    members_count: int | None


class User(InteractaModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    contact_email: str | None
    google_account_id: str | None
    microsoft_account_id: str | None
    service_account: bool | None
    system_account: bool | None
    activeDWD: bool | None
    account_photo_url: str | None
    deleted: bool | None
    blocked: bool | None
    external_id: str | None
    private_profile: bool | None
    licences: dict | None


class UserProfile(User):
    high_res_account_photo_url: str | None
    account_photo_url: str | None
    custom_photo_url: str | None
    google_photo_url: str | None
    microsoft_photo_url: str | None
    private_email: str | None
    private_email_verified: bool | None
    phone: str | None
    internal_phone: str | None
    mobile_phone: str | None
    place: str | None
    biography: str | None
    business_unit: BusinessUnit | None
    area: Area | None
    role: str | None
    manager: User | None
    employees: list[User] | None
    language: Language | None
    timezone: Timezone | None
    email_notifications_enabled: bool | None
    occ_token: int | None
    can_manage_profile_photo: bool | None
    edit_profile: bool | None


class UserFull(User):
    login_providers: list[str] | None
    last_access_timestamp: datetime | None
    user_profile_info: UserProfile | None


class Post(InteractaModel):
    id: int = 0
    community_id: int = 0
    custom_id: str | None = None
    title: str = ""
    description_plain_text: str | None = None
    description_delta: str | None = None
    visibility: int | None = None
    announcement: bool | None = None
    workflow_state_description: str | None = None
    workflow_state_color: str | None = None
    custom_data: Any | None = None
    creator_user: User | None = None
    creation_timestamp: datetime | None = None
    last_modify_user: User | None = None
    last_modify_timestamp: datetime | None = None
    last_operation_timestamp: datetime | None = None
    main_attachment: dict | None = None
    watchers_count: int | None = None
    image_attachments_count: int | None = None
    video_attachments_count: int | None = None
    comments_count: int | None = None
    tasks_count: int | None = None
    total_standard_tasks_count: int | None = None
    views_count: int | None = None
    viewed_by_users_count: int | None = None
    show_like_section: bool | None = None
    likes_count: int | None = None
    viewed_by_me: bool | None = None
    liked_by_me: bool | None = None
    followed_by_me: bool | None = None
    capabilities: dict | None = None
    cover_image: dict | None = None


class DriveAttachment(InteractaModel):
    drive_id: str = ""
    mime_type: str | None = None
    size: int | None = None
    web_view_link: str | None = None
    web_content_link: str | None = None


class Hashtag(InteractaModel):
    id: int
    name: str | None = None
    community_id: int | None = None
    external_id: str | None = None
    deleted: bool | None = None


class EnumValue(InteractaModel):
    id: int
    label: str | None = None
    external_id: str | None = None
    parent_ids: list[int] | None = None
    deleted: bool | None = None


class FieldDefinition(InteractaModel):
    id: int
    name: str | None = None
    label: str | None = None
    description: str | None = None
    type: int | None = None
    parent_id: int | None = None
    required: bool | None = None
    readonly: bool | None = None
    searchable: bool | None = None
    sortable: bool | None = None
    visible_in_preview: bool | None = None
    visible_in_detail: bool | None = None
    visible_in_create: bool | None = None
    visible_in_edit: bool | None = None
    external_id: str | None = None
    enum_values: list[EnumValue] | None = None
    metadata: dict | None = None
    validations: list[dict] | None = None


class CommunityDefinition(InteractaModel):
    community_id: int
    workflow_definition: dict | None = None  # creare model
    title_enabled: int | None = None
    description_enabled: int | None = None
    watchers_enabled: int | None = None
    watchers_visible_in_preview: bool | None = None
    manual_author_enabled: bool | None = None
    hash_tag_enabled: bool | None = None
    attachment_enabled: bool | None = None
    like_enabled: bool | None = None
    offline_Enabled: bool | None = None
    custom_fields_enabled: bool | None = None
    attachment_max_size: int | None = None
    field_definitions: list[FieldDefinition] | None = None
    hashtags: list[Hashtag] | None = None
    default_post_visibility: int | None = None
    post_views: list[dict] | None = None  # creare model
    community_relations: list[dict] | None = None  # creare model
    inverse_community_relations: list[dict] | None = None  # creare model
    acknowledge_task_enabled: bool | None = None


class PostDetail(Post):
    current_workflow_state: Any | None = None
    current_workflow_screen_data: Any | None = None
    mentions: Any | None = None
    comment_mentions: Any | None = None
    watchers: list[User] | None = None
    watcher_users: list[User] | None = None
    watcher_groups: list[dict] | None = None  # <-- creare model
    hashtags: list[dict] | None = None  # <-- creare model
    attachments_count: int | None = None


# Out Models


class ItemsOut(SchemaOut):
    items: list | None = []
    next_page_token: str | None = None
    total_items_count: int | None = None

    def count(self):
        if not self.items:
            return 0
        return len(self.items)

    def has_items(self):
        if self.count():
            return True
        return False


class PostsOut(ItemsOut):
    items: list[Post] | None = []


class PostDetailOut(SchemaOut, PostDetail):
    pass


class UsersOut(ItemsOut):
    items: list[UserFull] | None


class GroupsOut(ItemsOut):
    items: list[Group] | None = []


class GroupMembersOut(ItemsOut):
    items: list[User] | None = []


class HashtagsOut(ItemsOut):
    items: list[Hashtag] | None = []


class PostDefinitionOut(SchemaOut, CommunityDefinition):
    pass


class PostCreatedOut(SchemaOut):
    post_id: int
    next_occ_token: int | None = None
    post_data: PostDetail | None = None


# In Models


class AttachmentIn(BaseModel):
    type: int | None = None
    attachmentId: int | None = None
    name: str | None = None
    contentRef: str | None = None
    referencedAttachmentId: int | None = None
    hashtagIds: list[int] | None = None
    drive: DriveAttachment | None = None


class PostIn(BaseModel):
    title: str
    description: str | None
    descriptionFormat: bool | None
    customData: dict | None
    deltaAreaFormat: bool | None
    attachments: list[AttachmentIn] | None
    watcherUserIds: list[int] | None
    workflowInitStateId: int | None
    visibility: int | None
    announcement: bool | None
    # clientUid: str | None = ""
    # draft: bool | None = None
    # # scheduledPublication --> {"datetime": "string", "timezone": "string"
    # scheduledPublication: dict | None = None
