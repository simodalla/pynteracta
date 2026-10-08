# Piano 02 – Scrittura dei task: creazione, modifica, eliminazione

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Si estende la catena già usata dalle letture, senza toccare il transport: `ResourceClient` guadagna
`_put` e `_delete`; `TasksAPI` guadagna `create`/`create_raw`, `edit`/`edit_raw`, `delete`, che
costruiscono il corpo dai kwargs (camelCase, solo i campi passati) o dal DTO (`model_dump(mode="json",
exclude_none=True)`, come i `*_raw` esistenti); la façade `Task` espone `occ_token` e una nuova
façade `TaskWriteResult` avvolge le risposte di `create` ed `edit` rivalidando gli stub `RootModel`
(`TaskDetailDTO` → `TaskDetailDTO1`, `TaskCapabilitiesDTO` → `TaskCapabilitiesDTO1`) come fa
`Task` per le capabilities. La conversione della scadenza sta in un helper di `api/_utils.py`
usato sia dalla libreria sia dalla CLI. Nella CLI, `_common.py` riceve `EXIT_CONFLICT = 9`
(`ConcurrencyError` nella mappa), `confirm_destructive()` e `load_json_body()`; `cli/tasks.py`
riceve i tre comandi, che passano sempre dal percorso `*_raw` dopo aver unito flag e `--json`.
Fixture JSON e contract test per i cinque DTO; integration test opt-in a ciclo completo; pagine
`docs/`. Test prima del codice, come nella spec 01.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `src/pynteracta/api/_base.py` | modificato | `_put(path, *, json, params)` e `_delete(path, *, params)` sul modello di `_post`; entrambi restituiscono il corpo JSON come `dict` (`delete-task` risponde `DeleteTaskResponseDTO`) |
| `src/pynteracta/api/_utils.py` | modificato | `zoned_datetime_input(dt: datetime) -> dict[str, str]`: `ValueError` se `tzinfo is None`; con `tzinfo.key` (ZoneInfo) → `{"datetime": <locale senza offset, timespec="seconds">, "timezone": key}`; altrimenti → conversione in UTC e `"timezone": "UTC"`. `build_write_body(**kwargs)`: camelCase dei soli non-`None`, `BaseModel` nelle liste dumpati con `exclude_none` |
| `src/pynteracta/api/tasks.py` | modificato | `create`, `create_raw`, `edit`, `edit_raw`, `delete`; costanti dei tre percorsi; docstring Google con i campi |
| `src/pynteracta/models/facade/tasks.py` | modificato | `Task.occ_token`; `TaskWriteResult(raw: CreateTaskResponseDTO \| EditTaskResponseDTO)` con `task_id`, `next_occ_token`, `task: generated.TaskDetailDTO1 \| None`, `capabilities: TaskCapabilities \| None`, `from_create(data)`, `from_edit(data)` |
| `src/pynteracta/cli/_common.py` | modificato | `EXIT_CONFLICT = 9`; `ConcurrencyError: EXIT_CONFLICT` in `_EXIT_MAP`; `_stdin_is_interactive()` (wrapper di `sys.stdin.isatty()`, sostituibile nei test); `confirm_destructive(prompt, *, yes) -> bool` (True con `--yes`; prompt `typer.confirm` se interattivo; altrimenti messaggio `--yes is required when not running interactively` ed `Exit(EXIT_CONFIG)`); `load_json_body(source: str \| None, dto_cls) -> dict` (file o `-` = stdin; JSON non valido o chiavi fuori da `dto_cls.model_fields` → messaggio ed `Exit(EXIT_CONFIG)`) |
| `src/pynteracta/cli/tasks.py` | modificato | comandi `create`, `edit`, `delete`; opzioni condivise (`--title`, `--description`, `--expiration`, `--timezone`, `--priority`, `--assignee-user`, `--assignee-group`, `--watcher-user`, `--watcher-group`, `--client-uid`, `--json`); `_parse_expiration(value, timezone)` (ISO 8601 via `datetime.fromisoformat`; senza offset → `ZoneInfo(timezone)`, `ZoneInfoNotFoundError` → `Exit(EXIT_CONFIG)`); `_merge_body(flags, json_body)` (flag prevalgono campo per campo); tabella curata di `create`/`edit` (id, post_id, title, state, priority, expiration, assignee) |
| `tests/unit/test_api_tasks.py` | modificato | 02-C01…C07, 02-C13 |
| `tests/unit/test_cli_tasks.py` | modificato | 02-C08…C12 (snapshot syrupy per la tabella di `create`) |
| `tests/unit/test_cli_common.py` | nuovo | caratterizzazione di `error_exit_code` (mappa attuale) prima di aggiungere il 409; test di `confirm_destructive` e `load_json_body` |
| `tests/unit/test_api_utils.py` | nuovo | `zoned_datetime_input`: ZoneInfo, UTC, offset fisso, naive (02-C03); `build_write_body` |
| `tests/fixtures/payloads/create_task_response.json`, `edit_task_response.json`, `delete_task_response.json` | nuovi | risposte sagomate sul swagger, con `taskData` completo e `nextOccToken`; dati finti |
| `tests/fixtures/payloads/get_task_detail_response.json` | invariato | ha già `occToken`: lo usano 02-C07 e 02-C09 (il valore atteso nei test è quello della fixture) |
| `tests/contract/test_models.py` | modificato | 02-C14: `assert_superset` per `CreateTaskRequestDTO`, `CreateTaskResponseDTO`, `EditTaskRequestDTO`, `EditTaskResponseDTO`, `DeleteTaskResponseDTO`, `ZonedDatetimeInputDTO1`, `TaskDetailDTO1`; smoke `TaskWriteResult.from_create/from_edit` sulle fixture |
| `tests/integration/test_tasks_integration.py` | modificato | 02-C16: classe `TestTasksWriteIntegration`, ciclo `create → get → edit → delete` con `finally` |
| `tests/integration/.env.example`, `docs/testing.md` | modificati | `PYNTERACTA_TEST_WRITE_POST_ID` |
| `docs/api/tasks.md`, `docs/cli.md` | modificati | 02-C15: metodi, `TaskWriteResult`, `occ_token`, scadenza, campi omessi; comandi, `--json`, exit code 9 |
| `tests/unit/test_docs_snippets.py` | modificato | test con marker 02-C15 che verifica la presenza dei comandi e dell'exit code 9 nelle pagine |
| `specs/prd.md`, `CLAUDE.md` | modificati (chiusura) | RF-022a, RF-015a, RF-025a, RNF-010 nel PRD; conferma di RF-022, RF-025, RNF-009, §6; una riga nella sezione Lingua (interfaccia della CLI in inglese) |

