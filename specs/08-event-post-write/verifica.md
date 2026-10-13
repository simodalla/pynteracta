# Verifica 08 – Scrittura dei post evento

Data: 2026-10-13
Commit verificato: `a608881` sul branch `m34_event_post_write` (spec `85d70ea`, piano `43864e4`,
task `c7e1bdd`; T01–T15: `05a9ef5` … `5c8c70e`; T16 `f3fa37d`; revisione della spec dopo la
prova sul tenant `95e8828`; T18 `8a3278e`; T19 `ba55d41`, `a608881`; T17 `03a25e4`)
Esito: **nessun problema**. Spec chiusa.

## Task

19 su 19 spuntati, compreso T16 (`manuale`) con l'esito compilato: eseguito da Claude su
richiesta del maintainer sulla community di prova 126. Le prove hanno mostrato quattro
divergenze dalla spec, corrette con una revisione approvata dal maintainer (`95e8828`, task T18
e T19):

- gli eventi `allDay` vogliono date senza ora e nessun `timezone`: `--all-day` falliva con `400`
  (08-C13 sostituito da 08-C25; nuovi 08-C26, 08-C27);
- `EventData.start_at` leggeva `zonedDatetime` a offset fisso: rimandata a `edit_event`, la data
  spostava l'evento in `UTC` (nuovo 08-C28);
- le note di partecipazione in testo semplice sono rifiutate, il server vuole un delta (08-C07,
  08-C17 sostituiti da 08-C29, 08-C30);
- le risposte di scrittura non hanno `event` in `postData` (08-C12 sostituito da 08-C31).

