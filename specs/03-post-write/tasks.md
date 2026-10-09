# Task 03 – Scrittura dei post custom, commenti e workflow

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (modulo, metodo o comando inesistente, campo mancante); poi il codice;
il commit arriva con i cinque controlli bloccanti verdi. Ogni test porta `# criterio: 03-Cmm`
sulla riga sopra. Messaggi di commit in Conventional Commits con descrizione in italiano:
`feat(api)`, `feat(posts)`, `feat(cli)`, `refactor(cli)`, `test`, `docs`. Gli snapshot syrupy
nuovi si generano con `--snapshot-update` e si leggono prima del commit. Costanti dei test:
community `79`, post `21269`, `occToken: 5`, `screenOccToken: 3`, operazione `12`, utenti `7` e
`8`, campi custom `1411`, `1412`, `1413`.

## Elenco

### [x] T01 – `_put` con corpo vuoto e riga di ROADMAP

- Criteri: 03-C08 (helper)
- Dipende da: nessuno
- Test: `tests/unit/test_api_base.py::TestResourceClientEmptyBodies::test_put_without_body_returns_empty_dict`
  (`respx.put` con `httpx.Response(200)` senza corpo → `{}`), accanto ai test esistenti di
  caratterizzazione (`test_put_array_raises_type_error` resta verde).
- Passi:
  1. Scrivere il test; eseguirlo: rosso (`JSONDecodeError`).
  2. In `api/_base.py`: `_put` restituisce `{}` se `not response.content`, come `_delete`;
     docstring in italiano.
  3. `ROADMAP.md`: riga `0.11.0 | Post write: custom posts, comments and workflow (ADR 0001) | M29
     | ⏳ In progress | specs/03-post-write/spec.md`; nota "last used: M29".
  4. Controlli bloccanti; commit `feat(api): PUT senza corpo di risposta vale come oggetto vuoto;
     riga 0.11.0 in ROADMAP`.

### [ ] T02 – Fixture JSON, rigenerazione dei dati di screen e contract test dei DTO

- Criteri: 03-C29 (DTO)
- Dipende da: nessuno
- Rivisto il 2026-10-09: tre fixture del workflow non si validavano perché `screenData` e
  `newScreenData` erano `dict[str, dict]`; si aggiungono i passi 0 e il test
  `::test_screen_data_accepts_scalar_values` (rosso prima della rigenerazione).
- Test: `tests/contract/test_models.py::TestPostWriteDTOs::test_write_dto_superset` (i 22 DTO
  della spec, `CreateCustomPostRequest` compreso) e `::test_typed_stub_superset`
  (`PostDetailDTO1`, `PostEditableContentDataDTO1`, `PostCommentDTO1`,
  `PostWorkflowDefinitionStateDTO1`, `PostWorkflowDefinitionTransitionDTO1`,
  `WorkflowDefinitionScreenDTO1`, `InputPostAttachmentDTO1`, `InputPostCommentAttachmentDTO1`);
  verdi subito (caratterizzano i modelli generati). Le fixture si dimostrano con
  `::test_response_fixtures_parse` parametrizzato: ogni fixture si valida nel suo DTO generato.
- Passi:
  0. `scripts/generate_models.py`: `screenData` e `newScreenData` in `_PATCHED_FIELDS`;
     `uv run python scripts/generate_models.py --offline`; leggere il diff (solo quei campi).
  1. Scrivere le 14 fixture di `tests/fixtures/payloads/` elencate nel piano (`create_post_response.json`
     … `custom_field_validation_error_response.json`), sagomate sul swagger: `postData`/`contentData`
     completi con `descriptionDelta` finto, `customData: {"1411": 226, "1413": true}`,
     `occToken: 5`, `screenOccToken: 3`, `workflowPermittedOperations` con l'operazione `12`,
     `creatorUser` "Alice Rossi"; `post_for_edit_response.json` con `communityId: 79`.
  2. Scrivere i test; eseguirli: verdi (DTO già generati), tranne `test_response_fixtures_parse`
     che è rosso finché le fixture mancano.
  3. `uv run pytest -m contract` e controlli bloccanti; commit `test: fixture e contract test dei
     DTO di scrittura dei post, dati di screen come valori qualsiasi (03-T02)`.

### [ ] T03 – Façade di scrittura dei post

