# Verifica 04 – Upload degli allegati

Data: 2026-10-10
Commit verificato: `0c887d2` sul branch `m30_attachment_upload` (spec `ef82b8f`, piano `00c8812`,
task `cf0bc89`; T01–T14: `be13853` … `eaac41c`; T15 `5ef2d67`; T16 `00a6e0c`; T17 `0c887d2`)
Esito: **nessun problema**. Spec chiusa.

## Task

17 su 17 spuntati, compreso T15 (`manuale`) con l'esito compilato: eseguito da Claude su richiesta
del maintainer nella community di prova `126`. Upload, post con l'allegato, nuova versione con il
nome in `updateAttachments` (il server tiene l'id, porta la versione a 2 e applica il nome nuovo),
rimozione e cancellazione del post riuscite. La spec non ha avuto revisioni.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 04-C01 | `test_api_attachments.py::TestUpload::test_path_two_requests_in_order_no_authorization`; `test_api_attachments.py::TestUpload::test_string_path_is_accepted`; `test_api_attachments.py::TestUpload::test_empty_file_is_uploaded`; `test_api_attachments.py::TestUpload::test_library_closes_file_it_opened` (+2) | verde |
| 04-C02 | `test_api_attachments.py::TestUpload::test_bytes_with_name_octet_stream`; `test_api_attachments.py::TestUpload::test_fileobj_with_name_is_not_closed`; `test_api_attachments.py::TestUpload::test_mime_type_override`; `test_api_attachments.py::TestUpload::test_name_override_for_path` (+2) | verde |
| 04-C03 | `test_api_attachments.py::TestUpload::test_missing_path_raises_without_requests`; `test_api_attachments.py::TestUpload::test_directory_raises_without_requests`; `test_cli_attachments.py::TestAttachmentsUpload::test_missing_file_is_usage_error`; `test_cli_posts_write.py::TestPostsAttach::test_attach_missing_file_is_usage_error` | verde |
| 04-C04 | `test_api_attachments.py::TestUpload::test_storage_400_raises_upload_error_once`; `test_exceptions.py::test_upload_error_is_interacta_error_with_file_name`; `test_transport.py::TestPostMultipart::test_non_2xx_raises_upload_error_with_file_name` | verde |
| 04-C05 | `test_api_attachments.py::TestUpload::test_storage_timeout_raises_transport_error_once`; `test_transport.py::TestPostMultipart::test_timeout_maps_to_transport_error` | verde |
| 04-C06 | `test_api_attachments.py::TestRequestUploadUrl::test_returns_ticket`; `test_facade_attachments.py::TestUploadTicket::test_properties_from_fixture`; `test_facade_attachments.py::TestUploadTicket::test_form_params_is_a_copy`; `test_facade_attachments.py::TestUploadTicket::test_form_params_empty_without_params` (+1) | verde |
| 04-C07 | `test_api_posts_write.py::TestPostsUploadedAttachments::test_create_attachments`; `test_api_posts_write.py::TestPostsUploadedAttachments::test_add_comment_attachments`; `test_api_posts_write.py::TestPostsUploadedAttachments::test_edit_add_attachments`; `test_api_posts_write.py::TestPostsUploadedAttachments::test_copy_add_attachments` (+6) | verde |
| 04-C08 | `test_logging.py::TestSensitiveKeyCoverage::test_sensitive_keys_are_redacted`; `test_redaction.py::TestRedactString::test_url_query_without_sensitive_names_untouched`; `test_redaction.py::TestRedactString::test_signed_query_params_redacted`; `test_redaction.py::TestRedactString::test_sensitive_query_names_redacted` (+5) | verde |
| 04-C09 | `test_transport.py::TestPostMultipart::test_hooks_see_request_without_body_and_response_status`; `test_transport.py::TestPostMultipart::test_audit_events_carry_no_file_bytes_nor_form_fields` | verde |
| 04-C10 | `test_cli_attachments.py::TestAttachmentsUpload::test_table_output`; `test_cli_attachments.py::TestAttachmentsUpload::test_name_override_sent_as_filename`; `test_cli_attachments.py::TestAttachmentsUpload::test_json_output_full`; `test_cli_attachments.py::TestAttachmentsUpload::test_fields` (+1) | verde |
| 04-C11 | `test_cli_posts_write.py::TestPostsCreate::test_invalid_json_body_exits_2_without_requests`; `test_cli_posts_write.py::TestPostsAttach::test_create_two_attach_appended_after_json_items`; `test_cli_write.py::TestUploadAll::test_uploads_in_order`; `test_cli_write.py::TestUploadAll::test_none_gives_empty_list` (+3) | verde |
| 04-C12 | `test_cli_posts_write.py::TestPostsAttach::test_comment_attachments`; `test_cli_posts_write.py::TestPostsAttach::test_edit_add_attachments`; `test_cli_posts_write.py::TestPostsAttach::test_copy_add_attachments`; `test_cli_tasks.py::TestTasksAttach::test_create_attachments` (+1) | verde |
| 04-C13 | `test_cli_posts_write.py::TestPostsEditAttachments::test_add_update_remove_body_and_table`; `test_cli_posts_write.py::TestPostsEditAttachments::test_json_output_full`; `test_cli_posts_write.py::TestPostsEditAttachments::test_no_option_exits_2_without_requests`; `test_cli_posts_write.py::TestPostsEditAttachments::test_update_malformed_exits_2` (+4) | verde |
| 04-C14 | `test_cli_posts_write.py::TestPostsAttach::test_second_upload_fails_exits_11_without_write`; `test_cli_posts_write.py::TestPostsEditAttachments::test_failed_upload_exits_11_without_put`; `test_cli_write.py::TestUploadAll::test_first_error_propagates_and_stops` | verde |
| 04-C15 | `test_cli_attachments.py::TestAttachmentsUpload::test_storage_400_exits_11`; `test_cli_common.py::TestUploadErrorExit::test_upload_error_is_11`; `test_cli_common.py::TestUploadErrorExit::test_transport_error_is_7`; `test_cli_common.py::TestUploadErrorExit::test_handle_error_upload_prints_file_name_and_details` | verde |
| 04-C16 | `test_models.py::TestUploadNewAttachment::test_schema_superset`; `test_models.py::TestUploadNewAttachment::test_fixture_parses`; `test_models.py::TestUploadNewAttachment::test_facade_smoke` | verde |
| 04-C17 | `test_docs_snippets.py::test_attachments_pages_document_upload` | verde, più `mkdocs build --strict` |
| 04-C18 | `test_attachments_integration.py::TestAttachmentsUploadIntegration::test_full_cycle` | verde sul tenant (T15); saltato senza variabili |

Ogni test è stato visto rosso prima del codice (classe, metodo, comando od opzione inesistenti,
valore non redatto), tranne: i test di caratterizzazione di T02 (verdi per definizione); i test di
T08, verdi già dopo T06 perché fissano il contratto del protocollo `WriteInput`, come il task
prevedeva; `TestSensitiveKeyCoverage` con `signature`/`policy`, verde anche prima perché il suo
valore ha forma di JWT (la chiave è dimostrata da `test_signature_and_policy_keys_redacted`, rosso
prima di T03); i test d'uso con file mancante, che uscivano con `2` anche prima perché l'opzione
non esisteva. Nessun marker cita criteri inesistenti.

## Controlli automatici

| Controllo | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (116 file) |
| `uv run mypy src` | verde (56 file) |
| `uv run pytest -m "not integration and not contract"` | verde: 1090 test (+92), 77 snapshot (+2) |
| `uv run pytest -m contract` | verde: 161 test (+3) |
| `uv run mkdocs build --strict` (aggiuntivo) | verde |
| `uv run pre-commit run --all-files` (aggiuntivo) | verde |
| `uv run pytest -m integration tests/integration/test_attachments_integration.py` (T15, sul tenant) | `test_full_cycle` verde; `test_list_for_post` rosso anche su `main` (vedi "Problemi trovati") |

Controlli a cricchetto: nessuno configurato.

## Copertura

Comando: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`.

| Ambito | Copertura | Soglia | Esito |
|---|---|---|---|
| Totale | **94,51 %** (4994/5284 righe) | ≥ 85 % e ≥ 94,32 % (partenza) | ok |
| `exceptions.py` (toccato) | 100 % | ≥ 85 % | ok |
| `logging.py` (toccato) | 94,50 % | ≥ 85 % | ok |
| `transport.py` (toccato) | 98,73 % | ≥ 85 % | ok |
| `api/_utils.py` (toccato) | 98,36 % | ≥ 85 % | ok |
| `api/attachments.py` (toccato) | 100 % | ≥ 85 % | ok |
| `api/posts_write.py`, `api/tasks.py` (docstring) | 100 % | ≥ 85 % | ok |
| `models/facade/__init__.py` (toccato) | 100 % | ≥ 85 % | ok |
| `models/facade/attachments.py` (toccato) | 94,44 % | ≥ 85 % | ok |
| `cli/_common.py` (toccato) | 93,07 % | ≥ 85 % | ok |
| `cli/_write.py` (toccato) | 100 % | ≥ 85 % | ok |
| `cli/attachments.py` (toccato) | 96,05 % | ≥ 85 % | ok |
| `cli/posts_write.py` (toccato) | 96,26 % | ≥ 85 % | ok |
| `cli/tasks.py` (toccato) | 97,71 % | ≥ 85 % | ok |

Righe scoperte nel codice nuovo: nessuna in `api/attachments.py`, `cli/_write.py`, `exceptions.py`
e nelle façade nuove; in `cli/posts_write.py` il ramo `return {}` di `attachments_write_row` per un
oggetto che non è la façade attesa; le altre righe scoperte dei file toccati sono preesistenti
(`transport.py` 312–313 è il ramo di `_capture_response_body` per un corpo non JSON).

## Regole non negoziabili

| Regola | Controllo | Esito |
|---|---|---|
| Token e segreti mai nei log | La richiesta allo storage non porta `Authorization` (04-C01); `policy` e `signature` sono chiavi redatte e le query firmate (`Signature=`) perdono il valore in URL, body e messaggi (04-C08); l'unico log nuovo (`http.error` di `post_multipart`) porta stato e URL redatto. `attachments upload --full` stampa la policy firmata: è output scelto dall'operatore, previsto dalla spec e documentato in `docs/cli.md` come da tenere privato. | rispettata |
| Cache del token con permessi stretti | Codice non toccato. | n/a |
| Segreti fuori dal repository | Fixture con credenziali finte e riconoscibili (`fake@test.iam.gserviceaccount.com`, `FAKE-SIGNATURE`, `storage.example.com`); `.env.example` con soli nomi; nessun `.env`, `.secrets`, `audit.log` aggiunto. Le prove sul tenant hanno stampato solo host, chiavi e stati, mai firme o token. | rispettata |
| Soglie che non scendono | Controlli e regole di ruff/mypy invariati; copertura totale salita; ogni file toccato ≥ 85 %. | rispettata |
| Dati personali fuori dai log, con eccezione audit | Il contenuto dei file e i campi del form non entrano in log, audit né hook, neppure con `audit_log_bodies` (04-C09, RNF-011); il nome del file non è loggato, compare solo nel messaggio d'errore della CLI su stderr, per scelta della spec. | rispettata |
| Nessuna operazione ripetuta in automatico verso Interacta | Un solo `request` e un solo `post_multipart` per upload, senza `try/except` di ripetizione (04-C04, 04-C05); in CLI il primo upload fallito ferma il comando prima della scrittura (04-C14). | rispettata |

## Coerenza con spec, piano e PRD

- Il codice fa ciò che la spec descrive: upload in due passi con form multipart firmato,
  `UploadedAttachment` accettato dalle scritture di post e task, `UploadError` ed exit code `11`,
  redazione estesa, `--attach` sui sei comandi, `attachments upload`, `posts edit-attachments`.
- Scostamenti dal piano, dichiarati in `tasks.md`: in CLI il corpo si valida **anche prima** degli
  upload, così un `--json` non valido esce con `2` senza caricare file (il piano spostava la sola
  validazione dopo gli upload, e avrebbe caricato file prima di fallire); in `posts
  edit-attachments` i percorsi di `--update` si controllano prima di ogni richiesta, come `--add`;
  la caratterizzazione di `tasks create` riusa il test della spec 02; l'estensione ignota nei test
  è `.sconosciuto`. Precisazione non in contraddizione con la spec: con `name` esplicito su un
  percorso il MIME è dedotto dal nome dato (documentato).
- Requisiti nuovi entrati nel PRD (`0c887d2`): RF-024 precisato e confermato, RF-024a, RNF-001
  precisato, RNF-011, RF-021c aggiornato, voce "Dati scritti sul tenant" di §6 confermata. Nessun
  ADR necessario: l'upload era già deciso da ADR 0001, il meccanismo reale è registrato nella spec.
- Voci aggiuntive della checklist: swagger invariato, nessuna rigenerazione; comandi via
  `render_output` con snapshot; `docs/api/attachments.md`, `docs/api/posts.md`,
  `docs/api/tasks.md`, `docs/cli.md`, `docs/logging.md`, `docs/testing.md`, `docs/index.md` e
  `README.md` aggiornati senza numeri di versione; riga `0.12.0 ⏳` in `ROADMAP.md` dall'apertura
  (diventa ✅ alla release); sezione M30 in `PROGRESS.md` scritta con questa verifica.

## Linea di partenza

Aggiornata: copertura totale 94,32 % → 94,51 %, `api` 97,72 % → 97,83 %, `cli` 91,49 % → 91,75 %,
`models/facade` 95,66 % → 95,77 %, `logging.py` 94,39 % → 94,50 %, `transport.py` 97,84 % →
98,73 %. Nessuna violazione `P-<mm>` aperta; nessun controllo a cricchetto.

## Problemi trovati

Nessuno nella spec. Due osservazioni fuori ambito, emerse con T15, da seguire a parte:

- `tests/integration/test_attachments_integration.py::TestAttachmentsIntegration::test_list_for_post`
  (v0.3) fallisce anche su `main`: si aspetta `total_items_count`, che il server restituisce solo
  con `calculateTotalItemsCount`. Correzione proposta: un branch `bugfix_` che passi
  `calculate_total_items_count=True` nel test (o non lo pretenda).
- La riga `PYNTERACTA_TEST_WRITE_CUSTOM_DATA={"2003": [89]}` di `tests/integration/.env` non è
  leggibile né da `source` né da `uv run --env-file` (JSON non quotato): conviene quotarla con
  apici singoli e dirlo in `docs/testing.md` e in `.env.example`.
