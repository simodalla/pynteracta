# Verifica 03 – Scrittura dei post custom, commenti e workflow

Data: 2026-10-10
Commit verificato: `480115a` sul branch `m29_post_write` (spec `76fd132`, piano `2287d55`, task
`086a914`; revisioni `ca55ff3`, `cae452e`; T01–T15: `20cff1d` … `e2706e8`, più `a98cb0d`, `fa267ba`,
`ced2db6` sull'integration test; T18 `916a43f`; T16 `c943cc6`; T19 `65e8b8f`; T17 `480115a`)
Esito: **nessun problema**. Spec chiusa.

## Task

19 su 19 spuntati, compreso T16 (`manuale`) con l'esito compilato: `edit-post` e `copy-post` sono
sostituzioni; descrizione in testo semplice accettata in modifica; riferimenti a cataloghi e utenti
scritti come id; campi delta in testo semplice solo con `deltaAreaFormat: 2`; `mark-post-as-erasable`
risponde `postId: 0`; transizione senza screen accettata con corpo `{}`. Da T16 sono nate due
revisioni della spec (T18, T19).

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 03-C01 | `test_api_posts_write.py::TestPostsCreate::test_create_sends_only_given_fields_and_wraps_response`; `test_api_posts_write.py::TestPostsCreate::test_create_without_kwargs_sends_announcement_only` | verde |
| 03-C02 | `test_api_posts_write.py::TestPostsCreate::test_create_raw_equivalent`; `test_api_posts_write.py::TestPostsEdit::test_edit_raw_equivalent`; `test_api_posts_write.py::TestPostsCustomData::test_raw_equivalent`; `test_api_posts_write.py::TestPostsCopy::test_raw_equivalent` (+3) | verde |
| 03-C03 | `test_api_posts_write.py::TestPostsCreate::test_scheduled_publication_zoneinfo_in_body`; `test_api_posts_write.py::TestPostsCreate::test_naive_scheduled_publication_raises_before_request`; `test_api_posts_write.py::TestScheduledPublicationOnEditAndCopy` (edit e copy) | verde |
| 03-C04 | `test_api_posts_write.py::TestPostsEdit::test_edit_sends_only_given_fields`; `test_api_posts_write.py::TestPostsEdit::test_edit_without_fields_sends_empty_body` | verde |
| 03-C05 | `test_api_posts_write.py::TestPostsCustomData::test_edit_custom_data_body_and_result` | verde |
| 03-C06 | `test_api_posts_write.py::TestPostsCopy::test_copy_body_and_result` | verde |
| 03-C07 | `test_api_posts_write.py::TestPostsErrors::test_409_on_workflow_raises_concurrency_error_once` | verde |
| 03-C08 | `test_api_base.py::TestResourceClientEmptyBodies::test_put_without_body_returns_empty_dict`; `test_api_posts_write.py::TestPostsWatchersAttachments::test_edit_watchers_body_and_none`; `test_api_posts_write.py::TestPostsWatchersAttachments::test_edit_attachments_body_and_result` | verde |
| 03-C09 | `test_api_posts_write.py::TestPostsDelete::test_delete_returns_post_id`; `test_api_posts_write.py::TestPostsDelete::test_mark_as_erasable_puts_without_body_and_returns_post_id` | verde |
| 03-C10 | `test_api_posts_write.py::TestPostsComment::test_add_comment_body_and_facade` | verde |
| 03-C11 | `test_api_posts_write.py::TestPostsPrep::test_get_for_create`; `test_api_posts_write.py::TestPostsPrep::test_get_for_edit_no_query_and_occ_token`; `test_api_posts_write.py::TestPostsPrep::test_get_for_edit_load_attachments_false_in_query`; `test_api_posts_write.py::TestPostsPrep::test_get_for_copy` | verde |
| 03-C12 | `test_api_posts_write.py::TestPostsWorkflow::test_get_workflow_screen_without_operation`; `test_api_posts_write.py::TestPostsWorkflow::test_get_workflow_screen_with_operation_query` | verde |
| 03-C13 | `test_api_posts_write.py::TestPostsWorkflow::test_execute_operation_body_and_result`; `test_api_posts_write.py::TestPostsWorkflow::test_execute_operation_without_kwargs_sends_empty_body` | verde |
| 03-C14 | `test_api_posts_write.py::TestPostsWorkflow::test_edit_workflow_screen_body_and_result` | verde |
| 03-C15 | `test_cli_posts.py::TestPostsCapabilities::test_table_shows_write_flags_and_operations`; `test_facade_posts.py::TestPostCapabilities::test_capabilities_exposes_write_flags_and_operations` | verde |
| 03-C16 | `test_api_posts_write.py::TestPostsErrors::test_400_custom_field_validation_error_readable`; `test_cli_posts_write.py::TestPostsCreate::test_validation_error_exits_6_with_body` | verde |
| 03-C17 | `test_api_posts_write.py::TestPostsErrors::test_create_timeout_raises_transport_error_once`; `test_api_posts_write.py::TestPostsErrors::test_add_comment_timeout_raises_transport_error_once` | verde |
| 03-C18 | `test_cli_posts_write.py::TestPostsCreate::test_flags_and_json_merge_flags_win`; `test_cli_posts_write.py::TestPostsCreate::test_announcement_false_by_default`; `test_cli_posts_write.py::TestPostsCreate::test_json_custom_data_merged_with_flags`; `test_cli_posts_write.py::TestPostsCreate::test_scheduled_publication_default_timezone` (+6) | verde |
| 03-C19 | sostituito da 03-C32 il 2026-10-09: nessun marker, come atteso | — |
| 03-C20 | sostituito da 03-C33 il 2026-10-09: nessun marker, come atteso | — |
| 03-C21 | sostituito da 03-C34 il 2026-10-09: nessun marker, come atteso | — |
| 03-C22 | sostituito da 03-C35 il 2026-10-09: nessun marker, come atteso | — |
| 03-C23 | `test_cli_posts_write.py::TestPostsEditWatchers::test_add_and_remove_body_and_message`; `test_cli_posts_write.py::TestPostsEditWatchers::test_json_output`; `test_cli_posts_write.py::TestPostsEditWatchers::test_without_flags_exits_2` | verde |
| 03-C24 | `test_cli_posts_write.py::TestPostsDestructive` (5 casi × delete e mark-erasable) | verde |
| 03-C25 | `test_cli_posts_write.py::TestPostsComment::test_text_and_parent_body`; `test_cli_posts_write.py::TestPostsComment::test_json_body_with_client_uid`; `test_cli_posts_write.py::TestPostsComment::test_table_output`; `test_cli_posts_write.py::TestPostsComment::test_json_output` (+1) | verde |
| 03-C26 | `test_cli_posts_write.py::TestPostsPrep::test_get_for_edit_table_starts_with_occ_token`; `test_cli_posts_write.py::TestPostsPrep::test_get_for_copy_table`; `test_cli_posts_write.py::TestPostsPrep::test_get_for_create_table`; `test_cli_posts_write.py::TestPostsPrep::test_no_attachments_sends_query` (+1) | verde |
| 03-C27 | sostituito da 03-C36 il 2026-10-09: nessun marker, come atteso | — |
| 03-C28 | `test_cli_common.py::TestErrorExitCode::test_handle_error_concurrency_with_resource`; `test_cli_posts_write.py::TestPostsWorkflowConflicts::test_execute_conflict_exits_9_without_retry`; `test_cli_posts_write.py::TestPostsWorkflowConflicts::test_edit_screen_conflict_exits_9_without_retry` | verde |
| 03-C29 | `test_models.py::TestPostWriteDTOs::test_write_dto_superset`; `test_models.py::TestPostWriteDTOs::test_typed_stub_superset`; `test_models.py::TestPostWriteDTOs::test_response_fixtures_parse`; `test_models.py::TestPostWriteDTOs::test_response_fixtures_nested_typed` (+15) | verde |
| 03-C30 | `test_docs_snippets.py::test_posts_pages_document_write_commands` | verde; `mkdocs build --strict` verde |
| 03-C31 | `test_posts_integration.py::TestPostsWriteIntegration::test_full_cycle`; `test_posts_integration.py::TestPostsWriteIntegration::test_workflow_screen_read_only` | verde (eseguito sul tenant il 2026-10-09, T16); saltato senza le variabili |
| 03-C32 | `test_cli_posts_write.py::TestPostsEdit::test_edit_base_from_fixture`; `test_cli_posts_write.py::TestPostsEdit::test_edit_base_skips_missing_fields`; `test_cli_posts_write.py::TestPostsEdit::test_edit_reads_for_edit_then_puts_patched_body`; `test_cli_posts_write.py::TestPostsEdit::test_edit_with_occ_token_still_reads_base` (+4) | verde |
| 03-C33 | `test_cli_posts_write.py::TestPostsEdit::test_edit_description_flag_sets_plain_format`; `test_cli_posts_write.py::TestPostsEdit::test_edit_flags_win_over_json_over_read`; `test_cli_posts_write.py::TestPostsEdit::test_edit_json_description_keeps_read_format`; `test_cli_posts_write.py::TestPostsEdit::test_edit_watcher_flags_map_to_add_and_remove` (+1) | verde |
| 03-C34 | `test_cli_posts_write.py::TestPostsEditCustomData::test_reads_then_puts_merged_custom_data`; `test_cli_posts_write.py::TestPostsEditCustomData::test_json_and_occ_token`; `test_cli_posts_write.py::TestPostsEditCustomData::test_without_data_exits_2_without_requests` | verde |
| 03-C35 | `test_cli_posts_write.py::TestPostsCopy::test_copy_base_from_fixture`; `test_cli_posts_write.py::TestPostsCopy::test_copy_reads_for_copy_then_puts_base_with_title`; `test_cli_posts_write.py::TestPostsCopy::test_copy_table_shows_new_post` | verde |
| 03-C36 | `test_cli_posts_write.py::TestPostsWorkflow::test_screen_base`; `test_cli_posts_write.py::TestPostsWorkflow::test_workflow_screen_table`; `test_cli_posts_write.py::TestPostsWorkflow::test_workflow_screen_operation_query`; `test_cli_posts_write.py::TestPostsWorkflow::test_execute_with_screen_data_reads_screen_then_posts_merged` (+6) | verde |
| 03-C37 | `test_cli_posts_write.py::TestToWriteValue::test_to_write_values`; `test_docs_snippets.py::test_posts_pages_document_references_and_replacement` | verde; `mkdocs build --strict` verde |
| 03-C38 | `test_api_posts_write.py::TestPostsDelete::test_mark_as_erasable_returns_server_value_zero`; `test_cli_posts_write.py::TestPostsDestructive::test_server_post_id_zero_reports_requested_id` | verde |

Ogni test è stato visto rosso prima del codice (modulo, metodo o comando inesistente, corpo
diverso), tranne i test di caratterizzazione (helper di `cli/tasks.py` prima dello spostamento,
`mark_as_erasable` che restituisce il valore del server) e i contract test sui modelli generati,
verdi subito per definizione. Nessun marker cita criteri inesistenti; i cinque criteri sostituiti
non hanno marker, come atteso.

## Controlli automatici

| Controllo | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (116 file) |
| `uv run mypy src` | verde (56 file) |
| `uv run pytest -m "not integration and not contract"` | verde: 998 test (+172), 75 snapshot |
| `uv run pytest -m contract` | verde: 158 test (+61) |
| `uv run mkdocs build --strict` (aggiuntivo) | verde |
| `uv run pre-commit run --all-files` (aggiuntivo) | verde: tutti e 7 gli hook passano |

Controlli a cricchetto: nessuno configurato.

## Copertura

Comando: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`.

| Ambito | Copertura | Soglia | Esito |
|---|---|---|---|
| Totale | **94,32 %** (4817/5107 righe) | ≥ 85 % e ≥ 93,66 % (partenza) | ok |
| `api/_base.py` (toccato) | 100 % | ≥ 85 % | ok |
| `api/posts.py` (toccato) | 96,67 % | ≥ 85 % | ok |
| `api/posts_write.py` (nuovo) | 100 % | ≥ 85 % | ok |
| `cli/__init__.py` (toccato) | 89,09 % | ≥ 85 % | ok |
| `cli/_common.py` (toccato) | 93,01 % | ≥ 85 % | ok |
| `cli/_write.py` (nuovo) | 100 % | ≥ 85 % | ok |
| `cli/posts.py` (toccato) | 93,89 % | ≥ 85 % | ok |
| `cli/posts_write.py` (nuovo) | 96,14 % | ≥ 85 % | ok |
| `cli/tasks.py` (toccato) | 97,62 % | ≥ 85 % | ok |
| `models/facade/posts.py` (toccato) | 98,44 % | ≥ 85 % | ok |
| `models/facade/posts_write.py` (nuovo) | 99,47 % | ≥ 85 % | ok |

`models/generated/external_v2.py` è rigenerato ed escluso dalla misura. Righe scoperte nei file
nuovi (non bloccanti): `cli/posts_write.py` i rami `return {}` delle righe curate quando l'oggetto
non è della façade attesa e alcuni rami d'errore di validazione del corpo dopo la lettura;
`facade/posts_write.py` 202 (commento senza dati del padre); le righe scoperte di `cli/__init__.py`
e `cli/_common.py` sono preesistenti.

## Regole non negoziabili

| Regola | Controllo | Esito |
|---|---|---|
| Token e segreti mai nei log | Il diff di `src/` non aggiunge chiamate ai logger; le stampe nuove sono messaggi per l'operatore con soli id e il dettaglio di un errore di validazione su stderr. I corpi delle scritture passano dal transport, che li redige prima di log, audit e hook (non modificato). | rispettata |
| Cache del token con permessi stretti | Codice non toccato. | n/a |
| Segreti fuori dal repository | Fixture con dati finti (Maria Rossi, Alice Rossi, id piccoli); `.env.example` con soli nomi di variabili; nessun `.env`, `.secrets`, `audit.log` aggiunto. Le prove sul tenant sono state eseguite con le variabili caricate senza leggerle. | rispettata |
| Soglie che non scendono | Controlli e regole di ruff/mypy invariati; copertura totale salita; ogni file toccato ≥ 85 %. | rispettata |
| Dati personali fuori dai log, con eccezione audit | Titoli, descrizioni, campi custom e commenti viaggiano nei corpi e non vengono loggati; l'output dei comandi mostra nomi di autori e riferimenti come già `posts get`: è output per l'operatore, non log. Gli integration test scrivono solo nella community di prova e cancellano ciò che creano. | rispettata |
| Nessuna operazione ripetuta in automatico verso Interacta | Ogni metodo di scrittura fa una richiesta, senza `try/except`; `409` → `ConcurrencyError` senza rilettura (03-C07, 03-C28); timeout → `TransportError` con una sola richiesta (03-C17). Le patch della CLI fanno una lettura più una scrittura: la lettura non è una ripetizione. Nelle prove di T16 nessuna scrittura fallita è stata ripetuta con lo stesso corpo. | rispettata |

## Coerenza con spec, piano e PRD

- Il codice fa ciò che la spec rivista descrive: libreria con i soli campi passati e i token
  espliciti; CLI con patch che rileggono e rimandano i campi letti, riferimenti tradotti in id;
  conferma dei comandi distruttivi; exit code 9; id del post richiesto nell'output di `delete` e
  `mark-erasable`.
- Revisioni della spec, tutte approvate dal maintainer: rigenerazione dei dati di screen
  (`ca55ff3`, durante T02); riferimenti letti scritti come id (`cae452e`, durante T16: 03-C19…C22,
  C27 → 03-C32…C36, nuovo 03-C37, task T18); 03-C38 e task T19 (con T17).
- Scostamenti dal piano, dichiarati: `--json` e `--timezone` restano per modulo (si condividono le
  funzioni di `cli/_write.py`); `handle_error` mostra il dettaglio del server per ogni
  `ValidationError` della CLI, non solo per i post (necessario a 03-C16); nelle tabelle nuove i
  campi custom e di screen sono una riga per campo; l'integration test ha la variabile
  `PYNTERACTA_TEST_WRITE_CUSTOM_DATA` per i campi obbligatori della community di prova.
- Requisiti nuovi entrati nel PRD (`480115a`): RF-006a, RF-021a, RF-021b, RF-021c, RF-021d; RF-021,
  RF-006, §5 ("letture e scritture") e §7 confermati dal maintainer. Nessun ADR necessario: le
  scritture dei post erano già decise da ADR 0001.
- Voci aggiuntive della checklist: modelli rigenerati con lo script (swagger invariato, `screenData`
  e `newScreenData`); comandi via `render_output` con snapshot; `docs/api/posts.md`, `docs/cli.md`,
  `docs/testing.md`, `docs/index.md` e `README.md` aggiornati senza numeri di versione; riga
  `0.11.0 ⏳` in `ROADMAP.md` dall'apertura (diventa ✅ alla release); sezione M29 in `PROGRESS.md`
  scritta con questa verifica.

## Linea di partenza

Aggiornata (`specs/00-partenza/partenza.md`): copertura totale 93,66 % → 94,32 %, `api` 97,22 % →
97,72 %, `cli` 90,11 % → 91,49 %, `models/facade` 95,09 % → 95,66 %; unit test 826 → 998, contract
97 → 158. Nessuna violazione `P-<mm>` toccata.

## Debiti aperti

- Nessuna violazione `P-<mm>` aperta nella linea di partenza.
- Non bloccante, registrato in `PROGRESS.md`: i valori annidati (riferimenti) compaiono nella forma
  Python nelle tabelle della CLI.