- Criteri: 03-C29 (façade); base per 03-C01…C14
- Dipende da: T02
- Test: `tests/unit/test_facade_posts_write.py` (nuovo) — `PostWriteResult.from_create/from_edit/from_copy`
  sulle fixture (`post_id` dal DTO o da `post.id` con `from_edit`, `next_occ_token`, `post.title`
  tipizzato, `post is None` senza `postData`); `PostForCreate`, `PostForEdit` (`occ_token`,
  `community_id`, `custom_id`, `current_workflow_state.name`, `content_data.custom_data`),
  `PostForCopy`; `PostComment` (`parent_comment_id` da `parentComment.id`, `None` senza);
  `PostAttachmentsWriteResult` (`added`, `updated`, `removed_ids`); `WorkflowScreen`,
  `WorkflowOperationResult` (`new_permitted_operations[0].id`), `WorkflowScreenWriteResult`;
  `tests/contract/test_models.py::TestPostWriteDTOs::test_facade_smoke_*` (03-C29).
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError`).
  2. `models/facade/posts_write.py`: helper `_typed(stub, model)`; le otto façade con `.raw`,
     `from_dict` e le proprietà del piano; docstring in italiano.
  3. Controlli bloccanti (anche `-m contract`); commit `feat(posts): façade per le risposte di
     scrittura, le letture propedeutiche, i commenti e il workflow`.

### [ ] T04 – `PostCapabilities` estesa e `posts capabilities`

- Criteri: 03-C15
- Dipende da: nessuno
- Test: `tests/unit/test_facade_posts.py::test_capabilities_exposes_write_flags_and_operations`
  (fixture estesa: `can_copy`, `can_edit_attachments`, `can_edit_workflow_screen_data`,
  `workflow_permitted_operations[0].id == 12` e `.name`); `tests/unit/test_cli_posts.py::TestPostsCapabilities::test_table_shows_write_flags_and_operations`
  (`12 Approva` nell'output); snapshot esistente di `posts capabilities` rigenerato e riletto; i
  test attuali dei sette flag restano verdi.
- Passi:
  1. `tests/fixtures/payloads/get_post_capabilities_response.json`: aggiungere `canCopy`,
     `canEditAttachments`, `canEditWorkflowScreenData`, `workflowPermittedOperations` (nessuna
     chiave tolta); eseguire la suite: solo gli snapshot cambiano.
  2. Scrivere i test; eseguirli: rossi (`AttributeError`, colonna assente).
  3. `models/facade/posts.py`: le quattro proprietà (operazioni rivalidate in
     `PostWorkflowDefinitionTransitionDTO1`); `cli/posts.py`: riga curata con le tre colonne e
     `workflow_operations` (`"12 Approva, 13 Rifiuta"`).
  4. Snapshot, controlli bloccanti; commit `feat(posts): capabilities di copia, allegati e
     operazioni di workflow permesse`.

### [ ] T05 – `PostsWriteAPI`: letture propedeutiche e `create`

- Criteri: 03-C01, 03-C02 (create), 03-C03 (create), 03-C11, 03-C16 (libreria), 03-C17 (create)
- Dipende da: T03
- Test: `tests/unit/test_api_posts_write.py` (nuovo) — `TestPostsPrep::test_get_for_create`,
  `::test_get_for_edit_no_query_and_occ_token`, `::test_get_for_edit_load_attachments_false_in_query`,
  `::test_get_for_copy`; `TestPostsCreate::test_create_sends_only_given_fields_and_wraps_response`
  (corpo con `announcement: false`), `::test_create_raw_equivalent`,
  `::test_scheduled_publication_zoneinfo_in_body`, `::test_naive_scheduled_publication_raises_before_request`;
  `TestPostsErrors::test_400_custom_field_validation_error_readable`,
  `::test_timeout_raises_transport_error_once` (per `create`; `add_comment` si aggiunge in T07).
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError`).
  2. `api/posts_write.py`: `PostsWriteAPI(ResourceClient)`, costanti dei percorsi,
     `get_for_create`, `get_for_edit`, `get_for_copy`, `create`, `create_raw`; `api/posts.py`:
     `class PostsAPI(PostsWriteAPI)`.
  3. Controlli bloccanti; commit `feat(posts): letture propedeutiche con occ_token e creazione di
     un post (create, create_raw)`.

### [ ] T06 – `edit`, `edit_custom_data`, `copy` e il `409`

- Criteri: 03-C02 (edit, edit_custom_data, copy), 03-C03 (edit, copy), 03-C04, 03-C05, 03-C06,
  03-C07 (tre metodi)
