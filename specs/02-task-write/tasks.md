# Task 02 – Scrittura dei task: creazione, modifica, eliminazione

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (metodo o comando inesistente, campo mancante); poi il codice; il commit
arriva con i cinque controlli bloccanti verdi. Ogni test porta `# criterio: 02-Cmm` sulla riga sopra.
Messaggi di commit in Conventional Commits con descrizione in italiano: `feat(api)`, `feat(tasks)`,
`feat(cli)`, `test`, `docs`. Gli snapshot syrupy nuovi si generano con `--snapshot-update` e si
leggono prima del commit.

## Elenco

### [x] T01 – Utilità di scrittura: scadenza, corpo, `_put` e `_delete`

- Criteri: 02-C03 (helper)
- Dipende da: nessuno
- Test: `tests/unit/test_api_utils.py` (nuovo) — `test_zoned_datetime_input_zoneinfo`
  (`Europe/Rome` → `{"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"}`),
  `test_zoned_datetime_input_utc_zoneinfo`, `test_zoned_datetime_input_fixed_offset_converts_to_utc`
  (`+01:00` 18:00 → `17:00:00`, `"UTC"`), `test_zoned_datetime_input_naive_raises`,
  `test_build_write_body_camel_case_skips_none`, `test_build_write_body_dumps_models_in_lists`.
  `_put`/`_delete` di `ResourceClient` si dimostrano con i test di T03 e T04 (percorso e metodo HTTP).
- Passi:
  1. Scrivere i test; eseguirli: rossi per `ImportError`.
  2. In `api/_utils.py`: `zoned_datetime_input(dt)` e `build_write_body(**kwargs)` come da piano.
  3. In `api/_base.py`: `_put` e `_delete` sul modello di `_post`.
  4. Controlli bloccanti; commit `feat(api): utilità per le scritture (scadenza con fuso, corpo
     camelCase, PUT e DELETE nel client base)`.

### [x] T02 – Façade: `Task.occ_token`, `TaskWriteResult`, fixture e contract test

- Criteri: 02-C07, 02-C14
- Dipende da: nessuno
- Test: `tests/unit/test_api_tasks.py::TestTasksGet::test_occ_token_exposed` (valore `occToken`
  della fixture); `tests/contract/test_models.py::TestTaskWriteDTOs` — `assert_superset` per
  `CreateTaskRequestDTO`, `CreateTaskResponseDTO`, `EditTaskRequestDTO`, `EditTaskResponseDTO`,
  `DeleteTaskResponseDTO`, `ZonedDatetimeInputDTO` (→ `ZonedDatetimeInputDTO1`), `TaskDetailDTO`
  (→ `TaskDetailDTO1`); `test_facade_smoke_create` e `test_facade_smoke_edit` su
  `create_task_response.json` / `edit_task_response.json` (`task_id`, `next_occ_token`,
  `task.title`, `capabilities.can_modify`).
- Passi:
  1. Scrivere le tre fixture `tests/fixtures/payloads/create_task_response.json`,
     `edit_task_response.json`, `delete_task_response.json` (dati finti, `taskData` completo,
     `nextOccToken`, `capabilities`).
  2. Scrivere i test; eseguirli: rossi (`occ_token` e `TaskWriteResult` inesistenti); i contract
     `assert_superset` sui DTO generati sono verdi già oggi (caratterizzano i modelli).
  3. In `models/facade/tasks.py`: proprietà `occ_token` su `Task`; classe `TaskWriteResult` con
     `from_create`/`from_edit`, rivalidazione di `taskData` in `TaskDetailDTO1` e delle capabilities.
  4. Controlli bloccanti (anche `uv run pytest -m contract`); commit `feat(tasks): occ_token nella
     lettura e façade TaskWriteResult per le risposte di scrittura`.

### [x] T03 – `TasksAPI.create` e `create_raw`

- Criteri: 02-C01, 02-C02, 02-C03 (richiesta), 02-C13
- Dipende da: T01, T02
- Test: `tests/unit/test_api_tasks.py::TestTasksCreate` —
  `test_create_sends_only_given_fields_and_wraps_response` (POST su
  `communication/tasks/manage/create-task/42`, `json.loads(route.calls[0].request.content)` ==
  `{"title": "T", "priority": 2, "watcherUserIds": [7]}`, `route.call_count == 1`, risultato
  dalla fixture), `test_create_raw_equivalent`, `test_create_expiration_zoneinfo_in_body`,
  `test_create_naive_expiration_raises_before_request` (`route.call_count == 0`),
  `test_create_timeout_raises_transport_error_once` (`side_effect=httpx.ReadTimeout`,
  `TransportError`, `route.call_count == 1`).