Non si toccano: `transport.py`, `hooks.py`, `client.py` (`client.tasks` esiste già), `models/generated/`.

## Modello dati e migrazioni

Nessuna modifica: i DTO sono già generati (`CreateTaskRequestDTO`, `CreateTaskResponseDTO`,
`EditTaskRequestDTO`, `EditTaskResponseDTO`, `DeleteTaskResponseDTO`; `expiration` è lo stub
`ZonedDatetimeInputDTO` che accetta un dict).

## Flussi

```
Libreria
create(post_id, **kw)   → body = build_write_body(**kw, expiration=zoned_datetime_input(dt) se dt)
                        → _post("communication/tasks/manage/create-task/{post_id}", json=body)
                        → TaskWriteResult.from_create(resp)
create_raw(post_id, req)→ _post(..., json=req.model_dump(mode="json", exclude_none=True))
edit(task_id, occ_token, **kw)
                        → _put("communication/tasks/manage/edit-task/{task_id}/{occ_token}", json=body)
                        → TaskWriteResult.from_edit(resp)        (409 → ConcurrencyError dal transport)
delete(task_id)         → _delete("communication/tasks/manage/delete-task/{task_id}")
                        → DeleteTaskResponseDTO.model_validate(resp).postId
Errori: nessun try/except nei metodi: il transport solleva le InteractaError; una richiesta per chiamata.

CLI
tasks create POST_ID    → flags → dict camelCase (expiration via _parse_expiration + zoned_datetime_input)
                        → json_body = load_json_body(--json, CreateTaskRequestDTO) se dato
                        → merged = {**json_body, **flags_non_none}
                        → client.tasks.create_raw(POST_ID, CreateTaskRequestDTO.model_validate(merged))
                        → render_output([result], curated, …)
tasks edit TASK_ID      → occ = --occ-token oppure client.tasks.get(TASK_ID).occ_token
                            (occ_token None dal server → messaggio ed Exit(EXIT_GENERIC))
                        → merged come sopra con EditTaskRequestDTO
                        → client.tasks.edit_raw(TASK_ID, occ, EditTaskRequestDTO.model_validate(merged))
                        → render_output; ConcurrencyError → handle_error → EXIT_CONFLICT (9) con il
                          messaggio della spec (handle_error aggiunge il testo per ConcurrencyError)
tasks delete TASK_ID    → task = client.tasks.get(TASK_ID)
                        → confirm_destructive(f'Delete task {id} "{title}"? ', yes=--yes)
                            False → Exit(0), nessuna DELETE
                        → post_id = client.tasks.delete(TASK_ID)
                        → testo "Task {id} deleted (post {post_id})" oppure JSON {"task_id","post_id"}
```

