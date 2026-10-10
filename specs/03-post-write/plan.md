# Piano 03 – Scrittura dei post custom, commenti e workflow

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Si ripete la catena della spec 02 senza toccare il transport. Le scritture dei post stanno in un
mixin nuovo, `PostsWriteAPI` in `api/posts_write.py`, che `PostsAPI` eredita: `client.posts.*`
resta unico e `api/posts.py` non cambia. Ogni metodo costruisce il corpo dai kwargs con
`build_write_body` (camelCase, solo i campi passati; `scheduled_publication` tramite
`zoned_datetime_input`) oppure dal DTO (`model_dump(mode="json", exclude_none=True)`), fa una sola
chiamata `_get`/`_post`/`_put`/`_delete` e avvolge la risposta in una façade di
`models/facade/posts_write.py`, che rivalida gli stub `RootModel` nelle varianti tipizzate `…1`
(`PostDetailDTO1`, `PostCommentDTO1`, `PostEditableContentDataDTO1`,
`PostWorkflowDefinitionStateDTO1`, `PostWorkflowDefinitionTransitionDTO1`,
`WorkflowDefinitionScreenDTO1`) come già fanno `Task` e `TaskWriteResult`. `_put` del client base
impara a trattare una risposta senza corpo come `{}` (lo fa già `_delete`), perché
`edit-post-watchers` risponde `200` vuoto. `PostCapabilities` guadagna quattro proprietà.

