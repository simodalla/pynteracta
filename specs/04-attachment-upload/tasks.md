# Task 04 – Upload degli allegati

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (classe, metodo o comando inesistente, valore non redatto); poi il
codice; il commit arriva con i cinque controlli bloccanti verdi. Ogni test porta
`# criterio: 04-Cmm` sulla riga sopra. Messaggi di commit in Conventional Commits con descrizione
in italiano: `feat(api)`, `feat(transport)`, `feat(cli)`, `fix(logging)`, `refactor(transport)`,
`test`, `docs`. Gli snapshot syrupy nuovi si generano con `--snapshot-update` e si leggono prima
del commit. Costanti dei test: community `79`, post `21269`, task `9001`, allegato esistente `5`
(versione) e `9` (rimozione), `attachmentId: 3` nel `--json`; host dello storage
`https://storage.example.com`, bucket `bucket-test`; file creati in `tmp_path` (`nota.txt`,
`a.txt`, `b.pdf`, `vuoto.txt`, `dati.xyz`).

## Elenco

### [ ] T01 – Riga di ROADMAP, fixture della risposta e contract test

- Criteri: 04-C16 (DTO)
- Dipende da: nessuno
- Test: `tests/contract/test_models.py::TestUploadNewAttachment::test_schema_superset`
  (`assert_superset(GetTemporaryImageUploadUrlBaseResponseDTO, …)`, verde subito: caratterizza il
  modello generato) e `::test_fixture_parses` (la fixture si valida nel DTO generato; rosso finché
  la fixture manca).
- Passi:
  1. `ROADMAP.md`: riga `0.12.0 | Attachment upload (third write group, ADR 0001) | M30 | ⏳ In
     progress | specs/04-attachment-upload/spec.md`; nota "last used: M30".
  2. `tests/fixtures/payloads/upload_new_attachment_response.json` con i valori finti del piano
     (`contentRef` di 64 esadecimali, `uploadUrl` senza query, i quattro campi della policy con
     `fake@test.iam.gserviceaccount.com` e `FAKE-SIGNATURE`, `temporaryDownloadUrl` con
     `GoogleAccessId`, `Expires`, `Signature` in query).
  3. Scrivere i test; eseguire; `uv run pytest -m contract` e controlli bloccanti; commit
     `test: fixture e contract test della risposta di upload-new-attachment; riga 0.12.0 in
     ROADMAP (04-T01)`.

### [ ] T02 – Test di caratterizzazione

- Criteri: nessuno nuovo (protegge 04-C08, 04-C11, 04-C12)
- Dipende da: nessuno
- Test, verdi subito sul codice di oggi:
  - `tests/unit/test_redaction.py::TestRedactString::test_url_query_without_sensitive_names_untouched`
    (`https://x.example.com/p?loadViewLink=true&pageSize=10` resta identico);
  - `tests/unit/test_cli_posts_write.py::TestPostsCreate::test_invalid_json_body_exits_2_without_requests`
    e `tests/unit/test_cli_tasks.py::TestTasksCreate::test_invalid_json_body_exits_2_without_requests`
    (corpo `--json` con una chiave sconosciuta → exit `2`, la route di scrittura e quella del token
    non sono chiamate).
- Passi:
  1. Scrivere i tre test; eseguirli: verdi. Se uno è rosso, si ferma e si segnala: fissa un
     comportamento diverso da quello che il piano assume.
  2. Controlli bloccanti; commit `test: caratterizzazione della redazione delle query e dei corpi
     non validi di posts create e tasks create (04-T02)`.

### [ ] T03 – Redazione delle query firmate e delle chiavi `signature`/`policy`