Altre scoperte, documentate e lasciate al server: invitati obbligatori con almeno un ospite,
invitati non restituiti dalla lettura propedeutica, modifica e copia come sostituzione con
`title`, `visibility`, `endAt`, `location` obbligatori. Dopo le correzioni l'integration test è
verde e una prova della CLI sul tenant (`create-event --all-day`, `edit-event --start` sull'evento
tutto il giorno, `participate maybe --notes`) ha dato date `2026-10-14` → `2026-10-15` senza fuso
e `participateTypeId: 2`. Tutti i post di prova sono stati eliminati.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 08-C01 | `test_api_posts_event.py::TestBuildEventBlock::test_full_block`; `test_api_posts_event.py::TestEventCreate::test_create_event_sends_only_given_fields_and_wraps_response` | verde |
| 08-C02 | `test_api_posts_event.py::TestBuildEventBlock::test_invitations_without_type`; `test_api_posts_event.py::TestEventCreate::test_create_event_start_only_sends_event_block_without_announcement`; `test_api_posts_event.py::TestEventCreate::test_invited_user_without_type_sends_id_only`; `test_api_posts_event.py::TestEventCreate::test_end_at_converted_into_start_zone` (+7) | verde |
| 08-C03 | `test_api_posts_event.py::TestEventErrors::test_naive_datetime_raises_before_request_on_create`; `test_api_posts_event.py::TestEventErrors::test_naive_datetime_raises_before_request_on_edit_and_copy`; `test_api_utils.py::TestEventDatetimeBlock::test_naive_datetime_raises` | verde |
| 08-C04 | `test_api_posts_event.py::TestEventCreate::test_create_event_raw_equivalent`; `test_api_posts_event.py::TestEventEdit::test_raw_equivalent`; `test_api_posts_event.py::TestEventCopy::test_raw_equivalent`; `test_api_posts_event.py::TestParticipate::test_raw_equivalent` | verde |
| 08-C05 | `test_api_posts_event.py::TestBuildEventBlock::test_nothing_gives_empty_dict`; `test_api_posts_event.py::TestEventEdit::test_edit_event_sends_only_given_fields`; `test_api_posts_event.py::TestEventEdit::test_edit_event_end_only_sends_end_and_timezone`; `test_api_posts_event.py::TestEventEdit::test_edit_event_without_fields_sends_empty_body` | verde |
| 08-C06 | `test_api_posts_event.py::TestEventCopy::test_copy_event_body_and_result` | verde |
| 08-C07 | sostituito da 08-C29 il 2026-10-13: nessun marker, come atteso | — |
| 08-C08 | `test_api_posts_event.py::TestEventErrors::test_409_raises_concurrency_error_once` | verde |
| 08-C09 | `test_api_posts_event.py::TestEventErrors::test_create_400_custom_field_validation_readable`; `test_api_posts_event.py::TestEventErrors::test_participate_404_not_found_once`; `test_api_posts_event.py::TestEventErrors::test_participate_403_permission_once`; `test_cli_posts_event.py::TestExitCodes::test_create_validation_error_exits_6` (+2) | verde |
| 08-C10 | `test_api_posts_event.py::TestEventErrors::test_create_timeout_raises_transport_error_once`; `test_api_posts_event.py::TestEventErrors::test_participate_timeout_raises_transport_error_once` | verde |
| 08-C11 | `test_api_posts_event.py::TestEventPrep::test_get_event_for_create`; `test_api_posts_event.py::TestEventPrep::test_get_event_for_edit_no_query_occ_token_and_event`; `test_api_posts_event.py::TestEventPrep::test_get_event_for_edit_load_attachments_false_in_query`; `test_api_posts_event.py::TestEventPrep::test_get_event_for_copy` (+12) | verde |
| 08-C12 | sostituito da 08-C31 il 2026-10-13: nessun marker, come atteso | — |
| 08-C13 | sostituito da 08-C25 il 2026-10-13: nessun marker, come atteso | — |
| 08-C14 | `test_cli_posts_event.py::TestEventBases::test_edit_base`; `test_cli_posts_event.py::TestEventBases::test_bases_without_content`; `test_cli_posts_event.py::TestEditEvent::test_edit_reads_form_then_puts_patched_body`; `test_cli_posts_event.py::TestEditEvent::test_edit_with_occ_token_still_reads_base` (+3) | verde |
| 08-C15 | `test_cli_posts_event.py::TestMergeEvent::test_json_replaces_read_invitations_and_flag_replaces_users_only`; `test_cli_posts_event.py::TestEditEvent::test_start_without_timezone_uses_read_zone`; `test_cli_posts_event.py::TestEditEvent::test_read_zone_used_when_not_default`; `test_cli_posts_event.py::TestEditEvent::test_timezone_flag_changes_event_zone` (+2) | verde |
| 08-C16 | `test_cli_posts_event.py::TestEventBases::test_copy_base`; `test_cli_posts_event.py::TestCopyEvent::test_copy_reads_form_then_puts_base_with_title`; `test_cli_posts_event.py::TestCopyEvent::test_copy_table_shows_new_post` | verde |
| 08-C17 | sostituito da 08-C30 il 2026-10-13: nessun marker, come atteso | — |
| 08-C18 | `test_cli_posts_event.py::TestCoverAndAttach::test_cover_then_attach_uploaded_in_order`; `test_cli_posts_event.py::TestCoverAndAttach::test_cover_upload_failure_exits_11_without_write`; `test_cli_posts_event.py::TestCoverAndAttach::test_edit_event_cover_wins_over_read`; `test_cli_posts_event.py::TestCoverAndAttach::test_copy_event_cover` (+1) | verde |
| 08-C19 | `test_cli_posts_event.py::TestConflicts::test_conflict_exits_9_without_retry` | verde |
| 08-C20 | `test_cli_posts_event.py::test_posts_help_lists_event_commands`; `test_cli_posts_event.py::TestPrepCommands::test_get_event_for_edit_table_starts_with_occ_token`; `test_cli_posts_event.py::TestPrepCommands::test_get_event_for_copy_table`; `test_cli_posts_event.py::TestPrepCommands::test_get_event_for_create_table` (+2) | verde |
| 08-C21 | `test_cli_posts_event.py::TestEventWriteBlock::test_event_write_block`; `test_cli_posts_event.py::TestEventWriteBlock::test_null_keys_and_empty_dates_dropped` | verde |
| 08-C22 | `test_models.py::TestEventPostDTOs::test_request_dto_superset`; `test_models.py::TestEventPostDTOs::test_response_dto_superset`; `test_models.py::TestEventPostDTOs::test_typed_stub_superset`; `test_models.py::TestEventPostDTOs::test_response_fixtures_parse` (+3) | verde |
| 08-C23 | `test_docs_snippets.py::test_event_posts_pages_document_write_commands`; `uv run mkdocs build --strict` | verde |
| 08-C24 | `test_posts_integration.py::TestEventPostsWriteIntegration::test_full_cycle` (eseguito sul tenant in T16: verde) | verde |
| 08-C25 | `test_cli_posts_event.py::TestCreateEvent::test_date_only_all_day_sends_date_without_timezone`; `test_cli_posts_event.py::TestCreateEvent::test_datetimes_all_day_send_dates`; `test_cli_posts_event.py::TestCreateEvent::test_date_only_without_all_day_is_local_midnight`; `test_cli_posts_event.py::TestCreateEvent::test_explicit_offset_sends_utc` (+11) | verde |
| 08-C26 | `test_api_posts_event.py::TestAllDay::test_create_all_day_dates`; `test_api_posts_event.py::TestAllDay::test_aware_datetime_all_day_uses_local_date`; `test_api_posts_event.py::TestAllDay::test_naive_datetime_all_day_accepted`; `test_api_posts_event.py::TestAllDay::test_date_without_all_day_raises` (+1) | verde |
| 08-C27 | `test_cli_posts_event.py::TestAllDayBlock::test_all_day_drops_time_and_timezone`; `test_cli_posts_event.py::TestAllDayBlock::test_not_all_day_unchanged`; `test_cli_posts_event.py::TestAllDayMerge::test_edit_all_day_read_event_start_flag`; `test_cli_posts_event.py::TestAllDayMerge::test_copy_all_day` (+1) | verde |
| 08-C28 | `test_api_posts_event.py::TestAllDay::test_edit_with_read_start_keeps_zone`; `test_cli_posts_event.py::TestAllDayMerge::test_get_event_for_edit_all_day_shows_date`; `test_facade_posts_event.py::TestEventDates::test_iana_zone_from_local_and_timezone`; `test_facade_posts_event.py::TestEventDates::test_all_day_is_date` (+2) | verde |
| 08-C29 | `test_api_posts_event.py::TestParticipate::test_participate_body_and_none`; `test_api_posts_event.py::TestParticipate::test_participate_int_answer`; `test_api_posts_event.py::TestParticipate::test_participate_invalid_answer_raises_before_request`; `test_api_posts_event.py::TestParticipate::test_raw_equivalent` (+1) | verde |
| 08-C30 | `test_cli_posts_event.py::TestParticipate::test_yes_with_notes_body_and_message`; `test_cli_posts_event.py::TestParticipate::test_maybe_and_no_type_ids`; `test_cli_posts_event.py::TestParticipate::test_json_output`; `test_cli_posts_event.py::TestParticipate::test_invalid_choice_exits_2_without_requests` | verde |
| 08-C31 | `test_cli_posts_event.py::TestMergeEvent::test_flags_win_and_invitations_merge_by_key`; `test_cli_posts_event.py::TestCreateEvent::test_flags_and_json_merge_flags_win`; `test_cli_posts_event.py::TestCreateEvent::test_without_announcement_and_pinned_keys_missing`; `test_cli_posts_event.py::TestCreateEvent::test_table_output` (+2) | verde |