## Interfaccia

Comandi, opzioni e messaggi come nella sezione "CLI" della spec; testi in inglese. Help delle
opzioni breve, con il formato atteso (`ISO 8601, e.g. 2026-12-31T18:00`; `IANA name, default
Europe/Rome`). Nessuna pagina web.

## Configurazione

Nessuna variabile di runtime. Solo per gli integration test: `PYNTERACTA_TEST_WRITE_POST_ID` in
`tests/integration/.env.example` e `docs/testing.md`, con la raccomandazione di un post in una
community di prova.

## Sicurezza e dati personali

- **Nessuna operazione ripetuta in automatico**: i metodi fanno una richiesta e lasciano salire le
  eccezioni del transport; la CLI non riprova su `409` (02-C05, 02-C10, 02-C13).
- **Token e segreti mai nei log**: nessun log nuovo; i corpi delle scritture passano dall'audit log
  solo con `audit_log_bodies`, già redatti dal transport.
- **Dati personali**: i corpi contengono titolo, descrizione e id di persone; non si salvano. Le
  fixture usano valori finti (`"title": "Prepare the quarterly report"`, id piccoli). L'integration
  test usa `PYNTERACTA_TEST_WRITE_POST_ID`, mai `PYNTERACTA_TEST_POST_ID`, e `client_uid =
  f"pynteracta-it-{int(time.time())}"`.
- **Conferma delle operazioni distruttive**: `confirm_destructive` non ha una via che elimini senza
  `y` o `--yes` (02-C11, 02-C12).
- **Soglie che non scendono**: i file nuovi e toccati hanno test per ogni ramo; copertura ≥ 85 %
  per file e totale ≥ 93,18 %.

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `cli/_common.py::error_exit_code` | la mappa attuale: Auth → 3, Permission → 4, NotFound → 5, Validation → 6, Transport → 7, Server → 8, altro → 1 | `tests/unit/test_cli_common.py::test_error_exit_code_existing_mapping`, verde prima di aggiungere `ConcurrencyError` |
| `api/_base.py::ResourceClient._post` | corpo JSON inviato e risposta non-dict → `TypeError` | già fissato indirettamente dai test delle API (`test_api_posts.py`); non si modifica, si aggiungono metodi: nessun test nuovo |
| `facade/tasks.py::Task` | campi esposti e rivalidazione degli stub | già fissato da `test_api_tasks.py::TestTasksGet` e dal contract smoke: nessun test nuovo |
| `cli/tasks.py::tasks get` | tabella e JSON | già fissato dagli snapshot syrupy: nessun test nuovo |

## Strategia di test