Nella CLI, gli helper di scrittura oggi privati di `cli/tasks.py` (`_parse_expiration`,
`_merge_body`, `_validate_body`) si spostano in `cli/_write.py` come funzioni pubbliche, con un
nuovo `parse_kv_values` per `--custom-data`/`--screen-data`; `cli/tasks.py` li importa senza
cambiare comportamento. I quattordici comandi stanno in `cli/posts_write.py`, che registra i
comandi sullo stesso `Typer` di `cli/posts.py`; le patch (`edit`, `edit-custom-data`, `copy`,
`workflow-execute`, `workflow-edit-screen`) usano funzioni pure di base (`edit_base`, `copy_base`,
`merge_custom_data`) testabili da sole, e passano sempre dai `*_raw` dopo l'unione base < `--json`
< flag. `handle_error` riceve un `resource` opzionale per il messaggio del `409` della spec.
Fixture JSON e contract test per i 22 DTO; integration test opt-in nuovo
`test_posts_integration.py`; pagine `docs/`. Test prima del codice, come nelle spec 01 e 02.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `scripts/generate_models.py` | modificato | `screenData` e `newScreenData` in `_PATCHED_FIELDS`: `additionalProperties: {}` al posto di `{"type": "object"}` (revisione del 2026-10-09) |
| `src/pynteracta/models/generated/external_v2.py` | rigenerato | `uv run python scripts/generate_models.py --offline`; il diff tocca solo sette campi `screenData`/`newScreenData` (`dict[str, dict[str, Any]]` → `dict[str, Any]`) |
| `src/pynteracta/api/_base.py` | modificato | `_put`: `if not response.content: return {}` prima di `response.json()`, come `_delete` (03-C08, `edit_watchers`) |
| `src/pynteracta/api/posts_write.py` | nuovo | `PostsWriteAPI(ResourceClient)`: costanti dei 15 percorsi `communication/posts/manage/…`; `get_for_create`, `get_for_edit`, `get_for_copy` (query `loadAttachments` solo se passata, via `build_query_params`); `create`/`create_raw` (`announcement` sempre nel corpo), `edit`/`edit_raw`, `edit_custom_data`/`_raw`, `copy`/`_raw`, `edit_watchers`/`_raw` (→ `None`), `edit_attachments`/`_raw`, `delete`, `mark_as_erasable` (`_put` senza `json`), `add_comment`/`_raw`, `get_workflow_screen` (query `workflowOperationId` solo se passato), `execute_workflow_operation`/`_raw`, `edit_workflow_screen`/`_raw`; alias di tipo `WriteItems` come in `tasks.py`; docstring Google in italiano con tutti i kwargs |
| `src/pynteracta/api/posts.py` | modificato (una riga) | `class PostsAPI(PostsWriteAPI)`; docstring della classe cita le scritture |
| `src/pynteracta/models/facade/posts_write.py` | nuovo | `PostWriteResult(raw: CreatePostResponseDTO \| EditPostResponseDTO \| CopyPostResponseDTO)` con `post_id` (dal DTO o da `post.id`), `next_occ_token`, `post: PostDetailDTO1 \| None`, `from_create`/`from_edit`/`from_copy`; `PostForCreate` (`content_data: PostEditableContentDataDTO1 \| None`), `PostForEdit` (`occ_token`, `community_id`, `custom_id`, `current_workflow_state: PostWorkflowDefinitionStateDTO1 \| None`, `content_data`), `PostForCopy` (`occ_token`, `content_data`); `PostComment` (`id`, `comment_plain_text`, `comment_delta`, `creator_user: UserDTO`, `creation_timestamp`, `parent_comment_id` da `parentComment.id`); `WorkflowScreen` (`screen_data`, `screen_occ_token`, `screen: WorkflowDefinitionScreenDTO1 \| None`, `current_workflow_state`); `WorkflowOperationResult` (`new_current_state`, `new_screen_data`, `new_permitted_operations: list[PostWorkflowDefinitionTransitionDTO1]`, `new_can_edit_workflow_screen_data`, `post_data_has_changed`); `WorkflowScreenWriteResult` (`next_screen_occ_token`, `new_screen_data`, `post_data_has_changed`); `PostAttachmentsWriteResult` (`post_id`, `added`, `updated` come `list[PostAttachmentDataDTO1]`, `removed_ids`); tutte con `.raw` e `from_dict`; un `_typed(stub, model)` locale che rivalida lo stub (dict in `root`) nel modello tipizzato, o `None` |
| `src/pynteracta/models/facade/posts.py` | modificato | `PostCapabilities.can_copy`, `.can_edit_attachments`, `.can_edit_workflow_screen_data`, `.workflow_permitted_operations: list[PostWorkflowDefinitionTransitionDTO1]` (rivalidazione degli elementi stub) |
| `src/pynteracta/cli/_write.py` | nuovo | `DEFAULT_TIMEZONE = "Europe/Rome"`; `parse_zoned_datetime(value, timezone, *, option) -> dict \| None` (ex `_parse_expiration`, con il nome dell'opzione nel messaggio); `merge_body(json_body, **flags)` (ex `_merge_body`); `validate_body(merged, dto_cls)` (ex `_validate_body`); `parse_kv_values(values, *, option) -> dict[str, Any]` (`ID=VALORE` ripetibile, chiave lasciata com'è, valore via `coerce_filter_value`; token senza `=` → `typer.BadParameter`, come `parse_kv_filters`); `JsonBodyOption`, `TimezoneOption` condivisi |
| `src/pynteracta/cli/tasks.py` | modificato | importa gli helper da `_write.py` al posto delle copie private; nessun cambio di comportamento (gli snapshot e i test di `tasks create\|edit` restano verdi) |
| `src/pynteracta/cli/_common.py` | modificato | `handle_error(exc, *, console, resource: str \| None = None)`: con `resource` il ramo `ConcurrencyError` stampa `"{resource} changed since it was read: fetch it again and retry."`, altrimenti il testo attuale |
| `src/pynteracta/cli/posts_write.py` | nuovo | importa `app` da `cli/posts.py` e registra `create`, `edit`, `edit-custom-data`, `copy`, `edit-watchers`, `delete`, `mark-erasable`, `comment`, `get-for-create`, `get-for-edit`, `get-for-copy`, `workflow-screen`, `workflow-execute`, `workflow-edit-screen`; opzioni condivise (`--title`, `--description`, `--custom-data`, `--watcher-user`, `--remove-watcher-user`, `--visibility`, `--announcement`, `--draft`, `--scheduled-publication`, `--timezone`, `--workflow-init-state`, `--client-uid`, `--json`, `--occ-token`, `--screen-data`, `--screen-occ-token`, `--no-attachments`, `--operation`, `--text`, `--parent`, `--add`, `--remove`, `--yes`); funzioni pure: `edit_base(for_edit: PostForEdit) -> dict` (`title`, `description` = `descriptionDelta` con `descriptionFormat: 1`, `customData`, `visibility`; chiavi `None` omesse), `copy_base(for_copy: PostForCopy) -> dict` (come `edit_base` più `announcement`), `merge_custom_data(base, json_part, flags) -> dict` (unione chiave per chiave di `customData`, flag > json > letto), `screen_base(screen: WorkflowScreen) -> dict`, `drop_delta_if_plain(merged)` (se `descriptionFormat == 2` arriva da `--description`, la `description` letta è già sostituita: la funzione serve solo a non rimandare `descriptionFormat: 1` con un testo semplice), righe curate `write_result_row` (id, community_id, title, visibility, current_state, next_occ_token), `comment_row`, `for_edit_row` (occ_token in testa), `screen_row`, `operation_result_row` |
| `src/pynteracta/cli/__init__.py` | modificato | `import pynteracta.cli.posts_write` dopo `posts`, perché i comandi si registrino prima di `add_typer` |
| `src/pynteracta/cli/posts.py` | modificato | `posts capabilities`: la riga curata aggiunge `can_copy`, `can_edit_attachments`, `can_edit_workflow_screen_data`, `workflow_operations` (`"12 Approva, 13 Rifiuta"`) (03-C15) |
| `tests/unit/test_api_base.py` | modificato | `test_put_without_body_returns_empty_dict` (03-C08) |
| `tests/unit/test_api_posts_write.py` | nuovo | 03-C01…C14, 03-C16, 03-C17 (classi per gruppo: `TestPostsCreate`, `TestPostsEdit`, `TestPostsCustomData`, `TestPostsCopy`, `TestPostsWatchersAttachments`, `TestPostsDelete`, `TestPostsComment`, `TestPostsPrep`, `TestPostsWorkflow`, `TestPostsErrors`) |
| `tests/unit/test_facade_posts.py` | modificato | 03-C15 (`PostCapabilities` esteso sulla fixture aggiornata) |
| `tests/unit/test_facade_posts_write.py` | nuovo | le otto façade sulle fixture: campi, stub mancanti → `None`, `post_id` da `post.id` quando il DTO non lo ha (`from_edit`) |
| `tests/unit/test_cli_write.py` | nuovo | caratterizzazione di `parse_zoned_datetime`, `merge_body`, `validate_body` (comportamento attuale di `tasks.py`) scritta **prima** dello spostamento; `parse_kv_values` (tipi, `=` mancante, valori con `=` dentro) |
| `tests/unit/test_cli_posts_write.py` | nuovo | 03-C18…C28 (snapshot syrupy per le tabelle di `create`, `comment`, `get-for-edit`, `workflow-screen`; corpi inviati letti con `_sent_body` come in `test_cli_tasks.py`; prompt con `_stdin_is_interactive` sostituito) |
| `tests/unit/test_cli_posts.py` | modificato | 03-C15 (`posts capabilities` mostra i flag e le operazioni); snapshot esistente rigenerato e riletto |
| `tests/unit/test_cli_common.py` | modificato | `handle_error` con `resource` (messaggio della spec) e senza (testo attuale, già fissato) |
| `tests/fixtures/payloads/get_post_capabilities_response.json` | modificato | aggiunge `canCopy`, `canEditAttachments`, `canEditWorkflowScreenData`, `workflowPermittedOperations: [{id: 12, name: "Approva", fromState, toState}]` |
| `tests/fixtures/payloads/create_post_response.json`, `edit_post_response.json`, `copy_post_response.json`, `delete_post_response.json`, `mark_post_erasable_response.json`, `edit_post_attachments_response.json`, `create_post_comment_response.json`, `post_for_create_response.json`, `post_for_edit_response.json`, `post_for_copy_response.json`, `workflow_screen_response.json`, `execute_workflow_operation_response.json`, `edit_workflow_screen_response.json`, `custom_field_validation_error_response.json` | nuovi | risposte sagomate sul swagger con `postData`/`contentData` completi, `occToken: 5`, `screenOccToken: 3`, `customData: {"1411": 226, "1413": true}`, `descriptionDelta` finto; dati finti (`Alice Rossi`, id piccoli) |
| `tests/contract/test_models.py` | modificato | 03-C29: `TestPostWriteDTOs` con `assert_superset` per i 22 DTO della spec più le varianti tipizzate `PostDetailDTO1`, `PostEditableContentDataDTO1`, `PostCommentDTO1`, `PostWorkflowDefinitionStateDTO1`, `PostWorkflowDefinitionTransitionDTO1`, `WorkflowDefinitionScreenDTO1`, `InputPostAttachmentDTO1`, `InputPostCommentAttachmentDTO1`; smoke delle façade sulle fixture |
| `tests/integration/test_posts_integration.py` | nuovo | 03-C31: fixture `client` locale come negli altri file; `TestPostsWriteIntegration::test_full_cycle` (skip senza `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` o `PYNTERACTA_TEST_USER_ID`; `delete` dei post creati in `finally`, con `contextlib.suppress(NotFoundError)` per la copia) e `::test_workflow_screen_read_only` (skip senza `PYNTERACTA_TEST_WORKFLOW_POST_ID`); stampe `[T-manuale]` dei dati osservati (campi dopo `edit`, corpo della copia, formato della descrizione) |
| `tests/integration/.env.example`, `docs/testing.md` | modificati | `PYNTERACTA_TEST_WRITE_COMMUNITY_ID`, `PYNTERACTA_TEST_WORKFLOW_POST_ID` con la raccomandazione della community di prova |
| `docs/api/posts.md`, `docs/cli.md`, `docs/index.md`, `README.md` | modificati | 03-C30: sezione "Writing posts" (metodi, façade, `occ_token` dalle letture propedeutiche, date, campi omissi come verificati, `::: pynteracta.models.facade.posts_write`); quattordici comandi in `cli.md`; "tasks and posts" in home e README senza numeri di versione |
| `tests/unit/test_docs_snippets.py` | modificato | `test_posts_pages_document_write_commands` con marker 03-C30 |
| `ROADMAP.md`, `PROGRESS.md` | modificati | riga `0.11.0 ⏳ M29` all'apertura; sezione M29 alla verifica |
| `specs/prd.md` | modificato (chiusura) | RF-021a, RF-021b, RF-021c, RF-006a; conferma di RF-021, RF-006, §5 e §7 nella parte dei post |

