from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

from .core import InteractaIn, InteractaModel, PaginatedIn
from .models import (
    AcknowledgeTaskFilter,
    AdminUserPreferences,
    CustomFieldFilter,
    DriveAttachmentData,
    GroupBase,
    ResetUserCustomCredentialsCommand,
    UserCredentialsConfiguration,
    UserInfo,
    ZonedDatetimeInput,
)


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
    scheduled_publication: ZonedDatetimeInput | None = None


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


class ListCommunityPostsIn(InteractaIn):
    # ListCommunityPostsRequestDTO
    # Filtro sul titolo
    title: str | None = None
    # Filtro sulla descrizione
    description: str | None = None
    # Filtro utente creatore
    created_by_user_id: int | None = None
    # Filtro lowerbound sulla data di creazione
    creation_timestamp_from: int | None = None
    # Filtro upperbound sulla data di creazione
    creation_timestamp_to: int | None = None
    # Filtro utente ultima modifica
    modified_by_user_id: int | None = None
    # Filtro lowerbound sulla data di modifica
    modified_timestamp_from: int | None = None
    # Filtro upperbound sulla data di modifica
    modified_timestamp_to: int | None = None
    # Contenuto del post
    contains_text: str | None = None
    # Filtro post seguiti da me
    followed_by_me: bool | None = None
    # Filtro post per cui l'utente ha qualcosa da fare
    to_manage: bool | None = None
    # Filtro post per cui l'utente può effettuare una transizione di stat
    to_manage_processes: bool | None = None
    # Filtro post per cui l'utente ha dei task di tipo STANDARD non evase (scadute o da fare)
    # assegnate
    to_manage_standard_tasks: bool | None = None
    # Filtro post per cui l'utente è stato menzionato
    mentioned: bool | None = None
    # Stato del workflow del post (parametro passato per identificativo)
    current_workflow_status_ids: list[int] | None = None
    # Filtro sulla tipoloiga del post [1=CUSTOM, 2=EVENTO].
    post_type: int | None = None
    # Filtro sulla tipoloiga del post [1=CUSTOM, 2=EVENTO]
    post_types: list[int] | None = None
    # Filtro per le bozze [null=nessun filtro, 1=STANDARD_DRAFT, 2=SCHEDULED_DRAFT
    draft_type: int | None = None
    event_post_filter: dict | None = None
    # Criterio di ordinamento. Valori ammessi ['customId', 'title', 'creatorUser',
    # 'creationTimestamp', 'lastModifyUser', 'lastModifyTimestamp', 'lastModifyAndCommentTimestamp',
    #  'viewedByMeTimestamp', 'modifiedByMeTimestamp', 'commentedByMeTimestamp',
    # 'scheduled_publication', 'recency', 'customField-{id del campo custom}'].
    order_by: str | None = None
    # Filtri sugli hashtag
    hashtag_ids: list[int] | None = None
    # Indica se i filtri sugli hashtag vanno combinati in AND o in OR (default = false)
    hashtags_logical_and: bool | None = None
    # Filtri sugli hashtag degli allegati
    attachment_hashtag_ids: list[int] | None = None
    # Indica se i filtri sugli hashtag degli allegati vanno combinati in AND o in OR
    #  (default = false)
    attachment_hashtags_logical_and: bool | None = None
    # Filtro sulla visibilità pubblica/privata
    visibility: int | None = None
    custom_field_filters: list[CustomFieldFilter] | None = None
    # Filtri sui campi custom
    post_field_filters: list[CustomFieldFilter] | None = None
    # Filtri sui campi screen
    screen_field_filters: list[CustomFieldFilter] | None = None
    acknowledge_task_filter: AcknowledgeTaskFilter | None = None
    # Filtro per le bozze
    draft: bool | None = None
    # Ordinamento sui post pinnati. Default: 'true'
    pinned_first: bool | None = None


