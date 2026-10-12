# Task 08 – Scrittura dei post evento

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (modulo, metodo o comando inesistente, campo mancante); poi il codice;
il commit arriva con i cinque controlli bloccanti verdi. Ogni test porta `# criterio: 08-Cmm`
sulla riga sopra. Messaggi di commit in Conventional Commits con descrizione in italiano:
`feat(api)`, `feat(posts)`, `feat(cli)`, `refactor(facade)`, `test`, `docs`. Gli snapshot syrupy
nuovi si generano con `--snapshot-update` e si leggono prima del commit. Costanti dei test:
community `79`, post `21269`, `occToken: 5`, utenti `7` e `8`, gruppi `3` e `4`, `_ROME =
ZoneInfo("Europe/Rome")`, `_START` 2026-11-05 10:00 e `_END` 12:00 nel fuso `_ROME`.

## Elenco

### [x] T01 – `event_datetime_block` e riga di ROADMAP

- Criteri: 08-C02 (regola delle date), 08-C03 (helper)
- Dipende da: nessuno
- Test: `tests/unit/test_api_utils.py::TestEventDatetimeBlock`: fuso da `start_at` (`ZoneInfo.key`),
  `end_at` in `UTC` convertito nel fuso di `start_at`, offset fisso `+02:00` → `UTC` e ora
  convertita, solo `end_at` → fuso da `end_at`, `start_at` o `end_at` senza fuso → `ValueError`
  con il nome del parametro, `(None, None)` → `{}`; i test di `zoned_datetime_input` restano verdi
  (caratterizzazione).
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError`).
  2. `api/_utils.py`: `event_datetime_block(start_at, end_at)` come nel piano; docstring in
     italiano.
  3. `ROADMAP.md`: riga `| **0.14.0** | Event post write: create, edit, copy and participate (ADR 0001)
     | M34 | ⏳ In progress | [specs/08-event-post-write/spec.md](…) |`; nota "last used: M34".
  4. Controlli bloccanti; commit `feat(api): blocco data-ora degli eventi con fuso IANA; riga
     0.14.0 in ROADMAP`.

### [x] T02 – Fixture JSON e contract test dei DTO evento

- Criteri: 08-C22 (DTO)
- Dipende da: nessuno
- Test: `tests/contract/test_models.py::TestEventPostDTOs::test_request_dto_superset` (4 DTO di
  richiesta), `::test_response_dto_superset` (3 DTO di risposta), `::test_typed_stub_superset`
  (6 varianti tipizzate), verdi subito (caratterizzano i modelli generati);
  `::test_response_fixtures_parse` parametrizzato sulle sei fixture nel loro DTO generato, rosso
  finché le fixture mancano.
- Passi:
  1. Scrivere i test; eseguirli: i superset verdi, `test_response_fixtures_parse` rosso
     (`FileNotFoundError`).
  2. Scrivere le sei fixture di `tests/fixtures/payloads/` del piano
     (`create_event_post_response.json` … `event_post_for_copy_response.json`), sagomate sul
     swagger con i dati finti del piano; `event_post_for_copy_response.json` con `announcement:
     true`.
  3. `uv run pytest -m contract` e controlli bloccanti; commit `test: fixture e contract test dei
     DTO dei post evento`.

### [x] T03 – Helper di rivalidazione degli stub in `facade/_stubs.py`

- Criteri: nessuno (refactor preparatorio per 08-C11)
- Dipende da: nessuno
- Test: nessun test nuovo; `tests/unit/test_facade_posts_write.py` e i contract test delle façade
  di scrittura fissano già il comportamento di `_typed`/`_typed_list` e restano verdi.
- Passi:
  1. Eseguire `test_facade_posts_write.py`: verde (linea di riferimento).
  2. `models/facade/_stubs.py`: `typed` e `typed_list`, corpo invariato; `posts_write.py` li
     importa e toglie le copie locali.
  3. Controlli bloccanti (anche `-m contract`); commit `refactor(facade): helper di
     rivalidazione degli stub condivisi tra le façade`.

### [ ] T04 – Façade dei post evento e `ParticipationAnswer`

- Criteri: 08-C07 (enum), 08-C11 (façade), 08-C22 (façade)
- Dipende da: T02, T03
- Test: `tests/unit/test_facade_posts_event.py` (nuovo): `test_participation_answer_values`
  (`ParticipationAnswer(2) is MAYBE`, `(4)` → `ValueError`); `EventData` sulla fixture di edit
  (`start_at == _START` da `zonedDatetime`, `end_at`, `timezone`, `all_day`, `location`,
  `participants_count`, `my_answer is YES`, `invited_users[0].id == 7` e `.type_id == 2`,
  `invited_groups[0].id == 3`, `send_edit_post_notifications`), fallback `localDatetime` +
  `timezone`, `None` senza entrambi, `my_answer is None` senza `participateTypeId`;
  `EventInvitee.name` per utente e gruppo; `EventPostForCreate/Edit/Copy.from_dict` (`occ_token`,
  `community_id`, `content_data.title`, `content_data.coverImageContentRef`, `event is None`
  senza `event`); `tests/contract/test_models.py::TestEventPostDTOs::test_facade_smoke` e
  `::test_facade_raw_accessible`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError`).
  2. `models/facade/posts_event.py`: `ParticipationAnswer`, `EventInvitee`, `EventData`,
     `EventPostForCreate`, `EventPostForEdit`, `EventPostForCopy` come nel piano, con `.raw` e
     docstring in italiano; esportarli da `models/facade/__init__.py`.
  3. Controlli bloccanti (anche `-m contract`); commit `feat(posts): façade dei dati evento,
     delle letture propedeutiche e risposta di partecipazione`.

