from pydantic import ConfigDict, EmailStr

from .core import InteractaIn, InteractaModel
from .models import (
    AcknowledgeTaskFilter,
    AdminUserPreferences,
    CustomFieldFilter,
    GroupBase,
    ResetUserCustomCredentialsCommand,
    UserCredentialsConfiguration,
    UserInfo,
)


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


### Workflow


class ExecutePostWorkflowOperationIn(InteractaModel):
    model_config = ConfigDict(validate_assignment=True)

    # ExecutePostWorkflowOperationRequestDTO
    screen_data: dict = {}
    delta_area_format: int = 1
    screen_occ_token: int


### Utenti


class ListSystemUsersIn(InteractaIn):
    # ListSystemUsersRequestDTO
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
    # Filtro per businessUnits
    business_unit_ids: list[int] | None = None
    # Filtro per area
    area_ids: list[int] | None = None
    # Filtro full-text per luogo
    place: str | None = None
    # Filtro per tipologia login
    login_provider_filter: list[str] | None = None
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


class GetPostDefinitionCatalogsIn(InteractaModel):
    # GetPostDefinitionCatalogsRequest
    catalog_ids: list[int] = []