Non si toccano: `transport.py`, `hooks.py`, `client.py` (`client.posts` esiste già),
`api/posts.py` oltre alla riga di ereditarietà. `models/generated/` cambia solo per
rigenerazione, mai a mano.

## Modello dati e migrazioni

Nessuna modifica di schema: i DTO sono già generati. Revisione del 2026-10-09: i campi
`screenData` e `newScreenData` (cinque DTO del workflow più due contesti di screen) diventano
`dict[str, Any]` rigenerando i modelli con lo script corretto. Gli stub `RootModel` (`PostDetailDTO`,
`PostCommentDTO`, `PostEditableContentDataDTO`, `PostWorkflowDefinitionStateDTO`,
`PostWorkflowDefinitionTransitionDTO`, `WorkflowDefinitionScreenDTO`) hanno la variante tipizzata
`…1` nello stesso modulo; `scheduledPublication` è lo stub `ZonedDatetimeInputDTO` che accetta un
dict. Il DTO di creazione si chiama `CreateCustomPostRequest` e ha `announcement: bool`
obbligatorio: `create` lo mette sempre nel corpo, `create_raw` lo riceve dal DTO.

## Flussi

```
Libreria (api/posts_write.py)
get_for_edit(post_id, load_attachments=None)
    → _get("…/manage/post-data-for-edit/{post_id}", params=build_query_params(load_attachments=…) or None)
    → PostForEdit.from_dict(resp)                       (occ_token = resp["occToken"])
create(community_id, *, announcement=False, **kw)
    → body = build_write_body(announcement=announcement, …, scheduled_publication=zoned_datetime_input(dt) se dt)
    → _post("…/manage/create-post/{community_id}", json=body) → PostWriteResult.from_create(resp)
edit(post_id, occ_token, **kw)
    → _put("…/manage/edit-post/{post_id}/{occ_token}", json=body) → PostWriteResult.from_edit(resp)
edit_custom_data(post_id, occ_token, **kw)
    → _put("…/manage/edit-post-custom-data/{post_id}/{occ_token}", json=body) → PostWriteResult.from_edit(resp)
copy(post_id, occ_token, **kw)
    → _put("…/manage/copy-post/{post_id}/{occ_token}", json=body) → PostWriteResult.from_copy(resp)
edit_watchers(post_id, *, add_user_ids, remove_user_ids)
    → _put("…/manage/edit-post-watchers/{post_id}", json=body) → None     (corpo vuoto → {} in _put)
edit_attachments(post_id, *, add, update, remove_ids)
    → _put("…/manage/edit-post-attachments/{post_id}", json=body) → PostAttachmentsWriteResult
delete(post_id)            → _delete("…/manage/delete-post/{post_id}") → DeletePostResponseDTO.postId
mark_as_erasable(post_id)  → _put("…/manage/mark-post-as-erasable/{post_id}") → MarkPostAsErasableResponseDTO.postId
add_comment(post_id, **kw) → _post("…/manage/create-comment/{post_id}", json=body) → PostComment.from_dict(resp)
get_workflow_screen(post_id, operation_id=None)
    → _get("…/manage/post-workflow-screen-data-for-edit/{post_id}", params={"workflowOperationId": id} se dato)
    → WorkflowScreen.from_dict(resp)
execute_workflow_operation(post_id, operation_id, **kw)
    → _post("…/manage/execute-post-workflow-operation/{post_id}/{operation_id}", json=body) → WorkflowOperationResult
edit_workflow_screen(post_id, screen_occ_token, **kw)
    → _put("…/manage/edit-post-workflow-screen-data/{post_id}/{screen_occ_token}", json=body) → WorkflowScreenWriteResult
Errori: nessun try/except nei metodi; il transport solleva le InteractaError (400 → ValidationError con il
body, 409 → ConcurrencyError, timeout → TransportError); una richiesta per chiamata.

CLI (cli/posts_write.py)
posts create COMMUNITY_ID
    → json_part = load_json_body(--json, CreateCustomPostRequest)
    → merged = merge_body(json_part, title=…, description=…, description_format=2 se --description,
                          custom_data=merge_custom_data({}, json_part, parse_kv_values(--custom-data)),
                          watcher_user_ids=…, visibility=…, announcement=--announcement (sempre),
                          draft=…, scheduled_publication=parse_zoned_datetime(…), workflow_init_state_id=…, client_uid=…)
    → req = validate_body(merged, CreateCustomPostRequest)
    → client.posts.create_raw(COMMUNITY_ID, req) → render_output([result], write_result_row, …)
posts edit POST_ID
    → for_edit = client.posts.get_for_edit(POST_ID)                 (sempre)
    → token = --occ-token oppure for_edit.occ_token (None → messaggio ed Exit(EXIT_GENERIC))
    → base = edit_base(for_edit); merged = merge_body({**base, **json_part}, …flag…)
    → merged["customData"] = merge_custom_data(base, json_part, flag) se c'è un customData da qualche parte
    → --description X → description=X, descriptionFormat=2 (il delta letto è sostituito)
    → req = validate_body(merged, EditCustomPostRequestDTO)
    → client.posts.edit_raw(POST_ID, token, req) → render_output
    → ConcurrencyError → handle_error(exc, console=…, resource=f"Post {POST_ID}") → exit 9
posts edit-custom-data POST_ID   → come edit, base = {"customData": letti}, DTO EditPostCustomDataRequestDTO,
                                   nessun --custom-data né --json → Exit(EXIT_CONFIG) prima della GET
posts copy POST_ID               → for_copy = get_for_copy(POST_ID); base = copy_base(for_copy); PUT copy-post con il token letto
posts edit-watchers POST_ID      → nessun --add/--remove → Exit(EXIT_CONFIG); edit_watchers(…); testo o JSON
posts delete POST_ID             → post = client.posts.get(POST_ID) → confirm_destructive(f'Delete post {id} "{title}"?', yes=…)
                                   False → Exit(0) → post_id = delete(POST_ID) → "Post {id} deleted" | {"post_id": …}
posts mark-erasable POST_ID      → idem con mark_as_erasable e i testi della spec
posts comment POST_ID            → senza --text né --json → Exit(EXIT_CONFIG); merged = merge_body(json_part, comment=--text,
                                   comment_format=2 se --text, parent_comment_id=…, client_uid=…) → add_comment_raw → render_output
posts get-for-create|edit|copy   → letture, render_output con la riga curata (occ_token in testa)
posts workflow-screen POST_ID [--operation ID] → get_workflow_screen → render_output(screen_row)
posts workflow-execute POST_ID OPERATION_ID
    → dati = parse_kv_values(--screen-data) e/o json_part
    → senza dati: body = {} (+ screenOccToken se --screen-occ-token), nessuna GET
    → con dati: screen = get_workflow_screen(POST_ID, operation_id=OPERATION_ID); token = --screen-occ-token o screen.screen_occ_token;
                body = {"screenData": {**screen.screen_data, **json_part.get("screenData", {}), **flag}, "screenOccToken": token}
    → execute_workflow_operation_raw → render_output(operation_result_row); 409 → exit 9
posts workflow-edit-screen POST_ID → screen = get_workflow_screen(POST_ID) (sempre); token come sopra;
                                   PUT edit-post-workflow-screen-data con screenData unito → render_output
```