- Dipende da: T05
- Test: `test_api_posts_write.py::TestPostsEdit::test_edit_sends_only_given_fields`,
  `::test_edit_without_fields_sends_empty_body`, `::test_edit_raw_equivalent`;
  `TestPostsCustomData::test_edit_custom_data_body_and_result`, `::test_raw_equivalent`;
  `TestPostsCopy::test_copy_body_and_result`, `::test_raw_equivalent`;
  `TestPostsErrors::test_409_raises_concurrency_error_once` parametrizzato su `edit`,
  `edit_custom_data`, `copy` (i due metodi del workflow si aggiungono in T08);
  `test_scheduled_publication_*` estesi a `edit` e `copy`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (metodi inesistenti).
  2. `api/posts_write.py`: `edit`/`edit_raw`, `edit_custom_data`/`_raw`, `copy`/`_raw` con
     `build_write_body` e `PostWriteResult.from_edit`/`from_copy`.
  3. Controlli bloccanti; commit `feat(posts): modifica, campi custom e copia di un post con
     occToken`.

### [ ] T07 – Watcher, allegati, eliminazione, marcatura e commento

- Criteri: 03-C02 (edit_watchers, edit_attachments, add_comment), 03-C08, 03-C09, 03-C10,
  03-C17 (add_comment)
- Dipende da: T01, T05
- Test: `test_api_posts_write.py::TestPostsWatchersAttachments::test_edit_watchers_body_and_none`
  (risposta `200` vuota), `::test_edit_attachments_body_and_result`, `::test_raw_equivalents`;
  `TestPostsDelete::test_delete_returns_post_id`,
  `::test_mark_as_erasable_puts_without_body_and_returns_post_id` (`request.content == b""`);
  `TestPostsComment::test_add_comment_body_and_facade`, `::test_add_comment_raw_equivalent`;
  `TestPostsErrors::test_timeout_raises_transport_error_once` esteso a `add_comment`.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `api/posts_write.py`: `edit_watchers`/`_raw`, `edit_attachments`/`_raw`, `delete`,
     `mark_as_erasable`, `add_comment`/`_raw`.
  3. Controlli bloccanti; commit `feat(posts): watcher, allegati, eliminazione, marcatura per la
     cancellazione e commenti`.

### [ ] T08 – Workflow in libreria

- Criteri: 03-C02 (workflow), 03-C07 (workflow), 03-C12, 03-C13, 03-C14
- Dipende da: T05
- Test: `test_api_posts_write.py::TestPostsWorkflow::test_get_workflow_screen_without_operation`,
  `::test_get_workflow_screen_with_operation_query`, `::test_execute_operation_body_and_result`,
  `::test_execute_operation_without_kwargs_sends_empty_body`, `::test_edit_workflow_screen_body_and_result`,
  `::test_raw_equivalents`; `TestPostsErrors::test_409_raises_concurrency_error_once` esteso a
  `execute_workflow_operation` ed `edit_workflow_screen`.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `api/posts_write.py`: `get_workflow_screen`, `execute_workflow_operation`/`_raw`,
     `edit_workflow_screen`/`_raw`.
  3. Controlli bloccanti; commit `feat(posts): lettura dello screen, transizioni e dati di screen
     del workflow`.

### [ ] T09 – Helper CLI condivisi: caratterizzazione, `cli/_write.py`, `parse_kv_values`, `handle_error(resource=)`

- Criteri: 03-C28 (messaggio); base per 03-C18…C27
- Dipende da: nessuno
- Test: `tests/unit/test_cli_write.py` (nuovo) — **caratterizzazione prima**, scritta contro
  `pynteracta.cli.tasks._parse_expiration`, `_merge_body`, `_validate_body` e verde sul codice
  attuale: ISO 8601 senza offset nel fuso dato, con offset (fuso ignorato), non ISO → exit 2,
  fuso sconosciuto → exit 2; flag non-`None` sostituiscono le chiavi camelCase, `None` ignorati;
  corpo non valido → exit 2 con il nome del DTO. Poi, rossi: `test_parse_kv_values_types`
  (`true`/`false`, interi, stringhe, `=` dentro il valore), `test_parse_kv_values_missing_eq_raises`;
  `tests/unit/test_cli_common.py::test_handle_error_concurrency_with_resource` (`Post 21269 changed
  since it was read: fetch it again and retry`), il test senza `resource` resta verde.