27 criteri attivi su 27 con almeno un test; i 4 sostituiti non hanno marker; nessun marker cita
un criterio inesistente. Durante la verifica sei test di `parse_event_datetime` avevano ancora il
marker del sostituito 08-C13: corretti in 08-C25 con `a608881` (il loro comportamento è ripreso
uguale da 08-C25).

## Controlli automatici

| Comando | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde |
| `uv run mypy src` | verde (64 file) |
| `uv run pytest -m "not integration and not contract"` | verde (1549 test, 94 snapshot) |
| `uv run pytest -m contract` | verde (229 test) |
| `uv run mkdocs build --strict` | verde, nessun warning |
| `uv run pre-commit run --all-files` | verde |
| `uv run pytest -m integration -k EventPosts` (T16, sul tenant) | verde |

Nessun controllo a cricchetto configurato.

## Copertura

| Ambito | Linea di partenza | Ora |
|---|---|---|
| Totale | 95,18 % | **95,40 %** (6578/6895 righe) |
| `api` | 98,19 % | 98,44 % |
| `cli` | 93,11 % | 93,53 % |
| `models/facade` | 96,33 % | 96,35 % |

File toccati dalla spec, soglia 85 %:

| File | Copertura | Righe scoperte |
|---|---|---|
| `api/posts_event.py` | 100 % | – |
| `api/_utils.py` | 99 % | 58 (preesistente, `zoned_datetime_input`) |
| `api/posts.py` | 97 % | 283, 285, 291, 303, 333-334 (preesistenti, solo l'ereditarietà toccata) |
| `cli/_write.py` | 100 % | – |
| `cli/posts_event.py` | 97 % | 332 (righe curate senza evento), 359, 374, 392, 408 (guardie su oggetti di tipo inatteso), 416, 493, 531 (`handle_error` delle letture propedeutiche) |
| `cli/__init__.py` | 90 % | 168-174, 186-190 (preesistenti) |
| `models/facade/posts_event.py` | 97 % | 66-67, 76-77 (date illeggibili), 160 |
| `models/facade/posts_write.py` | 99 % | 187 (preesistente) |
| `models/facade/_stubs.py`, `models/facade/__init__.py` | 100 % | – |

Unit test 1383 → 1549, contract test 201 → 229. La linea di partenza è aggiornata.

## Regole non negoziabili

| Regola | Verifica | Esito |
|---|---|---|
| Token e segreti mai nei log | Nessun log nuovo nel codice della spec; l'`occToken` sta nel path ed è un contatore di versione, non un segreto. | rispettata |
| Cache del token con permessi stretti | Non toccata. | rispettata |
| Segreti fuori dal repository | Fixture con valori finti; `.env.example` con soli nomi; nessun `.env`, `.secrets` o `audit.log` versionato. Le sonde sul tenant (in scratchpad, fuori dal repo) hanno stampato id, date, stati e codici di errore. | rispettata |
| Soglie che non scendono | Copertura totale e per area in salita; regole di ruff e mypy invariate. | rispettata |
| Dati personali fuori dai log | Titoli, luoghi, note e id degli invitati vanno solo nel corpo delle richieste; nessun log nuovo. L'output della CLI (`console.print`) stampa id e risposta, non dati personali. | rispettata |
| Nessuna operazione ripetuta in automatico | Ogni metodo fa una richiesta e lascia salire le eccezioni; la CLI non riprova sul `409` (08-C08, 08-C19) né dopo un timeout (08-C10). La lettura propedeutica di `edit-event`/`copy-event` precede la scrittura e non la ripete. | rispettata |

## Coerenza

- Il codice fa ciò che dicono spec e piano, nella versione rivista dopo T16: quattro scritture e
  tre letture propedeutiche su `client.posts`, sette comandi CLI con patch sul form, `--cover`,
  date con fuso e date tutto il giorno, note in delta.
- Oltre il piano, solo nei test: l'integration test invita l'utente di prova come ospite, ripassa
  gli invitati in modifica e copia e controlla che il fuso resti `Europe/Rome` dopo la modifica.
- Nessun ADR nuovo: la spec resta dentro ADR 0001. I "Requisiti nuovi" sono nel PRD (`03a25e4`):
  RF-021e e RF-021f con la semantica verificata sul tenant, RF-021 aggiornato, §1 con la
  superficie di scrittura dell'ADR completa, RNF-010 esteso alle date degli eventi; RF-021,
  RNF-010 e la voce "Dati scritti sul tenant" di §6 confermati per la parte degli eventi.

## Debiti aperti della linea di partenza

Nessuna violazione `P-<mm>` aperta; nessun controllo a cricchetto. Copertura misurata.

## Problemi trovati

Nessuno nella spec. Osservazioni fuori ambito, da seguire a parte:

- La lettura propedeutica non restituisce gli invitati: se un tenant li restituisse, la patch
  della CLI li rimanderebbe già; altrimenti vanno ripassati a mano. Un endpoint per leggerli non
  c'è nel swagger.
- Il server mette `Europe/Paris` quando il fuso manca: la libreria lo manda sempre, tranne per
  gli eventi tutto il giorno.
- Il delta rimandato in modifica aggiunge al testo semplice un `​\n` finale (artefatto del
  server, innocuo).