- Criteri: 04-C08 (redazione)
- Dipende da: T02
- Test: `test_redaction.py::TestRedactString::test_signed_query_params_redacted` (solo il valore
  di `Signature` sparisce, `GoogleAccessId` ed `Expires` restano),
  `::test_sensitive_query_inside_text` (URL dentro una frase), `TestRedactBody::test_signature_and_policy_keys_redacted`
  (anche annidate), `::test_download_url_leaf_string_redacted`;
  `test_logging.py::TestSensitiveKeyCoverage` esteso con `signature` e `policy`. Rossi: valori in
  chiaro.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `logging.py`: `signature|policy` in `_SENSITIVE_KEY_RE`; `_SENSITIVE_QUERY_RE` del piano;
     `redact_string` applica la query poi i JWT; docstring in italiano.
  3. Il test di caratterizzazione di T02 resta verde.
  4. Controlli bloccanti; commit `fix(logging): redazione delle firme negli URL e delle chiavi
     signature e policy (04-T03)`.

### [ ] T04 – Scomposizione di `HttpTransport.request()`

- Criteri: nessuno (preparazione di 04-C01, C04, C05, C09)
- Dipende da: nessuno
- Test: nessun test nuovo; l'intero `tests/unit/test_transport.py`, `test_hooks.py` e
  `test_logging.py` restano verdi prima e dopo (caratterizzazione esistente indicata dal piano).
- Passi:
  1. Eseguire `uv run pytest tests/unit/test_transport.py tests/unit/test_hooks.py
     tests/unit/test_logging.py`: verdi; annotare il numero di test.
  2. Estrarre `_emit_request`, `_send`, `_emit_response` come nel piano; `request()` le compone
     senza cambiare ordine di hook, log ed eventi di audit.
  3. Gli stessi test, stesso numero, verdi; controlli bloccanti; commit `refactor(transport):
     request scomposta in helper condivisi (04-T04)`.

### [ ] T05 – `UploadError` e `HttpTransport.post_multipart`

