from datetime import datetime
from datetime import datetime as type_datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr

from ..enums import FieldFilterTypeEnum, FieldTypeEnum
from ..exceptions import ObjectDoesNotFound
from .core import InteractaModel, InteractaOut


class Link(BaseModel):
    label: str | None = None
    url: str | None = None


class AdminUserPreferences(InteractaModel):
    # AdminUserPreferencesDTO
    default_language_id: str | None = None
    default_timezone_id: int | None = None
    email_notifications_enabled: bool = True


class GoogleUserCredentialsConfiguration(InteractaModel):
    # GoogleUserCredentialsConfigurationDTO
    # Email autenticazione tramite servizi esterno Google
    google_account_id: str | None = None
    enabled: bool | None = None
    profile_photo_url: str | None = None


class MicrosoftUserCredentialsConfiguration(InteractaModel):
    # MicrosoftUserCredentialsConfigurationDTO
    # Email autenticazione tramite servizi esterno Microsoft
    microsoft_account_id: str | None = None
    enabled: bool | None = None
    profile_photo_url: str | None = None


class CustomUserCredentialsConfiguration(InteractaModel):
    # CustomUserCredentialsConfigurationDTO
    username: str | None = None
    can_user_manage_custom_credentials: bool | None = None
    active: bool | None = None
    profile_photo_url: str | None = None
    profile_photo: dict | None = None
    can_manage_profile_photo: bool | None = None


class UserCredentialsConfiguration(InteractaModel):
    # UserCredentialsConfigurationDTO
    google: GoogleUserCredentialsConfiguration | None = None
    microsoft: MicrosoftUserCredentialsConfiguration | None = None
    custom: CustomUserCredentialsConfiguration | None = None


class ResetUserCustomCredentialsCommand(InteractaModel):
    # ResetUserCustomCredentialsCommandDTO
    # Genera una password.
    generate_password: bool | None = None
    # Password da impostare. Campo da impostare nel caso in cui 'generatePassword' = false.
    password: list[str]
    # Indica se le credenziali devono essere cambiate al prossimo login.
    force_credentials_expiration: bool | None = None
    # Indica se è stata spedita un'email di notifica.
    email_notify_recipients: list[str]


class Language(InteractaModel):
    # LanguageDTO
    code: str | None = None
    description: str | None = None


class Timezone(InteractaModel):
    # TimezoneDTO
    id: int
    code: str | None = None
    zone_id: str | None = None
    description: str | None = None


class ZonedDatetime(InteractaModel):
    zoned_datetime: datetime | None = None
    local_datetime: datetime | None = None
    timezone: str | None = None


class GroupBase(InteractaModel):
    name: str | None = None
    email: str | None = None
    visible: bool | None = None
    external_id: str | None = None


class Group(GroupBase):
    # GroupDTO ##OK##
    id: int
    deleted: bool | None = None
    occ_token: int | None = None
    members_count: int | None = None


class ListSystemGroupsElement(Group):
    # ListSystemGroupsElementDTO
    pass