## Interfaccia

Comandi, opzioni e messaggi come nella sezione "CLI" della spec; testi in inglese. Help breve con
il formato atteso (`ID=VALUE, repeatable; true/false and integers are typed`; `ISO 8601, e.g.
2026-12-31T18:00`; `IANA name, default Europe/Rome`). `--announcement` è un flag booleano
(`is_flag=True`, default `False`), presente solo in `create` e `copy`. `--no-attachments` è un
flag che manda `loadAttachments=false`. Nessuna pagina web.

## Configurazione

Nessuna variabile di runtime. Solo per gli integration test: `PYNTERACTA_TEST_WRITE_COMMUNITY_ID`
(community di prova, mai di produzione: il test vi crea e cancella post) e
`PYNTERACTA_TEST_WORKFLOW_POST_ID` (post con workflow su cui si legge solo lo screen), in
`tests/integration/.env.example` e `docs/testing.md`.

## Sicurezza e dati personali

- **Nessuna operazione ripetuta in automatico**: ogni metodo fa una richiesta e lascia salire le
  eccezioni del transport; la CLI non riprova su `409` (03-C07, 03-C17, 03-C28). Le letture
  propedeutiche delle patch sono letture, non ripetizioni.
- **Token e segreti mai nei log**: nessun log nuovo; i corpi passano dall'audit log solo con
  `audit_log_bodies`, già redatti dal transport.