- Passi:
  1. Scrivere e vedere verde la caratterizzazione; scrivere gli altri test: rossi.
  2. `cli/_write.py`: `DEFAULT_TIMEZONE`, `parse_zoned_datetime(value, timezone, *, option)`,
     `merge_body`, `validate_body`, `parse_kv_values`, `JsonBodyOption`, `TimezoneOption`;
     `cli/tasks.py` importa da `_write.py` e perde le copie private; la caratterizzazione cambia
     solo l'import e resta verde; `test_cli_tasks.py` intero verde.
  3. `cli/_common.py`: `handle_error(exc, *, console, resource=None)`.
  4. Controlli bloccanti; commit `refactor(cli): helper di scrittura condivisi in cli/_write.py e
     messaggio del 409 con il nome della risorsa`.

### [ ] T10 – Comandi `posts create`, `posts comment`, `posts get-for-*`

- Criteri: 03-C16 (CLI), 03-C18, 03-C25, 03-C26
- Dipende da: T05, T07, T09
- Test: `tests/unit/test_cli_posts_write.py` (nuovo) — `test_posts_help_lists_write_commands`
  (i nomi dei comandi di questo task nell'help di `posts`; T11, T12 e T13 lo estendono fino ai
  quattordici); `TestPostsCreate::test_flags_and_json_merge_flags_win`,
  `::test_announcement_false_by_default`, `::test_table_output`, `::test_json_output` (snapshot),
  `::test_custom_data_bad_token_exits_2`, `::test_validation_error_exits_6_with_body`,
  `::test_scheduled_publication_default_timezone`; `TestPostsComment::test_text_and_parent_body`,
  `::test_table_output` (snapshot), `::test_json_output`, `::test_without_text_exits_2`;
  `TestPostsPrep::test_get_for_edit_table_starts_with_occ_token` (snapshot),
  `::test_get_for_copy_table`, `::test_get_for_create_table`, `::test_no_attachments_sends_query`,
  `::test_full_json`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (comandi inesistenti).
  2. `cli/posts_write.py`: opzioni condivise, `merge_custom_data`, righe curate
     `write_result_row`, `comment_row`, `for_edit_row`; comandi `create`, `comment`,
     `get-for-create`, `get-for-edit`, `get-for-copy`; `cli/__init__.py`: import di
     `posts_write` prima di `add_typer`.
  3. Snapshot, controlli bloccanti; commit `feat(cli): comandi posts create, comment e
     get-for-create|edit|copy`.

### [ ] T11 – Comandi `posts edit`, `posts edit-custom-data`, `posts copy`

- Criteri: 03-C19, 03-C20, 03-C21, 03-C22, 03-C28 (tre comandi)
- Dipende da: T06, T10
- Test: `test_cli_posts_write.py::TestPostsEdit::test_edit_base_from_fixture` (funzione pura),
  `::test_edit_reads_for_edit_then_puts_patched_body`, `::test_edit_with_occ_token_still_reads_base`,
  `::test_edit_base_skips_missing_fields`, `::test_edit_without_occ_token_in_response_exits_1`,
  `::test_edit_description_flag_sets_plain_format`, `::test_edit_flags_win_over_json_over_read`,
  `::test_merge_custom_data` (funzione pura), `::test_edit_json_output`;
  `TestPostsEditCustomData::test_reads_then_puts_merged_custom_data`,
  `::test_without_data_exits_2_without_requests`; `TestPostsCopy::test_copy_base_from_fixture`,
  `::test_copy_reads_for_copy_then_puts_base_with_title`, `::test_copy_table_shows_new_post`;
  `TestPostsConflicts::test_conflict_exits_9_without_retry` parametrizzato sui tre comandi
  (messaggio esatto della spec, una sola scrittura).
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_write.py`: `edit_base`, `copy_base`; comandi `edit`, `edit-custom-data`, `copy`
     (lettura propedeutica sempre, token da flag o letto, unione base < `--json` < flag,
     `handle_error(..., resource=f"Post {post_id}")`).
  3. Snapshot, controlli bloccanti; commit `feat(cli): posts edit, edit-custom-data e copy come
     patch con occToken letto o imposto`.

### [ ] T12 – Comandi `posts edit-watchers`, `posts delete`, `posts mark-erasable`

- Criteri: 03-C23, 03-C24
- Dipende da: T07, T10
- Test: `test_cli_posts_write.py::TestPostsEditWatchers::test_add_and_remove_body_and_message`,
  `::test_json_output`, `::test_without_flags_exits_2`; `TestPostsDelete::test_prompt_shows_id_and_title_and_y_deletes`
  (monkeypatch `_stdin_is_interactive`, `input="y\n"`, `GET post-detail-by-id` per il titolo),
  `::test_prompt_n_does_nothing`, `::test_yes_skips_prompt`, `::test_non_interactive_without_yes_refuses`,
  `::test_json_output`; `TestPostsMarkErasable` con gli stessi cinque casi e i testi della spec.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_write.py`: comandi `edit-watchers`, `delete`, `mark-erasable` (`confirm_destructive`,
     testo o JSON come `tasks delete`).
  3. Controlli bloccanti; commit `feat(cli): posts edit-watchers, delete e mark-erasable con
     conferma`.