Ordine: test prima del codice, rossi per il motivo giusto (metodo o comando inesistente, campo
mancante), poi il codice. Ogni test porta `# criterio: 02-Cmm`. Le fixture nuove si scrivono con
il test che le usa.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 02-C01 | `test_api_tasks.py::TestTasksCreate::test_create_sends_only_given_fields_and_wraps_response`: route `respx.post` sul percorso, `route.calls[0].request.content` == JSON atteso, `route.call_count == 1`, risultato da `create_task_response.json` (`task_id`, `next_occ_token`, `task.title`, `capabilities.can_modify`, `.raw`) | unitario |
| 02-C02 | `::test_create_raw_equivalent` con `CreateTaskRequestDTO(title="T")` | unitario |
| 02-C03 | `test_api_utils.py::test_zoned_datetime_input_*` (ZoneInfo Europe/Rome, ZoneInfo UTC, offset fisso → UTC, naive → `ValueError`); `test_api_tasks.py::test_create_naive_expiration_raises_before_request` (`route.call_count == 0`) e `::test_edit_naive_expiration_raises_before_request` | unitario |
| 02-C04 | `::TestTasksEdit::test_edit_sends_only_given_fields` (PUT su `…/7001/3`, corpo atteso, `next_occ_token` e `task` da `edit_task_response.json`); `::test_edit_raw_equivalent` | unitario |
| 02-C05 | `::test_edit_409_raises_concurrency_error_once`: `respx.put(...).mock(return_value=Response(409, json={...}))`, `pytest.raises(ConcurrencyError)`, `exc.status_code == 409`, `route.call_count == 1` | unitario |
| 02-C06 | `::TestTasksDelete::test_delete_returns_post_id`: DELETE, `delete_task_response.json`, `route.call_count == 1` | unitario |
| 02-C07 | `::TestTasksGet::test_occ_token_exposed` sulla fixture con `occToken: 5` | unitario |
| 02-C08 | `test_cli_tasks.py::TestTasksCreate::test_flags_and_json_merge_flags_win` (file `body.json` in `tmp_path`, corpo della POST uguale al dict atteso), `::test_table_output` (snapshot), `::test_json_output` (snapshot) | unitario |
| 02-C09 | `::TestTasksEdit::test_edit_reads_occ_token_then_puts` (route GET + PUT; `put_route.calls[0].request.url.path` termina con `/7001/5`); `::test_edit_with_occ_token_skips_get` (`get_route.call_count == 0`, path termina con `/7001/3`) | unitario |
| 02-C10 | `::test_edit_conflict_exits_9_without_retry`: PUT → 409, `exit_code == 9`, messaggio della spec in `result.output`, `put_route.call_count == 1` | unitario |
| 02-C11 | `::TestTasksDelete::test_prompt_shows_id_and_title_and_y_deletes` (monkeypatch `_stdin_is_interactive` → True, `input="y\n"`, DELETE chiamata, output `Task 7001 deleted (post 21269)`), `::test_prompt_n_does_nothing` (`input="n\n"`, `delete_route.call_count == 0`, `exit_code == 0`) | unitario |
| 02-C12 | `::test_yes_skips_prompt` (nessun monkeypatch, `--yes`, DELETE chiamata, nessun `?` nell'output); `::test_non_interactive_without_yes_refuses` (`exit_code == 2`, messaggio `--yes is required…`, `delete_route.call_count == 0`); più `test_cli_common.py::test_confirm_destructive_*` per i tre rami dell'helper | unitario |
| 02-C13 | `test_api_tasks.py::test_create_timeout_raises_transport_error_once`: `respx.post(...).mock(side_effect=httpx.ReadTimeout(...))`, `pytest.raises(TransportError)`, `route.call_count == 1` | unitario |
| 02-C14 | `tests/contract/test_models.py::TestTaskWriteDTOs`: `assert_superset` per i 7 modelli; `test_facade_smoke_create`/`_edit` sulle fixture | contract |
| 02-C15 | `test_docs_snippets.py::test_tasks_pages_document_write_commands` (marker 02-C15: `docs/cli.md` contiene `tasks create`, `tasks edit`, `tasks delete`, `--json`, `| 9 |`; `docs/api/tasks.md` contiene `create(`, `edit(`, `delete(`, `TaskWriteResult`, `occ_token`); `uv run mkdocs build --strict` nei controlli di verifica | unitario + verifica |
| 02-C16 | `test_tasks_integration.py::TestTasksWriteIntegration::test_create_edit_delete_cycle`: skip senza `PYNTERACTA_TEST_WRITE_POST_ID`; `create` con titolo, `client_uid`, `expiration` → `get` → `edit` (titolo nuovo) → asserzioni sul round trip → `delete` in `finally`; dopo il delete `get` → `NotFoundError` | integrazione (opt-in) + verifica manuale |

Verifica manuale (dalla spec): l'esito di 02-C16 sul tenant di prova stabilisce il formato reale di
`expiration` e la semantica dei campi omessi; si registra in `docs/api/tasks.md` e in `verifica.md`.
Se il server rifiuta il formato della scadenza previsto da 02-C03, la correzione passa da una
modifica della spec (criterio 02-C03), non da un aggiustamento silenzioso.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| `_put`/`_delete` in `ResourceClient` sul modello di `_post` | chiamare `self._transport.request` direttamente in `TasksAPI` | Stessa forma delle letture, riuso dalle prossime spec di scrittura |
| Corpo dai kwargs con `build_write_body` (camelCase, solo non-`None`) in `_utils.py` | costruire il DTO dai kwargs e dumparlo | Un solo helper per tutte le scritture future; nessuna chiave in più (02-C01) |
| `zoned_datetime_input` in `_utils.py`, usata da libreria e CLI; offset fisso → UTC | `tzname()` grezzo; `ValueError` sugli offset | Decisione del maintainer: istante preservato, nome IANA sempre valido |
| `TaskWriteResult` unico per `create` ed `edit`, con `from_create`/`from_edit` | due façade | Stessi campi utili (`next_occ_token`, `task`, `capabilities`); `task_id` dal DTO di create o da `task.id` |
| La CLI passa sempre da `*_raw` dopo l'unione di flag e `--json` | `create(**kwargs)` quando non c'è `--json` | Un solo percorso, l'unione "flag prevalgono" si testa una volta (02-C08) |
| Chiavi sconosciute in `--json` rilevate con `set(data) - set(dto_cls.model_fields)` | `model_config.extra = "forbid"` | I modelli generati non si modificano a mano |
| `confirm_destructive` + `_stdin_is_interactive` in `_common.py` | `typer.confirm` nudo | Messaggio della spec senza TTY; riuso; sostituibile nei test |
| Exit code degli errori d'uso = `EXIT_CONFIG` (2) | `6` | Coerenza con la CLI (`validate_full_fields`); spec corretta con l'approvazione del maintainer |
| Messaggio del 409 in `handle_error` (ramo `ConcurrencyError`) | messaggio nel comando | Vale per tutte le scritture future |
| `tasks delete` stampa testo o JSON senza `render_output` | `render_output` con una façade ad hoc | Non c'è un elenco di record da mostrare; `--output json` resta onorato |
| Integration test nello stesso file dei task, con `finally` | file separato; nessuna pulizia | Convenzione del progetto (un file per risorsa, fixture `client` locale) |
| Commit `feat(tasks):` per libreria e `feat(cli):` per i comandi | `feat:` unico | Scope come nella storia del progetto; semantic-release calcola 0.10.0 |

## Rischi

- **Formato della scadenza rifiutato dal server** → l'integration test lo scopre; se il server
  vuole un altro formato si corregge 02-C03 nella spec e `zoned_datetime_input`, non il test.
- **Campi omessi azzerati dal server** → l'integration test lo scopre; la documentazione lo dice
  come avviso; nessuna modifica alla libreria (decisione della spec).
- **`taskData` come stub `RootModel`** → rivalidazione in `TaskDetailDTO1` come per le capabilities;
  se `TaskDetailDTO1` non copre tutte le proprietà, il contract test lo mostra (02-C14).
- **`CliRunner` e stdin** → il prompt si testa sostituendo `_stdin_is_interactive`, mai leggendo
  `sys.stdin.isatty()` direttamente nel comando.
- **Snapshot syrupy nuovi** → generati con `--snapshot-update` al primo run del test, poi letti e
  controllati a mano prima del commit (contenuto della tabella, non solo esistenza).
- **Unione flag/`--json`** → un solo punto (`_merge_body`) con test dedicato (02-C08); nessuna
  unione profonda: un flag sostituisce la chiave intera.
- **Copertura di `cli/tasks.py`** → i rami di errore (`--json` non valido, chiavi sconosciute,
  timezone non valida, `occ_token` assente) hanno ciascuno un test in `test_cli_tasks.py` o
  `test_cli_common.py`.