### [ ] T05 – `PostsEventAPI`: blocco evento, letture propedeutiche e `create_event`

- Criteri: 08-C01, 08-C02, 08-C03 (create), 08-C04 (create), 08-C09 (400), 08-C10 (create),
  08-C11
- Dipende da: T01, T04
- Test: `tests/unit/test_api_posts_event.py` (nuovo): `TestEventPrep::test_get_event_for_create`,
  `::test_get_event_for_edit_no_query_occ_token_and_event`,
  `::test_get_event_for_edit_load_attachments_false_in_query`, `::test_get_event_for_copy`,
  `::test_event_none_when_missing`; `TestEventCreate::test_create_event_sends_only_given_fields_and_wraps_response`,
  `::test_create_event_start_only_sends_event_block_without_announcement`,
  `::test_invited_user_without_type_sends_id_only`, `::test_end_at_converted_into_start_zone`,
  `::test_fixed_offset_sends_utc`, `::test_create_event_raw_equivalent`; `build_event_block` da
  solo (`{}` senza kwargs); `TestEventErrors::test_naive_datetime_raises_before_request` (per
  `create_event`), `::test_create_400_custom_field_validation_readable`,
  `::test_timeout_raises_transport_error_once` (per `create_event`);
  `::test_posts_api_exposes_event_methods_and_keeps_custom_ones`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError`).
  2. `api/posts_event.py`: percorsi, `build_event_block`, `get_event_for_create|edit|copy`,
     `create_event`, `create_event_raw`; `api/posts.py`: `class PostsAPI(PostsWriteAPI,
     PostsEventAPI)`.
  3. Controlli bloccanti; commit `feat(posts): letture propedeutiche e creazione dei post evento`.

### [ ] T06 – `edit_event`, `copy_event` e il `409`

- Criteri: 08-C03 (edit, copy), 08-C04 (edit, copy), 08-C05, 08-C06, 08-C08
- Dipende da: T05
- Test: `test_api_posts_event.py::TestEventEdit::test_edit_event_sends_only_given_fields`,
  `::test_edit_event_end_only_sends_end_and_timezone`,
  `::test_edit_event_without_fields_sends_empty_body`, `::test_raw_equivalent`;
  `TestEventCopy::test_copy_event_body_and_result`, `::test_raw_equivalent`;
  `TestEventErrors::test_naive_datetime_raises_before_request` esteso a `edit_event` e
  `copy_event`; `::test_409_raises_concurrency_error_once` parametrizzato sui due metodi.
- Passi:
  1. Scrivere i test; eseguirli: rossi (metodi inesistenti).
  2. `api/posts_event.py`: `edit_event`/`_raw`, `copy_event`/`_raw` con `build_write_body`,
     `build_event_block` e `PostWriteResult.from_edit`/`from_copy`.
  3. Controlli bloccanti; commit `feat(posts): modifica e copia dei post evento con occToken`.

### [ ] T07 – `participate`

- Criteri: 08-C04 (participate), 08-C07, 08-C09 (404, 403), 08-C10 (participate)
- Dipende da: T05
- Test: `test_api_posts_event.py::TestParticipate::test_participate_body_and_none`,
  `::test_participate_int_answer`, `::test_participate_invalid_answer_raises_before_request`,
  `::test_raw_equivalent`; `TestEventErrors::test_participate_404_not_found_once`,
  `::test_participate_403_permission_once`, `::test_timeout_raises_transport_error_once` esteso
  a `participate`.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `api/posts_event.py`: `participate`/`participate_raw` (`ParticipationAnswer(answer)` prima
     della chiamata, `_put` con il corpo, restituisce `None`).
  3. Controlli bloccanti; commit `feat(posts): risposta all'invito di un post evento`.