- **Dati personali**: i corpi contengono titolo, descrizione, campi custom, commenti, id di
  persone; non si salvano. Le fixture usano valori finti. L'integration test usa
  `PYNTERACTA_TEST_WRITE_COMMUNITY_ID`, mai `PYNTERACTA_TEST_COMMUNITY_ID`, `client_uid =
  f"pynteracta-it-{int(time.time())}"`, titoli riconoscibili (`pynteracta integration test – safe
  to delete`), e non esegue transizioni di workflow.
- **Conferma delle operazioni distruttive**: `posts delete` e `posts mark-erasable` passano da
  `confirm_destructive`, che non ha una via che elimini senza `y` o `--yes` (03-C24).
- **Soglie che non scendono**: i file nuovi e toccati hanno test per ogni ramo; copertura ≥ 85 %
  per file e totale ≥ 93,66 %.

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `cli/tasks.py::_parse_expiration`, `_merge_body`, `_validate_body` | ISO 8601 con e senza offset, fuso di `--timezone`, fuso sconosciuto → exit 2; flag non-`None` sostituiscono le chiavi camelCase; corpo non valido → exit 2 con il nome del DTO | `tests/unit/test_cli_write.py`, scritto contro gli import attuali da `cli.tasks` e verde **prima** dello spostamento in `cli/_write.py`; dopo lo spostamento cambia solo l'import |
| `cli/_common.py::handle_error` | testo attuale del `409` senza `resource` | già fissato da `test_cli_common.py::test_handle_error_concurrency_message`; resta verde |
| `api/_base.py::_put` | corpo non-dict → `TypeError` | già fissato da `test_api_base.py::test_put_array_raises_type_error`; si aggiunge solo il ramo vuoto |
| `facade/posts.py::PostCapabilities` | i sette flag attuali | già fissati da `test_facade_posts.py` e `test_cli_posts.py` (`posts capabilities`); la fixture si estende senza togliere chiavi |
| `cli/posts.py::posts capabilities` | tabella attuale | snapshot syrupy esistente; cambia per le quattro colonne nuove (03-C15): rigenerato e riletto |
| `cli/tasks.py::tasks create\|edit` | corpi inviati e snapshot | già fissati da `test_cli_tasks.py`; restano verdi dopo l'import da `_write.py` |

## Strategia di test