- Passi:
  1. Scrivere i test; eseguirli: rossi (`create` inesistente).
  2. In `api/tasks.py`: costante del percorso; `create(post_id, *, …)` con `build_write_body` e
     `zoned_datetime_input`; `create_raw(post_id, req)` con `model_dump(mode="json",
     exclude_none=True)`; ritorno `TaskWriteResult.from_create`.
  3. Controlli bloccanti; commit `feat(tasks): creazione di un task su un post (create, create_raw)`.

### [x] T04 – `TasksAPI.edit`, `edit_raw` e `delete`

- Criteri: 02-C03 (edit), 02-C04, 02-C05, 02-C06
- Dipende da: T03
- Test: `tests/unit/test_api_tasks.py::TestTasksEdit` — `test_edit_sends_only_given_fields` (PUT su
  `…/edit-task/7001/3`, corpo `{"title": "T2", "removeWatcherUserIds": [7]}`, `next_occ_token` e
  `task` dalla fixture), `test_edit_raw_equivalent`, `test_edit_naive_expiration_raises_before_request`,
  `test_edit_409_raises_concurrency_error_once` (`status_code == 409`, `call_count == 1`);
  `::TestTasksDelete::test_delete_returns_post_id` (DELETE su `…/delete-task/7001`, `post_id` dalla
  fixture, `call_count == 1`).
- Passi:
  1. Scrivere i test; eseguirli: rossi (`edit`/`delete` inesistenti).
  2. In `api/tasks.py`: `edit(task_id, occ_token, *, …)`, `edit_raw`, `delete` (ritorna `postId` di
     `DeleteTaskResponseDTO`).
  3. Controlli bloccanti; commit `feat(tasks): modifica con occToken ed eliminazione di un task
     (edit, edit_raw, delete)`.

### [x] T05 – Helper CLI: exit code 9, conferma delle operazioni distruttive, corpo da `--json`

- Criteri: 02-C10 (exit code e messaggio), 02-C12 (helper)
- Dipende da: nessuno
- Test: `tests/unit/test_cli_common.py` (nuovo) — **caratterizzazione prima**:
  `test_error_exit_code_existing_mapping` (Auth 3, Permission 4, NotFound 5, Validation 6,
  Transport 7, Server 8, `InteractaError` generico 1), verde sul codice attuale; poi
  `test_error_exit_code_concurrency_is_9`, `test_handle_error_concurrency_message`,
  `test_confirm_destructive_yes_skips_prompt`, `test_confirm_destructive_interactive_y_and_n`
  (monkeypatch `_stdin_is_interactive` → True, `typer.confirm` sostituito o `CliRunner` con
  `input`), `test_confirm_destructive_non_interactive_exits_2_with_message`,
  `test_load_json_body_from_file_and_stdin`, `test_load_json_body_invalid_json_exits_2`,
  `test_load_json_body_unknown_keys_exits_2`.
- Passi:
  1. Scrivere e vedere verde il test di caratterizzazione; scrivere gli altri test: rossi.
  2. In `cli/_common.py`: `EXIT_CONFLICT = 9`; `ConcurrencyError` in `_EXIT_MAP`; ramo
     `ConcurrencyError` in `handle_error` con il messaggio `… changed since it was read: fetch it
     again and retry`; `_stdin_is_interactive()`; `confirm_destructive(prompt, *, yes)`;
     `load_json_body(source, dto_cls)`.
  3. Controlli bloccanti; commit `feat(cli): exit code 9 per i conflitti, conferma delle operazioni
     distruttive e corpo da --json`.

### [x] T06 – Comando `tasks create`