class CommunityPostFilters(InteractaModel):
    # 	CommunityPostFiltersDTO
    # Filtro sul titolo
    title: str | None = None
    # Filtro sulla descrizione
    description: str | None = None
    # Filtro utente creatore
    created_by_user_id: int | None = None
    # Filtro utenti creatori
    created_by_user_ids: list[int] | None = None
    # Filtro gruppi di utenti creatori
    created_by_group_ids: list[int] | None = None
    # Filtro lowerbound sulla data di creazione
    creation_timestamp_from: int | None = None
    # Filtro upperbound sulla data di creazione
    creation_timestamp_to: int | None = None
    # Filtro utente ultima modifica
    modified_by_user_id: int | None = None
    # Filtro lowerbound sulla data di modifica
    modified_timestamp_from: int | None = None
    # Filtro upperbound sulla data di modifica
    modified_timestamp_to: int | None = None
    # Contenuto del post
    contains_text: str | None = None
    # Filtro post seguiti da me
    followed_by_me: bool | None = None
    # Filtro post per cui l'utente ha qualcosa da fare
    to_manage: bool | None = None
    # Filtro post per cui l'utente può effettuare una transizione di stat
    to_manage_processes: bool | None = None
    # Filtro post per cui l'utente ha dei task di tipo STANDARD non evase (scadute o da fare)
    # assegnate
    to_manage_standard_tasks: bool | None = None
    # Filtro post per cui l'utente è stato menzionato
    mentioned: bool | None = None
    # Stato del workflow del post (parametro passato per identificativo)
    current_workflow_status_ids: list[int] | None = None
    # Filtro sulla tipoloiga del post [1=CUSTOM, 2=EVENTO, 3=QUESTIONARIO]
    post_types: list[int] | None = None
    # Filtro sulla tipoloiga del post [1=QUESTIONARIO, 2=MISSIONE]
    post_survey_types: list[int] | None = None
    # Filtro per le bozze [null=nessun filtro, 1=STANDARD_DRAFT, 2=SCHEDULED_DRAFT
    draft_type: int | None = None
    event_post_filter: dict | None = None  # TODO --> EventPostFilterDTO
    # Filtro per recuperare solo post pinnati
    only_pinned: bool | None = None
    # Filtro sull'ID del post (utile per visualizzare tutti gli attachments di un singolo post).
    post_id: int | None = None
    # Filtri sugli hashtag
    hashtag_ids: list[int] | None = None
    # Indica se i filtri sugli hashtag vanno combinati in AND o in OR (default = false)
    hashtags_logical_and: bool | None = None
    # Filtro sulla visibilità pubblica/privata
    visibility: int | None = None
    # Filtri sui campi custom
    post_field_filters: list[CustomFieldFilter] | None = None
    # Filtri sui campi screen
    screen_field_filters: list[CustomFieldFilter] | None = None
    acknowledge_task_filter: AcknowledgeTaskFilter | None = None
    # Filtro per le bozze
    draft: bool | None = None


class CommunityAttachmentFilters(InteractaModel):
    # CommunityAttachmentFiltersDTO
    # Filtro sul nome
    name: str | None = None
    # Filtro utente creatore
    created_by_user_id: int | None = None
    # Filtro utenti creatori
    created_by_user_ids: list[int] | None = None
    # Filtro gruppi di utenti creatori
    created_by_group_ids: list[int] | None = None
    # Filtro sul mimeType Valori ammessi: [1-AUDIO, 2-IMAGE, 3-VIDEO, 4-PDF, 5-TEXT, 6-DOCUMENT,
    # 7-SPREADSHEET, 8-PRESENTATION, 9-DRAWING, 10-ARCHIVE]
    mime_types: list[int] | None = None
    # Filtro sulla categoria di mimeType. Valori ammessi: ['multimedia', 'other']
    mime_type_category: Literal["multimedia", "other"]
    # Filtro sul tipo degli allegati. Valori ammessi: 1 (STORAGE, default), 2 (DRIVE)
    types: list[int] | None = None
    # Filtro per escludere i file provenienti da filePicker
    exclude_file_pickers: bool | None = None
    # Filtro sul tipo dell'entità dell'allegato. Valori ammessi:
    # 1 (POST, default), 2 (TASK), 3 (COMMENT)
    entity_types: list[int]
    # Filtro lowerbound sulla data di creazione
    creation_timestamp_from: int | None = None
    # Filtro upperbound sulla data di creazione
    creation_timestamp_to: int | None = None
    # Filtro utente ultima modifica
    modified_by_user_id: int | None = None
    # Filtro lowerbound sulla data di modifica
    modified_timestamp_from: int | None = None
    # Filtro upperbound sulla data di modifica
    modified_timestamp_to: int | None = None
    # Filtro sull'ID del filePicker di un campo custom (utile per visualizzare gli attachments
    # appartenenti ad uno specifico campo custom file picker).
    post_file_picker_field_id: int | None = None
    # Filtro sull'ID del filePicker di un campo screen del workflow (utile per visualizzare gli
    # attachments appartenenti ad uno specifico campo screen file picker).
    wf_screen_file_picker_field_id: int | None = None
    # Filtro sugli hashtag
    hashtag_ids: list[int] | None = None
    # Indica se i filtri sugli hashtag vanno combinati in AND o in OR (default = false)
    hashtags_logical_and: bool | None = None