Ordine: test prima del codice, rossi per il motivo giusto (modulo, metodo o comando inesistente,
campo mancante), poi il codice. Ogni test porta `# criterio: 03-Cmm`. Le fixture nuove si
scrivono con il test che le usa. `_sent_body(route)` e `mock_json` come in `test_cli_tasks.py`.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 03-C01 | `test_api_posts_write.py::TestPostsCreate::test_create_sends_only_given_fields_and_wraps_response`: `respx.post` su `…/create-post/79`, corpo == JSON atteso (con `announcement: false`), `call_count == 1`, risultato da `create_post_response.json` | unitario |
| 03-C02 | `::test_create_raw_equivalent`; un test `*_raw_equivalent` per ciascuno degli altri metodi (`edit`, `edit_custom_data`, `copy`, `edit_watchers`, `edit_attachments`, `add_comment`, `execute_workflow_operation`, `edit_workflow_screen`) nella classe del gruppo | unitario |
| 03-C03 | `::test_scheduled_publication_zoneinfo_in_body` (create, edit, copy parametrizzati), `::test_naive_scheduled_publication_raises_before_request` (`call_count == 0` per i tre) | unitario |
| 03-C04 | `::TestPostsEdit::test_edit_sends_only_given_fields` (PUT `…/edit-post/21269/5`, corpo atteso, `next_occ_token` e `post` da `edit_post_response.json`), `::test_edit_without_fields_sends_empty_body` | unitario |
| 03-C05 | `::TestPostsCustomData::test_edit_custom_data_body_and_result` | unitario |
| 03-C06 | `::TestPostsCopy::test_copy_body_and_result` (`post_id` del post nuovo da `copy_post_response.json`) | unitario |
| 03-C07 | `::TestPostsErrors::test_409_raises_concurrency_error_once` parametrizzato sui cinque metodi con token (`status 409`, `pytest.raises(ConcurrencyError)`, `exc.status_code == 409`, `call_count == 1`) | unitario |
| 03-C08 | `::TestPostsWatchersAttachments::test_edit_watchers_body_and_none` (risposta `200` vuota), `::test_edit_attachments_body_and_result`; `test_api_base.py::test_put_without_body_returns_empty_dict` | unitario |
| 03-C09 | `::TestPostsDelete::test_delete_returns_post_id`, `::test_mark_as_erasable_puts_without_body_and_returns_post_id` (`request.content == b""`) | unitario |
| 03-C10 | `::TestPostsComment::test_add_comment_body_and_facade` (`PostComment` da `create_post_comment_response.json`, `parent_comment_id`) | unitario |
| 03-C11 | `::TestPostsPrep::test_get_for_create`, `::test_get_for_edit_no_query_and_occ_token`, `::test_get_for_edit_load_attachments_false_in_query`, `::test_get_for_copy` | unitario |
| 03-C12 | `::TestPostsWorkflow::test_get_workflow_screen_without_operation`, `::test_get_workflow_screen_with_operation_query` | unitario |
| 03-C13 | `::test_execute_operation_body_and_result`, `::test_execute_operation_without_kwargs_sends_empty_body` | unitario |
| 03-C14 | `::test_edit_workflow_screen_body_and_result` | unitario |
| 03-C15 | `test_facade_posts.py::test_capabilities_exposes_write_flags_and_operations` sulla fixture estesa; `test_cli_posts.py::TestPostsCapabilities::test_table_shows_write_flags_and_operations` (snapshot rigenerato) | unitario |
| 03-C16 | `::TestPostsErrors::test_400_custom_field_validation_error_readable` (`ValidationError`, `response_body["validationErrors"]`, `call_count == 1`); `test_cli_posts_write.py::TestPostsCreate::test_validation_error_exits_6_with_body` | unitario |
| 03-C17 | `::TestPostsErrors::test_timeout_raises_transport_error_once` parametrizzato su `create` e `add_comment` (`httpx.ReadTimeout`) | unitario |
| 03-C18 | `test_cli_posts_write.py::TestPostsCreate::test_flags_and_json_merge_flags_win` (file in `tmp_path`, corpo atteso con `announcement: true`), `::test_announcement_false_by_default`, `::test_table_output` (snapshot), `::test_json_output` (snapshot), `::test_custom_data_bad_token_exits_2` | unitario |
| 03-C19 | `::TestPostsEdit::test_edit_reads_for_edit_then_puts_patched_body` (GET + PUT su `/21269/5`, corpo == `edit_base(fixture)` + `title`), `::test_edit_with_occ_token_still_reads_base` (PUT su `/21269/3`), `::test_edit_base_skips_missing_fields` (fixture ridotta: niente `descriptionDelta` né `customData`), `::test_edit_without_occ_token_in_response_exits_1`; `edit_base` testato da solo sulla fixture | unitario |
| 03-C20 | `::test_edit_description_flag_sets_plain_format`, `::test_edit_flags_win_over_json_over_read` (`visibility: 2`, `customData` unito `{"1411": 300, "1412": "a", "1413": true}`); `merge_custom_data` testato da solo | unitario |
| 03-C21 | `::TestPostsEditCustomData::test_reads_then_puts_merged_custom_data`, `::test_without_data_exits_2_without_requests` | unitario |
| 03-C22 | `::TestPostsCopy::test_copy_reads_for_copy_then_puts_base_with_title` (corpo == `copy_base(fixture)` + `title`), `::test_copy_table_shows_new_post` | unitario |
| 03-C23 | `::TestPostsEditWatchers::test_add_and_remove_body_and_message`, `::test_json_output`, `::test_without_flags_exits_2` | unitario |
| 03-C24 | `::TestPostsDelete::test_prompt_shows_id_and_title_and_y_deletes` (monkeypatch `_stdin_is_interactive`, `input="y\n"`), `::test_prompt_n_does_nothing`, `::test_yes_skips_prompt`, `::test_non_interactive_without_yes_refuses`, `::test_json_output`; `::TestPostsMarkErasable` con gli stessi quattro casi e i testi della spec | unitario |
| 03-C25 | `::TestPostsComment::test_text_and_parent_body`, `::test_table_output` (snapshot), `::test_json_output`, `::test_without_text_exits_2` | unitario |
| 03-C26 | `::TestPostsPrep::test_get_for_edit_table_starts_with_occ_token` (snapshot), `::test_get_for_copy_table`, `::test_get_for_create_table`, `::test_no_attachments_sends_query`, `::test_full_json` | unitario |
| 03-C27 | `::TestPostsWorkflow::test_execute_with_screen_data_reads_screen_then_posts_merged`, `::test_execute_without_data_posts_empty_body_without_get` (`get_route.call_count == 0`), `::test_execute_screen_occ_token_flag_wins`, `::test_edit_screen_reads_then_puts_merged`, `::test_workflow_screen_table` (snapshot) | unitario |
| 03-C28 | `::TestPostsConflicts::test_conflict_exits_9_without_retry` parametrizzato sui cinque comandi: `exit_code == 9`, `"Post 21269 changed since it was read: fetch it again and retry"` in output, `write_route.call_count == 1`; `test_cli_common.py::test_handle_error_concurrency_with_resource` | unitario |
| 03-C29 | `tests/contract/test_models.py::TestPostWriteDTOs::test_write_dto_superset` (22 DTO), `::test_typed_stub_superset` (8 varianti `…1`), `::test_facade_smoke_*` sulle fixture | contract |
| 03-C30 | `test_docs_snippets.py::test_posts_pages_document_write_commands` (i quattordici nomi di comando in `cli.md`; `create(`, `edit(`, `copy(`, `add_comment(`, `execute_workflow_operation(`, `PostWriteResult`, `occ_token`, `get_for_edit` in `api/posts.md`; `posts` nella frase delle scritture di `index.md` e `README.md`); `uv run mkdocs build --strict` nei controlli di verifica | unitario + verifica |
| 03-C31 | `tests/integration/test_posts_integration.py::TestPostsWriteIntegration::test_full_cycle` (skip senza le variabili; `create` → `get_by_client_uid` → `get_for_edit` → `edit` → `edit_watchers` → `add_comment` → `get_for_copy` → `copy` → `delete` × 2 in `finally` → `NotFoundError` × 2); `::test_workflow_screen_read_only` (skip senza `PYNTERACTA_TEST_WORKFLOW_POST_ID`) | integrazione (opt-in) + verifica manuale |
| 03-C32 | `test_cli_posts_write.py::TestPostsEdit` — i test di T11 marcati 03-C19 passano a 03-C32 con la fixture `post_for_edit_response.json` che ha anche `"2003": [{"id": 89, …}]`: corpo atteso con `"2003": [89]`; `edit_base` testato da solo | unitario |
| 03-C33 | i test di T11 marcati 03-C20 passano a 03-C33: `customData` unito con il letto tradotto, i valori di `--json` (`"2002": [7]`) invariati | unitario |
| 03-C34 | i test di T11 marcati 03-C21 passano a 03-C34, corpo con `"2003": [89]` | unitario |
| 03-C35 | i test di T11 marcati 03-C22 passano a 03-C35; `copy_base` sulla fixture `post_for_copy_response.json` con il riferimento | unitario |
| 03-C36 | i test di T13 marcati 03-C27 passano a 03-C36 con `workflow_screen_response.json` che ha anche `5233` e `5237` come oggetti; `screen_base` testato da solo | unitario |
| 03-C37 | `test_cli_posts_write.py::TestToWriteValue` parametrizzato sui casi del criterio; `test_docs_snippets.py::test_posts_pages_document_write_commands` esteso (`replacement`/`ids` in `docs/api/posts.md`, `Quill delta` in `docs/cli.md`) | unitario |