class UserBase(InteractaModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    account_photo_url: str | None = None
    contact_email: EmailStr | None = None


class User(UserBase):
    # UserDTO ##OK##
    google_account_id: str | None = None
    microsoft_account_id: str | None = None
    service_account: bool | None = None
    system_account: bool | None = None
    active_dwd: bool | None = None
    deleted: bool | None = None
    blocked: bool | None = None
    external_id: str | None = None
    private_profile: bool | None = None
    licences: dict | None = None  # LicenseDTO


class UserInfoBase(InteractaModel):
    id: int
    name: str | None = None
    external_id: str | None = None


class UserInfoBusinessUnit(UserInfoBase):
    # UserInfoBusinessUnitDTO
    pass


class UserInfoArea(UserInfoBase):
    # UserInfoAreaDTO
    pass


class UserProfileInfo(UserBase):
    # UserProfileInfoDTO
    high_res_account_photo_url: str | None = None
    custom_photo_url: str | None = None
    google_photo_url: str | None = None
    microsoft_photo_url: str | None = None
    private_email: EmailStr | None = None
    private_email_verified: bool | None = None
    phone: str | None = None
    internal_phone: str | None = None
    mobile_phone: str | None = None
    place: str | None = None
    biography: str | None = None
    business_unit: UserInfoBusinessUnit | None = None
    area: UserInfoArea | None = None
    role: str | None = None
    manager: User | None = None
    employees: list[User] | None = None
    language: Language | None = None
    timezone: Timezone | None = None
    email_notifications_enabled: bool | None = None
    deleted: bool | None = None
    blocked: bool | None = None
    occ_token: int | None = None
    can_manage_profile_photo: bool | None = None
    edit_profile: bool | None = None
    private_profile: bool | None = None


class DONTUSEUserInfo(InteractaModel):
    # UserInfoDTO
    area: UserInfoArea | None = None
    business_unit: UserInfoBusinessUnit | None = None
    private_email: EmailStr | None = None
    private_email_verified: bool | None = None
    private_email_verification_required: bool | None = None


class UserInfo(InteractaModel):
    # UserInfoDTO
    area: UserInfoArea | None = None
    biography: str | None = None
    business_unit: UserInfoBusinessUnit | None = None
    internal_phone: str | None = None
    manager: User | None = None
    mobile_phone: str | None = None
    phone: str | None = None
    place: str | None = None
    role: str | None = None


class ListSystemUsersElement(User):
    # ListSystemUsersElementDTO
    login_providers: list[str] | None = None  # [ CUSTOM, GOOGLE, MICROSOFT ]
    last_access_timestamp: datetime | None = None
    user_profile_info: UserProfileInfo | None = None  # UserProfileInfoDTO


class UserFull(User):
    login_providers: list[str] | None
    last_access_timestamp: datetime | None
    user_profile_info: UserProfileInfo | None


class DriveAttachmentData(InteractaModel):
    # DriveAttachmentDataDTO
    drive_id: str = ""
    mime_type: str | None = None
    size: int | None = None
    web_view_link: str | None = None
    web_content_link: str | None = None


class TagBase(InteractaModel):
    id: int
    name: str | None = None
    deleted: bool | None = None


class Hashtag(TagBase):
    # HashtagDTO ##OK##
    external_id: str | None = None


class Tag(TagBase):
    # TagDTO
    visible: str | None = None


class ZonedDatetimeIn(InteractaModel):
    # ZonedDatetimeInputDTO
    datetime: type_datetime = None
    timezone: str | None = None


class PostAttachmentData(InteractaModel):
    # PostAttachmentDataDTO ##OK##
    id: int
    temporary_content_view_link: str | None = None
    temporary_content_download_link: str | None = None
    temporary_content_preview_image_link: str | None
    temporary_content_preview_image_animated_link: str | None = None
    temporary_content_preview_image_hi_res_link: str | None = None
    temporary_content_preview_image_hi_des_animated_link: str | None = None
    version_number: int | None = None
    type: int | None = None
    content_ref: str | None = None
    content_mime_type: str | None = None
    etag: str | None = None
    md5_hash: str | None = None
    size: int | None = None
    creator_user: User | None = None
    creation_timestamp: int | None = None
    hashtags: list[Hashtag] = []
    reference: bool = False
    drive: dict | None = None


class PostWorkflowDefinitionState(InteractaModel):
    #  PostWorkflowDefinitionStateDTO
    id: int
    init_state: bool | None = None
    name: str = ""
    metadata: dict | None = None
    terminal: bool | None = None
    deleted: bool | None = None


class Post(InteractaModel):
    # ROOT
    id: int = 0
    community_id: int = 0
    custom_id: str | None = None
    title: str = ""
    description_plain_text: str | None = None
    description_delta: str | None = None
    visibility: int | None = None
    announcement: bool | None = None
    custom_data: Any | None = None
    creator_user: User | None = None
    creation_timestamp: datetime | None = None
    last_modify_user: User | None = None
    last_modify_timestamp: datetime | None = None
    last_operation_timestamp: datetime | None = None
    main_attachment: PostAttachmentData | None = None
    attachments_count: int | None = None
    image_attachments_count: int | None = None
    video_attachments_count: int | None = None
    comments_count: int | None = None
    views_count: int | None = None
    viewed_by_users_count: int | None = None
    show_like_section: bool | None = None
    likes_count: int | None = None
    liked_by_me: bool | None = None
    tasks_count: int | None = None
    followed_by_me: bool | None = None
    total_standard_tasks_count: int | None = None

    def get_absolute_url(self, base_url: str | None = None):
        url = f"post/{self.id}"
        if base_url:
            url = f"{base_url}{url}"
        return url


class BaseListPostsElement(Post):
    # BaseListPostsElementDTO
    workflow_state_description: str | None = None
    workflow_state_color: str | None = None
    watchers_count: int | None = None
    viewed_by_me: bool | None = None
    capabilities: dict | None = None
    cover_image: dict | None = None  # PostCoverImageDTO


class PostDetail(Post):
    # PostDetailDTO
    current_workflow_state: PostWorkflowDefinitionState | None = None
    current_workflow_screen_data: dict | None = None
    attachments: list[dict] | None = None  # PostAttachmentDataDTO
    mentions: list[User] | None = None
    watchers: list[User] | None = None
    watcher_users: list[User] | None = None
    watcher_groups: list[Group] | None = None
    hashtags: list[Hashtag] | None = None  # HashtagDTO
    cover_image: dict | None = None  # PostCoverImageDTO
    draft: bool = False  # Creazione in stato bozza/pubblicato
    draft_data: dict | None = None  # DraftPostDataDTO
    scheduled_publication: ZonedDatetimeIn | None = None
    # Info stato del post programmato [1=SUCCESS, 2=FAILED]
    scheduled_publication_result: int | None = None


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


class FieldMetadata(InteractaModel):
    model_config = ConfigDict(extra="allow")

    catalog_id: int | None = None
    hierarchical: bool | None = None
    generic_entity_list_config_id: str | None = None
    community_id: int | None = None


class FieldBase(InteractaModel):
    id: int
    name: str | None = None
    label: str | None = None
    type: FieldTypeEnum | None = None
    required: bool | None = None
    searchable: bool | None = None
    sortable: bool | None = None
    enum_values: list[EnumValue] | None = None
    metadata: FieldMetadata | None = None

    @property
    def catalog_id(self):
        return self.metadata.catalog_id


class FieldDefinition(FieldBase):
    description: str | None = None
    parent_id: int | None = None
    readonly: bool | None = None
    visible_in_preview: bool | None = None
    visible_in_detail: bool | None = None
    visible_in_create: bool | None = None
    visible_in_edit: bool | None = None
    external_id: str | None = None
    validations: list[dict] | None = None


class PostWorkflowDefinitionScreenFieldAssociation(FieldBase):
    # PostWorkflowDefinitionScreenFieldAssociation
    pass


class WorkflowDefinitionScreen(InteractaModel):
    # WorkflowDefinitionScreenDTO
    id: int
    name: str | None = None
    message: str | None = None
    field_metadatas: list[PostWorkflowDefinitionScreenFieldAssociation] | None = None


class PostWorkflowDefinitionState(InteractaModel):
    # PostWorkflowDefinitionStateDTO
    id: int
    init_state: bool | None = None
    name: str | None = None
    metadata: dict | None = None
    terminal: bool | None = None
    deleted: bool | None = None


class PostWorkflowDefinitionTransition(InteractaModel):
    # PostWorkflowDefinitionTransitionDTO
    id: int
    from_state: PostWorkflowDefinitionState | None = None
    to_state: PostWorkflowDefinitionState | None = None
    name: str | None = None
    metadata: dict | None = None
    screen: WorkflowDefinitionScreen | None = None


class PostWorkflowDefinition(InteractaModel):
    # PostWorkflowDefinitionDTO
    id: int
    title: str | None = None
    states: list[PostWorkflowDefinitionState] | None = None
    transitions: list[PostWorkflowDefinitionTransition] | None = None
    screen_field_metadatas: list[PostWorkflowDefinitionState] | None = None
    empty: bool | None = None

    def get_state(self, name: str) -> PostWorkflowDefinitionState:
        for state in self.states:
            if state.name.lower() == name.lower():
                return state
        raise ObjectDoesNotFound(f"State '{name}' not found")

    def get_transition(
        self, from_state_id: int, to_state_id: int
    ) -> PostWorkflowDefinitionTransition:
        for transition in self.transitions:
            if from_state_id == transition.from_state.id and to_state_id == transition.to_state.id:
                return transition
        raise ObjectDoesNotFound(
            f"Transition from state {from_state_id} to state {to_state_id} not found"
        )


class PostDefinition(InteractaModel):
    acknowledge_task_enabled: bool | None = None
    attachment_enabled: bool | None = None
    attachment_max_size: int | None = None
    community_id: int
    community_relations: list[dict] | None = None  # creare model
    custom_fields_enabled: bool | None = None
    default_post_visibility: int | None = None
    description_enabled: int | None = None
    field_definitions: list[FieldDefinition] | None = None
    workflow_definition: PostWorkflowDefinition | None = None  # creare model
    title_enabled: int | None = None
    watchers_enabled: int | None = None
    watchers_visible_in_preview: bool | None = None
    manual_author_enabled: bool | None = None
    hash_tag_enabled: bool | None = None
    like_enabled: bool | None = None
    offline_Enabled: bool | None = None
    hashtags: list[Hashtag] | None = None
    post_views: list[dict] | None = None  # creare model
    inverse_community_relations: list[dict] | None = None  # creare model

    def get_field_by_id(self, field_id: int) -> FieldDefinition | None:
        for field in self.field_definitions:
            if field_id == field.id:
                return field
        raise ObjectDoesNotFound(f"Field with id '{field}' not found in field_definitions")

    def get_enum_id(self, field_id: int, label: str) -> int | None:
        field = self.get_field_by_id(field_id=field_id)
        if not field:
            return None
        for option in field.enum_values:
            if label == option.label:
                return option.id
        return None

    @property
    def custom_fields_ids(self) -> list[int]:
        return [int(field.id) for field in self.field_definitions]

    @property
    def catalog_ids(self) -> list[int]:
        return [field.catalog_id for field in self.field_definitions if field.catalog_id]


class PostEditableContentData(InteractaModel):
    title: str = ""
    description: str | None = ""
    description_delta: str | None = None
    visibility: int | None = None
    custom_data: dict | None = None
    current_workflow_screen_data: dict | None = None
    attachments: list[dict] | None = None
    mentions: list[User] | None = None
    watchers: list[User] | None = None
    watchers_users: list[User] | None = None
    watchers_groups: list[Group] | None = None
    hashtags: list[Hashtag] | None = None
    draft: bool | None = None
    draft_data: dict | None = None
    scheduled_publication: dict | None = None
    scheduled_publication_result: int | None = None


class Community(InteractaModel):
    # -- GetCommunityDetailsResponseDTO
    draft: bool | None = None  # Se true community non ancora pubblicata.
    admin_capabilities: dict | None = None
    operational_capabilities: dict | None = None
    # Link temporaneo download immagine di copertina della community.
    cover_image_temporary_content_view_link: str | None = None
    name: str | None = None  # Nome della community.
    workspace_id: int | None = None  # Id workspace di appartenenza.
    color_code: str | None = None  # Colore community.
    etag: int | None = None  # ETag
    members_count: int | None = None  # Numero membri community.
    creation_timestamp: int | None = None  # Istante creazione
    creator_user: User | None = None
    id: int | None = None  # Identificativo univoco della community.
    description: str | None = None  # Descrizione della community.


class CustomFieldFilter(InteractaModel):
    # CustomFieldFilterDTO
    # Identificativo univoco del campo del post.
    column_id: int | None = None
    # ipo di ricerca [1=EQUAL, 2=INTERVAL, 3=LIKE, 4=IN, 5=CONTAINS, 6=IS_NULL_OR_IN, 7=IS_EMPTY].
    type_id: FieldFilterTypeEnum | None = None
    # Parametri del filtro, ove necessari.
    parameters: list[Any] | None = None


class AcknowledgeTaskFilter(InteractaModel):
    # AcknowledgeTaskFilterDTO
    confirmed: bool | None = None
    assigned_to_me: bool | None = None


class CatalogEntry(InteractaModel):
    # CatalogEntryDTO
    id: int
    catalog_id: int
    label: str | None = None
    external_id: str | None = None
    parent_ids: list[int] | None = None
    deleted: bool = False


class Catalog(InteractaModel):
    # CatalogDTO
    id: int
    name: str
    etag: int | None = None
    paged: bool = False
    entries: list[CatalogEntry] | None = None


# Out Models #######################################################################################


class GetCustomPostForEditResponse(InteractaOut):
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


class GetCommunityDetailsResponse(InteractaOut):
    community: Community | None = None


class GetPostWorkflowScreenDataForEditResponse(InteractaOut):
    # GetPostWorkflowScreenDataForEditResponseDTO
    screen_data: dict | None = None
    screen_occ_token: int | None = (
        None  # Token per il controllo delle modifiche concorrenti sugli screen.
    )
    screen: WorkflowDefinitionScreen | None = None
    current_workflow_state: PostWorkflowDefinitionState | None = None


# In Models


class AttachmentIn(BaseModel):
    # EditCustomPostRequestDTO
    # InputPostAttachmentDTO
    type: int | None = None
    attachment_id: int | None = None
    name: str | None = None
    content_ref: str | None = None  # Il riferimento sul cloudStorage dell'allegato.
    referenced_attachment_id: int | None = None  # Identificativo dell'allegato di riferimento
    hashtag_ids: list[int] | None = None
    drive: DriveAttachmentData | None = None


class CustomPostIn(InteractaModel):
    # ROOT
    title: str
    description: str | None = None  # Descrizione del post
    description_format: int = (
        1  # Formato della descrizione del post, facoltativo (1=delta, 2=markdown, default: 1)
    )
    custom_data: dict | None = None  # Dati custom del post
    # Formato dei campi custom di tipo 11-delta, facoltativo (1=delta, 2=plain text, default: 1)
    delta_area_format: int = 1
    visibility: int | None = None
    # Identificativo dello stato iniziale del workflow, se la community lo permette
    workflow_init_state_id: int | None = None
    draft: bool = False  # Creazione in stato bozza/pubblicato
    scheduled_publication: ZonedDatetimeIn | None = None


class CreateCustomPostIn(CustomPostIn):
    # CreateCustomPostRequest
    attachments: list[AttachmentIn] | None = None
    watcher_user_ids: list[int] | None = None
    announcement: bool | None = None
    client_uid: str | None = None


class EditCustomPostIn(CustomPostIn):
    # EditCustomPostRequestDTO
    add_attachments: list[AttachmentIn] = []
    update_attachments: list[AttachmentIn] = []
    remove_attachment_ids: list[int] = []
    add_watcher_user_ids: list[int] = []
    remove_watcher_user_ids: list[int] = []