### [ ] T08 – `parse_event_datetime` nella CLI

- Criteri: 08-C13 (parsing)
- Dipende da: nessuno
- Test: `tests/unit/test_cli_write.py::TestParseEventDatetime`: sola data → mezzanotte nel fuso
  dato, data-ora senza offset → fuso dato, offset esplicito conservato, fuso sconosciuto → exit
  `2` con `--timezone: unknown IANA time zone`, valore non ISO → exit `2` con il nome
  dell'opzione, `None` → `None`; i test di `parse_zoned_datetime` restano verdi.
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError`).
  2. `cli/_write.py`: `parse_event_datetime(value, timezone, *, option)` come nel piano.
  3. Controlli bloccanti; commit `feat(cli): lettura delle date degli eventi da data o data-ora`.

### [ ] T09 – Modulo `cli/posts_event.py` e comandi `get-event-for-*`

- Criteri: 08-C20
- Dipende da: T05
- Test: `tests/unit/test_cli_posts_event.py` (nuovo): `test_posts_help_lists_event_commands` (i
  tre comandi di lettura; T10, T11 e T12 aggiungono i loro nomi);
  `TestPrepCommands::test_get_event_for_edit_table_starts_with_occ_token` (snapshot),
  `::test_get_event_for_copy_table` (snapshot), `::test_get_event_for_create_table` (snapshot),
  `::test_no_attachments_sends_query` (edit e copy), `::test_full_json`;
  `test_cli_posts_write.py::test_posts_help_lists_write_commands` resta verde.
- Passi:
  1. Scrivere i test; eseguirli: rossi (comandi inesistenti).
  2. `cli/posts_event.py`: registrazione sull'`app` di `cli/posts.py`, `read_timezone`, righe
     `event_for_create_row`, `event_for_edit_row`, `event_for_copy_row`, i tre comandi di
     lettura; `cli/__init__.py`: import dopo `posts_write`.
  3. Snapshot letti, controlli bloccanti; commit `feat(cli): letture propedeutiche dei post
     evento`.

### [ ] T10 – `posts create-event`

- Criteri: 08-C09 (exit 6), 08-C12, 08-C13
- Dipende da: T08, T09
- Test: `test_cli_posts_event.py::TestCreateEvent::test_flags_and_json_merge_flags_win`,
  `::test_without_announcement_and_pinned_keys_missing`, `::test_table_output` (snapshot),
  `::test_json_output` (snapshot), `::test_date_only_is_local_midnight_and_all_day`,
  `::test_explicit_offset_sends_utc`, `::test_timezone_flag_applied`,
  `::test_unknown_timezone_exits_2`, `::test_bad_start_exits_2`,
  `::test_missing_start_exits_2_without_requests`, `::test_start_from_json_event_is_enough`;
  `merge_event` da solo (`--invite-user` sostituisce `users`, `allDay` del json resta);
  `TestExitCodes::test_create_validation_error_exits_6`.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_event.py`: opzioni nuove dell'evento, `event_flags_block`, `merge_event`,
     `event_write_result_row`, comando `create-event` (senza `--cover`, che arriva in T13).
  3. Snapshot letti, controlli bloccanti; commit `feat(cli): creazione dei post evento`.