- Criteri: 02-C08
- Dipende da: T03, T05
- Test: `tests/unit/test_cli_tasks.py::TestTasksCreate` — `test_flags_and_json_merge_flags_win`
  (`body.json` in `tmp_path` con `{"title": "X", "assigneeUserId": 9}`, flag `--title T --priority 2
  --watcher-user 7 --watcher-user 8`, corpo della POST == `{"title": "T", "priority": 2,
  "watcherUserIds": [7, 8], "assigneeUserId": 9}`), `test_expiration_flag_default_timezone`
  (`--expiration 2026-12-31T18:00` → `Europe/Rome`), `test_expiration_with_offset_ignores_timezone`,
  `test_invalid_timezone_exits_2` (nessuna POST), `test_json_unknown_key_exits_2` (nessuna POST),
  `test_table_output` e `test_json_output` (snapshot), `test_help_lists_options`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (comando inesistente).
  2. In `cli/tasks.py`: opzioni condivise, `_parse_expiration`, `_merge_body`, comando `create`
     via `create_raw`, tabella curata (id, post_id, title, state, priority, expiration, assignee),
     `render_output` con `single_command=True`.
  3. Generare e leggere gli snapshot; controlli bloccanti; commit `feat(cli): comando tasks create
     con flag e --json`.

### [x] T07 – Comando `tasks edit`

- Criteri: 02-C09, 02-C10
- Dipende da: T04, T06
- Test: `tests/unit/test_cli_tasks.py::TestTasksEdit` — `test_edit_reads_occ_token_then_puts`
  (route GET + PUT; la PUT finisce con `/7001/<occToken della fixture>`; `get_route.call_count ==
  1`), `test_edit_with_occ_token_skips_get` (`get_route.call_count == 0`, PUT su `/7001/3`),
  `test_edit_conflict_exits_9_without_retry` (`exit_code == 9`, messaggio della spec,
  `put_route.call_count == 1`), `test_edit_task_without_occ_token_exits_1` (fixture senza
  `occToken` → messaggio, nessuna PUT), `test_edit_json_output` (snapshot).
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. In `cli/tasks.py`: comando `edit` (GET implicita salvo `--occ-token`, `edit_raw`, stesse
     opzioni e tabella di `create`).
  3. Snapshot, controlli bloccanti; commit `feat(cli): comando tasks edit con occToken letto o
     imposto`.

### [x] T08 – Comando `tasks delete`