class ListCommunityPostsFilteredIn(InteractaIn):
    # ListCommunityPostsFilteredRequestDTO
    community_post_filters: CommunityPostFilters | None = None
    community_attachment_filters: CommunityAttachmentFilters | None = None
    # Criterio di ordinamento. Valori ammessi ['postCustomId', 'postTitle', 'postCreatorUser',
    # 'postCreationTimestamp', 'postLastModifyUser', 'postLastModifyTimestamp',
    # 'postLastModifyAndCommentTimestamp', 'postViewedByMeTimestamp', 'postModifiedByMeTimestamp',
    # 'postCommentedByMeTimestamp', 'postScheduledPublication', 'postRecency',
    # 'postCustomField-{id del campo custom}'].
    order_by: str | None = None
    # Ordinamento sui post pinnati. Default: 'true'
    pinned_first: bool | None = None


### Workflow


class EditPostWorkflowScreenDataIn(InteractaModel):
    # EditPostWorkflowScreenDataRequestDTO
    model_config = ConfigDict(validate_assignment=True)

    screen_data: dict = {}
    delta_area_format: int = 1


class ExecutePostWorkflowOperationIn(EditPostWorkflowScreenDataIn):
    # ExecutePostWorkflowOperationRequestDTO
    screen_occ_token: int


### Utenti


class ListSystemUsersIn(InteractaIn):
    # ListSystemUsersRequestDTO

    # Filtro sul tipo di capability che deve avere l'utente, i valori ammessi sono:
    # [manageUsers, manageDigitalWorplace]
    admin_capabilities: list[Literal["manageUsers", "manageDigitalWorplace"]] | None = None
    # Filtro fulltext su nome cognome e email
    full_text_filter: str | None = None
    # Filtro sul nome dell'utente
    first_name_prefix_full_text_filter: str | None = None
    # Filtro sul cognome dell'utente
    last_name_prefix_full_text_filter: str | None = None
    # Filtro sull'email dell'utente
    email_prefix_full_text_filter: str | None = None
    # Filtro sull'email di autenticazione con servizi esterni
    external_auth_service_email_full_text_filter: str | None = None
    # Filtro sullo stato dell'utente, 0 = solo utenti attivi
    status_filter: list[int] | None = None
    # Filtro sui workspace
    workspace_ids: list[int] | None = None
    # Filtro sulle community
    community_ids: list[int] | None = None
    # Filtro per businessUnits
    business_unit_ids: list[int] | None = None
    # Filtro per area
    area_ids: list[int] | None = None
    # Filtro full-text per luogo
    place: str | None = None
    # Filtro per data di creazione
    creation_timestamp_from: int | None = None
    # Filtro per data di creazione
    creation_timestamp_to: int | None = None
    # Filtro per data di creazione
    last_access_timestamp_from: int | None = None
    # Filtro per data di creazione
    last_access_timestamp_to: int | None = None
    # Filtro per riferimento esterno
    external_id_full_text_filter: str | None = None
    # Filtro sull'email dell'utente
    personal_email_full_text_filter: str | None = None
    # Filtro per ruolo
    role: str | None = None
    # Filtro per manager
    manager_ids: list[int] | None = None
    # Filtro per lingua
    lang: list[str] | None = None
    # Filtro per fuso orario
    time_zone_ids: list[int] | None = None
    # Filtro per tipologia login
    login_provider_filter: list[str] | None = None
    # Filtro Sezione Persone Abilitata
    people_section_enabled: bool | None = None
    # Filtro Visibile nella Sezione Persone
    visible_in_people_section: bool | None = None
    # Filtro Profilo Ridotto (Base/Avanzato)
    reduced_profile: bool | None = None
    # Filtro Visualizzazione Altri Profili Abilitata
    view_user_profiles: bool | None = None
    # Id campo di ordinamento
    order_type_id: str | None = None


