from datetime import datetime

from pydantic import BaseModel, PrivateAttr
from pydantic.typing import Any

from ..utils import to_camel


class InteractaModel(BaseModel):
    class Config:
        alias_generator = to_camel


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


class User(InteractaModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    contact_rmail: str | None
    google_acountId: str | None
    microsoft_accountId: str | None
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
    highResAccountPhotoUrl: str | None
    accountPhotoUrl: str | None
    customPhotoUrl: str | None
    googlePhotoUrl: str | None
    microsoftPhotoUrl: str | None
    privateEmail: str | None
    privateEmailVerified: bool | None
    phone: str | None
    internalPhone: str | None
    mobilePhone: str | None
    place: str | None
    biography: str | None
    businessUnit: BusinessUnit | None
    area: Area | None
    role: str | None
    manager: User | None
    employees: list[User] | None
    language: Language | None
    timezone: Timezone | None
    emailNotificationsEnabled: bool | None
    occToken: int | None
    canManageProfilePhoto: bool | None
    editProfile: bool | None


class UserFull(User):
    loginProviders: list[str] | None
    lastAccessTimestamp: datetime | None
    userProfileInfo: UserProfile | None


class Post(InteractaModel):
    id: int
    community_id: int
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


class DriveAttachment(BaseModel):
    driveId: str = ""
    mimeType: str | None = None
    size: int | None = None
    webViewLink: str | None = None
    webContentLink: str | None = None


# Out Models


class ItemsOut(SchemaOut):
    items: list | None = []
    next_page_token: str | None = None
    total_items_count: int | None = None


class PostsOut(ItemsOut):
    items: list[Post] | None = []


class PostDetailOut(SchemaOut, Post):
    current_workflow_state: Any | None = None
    current_workflow_screen_data: Any | None = None
    mentions: Any | None = None
    comment_mentions: Any | None = None
    watchers: list[User] | None = None
    watcher_users: list[User] | None = None
    watcher_groups: list[dict] | None = None  # <-- creare model
    hashtags: list[dict] | None = None  # <-- creare model
    attachments_count: int | None = None


class UsersOut(ItemsOut):
    items: list[UserFull] | None


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
