# Piano 04 – Upload degli allegati

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Due aggiunte alla base e una catena sopra. Alla base, il transport impara una seconda forma di
richiesta, `post_multipart(url, *, fields, file_name, content, content_type)`: URL assoluto, solo
`User-Agent` negli header (nessun `Authorization`), corpo multipart costruito da `httpx` (il file
è un oggetto aperto, quindi in streaming), stesso passaggio da log, audit e hook di `request()`
ma con `body=None` sempre, e una risposta non 2xx che diventa `UploadError`. Per non duplicare,
`request()` viene scomposto in tre helper (`_emit_request`, `_send`, `_emit_response`) che le
due forme condividono; i test di `test_transport.py` fissano già hook, audit e redazione di
`request()`, quindi la scomposizione è protetta. La redazione (`logging.py`) si estende in due
punti: `signature|policy` nel pattern delle chiavi dei body, e un pattern sui parametri di query
dentro `redact_string`, così da coprire URL nei log, negli hook, nei body dell'audit (il
`temporaryDownloadUrl` della risposta) e nei messaggi delle eccezioni senza toccare il processor.

Sopra, `AttachmentsAPI` guadagna `request_upload_url()` (una `_post` senza corpo →
`UploadTicket`) e `upload(file, *, name=None, mime_type=None)`: normalizza la sorgente **prima**
di qualunque richiesta (percorso → nome, MIME da `mimetypes`, file aperto; `bytes`/file-like →
`name` obbligatorio), chiede il ticket, chiama `post_multipart`, restituisce
`UploadedAttachment`. Perché i metodi di scrittura di post e task accettino `UploadedAttachment`
senza cambiare firma, `build_write_body` riconosce un protocollo `WriteInput` (`as_write_input()
-> dict`) accanto ai `BaseModel` e ai dict: una riga in `_dump_value`, nessun cambiamento in
`posts_write.py` e `tasks.py` oltre alle docstring. In CLI un helper condiviso in `cli/_write.py`
(`upload_all(client, paths) -> list[dict]`, `AttachOption`, `parse_id_path_pairs`) serve i sei
comandi con `--attach`, il nuovo `attachments upload` e `posts edit-attachments`; `handle_error`
mappa `UploadError` su `EXIT_UPLOAD = 11` e ne stampa il nome del file. Fixture, contract test,
integration test opt-in nel file degli allegati, pagine `docs/`. Test prima del codice, come nelle
spec 01, 02 e 03.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `ROADMAP.md` | modificato (apertura) | riga `0.12.0 ⏳ M30`, "Attachment upload (third write group, ADR 0001)", link alla spec |
| `src/pynteracta/exceptions.py` | modificato | `UploadError(InteractaError)` con l'attributo in più `file_name: str \| None` (kwarg `file_name=None`); docstring: risposta non 2xx dello storage, `response_body` = testo XML com'è, `request_id` assente |
| `src/pynteracta/logging.py` | modificato | `_SENSITIVE_KEY_RE` → `(?i)token\|password\|secret\|privatekey\|assertion\|jwt\|signature\|policy`; nuovo `_SENSITIVE_QUERY_RE = re.compile(r"(?i)([?&][^&=#\s]*(?:signature\|token\|secret\|password\|key)[^&=#\s]*=)([^&#\s\"']*)")`; `redact_string` applica prima la query (`\1***REDACTED***`) poi i JWT; docstring aggiornate |
| `src/pynteracta/transport.py` | modificato | scomposizione di `request()` in `_emit_request(method, redacted_url, headers, body) -> RequestInfo`, `_send(method, url, *, headers, params=None, json=None, data=None, files=None, redacted_url) -> (httpx.Response, elapsed_ms)` (gestisce timeout/rete → `TransportError` + `on_error`), `_emit_response(response, redacted_url, elapsed_ms, *, capture_body: bool)`; nuovo `post_multipart(url, *, fields: Mapping[str, str], file_name: str, content: BinaryIO, content_type: str) -> httpx.Response`: header solo `User-Agent`, `files={"file": (file_name, content, content_type)}`, `data=dict(fields)`, `body=None` in request e response info anche con `audit_bodies`, non 2xx → `UploadError(f"Upload of {file_name} failed", status_code, request_method="POST", request_url=redacted_url, response_body=response.text or None, file_name=file_name)` passato a `on_error` e sollevato; `redacted_url` sempre via `redact_string` (che ora copre le query) |
| `src/pynteracta/api/_utils.py` | modificato | `WriteInput` (`Protocol`, `runtime_checkable`): `as_write_input(self) -> dict[str, Any]`; `_dump_value`: `if isinstance(value, WriteInput): return value.as_write_input()` prima del ramo `BaseModel`; docstring di `build_write_body` |
| `src/pynteracta/models/facade/attachments.py` | modificato | `UploadTicket(raw: GetTemporaryImageUploadUrlBaseResponseDTO)`: `content_ref`, `upload_url`, `form_params: dict[str, str]` (copia di `uploadMultipartRequestBodyParams` o `{}`), `temporary_download_url`, `from_dict`; `UploadedAttachment(ticket, *, name, mime_type)`: `raw` (lo stesso DTO), `content_ref`, `name`, `mime_type`, `temporary_download_url`, `as_write_input() -> {"name", "contentRef"}`, `as_version_of(attachment_id) -> {"attachmentId", "contentRef", "name"}`; aggiornare la docstring del modulo |
| `src/pynteracta/models/facade/__init__.py` | modificato | esporta `UploadTicket`, `UploadedAttachment` |
| `src/pynteracta/api/attachments.py` | modificato | `_UPLOAD_PATH = "core/storage/upload-new-attachment"`; `_DEFAULT_MIME = "application/octet-stream"`; `UploadSource = Path \| str \| bytes \| BinaryIO`; `_open_source(file, name, mime_type) -> tuple[str, str, BinaryIO, bool]` (percorso: `Path(file)`, `open("rb")` solleva `FileNotFoundError`/`IsADirectoryError`, nome = `path.name`, MIME = `mimetypes.guess_type(path.name)[0] or _DEFAULT_MIME`, da chiudere; `bytes` → `io.BytesIO`; file-like → com'è, non si chiude; senza `name` → `ValueError("name is required when uploading bytes or a file object")`); `request_upload_url() -> UploadTicket` (`self._post(_UPLOAD_PATH)`); `upload(file, *, name=None, mime_type=None) -> UploadedAttachment`: `_open_source` → `request_upload_url` → `self._transport.post_multipart(ticket.upload_url, fields=ticket.form_params, file_name=…, content=…, content_type=…)` in `try/finally` che chiude il file aperto dalla libreria → `UploadedAttachment(ticket, name=…, mime_type=…)`; docstring della classe aggiornata (letture più upload) |
| `src/pynteracta/api/posts_write.py`, `src/pynteracta/api/tasks.py` | modificati (solo docstring) | `attachments`/`add_attachments`/`add`/`update` citano `UploadedAttachment` e `as_version_of`; la nota "l'upload non fa parte di questa libreria" di `edit_attachments` sparisce; `WriteItems` resta |
| `src/pynteracta/cli/_common.py` | modificato | `EXIT_UPLOAD = 11`; `_EXIT_MAP[UploadError] = EXIT_UPLOAD` (prima di `TransportError`, l'ordine del dict è quello di `isinstance`); `handle_error`: per `UploadError` la prima riga è `Error: Upload of {file_name} failed` (quella del messaggio) e `Details:` con il corpo XML compattato se presente |
| `src/pynteracta/cli/_write.py` | modificato | `AttachOption = Annotated[list[pathlib.Path] \| None, typer.Option("--attach", help="File to upload and attach (repeatable).", exists=True, dir_okay=False, readable=True)]`; `upload_all(client, paths) -> list[dict[str, Any]]` (nell'ordine; `client.attachments.upload(path).as_write_input()`; il primo errore risale); `append_attachments(merged, key, items)` (`merged[key] = [*merged.get(key, []), *items]` solo se `items`); `parse_id_path_pairs(values, *, option) -> list[tuple[int, pathlib.Path]]` (`ID=PATH`, `=` mancante o id non intero → `typer.BadParameter`) |
| `src/pynteracta/cli/attachments.py` | modificato | comando `upload PATH [--name N]` con `render_output` (`--output`, `--full`, `--fields`, `--export`): riga curata `upload_row` = `name`, `content_ref`, `temporary_download_url`; `--full`/json → `.raw`; titolo `Uploaded NAME`; errori via `handle_error` |
| `src/pynteracta/cli/posts_write.py` | modificato | `posts create`, `posts comment`: `attach: AttachOption = None`; `validate_body` e la chiamata si spostano dentro `with build_client`, dopo `append_attachments(merged, "attachments", upload_all(client, attach))`; `posts edit`, `posts copy`: `append_attachments(merged, "addAttachments", …)` dopo `_patch_body`, prima di `validate_body`; nuovo `posts edit-attachments POST_ID [--add PATH]… [--remove ID]… [--update ID=PATH]…`: nessuna delle tre → `"--add, --remove or --update is required."` ed `EXIT_CONFIG`; `--update` via `parse_id_path_pairs`; dentro il client: `add = upload_all(client, add_paths)`, `update = [client.attachments.upload(p).as_version_of(i) for i, p in pairs]`, `client.posts.edit_attachments(post_id, add=add or None, update=update or None, remove_ids=remove or None)`; riga curata `attachments_write_row` = `post_id`, `added` (`"id name, …"`), `updated`, `removed_ids`; `_render_single` con titolo `Attachments of post POST_ID updated`; `handle_error(..., resource=f"Post {post_id}")`; docstring dei comandi aggiornate (`--attach` nel testo di aiuto) |
| `src/pynteracta/cli/tasks.py` | modificato | `tasks create`: `attach: AttachOption`, `append_attachments(merged, "attachments", …)` dentro il client prima di `validate_body` (la validazione si sposta dentro il `with`); `tasks edit`: `append_attachments(merged, "addAttachments", …)` dopo `merge_body`, prima di `validate_body` |
| `tests/fixtures/payloads/upload_new_attachment_response.json` | nuovo | `contentRef` finto di 64 esadecimali, `uploadUrl: "https://storage.example.com/bucket-test"`, `uploadMultipartRequestBodyParams` con `GoogleAccessId: "fake@test.iam.gserviceaccount.com"`, `key: "temporary-uploads/<contentRef>"`, `policy: "eyJleHBpcmF0aW9uIjo…"` (base64 finto, non un JWT: senza il terzo segmento), `signature: "FAKE-SIGNATURE"`; `temporaryDownloadUrl: "https://storage.example.com/bucket-test/temporary-uploads/<contentRef>?GoogleAccessId=…&Expires=…&Signature=FAKE"` |
| `tests/unit/test_redaction.py` | modificato | 04-C08: `TestRedactString::test_signed_query_params_redacted` (solo `Signature`, `GoogleAccessId` ed `Expires` restano), `test_query_without_sensitive_names_untouched`, `test_sensitive_query_inside_text`; `TestRedactBody::test_signature_and_policy_keys_redacted`, `test_download_url_leaf_string_redacted` |
| `tests/unit/test_transport.py` | modificato | 04-C09 e parte di 04-C01/C04/C05 sul transport: `TestPostMultipart` (`respx` sull'host di storage): nessun `Authorization` e `User-Agent` presente, corpo multipart con i quattro campi e il file (`request.content` contiene `name="file"; filename="nota.txt"` e `Content-Type: text/plain`), hook `on_request.body is None` e `on_response.status_code == 204` con `audit_bodies=True`, evento audit senza byte né campi, `400` → `UploadError` con `status_code`, `request_url`, `response_body`, `file_name` e `on_error` chiamato una volta, `TimeoutException` → `TransportError`, `request_url` con query firmata redatta; `test_hooks_on_success` e gli altri test esistenti restano verdi dopo la scomposizione |
| `tests/unit/test_api_utils.py` | modificato | 04-C07 (parte): `TestBuildWriteBody::test_write_input_objects_are_converted` con un oggetto che implementa `as_write_input` dentro una lista insieme a un dict e a un `BaseModel` |
| `tests/unit/test_facade_attachments.py` | modificato | `UploadTicket` e `UploadedAttachment` sulla fixture: proprietà, `form_params` copia, `as_write_input`, `as_version_of`, `.raw` |
| `tests/unit/test_api_attachments.py` | modificato | 04-C01…C06 su `AttachmentsAPI` con `respx` sui due host (`BASE_URL` e `https://storage.example.com`): sequenza delle due chiamate e ordine (`respx.calls`), file da `tmp_path` (`.txt`, vuoto, `.xyz` → octet-stream), `bytes`/`BytesIO` con e senza `name`, `mime_type` esplicito, percorso inesistente e cartella → nessuna route chiamata, `400` dello storage → `UploadError` e una sola chiamata per host, timeout → `TransportError`, `request_upload_url` → `UploadTicket` |
| `tests/unit/test_api_posts_write.py`, `tests/unit/test_api_tasks.py` | modificati | 04-C07: `UploadedAttachment` (costruito dalla fixture) in `create`/`add_comment`/`edit`/`copy`/`edit_attachments` e `tasks.create`/`edit`, corpo con `{"name", "contentRef"}` accanto a un dict; `as_version_of(7)` in `update` |
| `tests/unit/test_cli_common.py` | modificato | 04-C15: `UploadError → 11`, `TransportError → 7` in `TestErrorExitCode`; `handle_error` con `UploadError` stampa il nome del file e `Details` |
| `tests/unit/test_cli_write.py` | modificato | `upload_all` (ordine, errore al primo), `append_attachments` (chiave assente, presente, lista vuota), `parse_id_path_pairs` (valido, senza `=`, id non intero) |
| `tests/unit/test_cli_attachments.py` | modificato | 04-C10: `attachments upload` tabella (snapshot), `--name`, `--output json`, `--full`, `--fields content_ref`; file in `tmp_path`; errore `400` dello storage → exit `11` |
| `tests/unit/test_cli_posts_write.py` | modificato | 04-C11, 04-C12 (post), 04-C13, 04-C14: `TestPostsAttach` (due `--attach` con `--json` che ha `attachmentId: 3` → ordine e accodamento in `create-post`; `comment` → `attachments`; `edit`/`copy` → `addAttachments`), `TestPostsEditAttachments` (corpo della `PUT`, snapshot della tabella, nessuna opzione → `2` e route non chiamata, `--update b.pdf` → exit `2` con messaggio di Typer), `test_second_upload_fails_exits_11_without_write` (`respx` con `side_effect` che risponde `204` poi `400`; route di `create-post` con `called is False`) |
| `tests/unit/test_cli_tasks.py` | modificato | 04-C12 (task): `--attach` su `tasks create` (`attachments`) e `tasks edit` (`addAttachments`) |
| `tests/contract/test_models.py` | modificato | 04-C16: `TestUploadNewAttachment` con `assert_superset(GetTemporaryImageUploadUrlBaseResponseDTO, "GetTemporaryImageUploadUrlBaseResponseDTO")` e smoke di `UploadTicket.from_dict` e `UploadedAttachment` sulla fixture |
| `tests/integration/test_attachments_integration.py` | modificato | 04-C18: `TestAttachmentsUploadIntegration::test_full_cycle` (skip senza `PYNTERACTA_TEST_WRITE_COMMUNITY_ID`): file generato in `tmp_path`, `upload`, `posts.create(..., attachments=[uploaded], custom_data=…)` riusando `_custom_data` di `test_posts_integration.py` (spostarlo in un helper condiviso `tests/integration/_env.py` o duplicarlo: si duplica, due righe), `attachments.list_for_post` contiene il nome, `edit_attachments(update=[second.as_version_of(id)])` e verifica di `version_number`/nome, `edit_attachments(remove_ids=[id])`, `delete` in `finally`; stampa `[T-manuale]` di cosa fa il server con il nome in `updateAttachments` |
| `tests/integration/.env.example`, `docs/testing.md` | modificati | nota che il ciclo degli allegati riusa `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` e `PYNTERACTA_TEST_WRITE_CUSTOM_DATA` |
| `docs/api/attachments.md` | modificato | sezione "Uploading files" (i due passi, `upload`, `request_upload_url`, `UploadedAttachment` nei metodi di post e task, `as_version_of`, `UploadError`, nessun retry, redazione dei link firmati); membri `request_upload_url`, `upload` nel riferimento; façade `UploadTicket`, `UploadedAttachment`; "three read endpoints" → letture più upload |
| `docs/api/posts.md`, `docs/api/tasks.md` | modificati | gli `attachments` accettano `UploadedAttachment`; esempio con `client.attachments.upload` |
| `docs/cli.md` | modificato | `attachments upload`; `--attach` nei sei comandi; `posts edit-attachments` (sostituisce la frase "not yet from the CLI"); riga `11` nella tabella "Exit codes"; nota "stops at the first failed upload" |
| `docs/logging.md` | modificato | "Redaction guarantees": chiavi `signature`/`policy`, parametri di query firmati, contenuto dei file mai nei log/audit/hook; esempio con `temporaryDownloadUrl` redatto |
| `docs/index.md`, `README.md` | modificati | "attachment upload" passa da "follow" a presente, senza numeri di versione; la riga "Writes on … attachment upload … planned" di `index.md` perde l'upload |
| `tests/unit/test_docs_snippets.py` | modificato | 04-C17: `test_attachments_pages_document_upload` (le pagine citano `upload`, `--attach`, `edit-attachments`, exit code `11`; `logging.md` cita `signature`); gli snippet nuovi di `attachments.md` passano dal controllo di coerenza esistente |
| `PROGRESS.md` | modificato (verifica) | sezione M30 |
| `specs/prd.md` | modificato (chiusura) | RF-024 precisato, RF-024a, RNF-001 precisato, RNF-011; conferma di RF-024 e della voce di §6 |

Non si toccano: `hooks.py` (le dataclass bastano), `client.py` (`client.attachments` esiste e ha
il transport autenticato, che per lo storage non manda il token), `api/_base.py`,
`models/generated/` (il DTO esiste già, il swagger non cambia), `urls.py`.

## Modello dati e migrazioni

Nessuna modifica di schema. Il DTO `GetTemporaryImageUploadUrlBaseResponseDTO` è già generato
(`contentRef`, `uploadUrl`, `uploadMultipartRequestBodyParams: dict[str, str] | None`,
`temporaryDownloadUrl`). Le due façade nuove lo avvolgono; `UploadedAttachment` aggiunge `name` e
`mime_type` scelti dalla libreria. `UploadError` aggiunge `file_name` agli attributi comuni di
`InteractaError`.

## Flussi

Flusso principale, `client.attachments.upload(Path("nota.txt"))`:

```
upload(file, name, mime_type)
  _open_source                         # FileNotFoundError / IsADirectoryError / ValueError: nessuna richiesta
  request_upload_url()
    transport.request POST core/storage/upload-new-attachment   (Authorization, hook, audit)
    → UploadTicket(content_ref, upload_url, form_params, temporary_download_url)
  transport.post_multipart(upload_url, fields=form_params, file_name, content, content_type)
    headers = {User-Agent}             # nessun Authorization
    _emit_request(body=None) → hook on_request, audit.request (url senza query)
    httpx POST multipart: campi della policy + file (streaming dal file aperto)
    _emit_response(capture_body=False) → hook on_response(status 204), audit.response
    non 2xx → UploadError(file_name, status, url redatto, corpo XML) → on_error → raise
    timeout / rete → TransportError → on_error → raise
  finally: chiude il file aperto dalla libreria
  → UploadedAttachment(ticket, name, mime_type)
```

Uso nel post: `client.posts.create(79, attachments=[uploaded])` → `build_write_body` →
`_dump_value(uploaded)` → `uploaded.as_write_input()` → `{"name": …, "contentRef": …}`; nessuna
richiesta in più rispetto a oggi.

CLI, `posts create 79 --title T --attach a.txt --attach b.pdf --json body.json`:

```
load_json_body, parse flag, merge_body            # come oggi, fuori dal client
with build_client(state) as client:
    items = upload_all(client, [a.txt, b.pdf])    # due upload, in ordine; il primo errore risale
    append_attachments(merged, "attachments", items)
    req = validate_body(merged, CreateCustomPostRequest)
    result = client.posts.create_raw(79, req)
render → exit 0
except InteractaError → handle_error → UploadError: "Error: Upload of b.pdf failed" + Status, exit 11
                                      → TransportError: exit 7
```

`posts edit-attachments 21269 --add a.txt --update 5=b.pdf --remove 9`: `parse_id_path_pairs`
fuori dal client; dentro, `upload_all` per `--add`, `upload(...).as_version_of(5)` per
`--update`, poi `client.posts.edit_attachments(...)` (una `PUT`); tabella `attachments_write_row`.

## Interfaccia

Comandi e opzioni come nella spec ("Comportamento > CLI"), testi in inglese. Messaggi nuovi:
`"--add, --remove or --update is required."` (exit `2`), `"--update must be ID=PATH, got: …"`
(`BadParameter`, exit `2`), `"Error: Upload of NAME failed"` più `Status:` e `Details:` (exit
`11`). `--attach` usa la validazione di Typer per i percorsi (`exists=True, dir_okay=False`):
un percorso mancante è un errore d'uso prima di qualunque chiamata, coerente con 04-C03.
Tabelle: `attachments upload` (`name`, `content_ref`, `temporary_download_url`) e
`posts edit-attachments` (`post_id`, `added`, `updated`, `removed_ids`), entrambe con snapshot
syrupy. Nessun `--web-url` (gruppo allegati, D-v0.3-3b; il post di `edit-attachments` non è il
risultato).

## Configurazione

Nessuna variabile nuova. Il timeout è quello di `timeout_seconds` (per operazione di rete:
`httpx` lo applica a connect/read/write, non alla durata totale, quindi un file grande passa
finché ogni scrittura sul socket resta sotto il limite). L'integration test riusa
`PYNTERACTA_TEST_WRITE_COMMUNITY_ID` e `PYNTERACTA_TEST_WRITE_CUSTOM_DATA`: `.env.example` lo
dice.

## Sicurezza e dati personali

- **Token e segreti mai nei log**: la richiesta allo storage non ha `Authorization`
  (`post_multipart` non chiama `_build_headers`, costruisce `{User-Agent}`); `policy` e
  `signature` entrano nel pattern delle chiavi, le `Signature=` nelle query entrano in
  `redact_string`, che è già applicato a URL, header, leaf dei body e messaggi; i campi del form
  e il file non entrano in `RequestInfo.body` né nell'audit (`body=None` fisso, non dipende da
  `audit_bodies`). Test: 04-C08, 04-C09, più `test_exception_url_does_not_contain_raw_token`
  esteso alla query.
- **Nessuna operazione ripetuta**: un solo `request` e un solo `post_multipart` per upload; in
  CLI `upload_all` si ferma al primo errore e la scrittura non parte (04-C04, C05, C14).
- **Dati personali**: il contenuto del file va solo allo storage; il nome del file compare nel
  messaggio di errore della CLI (scelta della spec) e nel corpo della scrittura, come oggi.
- **Fixture**: credenziali finte e riconoscibili (`fake@test.iam.gserviceaccount.com`,
  `FAKE-SIGNATURE`, host `storage.example.com`); nessun dato del tenant.

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `transport.request()` (scomposizione in helper) | hook, audit, redazione, mappa degli errori, `User-Agent`, `Authorization` | già fissati da `test_transport.py` (`test_hooks_on_success`, `test_audit_*`, `TestResponseRedaction`, `test_error_mapping_by_status`…): nessun test nuovo, devono restare verdi prima e dopo |
| `redact_string` / `redact_body` | JWT redatti, stringhe comuni intatte, chiavi non sensibili intatte | già fissati da `test_redaction.py` e `TestSensitiveKeyCoverage`; si aggiunge `test_url_query_without_sensitive_names_untouched` **prima** della modifica, per fissare che una query ordinaria (`?loadViewLink=true&pageSize=10`) resta intatta |
| `build_write_body` / `_dump_value` | dict e `BaseModel` nelle liste | già fissati da `TestBuildWriteBody` |
| `posts create`, `posts comment`, `tasks create` (spostamento di `validate_body` dentro il client) | corpo inviato, exit `2` su corpo non valido senza chiamate al server | i test esistenti coprono il corpo; si aggiunge **prima** `test_invalid_json_body_exits_2_without_requests` per `posts create` e `tasks create` (route non chiamate), così lo spostamento non cambia l'esito |
| `handle_error` | messaggi e exit code attuali | già fissati da `test_cli_common.py` |

## Strategia di test

| Criterio | Test previsto | Tipo |
|---|---|---|
| 04-C01 | `test_api_attachments.py::TestUpload::test_path_two_requests_in_order_no_authorization` (route su `BASE_URL` e sullo storage; `respx.calls` in ordine; `"Authorization" not in request.headers`; contenuto multipart con i quattro campi, `filename="nota.txt"`, `Content-Type: text/plain`, i byte); `test_empty_file_is_uploaded`; proprietà del risultato | unitario |
| 04-C02 | `TestUpload::test_bytes_with_name_octet_stream`, `test_fileobj_with_name`, `test_mime_type_override`, `test_bytes_without_name_raises_before_requests` (`respx` senza chiamate) | unitario |
| 04-C03 | `TestUpload::test_missing_path_raises_without_requests`, `test_directory_raises_without_requests` | unitario |
| 04-C04 | `TestUpload::test_storage_400_raises_upload_error_once` (attributi, `calls` = 1 per host); `test_transport.py::TestPostMultipart::test_non_2xx_raises_upload_error_with_file_name` | unitario |
| 04-C05 | `TestUpload::test_storage_timeout_raises_transport_error_once`; `TestPostMultipart::test_timeout_maps_to_transport_error` | unitario |
| 04-C06 | `TestRequestUploadUrl::test_returns_ticket`; `test_facade_attachments.py::TestUploadTicket` | unitario |
| 04-C07 | `test_api_utils.py::TestBuildWriteBody::test_write_input_objects_are_converted`; `test_api_posts_write.py::TestPostsUploadedAttachments` (create, add_comment, edit, copy, edit_attachments add e update con `as_version_of`); `test_api_tasks.py::TestTasksUploadedAttachments` (create, edit); `test_facade_attachments.py::TestUploadedAttachment::test_as_write_input_and_as_version_of` | unitario |
| 04-C08 | `test_redaction.py::TestRedactString::test_signed_query_params_redacted`, `test_sensitive_query_inside_text`; `TestRedactBody::test_signature_and_policy_keys_redacted`, `test_download_url_leaf_string_redacted`; `test_transport.py::TestPostMultipart::test_upload_error_url_query_is_redacted`; `test_logging.py::TestSensitiveKeyCoverage` esteso a `signature`, `policy`; evento di log e hook con URL firmato in `test_transport.py::test_signed_url_redacted_in_hooks_and_audit` | unitario |
| 04-C09 | `test_transport.py::TestPostMultipart::test_hooks_see_request_without_body_and_response_status` (`audit_bodies=True`), `test_audit_events_carry_no_file_bytes_nor_form_fields` (cattura di `structlog` come negli altri test di audit) | unitario |
| 04-C10 | `test_cli_attachments.py::TestAttachmentsUpload::test_table_output` (snapshot), `test_name_override_sent_as_filename`, `test_json_output_full`, `test_fields`, `test_export` | unitario |
| 04-C11 | `test_cli_posts_write.py::TestPostsAttach::test_create_two_attach_appended_after_json_items` | unitario |
| 04-C12 | `TestPostsAttach::test_comment_attachments`, `test_edit_add_attachments`, `test_copy_add_attachments`; `test_cli_tasks.py::TestTasksAttach::test_create_attachments`, `test_edit_add_attachments` | unitario |
| 04-C13 | `test_cli_posts_write.py::TestPostsEditAttachments::test_add_update_remove_body_and_table` (snapshot), `test_no_option_exits_2_without_requests`, `test_update_malformed_exits_2` | unitario |
| 04-C14 | `TestPostsAttach::test_second_upload_fails_exits_11_without_write` (messaggio con `b.pdf`, route di `create-post` non chiamata) | unitario |
| 04-C15 | `test_cli_common.py::TestErrorExitCode::test_upload_error_is_11`, `test_transport_error_is_7`; `test_handle_error_upload_prints_file_name_and_details` | unitario |
| 04-C16 | `tests/contract/test_models.py::TestUploadNewAttachment::test_schema_superset`, `test_facade_smoke` | contratto |
| 04-C17 | `uv run mkdocs build --strict` (controllo di verifica); `test_docs_snippets.py::test_attachments_pages_document_upload` (pagine, exit code `11`, README e `index.md` con "attachment upload" fuori dalla lista di ciò che manca, nessun numero di versione nelle frasi nuove) | unitario + controllo |
| 04-C18 | `tests/integration/test_attachments_integration.py::TestAttachmentsUploadIntegration::test_full_cycle`, eseguito sul tenant di prova dal maintainer; skip senza le variabili | integrazione |

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| `post_multipart` come metodo di `HttpTransport`, con `request()` scomposto in helper condivisi | Classe `StorageTransport` separata; `httpx.Client` a parte in `AttachmentsAPI` | Hook, audit, `User-Agent`, mappa dei timeout e redazione stanno nel transport e devono valere anche per lo storage (spec); una classe nuova duplicherebbe tutto; la scomposizione è protetta dai test esistenti |
| Query firmate redatte dentro `redact_string` con un regex sui nomi dei parametri | `redact_url` strutturato (`urlsplit`) applicato solo alle chiavi `url` del processor e del transport | `redact_string` è già applicato ovunque (URL, header, leaf dei body, messaggi): copre il `temporaryDownloadUrl` nei body dell'audit e gli URL nei messaggi senza toccare il processor; il regex richiede `?` o `&` prima del nome, quindi non tocca testo ordinario |
| `WriteInput` come `Protocol` riconosciuto da `_dump_value` | `UploadedAttachment` come `BaseModel` con alias camelCase; conversione esplicita in ogni metodo di post e task | Nessuna firma cambia, una riga in `_utils.py`; la façade resta della stessa famiglia delle altre (`.raw`, proprietà) |
| `UploadError` sollevata dal transport, con `file_name` | Sollevata da `AttachmentsAPI` traducendo un'eccezione generica del transport | Il transport è l'unico posto che mappa gli stati HTTP (`_map_error`); il nome del file lo conosce perché costruisce il multipart |
| Sorgente normalizzata in `_open_source` prima di `request_upload_url` | Chiedere il ticket e poi aprire il file | Un file mancante non consuma una policy (spec, 04-C03); il file resta aperto solo per la durata della `POST` |
| `--attach` con `exists=True, dir_okay=False` di Typer | Lasciare l'errore a `upload` dentro il client | L'errore d'uso arriva prima di autenticarsi e di qualunque richiesta, con il messaggio standard di Typer |
| `validate_body` spostata dentro il client nei comandi con `--attach` | Validare prima e poi aggiungere gli allegati senza rivalidare | Il corpo inviato è sempre quello validato dal DTO; i test di caratterizzazione fissano che un corpo non valido esce con `2` senza chiamate |
| Integration test nel file degli allegati, `_custom_data` duplicato | Helper condiviso `tests/integration/_env.py` | Due righe duplicate contro un modulo nuovo in una cartella opt-in |
| Multipart costruito da `httpx` (`files=` + `data=`) | Corpo multipart a mano | `httpx` ordina i campi `data` prima dei `files`, come la policy di GCS richiede (il campo `file` deve essere l'ultimo), e fa lo streaming dal file aperto |

## Rischi

- **Ordine dei campi del multipart**: GCS esige `file` per ultimo; `httpx` mette `data` prima
  di `files`. → test di 04-C01 che controlla l'ordine nel contenuto; integration test 04-C18 sul
  tenant.
- **`updateAttachments` con `name`**: il server potrebbe ignorare o rifiutare il nome nella
  nuova versione. → 04-C18 stampa il risultato; se rifiuta, la spec si rivede (nome omesso) con
  l'approvazione del maintainer.
- **Over-redazione del regex sulle query**: parametri legittimi con `key`/`token` nel nome (per
  esempio `pageToken`) perdono il valore nei log. → accettato: sono valori opachi, e il
  comportamento è quello della spec ("il cui nome contiene"); test fissa che una query ordinaria
  resta intatta.
- **Scomposizione di `request()`**: una regressione su hook o audit. → i test esistenti di
  `test_transport.py` girano prima e dopo; nessun cambio di comportamento atteso.
- **Timeout per operazione su file grandi**: una scrittura lenta sul socket oltre
  `timeout_seconds` → `TransportError` con esito sconosciuto. → documentato in
  `docs/api/attachments.md`: alzare `timeout_seconds` per file grandi; nessun retry.
- **Snapshot syrupy**: tabelle nuove con `temporary_download_url` lungo. → la fixture usa URL
  corti e fissi.