- Criteri: 04-C04, 04-C05, 04-C09, 04-C08 (transport)
- Dipende da: T03, T04
- Test: `tests/unit/test_transport.py::TestPostMultipart` (`respx` sull'host dello storage):
  `test_no_authorization_and_user_agent_present`, `test_multipart_fields_then_file_in_order`
  (i quattro campi prima di `name="file"; filename="nota.txt"` e `Content-Type: text/plain`),
  `test_hooks_see_request_without_body_and_response_status` (`audit_bodies=True`, `body is None`,
  `status_code == 204`), `test_audit_events_carry_no_file_bytes_nor_form_fields`,
  `test_non_2xx_raises_upload_error_with_file_name` (attributi, `on_error` una volta),
  `test_timeout_maps_to_transport_error`, `test_upload_error_url_query_is_redacted`,
  `test_signed_url_redacted_in_hooks_and_audit`; `tests/unit/test_exceptions.py::test_upload_error_is_interacta_error_with_file_name`.
  Rossi: classe e metodo inesistenti.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `exceptions.py`: `UploadError(InteractaError)` con `file_name`.
  3. `transport.py`: `post_multipart` come nel piano, sugli helper di T04; `body=None` fisso; non
     2xx → `UploadError`; timeout e rete → `TransportError` tramite `_send`.
  4. Controlli bloccanti; commit `feat(transport): POST multipart verso lo storage senza token
     né corpo nei log, UploadError (04-T05)`.

### [ ] T06 – Façade dell'upload e protocollo `WriteInput`

- Criteri: 04-C06 (façade), 04-C07 (conversione), 04-C16 (smoke)
- Dipende da: T01
- Test: `tests/unit/test_facade_attachments.py::TestUploadTicket` (proprietà, `form_params`
  copia del dict, `{}` senza parametri, `.raw`) e `::TestUploadedAttachment::test_as_write_input_and_as_version_of`;
  `tests/unit/test_api_utils.py::TestBuildWriteBody::test_write_input_objects_are_converted`
  (lista con un `WriteInput`, un dict e un `BaseModel`); `tests/contract/test_models.py::TestUploadNewAttachment::test_facade_smoke`.
  Rossi: classi e protocollo inesistenti.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `models/facade/attachments.py`: `UploadTicket`, `UploadedAttachment`; esportarle da
     `models/facade/__init__.py`.
  3. `api/_utils.py`: `WriteInput` (`Protocol`, `runtime_checkable`) e il ramo in `_dump_value`.
  4. Controlli bloccanti; commit `feat(api): façade UploadTicket e UploadedAttachment, protocollo
     WriteInput nei corpi di scrittura (04-T06)`.

### [ ] T07 – `AttachmentsAPI.upload` e `request_upload_url`

- Criteri: 04-C01, 04-C02, 04-C03, 04-C04, 04-C05, 04-C06
- Dipende da: T05, T06
- Test: `tests/unit/test_api_attachments.py::TestRequestUploadUrl::test_returns_ticket` (una
  `POST` senza corpo); `::TestUpload` con route su `BASE_URL` e sullo storage:
  `test_path_two_requests_in_order_no_authorization`, `test_empty_file_is_uploaded`,
  `test_bytes_with_name_octet_stream`, `test_fileobj_with_name`, `test_mime_type_override`,
  `test_unknown_extension_octet_stream`, `test_bytes_without_name_raises_before_requests`,
  `test_missing_path_raises_without_requests`, `test_directory_raises_without_requests`,
  `test_storage_400_raises_upload_error_once` (una chiamata per host),
  `test_storage_timeout_raises_transport_error_once`, `test_library_closes_file_it_opened`.
  Rossi: metodi inesistenti.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `api/attachments.py`: `_UPLOAD_PATH`, `_open_source`, `request_upload_url`, `upload` come
     nel piano; docstring della classe.
  3. Controlli bloccanti; commit `feat(api): upload degli allegati in due passi su
     client.attachments (04-T07)`.

### [ ] T08 – `UploadedAttachment` nei metodi di scrittura di post e task

- Criteri: 04-C07
- Dipende da: T06
- Test: `tests/unit/test_api_posts_write.py::TestPostsUploadedAttachments` (`create` e
  `add_comment` in `attachments`, `edit` e `copy` in `addAttachments`, `edit_attachments` in
  `addAttachments` e `as_version_of(7)` in `updateAttachments`, accanto a un dict
  `{"attachmentId": 3}`); `tests/unit/test_api_tasks.py::TestTasksUploadedAttachments` (`create`,
  `edit`). Verdi già dopo T06 se il protocollo funziona: si eseguono prima di toccare le
  docstring e si annota l'esito; il task fissa il contratto pubblico.
- Passi:
  1. Scrivere i test; eseguirli.
  2. Docstring di `posts_write.py` e `tasks.py`: i parametri degli allegati citano
     `UploadedAttachment` e `as_version_of`; via la nota "l'upload non fa parte di questa
     libreria".
  3. Controlli bloccanti; commit `feat(api): UploadedAttachment accettato dalle scritture di post
     e task (04-T08)`.

### [ ] T09 – Exit code `11` e helper della CLI per gli allegati

- Criteri: 04-C15; base per 04-C10…C14
- Dipende da: T05, T07
- Test: `tests/unit/test_cli_common.py::TestErrorExitCode::test_upload_error_is_11`,
  `::test_transport_error_is_7`, `::test_handle_error_upload_prints_file_name_and_details`;
  `tests/unit/test_cli_write.py::TestUploadAll` (ordine, primo errore risale, nessuna chiamata
  dopo), `::TestAppendAttachments` (chiave assente, presente, lista vuota invariata),
  `::TestParseIdPathPairs` (valido, senza `=`, id non intero → `BadParameter`). Rossi.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/_common.py`: `EXIT_UPLOAD = 11`, `UploadError` in `_EXIT_MAP` prima di
     `TransportError`, ramo di `handle_error`.
  3. `cli/_write.py`: `AttachOption`, `upload_all`, `append_attachments`, `parse_id_path_pairs`.
  4. Controlli bloccanti; commit `feat(cli): exit code 11 per gli upload falliti e helper per
     --attach (04-T09)`.

### [ ] T10 – `attachments upload`

- Criteri: 04-C10
- Dipende da: T09
- Test: `tests/unit/test_cli_attachments.py::TestAttachmentsUpload`: `test_table_output`
  (snapshot), `test_name_override_sent_as_filename`, `test_json_output_full`, `test_fields`,
  `test_export`, `test_storage_400_exits_11`. Rossi: comando inesistente.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/attachments.py`: comando `upload PATH [--name N]`, riga curata `upload_row`, docstring
     del modulo.
  3. Generare e leggere lo snapshot; controlli bloccanti; commit `feat(cli): comando attachments
     upload (04-T10)`.

### [ ] T11 – `--attach` sui comandi dei post

- Criteri: 04-C11, 04-C12 (post), 04-C14
- Dipende da: T02, T09
- Test: `tests/unit/test_cli_posts_write.py::TestPostsAttach`:
  `test_create_two_attach_appended_after_json_items`, `test_comment_attachments`,
  `test_edit_add_attachments`, `test_copy_add_attachments`,
  `test_second_upload_fails_exits_11_without_write` (storage `204` poi `400`, messaggio con
  `b.pdf`, route di `create-post` non chiamata), `test_attach_missing_file_is_usage_error`. Rossi:
  opzione inesistente. Il test di caratterizzazione di T02 resta verde.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_write.py`: `attach: AttachOption` su `create`, `comment`, `edit`, `copy`;
     `validate_body` dentro il client dopo `append_attachments`; testi di aiuto.
  3. Snapshot di `--help` esistenti rigenerati e riletti se cambiano.
  4. Controlli bloccanti; commit `feat(cli): --attach su posts create, comment, edit e copy
     (04-T11)`.

### [ ] T12 – `--attach` sui comandi dei task

- Criteri: 04-C12 (task)
- Dipende da: T02, T09
- Test: `tests/unit/test_cli_tasks.py::TestTasksAttach::test_create_attachments`,
  `::test_edit_add_attachments`. Rossi. Il test di caratterizzazione di T02 resta verde.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/tasks.py`: `attach: AttachOption` su `create` (`attachments`) e `edit`
     (`addAttachments`); `validate_body` di `create` dentro il client; testi di aiuto.
  3. Controlli bloccanti; commit `feat(cli): --attach su tasks create ed edit (04-T12)`.

### [ ] T13 – `posts edit-attachments`

- Criteri: 04-C13
- Dipende da: T09
- Test: `tests/unit/test_cli_posts_write.py::TestPostsEditAttachments`:
  `test_add_update_remove_body_and_table` (due upload, una `PUT` con i tre campi, snapshot),
  `test_json_output_full`, `test_no_option_exits_2_without_requests`,
  `test_update_malformed_exits_2`; il test parametrizzato dei comandi registrati (03-C18) guadagna
  `edit-attachments`. Rossi: comando inesistente.
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `cli/posts_write.py`: comando e riga curata `attachments_write_row` come nel piano.
  3. Generare e leggere lo snapshot; controlli bloccanti; commit `feat(cli): comando posts
     edit-attachments con upload, nuove versioni e rimozioni (04-T13)`.

### [ ] T14 – Integration test opt-in del ciclo degli allegati

- Criteri: 04-C18 (codice del test)
- Dipende da: T07, T08
- Test: `tests/integration/test_attachments_integration.py::TestAttachmentsUploadIntegration::test_full_cycle`;
  qui si verifica solo che sia raccolto e saltato senza le variabili
  (`uv run pytest -m integration -k upload` → `skipped` con l'ambiente vuoto).
- Passi:
  1. Scrivere il test come nel piano: file generato, `upload`, `posts.create` con l'allegato e
     `_custom_data` duplicato, `list_for_post`, `edit_attachments(update=[…as_version_of(id)])`,
     `edit_attachments(remove_ids=[id])`, `delete` in `finally`; stampa `[T15]` della risposta a
     `updateAttachments` con il nome.
  2. `tests/integration/.env.example` e `docs/testing.md`: il ciclo riusa
     `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` e `PYNTERACTA_TEST_WRITE_CUSTOM_DATA`.
  3. Controlli bloccanti; commit `test: integration test opt-in del ciclo upload, allegato, nuova
     versione, rimozione (04-T14)`.

### [ ] T15 – Esecuzione dell'integration test sul tenant di prova (manuale)

- Criteri: 04-C18
- Chi: maintainer
- Cosa fare: con `tests/integration/.env` compilato (community di prova), eseguire
  `uv run pytest -m integration tests/integration/test_attachments_integration.py -s`; riportare
  l'esito e la riga `[T15]`. Se il server rifiuta o ignora il nome in `updateAttachments`, si
  rivede la spec (nome omesso nelle nuove versioni) con la sua approvazione prima di T16.
- Esito: <compilato a mano>

### [ ] T16 – Documentazione

- Criteri: 04-C17
- Dipende da: T10, T11, T12, T13, T15
- Test: `tests/unit/test_docs_snippets.py::test_attachments_pages_document_upload` (le pagine
  citano `upload`, `request_upload_url`, `--attach`, `edit-attachments`, exit code `11`;
  `logging.md` cita `signature`; `index.md` e README non mettono più l'upload tra ciò che manca e
  non citano numeri di versione nelle frasi nuove); rosso prima delle pagine. Più
  `uv run mkdocs build --strict`.
- Passi:
  1. Scrivere il test; eseguirlo: rosso.
  2. `docs/api/attachments.md` (sezione "Uploading files", membri e façade nuove, nota sul
     timeout per i file grandi), `docs/api/posts.md`, `docs/api/tasks.md`, `docs/cli.md`
     (`attachments upload`, `--attach`, `posts edit-attachments` al posto di "not yet from the
     CLI", riga `11` in "Exit codes"), `docs/logging.md` (garanzie di redazione), `docs/index.md`,
     `README.md`.
  3. `uv run mkdocs build --strict`, controlli bloccanti; commit `docs: upload degli allegati in
     libreria e CLI, redazione dei link firmati (04-T16)`.

### [ ] T17 – Chiusura: PRD

- Criteri: nessuno nuovo (requisiti nuovi della spec)
- Dipende da: T16
- Test: nessuno; si verifica rileggendo il PRD contro la sezione "Requisiti nuovi" della spec.
- Passi:
  1. `specs/prd.md`: RF-024 precisato (form multipart firmato, `UploadedAttachment`,
     `UploadError`), RF-024a, RNF-001 precisato (`signature`, `policy`, query firmate), RNF-011;
     RF-021c aggiornato (`posts edit-attachments` fatto); nota di conferma su RF-024 e sulla voce
     di §6 (contenuto dei file verso lo storage del tenant); riga in "Storia del documento".
  2. Controlli bloccanti; commit `docs: PRD con RF-024 precisato, RF-024a, RNF-001 e RNF-011
     (04-T17)`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 04-C01 | T05, T07 |
| 04-C02 | T07 |
| 04-C03 | T07 |
| 04-C04 | T05, T07 |
| 04-C05 | T05, T07 |
| 04-C06 | T06, T07 |
| 04-C07 | T06, T08 |
| 04-C08 | T03, T05 |
| 04-C09 | T05 |
| 04-C10 | T10 |
| 04-C11 | T11 |
| 04-C12 | T11, T12 |
| 04-C13 | T13 |
| 04-C14 | T11 |
| 04-C15 | T09 |
| 04-C16 | T01, T06 |
| 04-C17 | T16 |
| 04-C18 | T14, T15 |