### [ ] T13 – Comandi del workflow

- Criteri: 03-C27, 03-C28 (due comandi)
- Dipende da: T08, T10
- Test: `test_cli_posts_write.py::TestPostsWorkflow::test_workflow_screen_table` (snapshot),
  `::test_workflow_screen_operation_query`, `::test_execute_with_screen_data_reads_screen_then_posts_merged`,
  `::test_execute_without_data_posts_empty_body_without_get`, `::test_execute_screen_occ_token_flag_wins`,
  `::test_execute_table_shows_new_state`, `::test_edit_screen_reads_then_puts_merged`,
  `::test_screen_base` (funzione pura); `TestPostsConflicts::test_conflict_exits_9_without_retry`
  esteso a `workflow-execute` e `workflow-edit-screen`; `test_posts_help_lists_write_commands`
  completato con i quattordici nomi.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_write.py`: `screen_base`, `screen_row`, `operation_result_row`; comandi
     `workflow-screen`, `workflow-execute`, `workflow-edit-screen`.
  3. Snapshot, controlli bloccanti; commit `feat(cli): posts workflow-screen, workflow-execute e
     workflow-edit-screen`.

### [ ] T14 – Documentazione: pagine API e CLI, home, README, testing, `.env.example`

- Criteri: 03-C30
- Dipende da: T13
- Test: `tests/unit/test_docs_snippets.py::test_posts_pages_document_write_commands` (marker
  03-C30: i quattordici comandi in `docs/cli.md`; `create(`, `edit(`, `copy(`, `add_comment(`,
  `execute_workflow_operation(`, `PostWriteResult`, `occ_token`, `get_for_edit` in
  `docs/api/posts.md`; "posts" nella frase delle scritture di `docs/index.md` e `README.md`);
  rosso prima delle pagine; più `uv run mkdocs build --strict`.
- Passi:
  1. Scrivere il test; eseguirlo: rosso.
  2. `docs/api/posts.md`: sezione "Writing posts" (letture propedeutiche e `occ_token`, metodi,
     façade con `::: pynteracta.models.facade.posts_write`, date, campi custom, workflow, campi
     omessi "to be confirmed against the tenant, see T16"); snippet coerenti con l'API.
  3. `docs/cli.md`: i quattordici comandi con esempi, patch e `--occ-token`, prompt e `--yes`,
     `--custom-data`/`--screen-data`; `docs/index.md` e `README.md`: "tasks and posts" nelle
     frasi delle scritture, senza numeri di versione; `docs/testing.md` e
     `tests/integration/.env.example`: le due variabili nuove.
  4. `uv run mkdocs build --strict`, controlli bloccanti; commit `docs: scrittura dei post nelle
     pagine API e CLI, home e README, variabili per gli integration test`.

### [ ] T15 – Integration test del ciclo completo e della lettura dello screen

- Criteri: 03-C31 (codice)
- Dipende da: T08
- Test: `tests/integration/test_posts_integration.py` (nuovo) —
  `TestPostsWriteIntegration::test_full_cycle` (skip senza `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` o
  `PYNTERACTA_TEST_USER_ID`; `create` con titolo riconoscibile, `description` testo semplice,
  `client_uid = f"pynteracta-it-{int(time.time())}"` → `get_by_client_uid` → `get_for_edit` →
  `edit` con il solo titolo → `get` e stampa `[T16]` dei campi (descrizione, visibilità, custom
  data) → `edit_watchers(add=[user])` → `add_comment` → `get_for_copy` → `copy` con titolo →
  `delete` della copia e dell'originale in `finally` (`contextlib.suppress(NotFoundError)`) →
  `NotFoundError` su entrambi); `::test_workflow_screen_read_only` (skip senza
  `PYNTERACTA_TEST_WORKFLOW_POST_ID`; `get_workflow_screen` → `screen_occ_token` e
  `current_workflow_state` non `None`; nessuna transizione). Si verifica che i due test siano
  raccolti e **saltati** senza le variabili.
- Passi:
  1. Scrivere i test; `uv run pytest tests/integration/test_posts_integration.py -m integration -q`
     → `skipped`.
  2. Controlli bloccanti; commit `test: integration test opt-in del ciclo di scrittura dei post`.

### [ ] T16 – Esecuzione sul tenant di prova e prove manuali (manuale)

- Criteri: 03-C31 (esecuzione), verifica manuale della spec
- Chi: maintainer
- Cosa fare: in `tests/integration/.env` impostare `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` con una
  community **di prova** e, se disponibile, `PYNTERACTA_TEST_WORKFLOW_POST_ID`; esportare le
  variabili; eseguire `uv run pytest tests/integration/test_posts_integration.py -m integration
  -v -s`; annotare qui: (a) dopo `edit` con il solo titolo, se descrizione, visibilità e custom
  data sono rimasti invariati o azzerati; (b) cosa contiene la copia fatta con il solo titolo
  (descrizione e custom data copiati o vuoti); (c) se `descriptionFormat: 2` in `edit` è stato
  accettato come testo semplice; (d) a mano, su un post di prova: `pynteracta posts mark-erasable
  ID --yes` e poi `posts get ID`, rispetto a `posts delete`; (e) a mano, se c'è un post di workflow
  di prova con una transizione senza screen: `posts workflow-execute ID OP` con corpo `{}`
  accettato o rifiutato; (f) errori. Se il server **non** azzera i campi omessi, fermarsi: la base
  delle patch si riduce con una revisione della spec (03-C19…03-C22) prima di T17.
- Esito: <compilato a mano>

### [ ] T17 – Chiusura: PRD, esito delle prove nei docs, eventuale revisione

- Criteri: nessuno nuovo (chiusura: "Requisiti nuovi", conferme, esito di T16)
- Dipende da: T14, T16
- Test: nessuno; verifica con la rilettura dei diff, il controllo che ogni link risolva,
  `test_docs_snippets` e `uv run mkdocs build --strict`.
- Passi:
  1. `specs/prd.md`: RF-021a, RF-021b, RF-021c, RF-006a dalla sezione "Requisiti nuovi" della
     spec; conferma del maintainer accanto a RF-021, RF-006, §5 e §7 (parte dei post); riga nella
     storia.
  2. `docs/api/posts.md` e `docs/cli.md`: l'esito di T16 al posto di "to be confirmed" (campi
     omessi, formato della descrizione, `mark-erasable`, transizione senza screen).
  3. Se T16 ha imposto una revisione della spec: sezione "Revisioni" in `spec.md`, criteri
     sostituiti, codice e test adeguati (in un task aggiunto, come T13 della spec 02).
  4. Commit `docs: PRD e pagine aggiornate con l'esito delle prove sul tenant per la spec 03`.

La riga `0.11.0 ⏳ M29` in `ROADMAP.md` la scrive T01; la sezione M29 in `PROGRESS.md` la scrive
`/sddpa:verifica`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 03-C01 | T05 |
| 03-C02 | T05, T06, T07, T08 |
| 03-C03 | T05, T06 |
| 03-C04 | T06 |
| 03-C05 | T06 |
| 03-C06 | T06 |
| 03-C07 | T06, T08 |
| 03-C08 | T01, T07 |
| 03-C09 | T07 |
| 03-C10 | T07 |
| 03-C11 | T05 |
| 03-C12 | T08 |
| 03-C13 | T08 |
| 03-C14 | T08 |
| 03-C15 | T04 |
| 03-C16 | T05, T10 |
| 03-C17 | T05, T07 |
| 03-C18 | T10 |
| 03-C19 | T11 |
| 03-C20 | T11 |
| 03-C21 | T11 |
| 03-C22 | T11 |
| 03-C23 | T12 |
| 03-C24 | T12 |
| 03-C25 | T10 |
| 03-C26 | T10 |
| 03-C27 | T13 |
| 03-C28 | T09, T11, T13 |
| 03-C29 | T02, T03 |
| 03-C30 | T14 |
| 03-C31 | T15, T16 (manuale) |