class UserSettingsIn(InteractaModel):
    # UserSettingsRequestDTO
    # Sezione Persone abilitata/disabilitata
    people_section_enabled: bool = True
    # Utente visibile nella sezione persone
    visible_in_people_section: bool = True
    # Visualizzazione profilo in versione ridotta/estesa
    reduced_profile: bool = False
    # Possibilità di visualizzare o meno il profilo di utenti terzi
    view_user_profiles: bool = True


class DataUserInfoIn(InteractaModel):
    id: int


class UserInfoIn(UserInfo):
    business_unit: DataUserInfoIn | None = None
    area: DataUserInfoIn | None = None
    manager: DataUserInfoIn | None = None


class UserEditBase(InteractaModel):
    firstname: str = ""
    lastname: str = ""
    contact_email: EmailStr | None = None
    private_email: EmailStr | None = None
    external_id: str | None = None
    user_preferences: AdminUserPreferences | None = None
    user_info: UserInfoIn | None = None
    user_settings: UserSettingsIn | None = None


class UserIn(UserEditBase):
    pass


class CreateUserIn(UserIn):
    # CreateUserRequestDTO
    user_credentials_configuration: UserCredentialsConfiguration | None = None
    reset_user_custom_credentials_command: ResetUserCustomCredentialsCommand | None = None


class EditUserIn(UserIn):
    # EditUserRequestDTO
    occ_token: int | None = None


### Gruppi


class ListSystemGroupsIn(InteractaIn):
    # ListSystemGroupsRequestDTO

    # Filtro sul tipo di capability che deve avere l'utente, i valori ammessi sono:
    # [manageUsers, manageDigitalWorplace]
    admin_capabilities: list[Literal["manageUsers", "manageDigitalWorplace"]] | None = None
    # Filtro fulltext su nome e email
    full_text_filter: str | None = None
    # Filtro sullo stato dell'utente
    status_filter: list[int] | None = None  # 0 == solo gruppi non eliminati
    # Filtro sui workspace
    workspace_ids: list[int] | None = None
    # Filtro per escludere i gruppi che contengono l'utente
    exclude_group_by_member_user_id: int | None = None
    # Id campo di ordinamento
    order_type_id: str | None = None


class ListGroupMembersIn(InteractaIn):
    # ListGroupMembersRequestDTO
    pass


class CreateGroupIn(GroupBase):
    # CreateGroupRequestDTO
    member_ids: list[int] | None = None


class EditGroupIn(CreateGroupIn):
    # EditGroupRequestDTO
    occ_token: int | None = None


class EditGroupMember(InteractaModel):
    # creato da rreverse engineering, non supportato da api a settembre 2023
    id: int | None = None
    occ_token: int | None = None
    add_user_ids: list[int] | None = None
    delete_user_ids: list[int] | None = None


class EditGroupMembersIn(InteractaModel):
    # creato da rreverse engineering, non supportato da api a settembre 2023
    group_members: list[EditGroupMember] | None = None


### Catalogs


class GetPostDefinitionCatalogsIn(InteractaModel):
    # GetPostDefinitionCatalogsRequest
    catalog_ids: list[int] = []


### Comments


class ListPostCommentsIn(PaginatedIn):
    # ListPostCommentsRequestDTO
    pass


class InputPostCommentAttachmentIn(InteractaModel):
    # InputPostCommentAttachmentDTO
    attachment_id: int | None = None
    name: str | None = None
    content_ref: str | None = None


class CreatePostCommentIn(InteractaModel):
    # CreatePostCommentRequestDTO
    comment: str | None = None
    comment_format: int = 1  # Formato del commento, facoltativo (1=delta, 2=plainText, default: 1)
    client_uid: str | None = None
    attachments: InputPostCommentAttachmentIn | None = None
    parent_comment_id: int | None = None
