from .models import AcknowledgeTaskFilter, CustomFieldFilter, InteractaModel


class InteractaIn(InteractaModel):
    page_token: str | None = None
    page_size: int | None = None
    calculate_total_items_count: bool | None = True
    order_desc: bool | None = None

    class Config:
        validate_assignment = True


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
    # Filtro sullo stato dell'utente
    status_filter: list[int] | None = None
    # Filtro sui workspace
    workspace_ids: list[int] | None = None
    # Filtro per businessUnits
    business_unit_ids: list[int] | None = None
    # Filtro per area
    area_ids: list[int] | None = None
    # Filtro full-text per luogo
    place: str | None = None
    # Id campo di ordinamento
    order_type_id: str | None = None


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