Verifica manuale (dalla spec): l'esecuzione di 03-C31 sulla community di prova, più le prove a
mano in un task dedicato (campi omessi in `edit-post`, `edit-post-custom-data` e `copy-post`;
`descriptionFormat: 2` in modifica; `mark-post-as-erasable` rispetto a `delete-post`; corpo `{}`
di una transizione senza screen), stabilisce ciò che lo swagger non documenta. L'esito si registra
in `docs/api/posts.md` e in `verifica.md`. Se il server non azzera i campi omessi, la base delle
patch si riduce con una revisione della spec (03-C19…03-C22), non con un aggiustamento silenzioso.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| `screenData`/`newScreenData` corretti nello script di generazione e modelli rigenerati (2026-10-09) | modifica a mano del file generato; `model_construct` per aggirare la validazione | Regola del progetto: `models/generated/` non si modifica a mano; stesso meccanismo di `customData` |
| Mixin `PostsWriteAPI` in `api/posts_write.py`, ereditato da `PostsAPI` | tutto in `api/posts.py` | Decisione del maintainer: `client.posts.*` unico, file leggibili, `posts.py` non cambia |
| Façade in `models/facade/posts_write.py`; `PostCapabilities` resta in `posts.py` | tutto in `facade/posts.py` | Decisione del maintainer; `posts.py` tocca solo le capabilities |
| Comandi in `cli/posts_write.py` sullo stesso `Typer` di `posts.py`; helper in `cli/_write.py` | tutto in `cli/posts.py`; helper duplicati; helper in `_common.py` | Decisione del maintainer: nessun codice doppio con `tasks.py`, `_common.py` non cresce; i comandi restano sotto `posts` |
| `_put` tratta il corpo vuoto come `{}` | `edit_watchers` che chiama il transport direttamente | Stessa regola di `_delete`; serve a `edit-post-watchers` e vale per le scritture future |
| `handle_error(..., resource=)` per il messaggio del `409` | messaggio nel comando; testo generico come oggi | Il testo esatto della spec (03-C28) in un solo punto, riusabile; i task restano con il testo attuale |
| `edit_base`/`copy_base`/`screen_base`/`merge_custom_data` come funzioni pure | unione dentro i comandi | Testabili da sole (03-C19…C22, C27); stessa forma di `_edit_base` dei task |
| `customData` e `screenData` uniti chiave per chiave; gli altri campi sostituiti interi | unione profonda ovunque | Solo i dizionari dei campi hanno senso da fondere; la regola è quella della spec |
| `--description` manda `description` + `descriptionFormat: 2`; `--json` con `description` mantiene il formato letto o quello del JSON | riconoscere il delta dal contenuto | Il formato lo decide chi scrive; nessuna euristica |
| `announcement` sempre nel corpo di `create` (`False` di default) | opzionale come gli altri | Il DTO generato lo dichiara obbligatorio: `create_raw` non può ometterlo |
| `workflow-execute` senza dati non legge lo screen | leggere sempre | Una transizione senza screen non ha token; una `GET` inutile non è una ripetizione ma non serve |
| `PostWriteResult` unico per create/edit/copy con `from_*` | tre façade | Stessi campi utili; `post_id` dal DTO o da `post.id` come `TaskWriteResult` |
| Integration test in un file nuovo `test_posts_integration.py` | dentro `test_tasks_integration.py` | Convenzione del progetto: un file per risorsa |
| Commit `feat(posts):` per libreria, `feat(cli):` per i comandi, `refactor(cli):` per lo spostamento degli helper | `feat:` unico | Scope come nella storia del progetto; semantic-release calcola 0.11.0 |

