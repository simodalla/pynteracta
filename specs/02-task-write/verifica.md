# Verifica 02 – Scrittura dei task: creazione, modifica, eliminazione

Data: 2026-10-08
Commit verificato: `d38f386` sul branch `m28_task_write` (spec `77069ef`, piano `4270fb3`, task
`61f4f62`; T01–T10: `33916e0`, `ce6b104`, `a546ff8`, `48d3ffb`, `9a80a74`, `dbdeb76`, `3fc3e28`,
`b746cda`, `2a511c4`, `0b19378`; revisione dopo T11: `7ebc649`; T13: `69b1f5b`; T12: `d38f386`)
Esito: **un problema** (copertura di `src/pynteracta/api/_base.py` sotto soglia). Spec non chiusa.

## Task

13 su 13 spuntati, compreso T11 (`manuale`) con l'esito compilato: scadenza accettata nel formato
della spec; `edit` è una sostituzione (campi omessi azzerati); assegnatario e scadenza obbligatori
sul tenant; `state` dei sub-task obbligatorio e `0` rifiutato. Da T11 è nata la revisione della spec
(02-C09 sostituito da 02-C17 e 02-C18, task T13).

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 02-C01 | `tests/unit/test_api_tasks.py::TestTasksCreate::test_create_sends_only_given_fields_and_wraps_response`; `tests/unit/test_api_utils.py::TestBuildWriteBody` (3 test) | verde |
| 02-C02 | `test_api_tasks.py::TestTasksCreate::test_create_raw_equivalent` | verde |
| 02-C03 | `test_api_utils.py::TestZonedDatetimeInput` (5 test); `test_api_tasks.py::TestTasksCreate::test_create_expiration_zoneinfo_in_body`, `::test_create_naive_expiration_raises_before_request`; `::TestTasksEdit::test_edit_naive_expiration_raises_before_request` | verde |
| 02-C04 | `test_api_tasks.py::TestTasksEdit::test_edit_sends_only_given_fields`, `::test_edit_raw_equivalent`, `::test_edit_without_fields_sends_empty_body` | verde |
| 02-C05 | `test_api_tasks.py::TestTasksEdit::test_edit_409_raises_concurrency_error_once` | verde |
| 02-C06 | `test_api_tasks.py::TestTasksDelete::test_delete_returns_post_id`, `::test_delete_without_body_returns_none` | verde |
| 02-C07 | `test_api_tasks.py::TestTasksGet::test_occ_token_exposed` | verde |
| 02-C08 | `tests/unit/test_cli_tasks.py::TestTasksCreate` (12 test: unione flag/`--json`, scadenza e fuso, errori d'uso, stdin, snapshot tabella e JSON, help); `tests/unit/test_cli_common.py::TestLoadJsonBody` (6 test) | verde |
| 02-C09 | sostituito da 02-C17 il 2026-10-08: nessun marker, come atteso | — |
| 02-C10 | `test_cli_tasks.py::TestTasksEdit::test_edit_conflict_exits_9_without_retry`; `test_cli_common.py::TestExitMap::test_concurrency_is_9`, `::test_handle_error_concurrency_message` | verde |
| 02-C11 | `test_cli_tasks.py::TestTasksDelete::test_prompt_shows_id_and_title_and_y_deletes`, `::test_prompt_n_does_nothing`, `::test_json_output`, `::test_not_found_exits_5_without_delete`; `test_cli_common.py::TestConfirmDestructive::test_interactive_prompt_returns_answer` | verde |
| 02-C12 | `test_cli_tasks.py::TestTasksDelete::test_yes_skips_prompt`, `::test_short_yes_flag`, `::test_non_interactive_without_yes_refuses`; `test_cli_common.py::TestConfirmDestructive::test_yes_skips_prompt`, `::test_non_interactive_without_yes_exits_2_with_message` | verde |
| 02-C13 | `test_api_tasks.py::TestTasksCreate::test_create_timeout_raises_transport_error_once` | verde |
| 02-C14 | `tests/contract/test_models.py::TestTaskWriteDTOs` (superset dei 7 modelli, `test_facade_smoke_create`, `test_facade_smoke_edit`, `test_delete_response_fixture_parses`) | verde |
| 02-C15 | `tests/unit/test_docs_snippets.py::test_tasks_pages_document_write_commands`; `uv run mkdocs build --strict` | verde |
| 02-C16 | `tests/integration/test_tasks_integration.py::TestTasksWriteIntegration::test_create_edit_delete_cycle` — eseguito sul tenant di prova il 2026-10-08 (T11): **passato** (task 2815 creato, modificato, eliminato, `404` dopo); saltato senza le variabili | verde (manuale) |
| 02-C17 | `test_cli_tasks.py::TestTasksEdit::test_edit_base_from_fixture`, `::test_edit_reads_task_then_puts_patched_body`, `::test_edit_with_occ_token_still_reads_base`, `::test_edit_watcher_flags_map_to_add_and_remove`, `::test_edit_task_without_occ_token_exits_1`, `::test_edit_json_output` | verde |
| 02-C18 | `test_cli_tasks.py::TestTasksEdit::test_edit_description_flag_drops_delta`, `::test_edit_flags_win_over_json_over_read`, `::test_edit_base_skips_missing_fields` | verde |

Ogni test è stato visto rosso prima del codice (per `ImportError`, `AttributeError`, comando o
opzione inesistente, corpo diverso). Nessun marker cita criteri inesistenti; i test preesistenti
senza marker e il test di caratterizzazione della mappa degli exit code non sono un problema.

## Controlli automatici

| Controllo | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (105 file) |
| `uv run mypy src` | verde (52 file) |
| `uv run pytest -m "not integration and not contract"` | verde: 822 test (+71 rispetto alla partenza), 70 snapshot |
| `uv run pytest -m contract` | verde (97, +10) |
| `uv run mkdocs build --strict` (aggiuntivo) | verde |
| `uv run pre-commit run --all-files` (aggiuntivo) | verde: tutti e 7 gli hook passano (il debito della verifica 01 è stato chiuso dal branch `bugfix_precommit_hooks`) |

Controlli a cricchetto: nessuno configurato.

## Copertura

Comando: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`.

| Ambito | Copertura | Soglia | Esito |
|---|---|---|---|
| Totale | **93,48 %** (4112/4399 righe) | ≥ 85 % e ≥ 93,18 % (partenza) | ok |
| `src/pynteracta/api/_base.py` (toccato) | **77,78 %** (28/36) | ≥ 85 % | **sotto soglia** |
| `src/pynteracta/api/_utils.py` (toccato) | 98,25 % (56/57) | ≥ 85 % | ok |
| `src/pynteracta/api/tasks.py` (toccato) | 100 % (36/36) | ≥ 85 % | ok |
| `src/pynteracta/models/facade/tasks.py` (toccato) | 98,30 % (173/176) | ≥ 85 % | ok |
| `src/pynteracta/cli/_common.py` (toccato) | 92,62 % (301/325) | ≥ 85 % | ok |
| `src/pynteracta/cli/tasks.py` (toccato) | 96,10 % (148/154) | ≥ 85 % | ok |

Righe scoperte di `api/_base.py`: 21–22, 35–36, 49–50, 60–61, cioè i quattro rami `TypeError`
"risposta non oggetto JSON" di `_get`, `_post`, `_put`, `_delete`. I primi due sono preesistenti e
senza test; la spec ha aggiunto `_put` e `_delete` sullo stesso modello, con lo stesso ramo non
testato: il file resta al 78 % e il piano lo dava per "già fissato indirettamente", a torto.
Scoperte altrove (non bloccanti): `cli/tasks.py` 148–150 (ramo `pydantic.ValidationError` di
`_validate_body`), 272, 443, 462; `facade/tasks.py` 163, 196, 219 (rami `None` degli stub).

## Regole non negoziabili

| Regola | Controllo | Esito |
|---|---|---|
| Token e segreti mai nei log | Il diff di `src/` non aggiunge chiamate ai logger né `print`; l'unica stampa nuova è `console.print("Task … deleted (post …)")` con soli id. I corpi delle scritture passano dal transport, che li redige prima di log, audit e hook (non modificato). | rispettata |
| Cache del token con permessi stretti | Codice non toccato. | n/a |
| Segreti fuori dal repository | Fixture con dati finti (`Alice Rossi`, id piccoli, `occToken: 3`); `tests/integration/.env.example` ha solo nomi di variabili; nessun `.env`, `.secrets`, `audit.log` aggiunto. Le prove T11 sono state eseguite con le variabili caricate nella shell, senza leggerle né copiarle. | rispettata |
| Soglie che non scendono | Controlli e regole di ruff/mypy invariati; copertura totale salita. La soglia per file toccati **non è rispettata** da `api/_base.py` (sopra): la spec non si chiude finché non lo è. | **da sistemare** |
| Dati personali fuori dai log, con eccezione audit | Titolo, descrizione e id di persone viaggiano nei corpi delle richieste e non vengono loggati; l'integration test usa un post di prova e un `client_uid` riconoscibile. L'output di `tasks create|edit` mostra il nome dell'assegnatario, come già `tasks get`: è output per l'operatore, non log. | rispettata |
| Nessuna operazione ripetuta in automatico verso Interacta | `create`, `edit`, `delete` fanno una richiesta ciascuno, senza `try/except`; `409` → `ConcurrencyError` senza rilettura (02-C05, 02-C10); timeout → `TransportError` con una sola richiesta (02-C13). `tasks edit` fa una `GET` di lettura più una `PUT`: la lettura non è una ripetizione. | rispettata |

## Coerenza con spec, piano e PRD

- Il codice fa ciò che la spec rivista descrive e niente di più: libreria con i soli campi passati e
  `occ_token` esplicito; CLI `tasks edit` come patch (base dal task letto < `--json` < flag, delta
  tolto con un testo semplice, `--occ-token` che impone solo il token); `tasks delete` con prompt,
  `--yes` e rifiuto senza TTY; exit code 9.
- Scostamenti dal piano, dichiarati: `_validate_body` di `tasks edit` gira dopo la `GET` (il corpo
  dipende dal task letto); le chiavi sconosciute di `--json` restano rifiutate prima di ogni
  richiesta da `load_json_body`.
- La revisione della spec dopo T11 (`7ebc649`) è dentro l'ambito della spec e non tocca il PRD né gli
  ADR oltre ai "Requisiti nuovi": nessun ADR necessario. RF-022a, RF-015a, RF-025a, RF-025b, RNF-010
  sono entrati nel PRD (`d38f386`); RF-022, RF-025, RNF-009 e §6 portano la conferma del maintainer.
- Voci aggiuntive della checklist: nessuna rigenerazione dei modelli (swagger pinnato invariato);
  `tasks create|edit` passano da `render_output` con snapshot; `docs/cli.md`, `docs/api/tasks.md`,
  `docs/testing.md` aggiornati; riga `0.10.0 ⏳` in `ROADMAP.md` dall'apertura; la sezione M28 di
  `PROGRESS.md` si scrive alla chiusura.

## Linea di partenza

Non aggiornata: si aggiorna alla verifica che chiude la spec.

## Debiti aperti

- Nessuna violazione `P-<mm>` aperta nella linea di partenza.
- `cli/communities.py` al 53 % di copertura (dalla partenza).

## Problemi trovati

1. **`src/pynteracta/api/_base.py` al 77,78 %, sotto la soglia dell'85 % per i file toccati.**
   Proposta: riaprire **T01** (che ha aggiunto `_put` e `_delete`) con un test di caratterizzazione
   `tests/unit/test_api_base.py::TestResourceClient` che, con `respx`, fa rispondere un array JSON a
   `GET`, `POST`, `PUT` e `DELETE` e attende `TypeError` con il messaggio `Expected JSON object
   response from <path>` (quattro test, marker 02-C01 per `_post` e 02-C04/02-C06 per `_put` e
   `_delete`; `_get` è caratterizzazione pura). Il file sale al 100 %. Poi `/sddpa:verifica 02` di
   nuovo.