### [ ] T11 – `posts edit-event` e `posts copy-event`

- Criteri: 08-C14, 08-C15, 08-C16, 08-C19, 08-C21
- Dipende da: T06, T10
- Test: `test_cli_posts_event.py::TestEventWriteBlock::test_event_write_block` (i quattro casi);
  `event_edit_base` ed `event_copy_base` da soli sulle fixture;
  `TestEditEvent::test_edit_reads_form_then_puts_patched_body`,
  `::test_edit_with_occ_token_still_reads_base`, `::test_edit_base_skips_missing_fields`,
  `::test_edit_without_occ_token_in_response_exits_1`,
  `::test_edit_post_not_found_exits_5_without_put`,
  `::test_start_without_timezone_uses_read_zone`, `::test_timezone_flag_changes_event_zone`,
  `::test_invite_user_replaces_users_keeps_groups`, `::test_json_event_over_read_flags_over_json`;
  `TestCopyEvent::test_copy_reads_form_then_puts_base_with_title`,
  `::test_copy_table_shows_new_post` (snapshot); `TestConflicts::test_conflict_exits_9_without_retry`
  parametrizzato sui due comandi.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_event.py`: `event_write_block`, `event_edit_base`, `event_copy_base`, comandi
     `edit-event` (`--timezone` senza default, watcher add/remove) e `copy-event`.
  3. Snapshot letti, controlli bloccanti; commit `feat(cli): modifica e copia dei post evento a
     partire dal form letto`.

### [ ] T12 – `posts participate`

- Criteri: 08-C09 (exit 5, 4), 08-C17
- Dipende da: T07, T09
- Test: `test_cli_posts_event.py::TestParticipate::test_yes_with_notes_body_and_message`,
  `::test_maybe_and_no_type_ids` (parametrizzato), `::test_json_output`,
  `::test_invalid_choice_exits_2_without_requests`;
  `TestExitCodes::test_participate_not_found_exits_5`, `::test_participate_forbidden_exits_4`;
  `test_posts_help_lists_event_commands` completo con i sette nomi.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_event.py`: `ParticipationChoice`, comando `participate` con `--notes`.
  3. Controlli bloccanti; commit `feat(cli): risposta all'invito di un post evento`.

### [ ] T13 – Copertina con `--cover`

- Criteri: 08-C18
- Dipende da: T10, T11
- Test: `test_cli_posts_event.py::TestCoverAndAttach::test_cover_then_attach_uploaded_in_order`,
  `::test_cover_upload_failure_exits_11_without_write`, `::test_edit_event_cover_wins_over_read`,
  `::test_copy_event_cover`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (opzione inesistente).
  2. `cli/posts_event.py`: `--cover` sui tre comandi di scrittura e `_cover_ref`, caricata dopo
     la prima `validate_body` e prima di `--attach`.
  3. Controlli bloccanti; commit `feat(cli): copertina dei post evento caricata dallo storage`.

### [ ] T14 – Documentazione

- Criteri: 08-C23
- Dipende da: T07, T13
- Test: `tests/unit/test_docs_snippets.py::test_event_posts_pages_document_write_commands`
  (rosso prima delle pagine); `uv run mkdocs build --strict`.
- Passi:
  1. Scrivere il test; eseguirlo: rosso.
  2. `docs/api/posts.md`: sezione "Event posts" e reference `::: pynteracta.api.posts_event.PostsEventAPI`
     e `::: pynteracta.models.facade.posts_event`; via "read-only for now"; semantica dei campi
     omessi "to be confirmed" fino a T16.
  3. `docs/cli.md`: i sette comandi; exit `11` cita `--cover`. `docs/index.md` e `README.md`:
     scrittura completa per i gruppi dell'ADR 0001, via "Event posts follow", nessun numero di
     versione.
  4. `docs/testing.md` e `tests/integration/.env.example`: `PYNTERACTA_TEST_EVENT_COMMUNITY_ID`.
  5. Controlli bloccanti e `mkdocs build --strict`; commit `docs: scrittura dei post evento nella
     libreria e nella CLI`.