- Criteri: 02-C11, 02-C12
- Dipende da: T04, T05
- Test: `tests/unit/test_cli_tasks.py::TestTasksDelete` —
  `test_prompt_shows_id_and_title_and_y_deletes` (monkeypatch `_stdin_is_interactive` → True,
  `input="y\n"`, prompt con `7001` e il titolo della fixture, DELETE chiamata, output `Task 7001
  deleted (post 21269)`), `test_prompt_n_does_nothing` (`delete_route.call_count == 0`,
  `exit_code == 0`), `test_yes_skips_prompt` (nessun `?` nell'output, DELETE chiamata),
  `test_non_interactive_without_yes_refuses` (`exit_code == 2`, messaggio, nessuna DELETE),
  `test_json_output` (`{"task_id": 7001, "post_id": 21269}`).
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. In `cli/tasks.py`: comando `delete` (GET, `confirm_destructive`, `delete`, testo o JSON).
  3. Controlli bloccanti; commit `feat(cli): comando tasks delete con conferma e --yes`.

### [ ] T09 – Documentazione: pagine API e CLI, testing, `.env.example`

- Criteri: 02-C15
- Dipende da: T08
- Test: `tests/unit/test_docs_snippets.py::test_tasks_pages_document_write_commands` (marker
  02-C15: `docs/cli.md` contiene `tasks create`, `tasks edit`, `tasks delete`, `--json` e la riga
  dell'exit code `9`; `docs/api/tasks.md` contiene `create(`, `edit(`, `delete(`, `TaskWriteResult`,
  `occ_token`); rosso prima della modifica delle pagine; più `uv run mkdocs build --strict`.
- Passi:
  1. Scrivere il test; eseguirlo: rosso.
  2. `docs/api/tasks.md`: sezione "Writing tasks" (tre metodi, `TaskWriteResult`, `occ_token`,
     scadenza e fusi, campi omessi "to be confirmed against the tenant, see T11"), snippet Python
     coerenti con l'API (li controlla `test_docs_snippets`).
  3. `docs/cli.md`: i tre comandi con esempi, `--json`, prompt e `--yes`, riga `9` nella tabella
     degli exit code; `docs/testing.md` e `tests/integration/.env.example`:
     `PYNTERACTA_TEST_WRITE_POST_ID`.
  4. `uv run mkdocs build --strict`, controlli bloccanti; commit `docs: scrittura dei task nelle
     pagine API e CLI, exit code 9, variabile per gli integration test`.

### [ ] T10 – Integration test del ciclo `create → edit → delete`

- Criteri: 02-C16 (codice)
- Dipende da: T04
- Test: `tests/integration/test_tasks_integration.py::TestTasksWriteIntegration::test_create_edit_delete_cycle`
  — skip senza `PYNTERACTA_TEST_WRITE_POST_ID`; `create` con titolo, `client_uid =
  f"pynteracta-it-{int(time.time())}"`, `expiration` in `Europe/Rome`, `priority`; `get` →
  `occ_token`; `edit` con titolo nuovo e senza gli altri campi; asserzioni sul round trip (titolo,
  scadenza, e i campi non passati all'edit, registrati con `print` per T11); `delete` in `finally`;
  dopo il delete `get` → `NotFoundError`. Si verifica che il test sia **saltato** senza la
  variabile (`uv run pytest -m integration -k cycle`) e che sia raccolto.
- Passi:
  1. Scrivere il test; `uv run pytest tests/integration/test_tasks_integration.py -m integration
     -q` → `skipped`.
  2. Controlli bloccanti (il test non entra nella suite unit); commit `test: integration test
     opt-in del ciclo di scrittura dei task`.

### [ ] T11 – Esecuzione dell'integration test sul tenant di prova (manuale)

- Criteri: 02-C16 (esecuzione), verifica manuale della spec
- Chi: maintainer
- Cosa fare: in `tests/integration/.env` impostare `PYNTERACTA_TEST_WRITE_POST_ID` con l'id di un
  post di una community **di prova**; esportare le variabili (`export $(grep -v '^#'
  tests/integration/.env | xargs)`); eseguire `uv run pytest tests/integration/test_tasks_integration.py
  -m integration -k cycle -v -s`; annotare qui: (a) se il server ha accettato `expiration` nel
  formato `{"datetime": "YYYY-MM-DDTHH:MM:SS", "timezone": "Europe/Rome"}` e come l'ha restituita;
  (b) se dopo l'`edit` con il solo titolo gli altri campi (priority, expiration, watcher) sono
  rimasti invariati o azzerati; (c) eventuali errori. Se il formato della scadenza è rifiutato,
  fermarsi: si corregge la spec (02-C03) prima di T12.
- Esito: <compilato a mano>

### [ ] T12 – Chiusura: PRD, `CLAUDE.md`, nota sui campi omessi

- Criteri: nessuno nuovo (chiusura: "Requisiti nuovi", conferme, esito di T11)
- Dipende da: T09, T11
- Test: nessuno; verifica con la rilettura dei diff, il controllo che ogni link risolva e
  `uv run mkdocs build --strict`.
- Passi:
  1. `specs/prd.md`: RF-022a, RF-015a, RF-025a, RNF-010 dalla sezione "Requisiti nuovi" della
     spec; conferma del maintainer (2026-10-08, spec 02) accanto a RF-022, RF-025, RNF-009 e alla
     voce "Dati scritti sul tenant" di §6; riga nella storia.
  2. `CLAUDE.md`, sezione "Lingua": una riga — l'interfaccia utente della CLI (help, prompt,
     messaggi) resta in inglese per coerenza con la CLI e il sito esistenti (spec 02).
  3. `docs/api/tasks.md`: sostituire "to be confirmed" con l'esito di T11 (formato della scadenza
     accettato; campi omessi invariati o azzerati, come avviso se azzerati).
  4. Commit `docs: PRD e CLAUDE.md per la spec 02, esito dell'integration test nella pagina API`.

La riga `0.10.0 ⏳ M27–M28` in `ROADMAP.md` è già stata scritta con la spec; la sezione M28 in
`PROGRESS.md` la scrive `/sddpa:verifica`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 02-C01 | T03 |
| 02-C02 | T03 |
| 02-C03 | T01, T03, T04 |
| 02-C04 | T04 |
| 02-C05 | T04 |
| 02-C06 | T04 |
| 02-C07 | T02 |
| 02-C08 | T06 |
| 02-C09 | T07 |
| 02-C10 | T05, T07 |
| 02-C11 | T08 |
| 02-C12 | T05, T08 |
| 02-C13 | T03 |
| 02-C14 | T02 |
| 02-C15 | T09 |
| 02-C16 | T10, T11 (manuale) |