## Rischi

- **Campi omessi azzerati o conservati dal server** → l'integration test e il task manuale lo
  scoprono; la spec si rivede se serve (03-C19…C22), la libreria non cambia.
- **`descriptionFormat: 2` rifiutato o interpretato come markdown in modifica** → prova manuale;
  se il server vuole il delta, `--description` in `posts edit` passa a `descriptionFormat: 1` con un
  delta minimo generato, con revisione della spec.
- **Risposta vuota di `edit-post-watchers`** → `_put` gestisce `content == b""`; se il server
  risponde `204`, il transport la tratta già come successo (`raise_for_status` solo su `>= 400`).
- **Stub `RootModel` e varianti `…1` incomplete** → i contract test `test_typed_stub_superset`
  lo mostrano (03-C29).
- **Registrazione dei comandi in `posts_write.py`** → l'import in `cli/__init__.py` deve
  precedere `add_typer`; un test di `test_cli_posts_write.py` invoca `posts --help` e verifica i
  quattordici nomi.
- **Spostamento degli helper da `tasks.py`** → test di caratterizzazione verdi prima e dopo;
  `test_cli_tasks.py` intero resta verde.
- **Snapshot syrupy** → generati con `--snapshot-update` al primo run, poi riletti a mano.
- **Copertura di `cli/posts_write.py`** (14 comandi) → ogni ramo di errore (`--json` non valido,
  token assente, flag mancanti, timezone non valida, `409`, `404` dalla lettura) ha un test.
- **`posts capabilities` cambia tabella** → snapshot rigenerato e riletto; nessuna colonna tolta.

## Revisioni

### 2026-10-09, durante T16: riferimenti letti scritti come id

Le prove sul tenant hanno mostrato che le letture restituiscono i riferimenti (voci di catalogo,
utenti, gruppi) come oggetti completi e le scritture li accettano solo come id, e che
`edit-post` sostituisce il post. La libreria non cambia; cambia la base delle patch della CLI.

| File | Modifica |
|---|---|
| `src/pynteracta/cli/posts_write.py` | `to_write_value(value) -> Any`: lista di dict tutti con `id` → lista degli id; dict con `id` → l'id; il resto invariato (lista vuota compresa). `to_write_values(mapping) -> dict` la applica a ogni valore. `edit_base`/`copy_base` traducono `customData`; `screen_base` traduce `screenData`. I valori di `--json` e dei flag non passano dalla traduzione |
| `tests/fixtures/payloads/post_for_edit_response.json`, `post_for_copy_response.json` | `customData` con anche `"2003": [{"id": 89, "catalogId": 12, "label": "3 - Bassa", …}]` |
| `tests/fixtures/payloads/workflow_screen_response.json` | `screenData` con anche `"5233"` (voce di catalogo) e `"5237"` (utente finto) come liste di oggetti |
| `tests/unit/test_cli_posts_write.py` | marker 03-C19…C22, C27 → 03-C32…C36 con le nuove attese; `TestToWriteValue` (03-C37) |
| `tests/integration/test_posts_integration.py` | `edit` rimanda descrizione (delta, formato 1) e `customData` letti tradotti con `to_write_values`, come fa la CLI; stampa `[T16]` dei campi dopo la modifica |
| `docs/api/posts.md`, `docs/cli.md`, `tests/unit/test_docs_snippets.py` | `edit` come sostituzione, riferimenti come id, campi delta in formato delta (03-C37) |

Scelta tecnica: la traduzione sta nel modulo CLI, non nella libreria, perché la libreria invia solo
ciò che riceve; un chiamante della libreria può importare `to_write_values` da `cli/posts_write.py`
solo come dettaglio interno, la documentazione gli mostra la forma con gli id.