### [ ] T15 – Integration test del ciclo completo

- Criteri: 08-C24 (parte automatica)
- Dipende da: T07
- Test: `tests/integration/test_posts_integration.py::TestEventPostsWriteIntegration::test_full_cycle`
  come nel piano; senza le variabili è saltato (verifica: `uv run pytest -m integration -k
  EventPosts` senza `.env` → `skipped`).
- Passi:
  1. Scrivere il test con la pulizia in `finally` e le stampe `[T-manuale]`.
  2. Verificare lo skip senza variabili; `uv run ruff check .` e `mypy`.
  3. Commit `test: ciclo completo dei post evento sul tenant (opt-in)`.

### [ ] T16 – Prove sul tenant (manuale)

- Criteri: 08-C24 (esecuzione)
- Chi: maintainer
- Cosa fare: impostare `PYNTERACTA_TEST_EVENT_COMMUNITY_ID` (community di prova, mai di
  produzione) e `PYNTERACTA_TEST_USER_ID`; eseguire `uv run pytest -m integration -k EventPosts
  -s`; poi provare a mano con la CLI su un post evento di prova e annotare: campi omessi in
  `edit-event-post` e `copy-event-post` (per il post e per le chiavi di `event`); `typeId` degli
  invitati obbligatorio o no e suo default; effetto di `allDay` con date-ora; partecipazione del
  service account; formato della descrizione in modifica; presenza di `event` in `postData`
  delle risposte di scrittura.
- Esito: <compilato a mano>

### [ ] T17 – Chiusura: PRD, esito delle prove nei docs, eventuale revisione

- Criteri: nessuno nuovo (chiusura: "Requisiti nuovi", conferme, esito di T16)
- Dipende da: T14, T16
- Test: nessuno; verifica con la rilettura dei diff, `test_docs_snippets` e `uv run mkdocs build
  --strict`.
- Passi:
  1. `specs/prd.md`: RF-021e e RF-021f dalla sezione "Requisiti nuovi" della spec; RF-021
     aggiornato; §1 con la superficie di scrittura dell'ADR 0001 completa; conferma accanto a
     RF-021, RNF-010 e §6 per la parte degli eventi; riga nella storia.
  2. `docs/api/posts.md` e `docs/cli.md`: l'esito di T16 al posto di "to be confirmed" (campi
     omessi, `typeId`, `allDay`, colonne vuote se `event` manca da `postData`).
  3. Se T16 impone una revisione della spec (08-C14…C16 o default di `invitation_type_id`):
     sezione "Revisioni" in `spec.md`, criteri nuovi, codice e test in un task aggiunto.
  4. Commit `docs: PRD e pagine aggiornate con l'esito delle prove sul tenant per la spec 08`.

La riga `0.14.0 ⏳ M34` in `ROADMAP.md` la scrive T01; la sezione M34 in `PROGRESS.md` la scrive
`/sddpa:verifica`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 08-C01 | T05 |
| 08-C02 | T01, T05 |
| 08-C03 | T01, T05, T06 |
| 08-C04 | T05, T06, T07 |
| 08-C05 | T06 |
| 08-C06 | T06 |
| 08-C07 | T04, T07 |
| 08-C08 | T06 |
| 08-C09 | T05, T07, T10, T12 |
| 08-C10 | T05, T07 |
| 08-C11 | T04, T05 |
| 08-C12 | T10 |
| 08-C13 | T08, T10 |
| 08-C14 | T11 |
| 08-C15 | T11 |
| 08-C16 | T11 |
| 08-C17 | T12 |
| 08-C18 | T13 |
| 08-C19 | T11 |
| 08-C20 | T09 |
| 08-C21 | T11 |
| 08-C22 | T02, T04 |
| 08-C23 | T14 |
| 08-C24 | T15, T16 (manuale) |
