# Verifica 05 – Anagrafiche admin, prima metà: utenti e gruppi

Data: 2026-10-10
Commit verificato: `59c229e` sul branch `m31_admin_users_groups` (spec `41e3a33`, piano `a1ab8cc`,
task `f06764b`; T01–T14: `a7efe8a` … `fc7b835`; correzione della password generata `41dfd76`;
revisione della spec dopo T15 `37d0cc0`; T18 `3aebc6b`; T15 `4c075da`; T16 `768fe21`;
T17 `59c229e`)
Esito: **nessun problema**. Spec chiusa.

## Task

18 su 18 spuntati, compreso T15 (`manuale`) con l'esito compilato: eseguito da Claude su
richiesta del maintainer sul tenant di prova, con sonde aggiuntive su utenti e gruppi usa e getta
(tutti cancellati). La prima esecuzione ha mostrato tre divergenze dal swagger e dalla spec
(`generatedPassword` stringa, `edit-credentials` rifiutato con la patch, `204` vuoto per l'utente
inesistente): la spec è stata rivista con l'approvazione del maintainer (`37d0cc0`: criteri
05-C27, 05-C28, 05-C29, 05-C14 sostituito, task T18) e i cicli sono poi verdi.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 05-C01 | `test_api_users.py::TestUsersCreate::test_create_sends_only_given_fields_and_wraps_response`; `::test_create_raw_equivalent`; `::test_create_without_fields_sends_empty_body`; `test_facade_users.py::TestUserWriteResult::test_from_create_exposes_response_fields` (+1) | verde |
| 05-C02 | `test_api_users.py::TestUsersEdit::test_edit_sends_given_fields_and_occ_token`; `::test_edit_raw_equivalent`; `::test_edit_without_fields_sends_only_occ_token`; `test_facade_users.py::TestUserWriteResult::test_from_edit_uses_given_user_id` | verde |
| 05-C03 | `test_api_users.py::TestUsersDelete::test_delete_sends_one_request_and_returns_none`; `::test_delete_404_raises_not_found` | verde |
| 05-C04 | `test_api_users.py::TestUsersEditCredentials::test_edit_credentials_wraps_blocks_and_occ_token`; `::test_edit_credentials_raw_equivalent`; `test_facade_users.py::TestUserWriteResult::test_from_credentials_uses_given_user_id` | verde |
| 05-C05 | `test_api_groups.py::TestGroupsEdit::test_edit_409_raises_concurrency_error_once`; `test_api_users.py::TestUsersEdit::test_edit_409_raises_concurrency_error_once`; `test_api_users.py::TestUsersEditCredentials::test_edit_credentials_409_raises_concurrency_error_once` | verde |
| 05-C06 | `test_api_groups.py::TestGroupsGetForEdit::test_get_for_edit_exposes_occ_token`; `test_api_users.py::TestUsersEditCredentials::test_get_credentials_for_edit_is_alias`; `test_facade_admin_manage.py::TestUserCredentialsForEdit::test_occ_token_exposed`; `test_facade_groups.py::TestGroupForEdit::test_occ_token_exposed` (+1) | verde |
| 05-C07 | `test_api_groups.py::TestGroupsCreate::test_create_sends_only_given_fields_and_wraps_response`; `::test_create_raw_equivalent`; `test_facade_groups.py::TestGroupWriteResult::test_from_create_exposes_response_fields` | verde |
| 05-C08 | `test_api_groups.py::TestGroupsEdit::test_edit_sends_given_fields_and_occ_token`; `::test_edit_raw_equivalent`; `test_api_groups.py::TestGroupsDelete::test_delete_sends_one_request_and_returns_none`; `::test_delete_404_raises_not_found` (+1) | verde |
| 05-C09 | `test_api_groups.py::TestGroupsEditMembers::test_success_returns_group_with_next_occ_token`; `::test_only_given_keys_are_sent`; `::test_conflict_raises_concurrency_error`; `::test_missing_group_raises_interacta_error` (+1) | verde |
| 05-C10 | `test_api_groups.py::TestGroupsEditMembersBulk::test_returns_both_lists_without_raising`; `::test_bulk_raw_equivalent`; `::test_empty_list_is_sent_as_is`; `test_facade_groups.py::TestGroupSummary::test_from_stub_revalidates_group_dto` (+1) | verde |
| 05-C11 | `test_cli_users_write.py::TestUsersCreate::test_flags_and_json_merge_flags_win`; `::test_table_output_shows_generated_password`; `::test_json_output`; `::test_json_full_output_has_raw_list` (+3) | verde |
| 05-C12 | `test_cli_users_write.py::TestUsersCreate::test_password_stdin_non_interactive`; `::test_password_prompt_interactive`; `::test_generate_and_stdin_together_exit_2`; `::test_stdin_and_json_dash_exit_2` (+4, tra cui `test_cli_write.py::TestReadPassword`) | verde |
| 05-C13 | `test_cli_users_write.py::TestEditBase::test_edit_base_revalidates_blocks_and_drops_none`; `::test_edit_base_without_blocks`; `test_cli_users_write.py::TestUsersEdit::test_edit_reads_form_then_puts_patched_body`; `::test_json_then_flags_precedence` (+4) | verde |
| 05-C14 | *sostituito da 05-C28* (`37d0cc0`): la patch rimandava `username` e il server la rifiuta; i test della patch sono stati tolti con il codice (T18) | n/a |
| 05-C15 | `test_cli_groups_write.py::TestGroupsEdit::test_409_exits_9_without_retry`; `test_cli_users_write.py::TestUsersEdit::test_409_exits_9_without_retry`; `test_cli_users_write.py::TestUsersEditCredentials::test_409_exits_9_without_retry` | verde |
| 05-C16 | `test_cli_groups_write.py::TestGroupsDelete::test_prompt_shows_id_and_name_and_y_deletes`; `::test_prompt_n_does_nothing`; `::test_yes_skips_prompt`; `::test_json_output` (+7, tra cui `test_cli_users_write.py::TestUsersDelete`) | verde |
| 05-C17 | `test_cli_groups_write.py::TestGroupsCreate::test_flags_body_and_table`; `::test_json_and_flags_merge`; `::test_unknown_json_key_exits_2`; `test_cli_groups_write.py::TestGroupEditBase::test_group_edit_base_from_form` (+4) | verde |
| 05-C18 | `test_cli_groups_write.py::TestGroupsEditMembers::test_add_remove_reads_occ_token_then_puts`; `::test_occ_token_skips_get`; `::test_conflict_exits_9`; `::test_without_add_or_remove_exits_2` | verde |
| 05-C19 | `test_cli_groups_write.py::TestGroupsEditMembers::test_group_id_with_json_exits_2`; `::test_no_group_id_and_no_json_exits_2`; `test_cli_groups_write.py::TestGroupsEditMembersBulk::test_json_rows_and_exit_9_on_conflict`; `::test_all_success_exits_0` (+1) | verde |
| 05-C20 | `test_transport.py::test_password_keys_redacted_in_audit_and_hooks`; `test_facade_users.py::TestUserWriteResult::test_from_create_invalid_response_hides_values` | verde |
| 05-C21 | `test_api_groups.py::TestGroupsCreate::test_create_timeout_raises_transport_error_once`; `test_api_users.py::TestUsersCreate::test_create_timeout_raises_transport_error_once` | verde |
| 05-C22 | `test_models.py::TestAdminUsersWriteDTOs::test_schema_superset`; `::test_typed_stub_superset`; `::test_fixtures_parse`; `::test_facade_smoke` (+4 in `TestAdminGroupsWriteDTOs`) | verde |
| 05-C23 | `test_docs_snippets.py::test_users_groups_pages_document_write_commands` | verde, più `mkdocs build --strict` |
| 05-C24 | `test_groups_hashtags_integration.py::TestGroupsWriteIntegration::test_create_edit_members_delete_cycle` | verde sul tenant (T15); saltato senza variabili |
| 05-C25 | `test_users_integration.py::TestUsersWriteIntegration::test_create_edit_credentials_delete_cycle` | verde sul tenant (T15, dopo `41dfd76` e T18); saltato senza `PYNTERACTA_TEST_WRITE_USERS=1` |
| 05-C26 | esito di T15 in `tasks.md` e sezione «Campi omessi» della spec; `test_facade_users.py::TestUserWriteResult::test_from_create_normalizes_string_generated_password` fissa il formato della password | registrato (manuale) |
| 05-C27 | `test_api_base.py::TestResourceClientEmptyBodies::test_get_204_raises_not_found`; `test_cli_users.py::TestUsersGetForEdit::test_204_exits_5`; `test_cli_users_write.py::TestUsersEditCredentials::test_form_204_exits_5_without_put` | verde |
| 05-C28 | `test_cli_users_write.py::TestUsersEditCredentials::test_google_flag_and_no_custom_send_only_those_blocks`; `::test_username_sets_custom_active`; `::test_no_google_sends_enabled_false`; `::test_custom_inactive_and_no_microsoft` (+4) | verde |
| 05-C29 | `test_cli_users_write.py::TestUsersEditCredentialsConfirm::test_prompt_n_does_nothing`; `::test_prompt_y_sends_removal`; `::test_non_interactive_without_yes_refuses` | verde |

Ogni test è stato visto rosso prima del codice (classe, metodo, proprietà, comando od opzione
inesistenti, corpo diverso, valore non redatto), tranne: i contract test di `test_schema_superset`
(caratterizzano i modelli generati); i quattro casi di `test_conflicting_flags_exit_2` di T18,
che uscivano con `2` anche prima perché `--yes` non esisteva (il motivo giusto è dimostrato dal
messaggio `are mutually exclusive`, assente prima). Nessun marker cita criteri inesistenti. Il
commit di T02 è stato corretto con `--amend` prima di ogni push perché un pipe nascondeva un
test rosso; da lì ogni catena di controlli usa `set -o pipefail`.

## Controlli automatici

| Controllo | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (122 file) |
| `uv run mypy src` | verde (58 file) |
| `uv run pytest -m "not integration and not contract"` | verde: 1208 test (+118), 82 snapshot (+5) |
| `uv run pytest -m contract` | verde: 185 test (+24) |
| `uv run mkdocs build --strict` (aggiuntivo) | verde |
| `uv run pre-commit run --all-files` (aggiuntivo) | verde (7 hook) |
| `uv run pytest -m integration` senza ambiente | 26 saltati |
| `uv run pytest -m integration … -k Write` e `PYNTERACTA_TEST_WRITE_USERS=1 … test_users_integration.py` (T15, sul tenant) | verdi |

Controlli a cricchetto: nessuno configurato.

## Copertura

Comando: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`.

| Ambito | Copertura | Soglia | Esito |
|---|---|---|---|
| Totale | **94,94 %** (5531/5826 righe) | ≥ 85 % e ≥ 94,51 % (partenza) | ok |
| `api/_base.py` (toccato) | 100 % | ≥ 85 % | ok |
| `api/admin_manage.py` (docstring) | 100 % | ≥ 85 % | ok |
| `api/groups.py` (toccato) | 95,83 % | ≥ 85 % | ok |
| `api/users.py` (toccato) | 100 % | ≥ 85 % | ok |
| `cli/__init__.py` (toccato) | 89,47 % | ≥ 85 % | ok |
| `cli/_write.py` (toccato) | 100 % | ≥ 85 % | ok |
| `cli/groups_write.py` (nuovo) | 96,38 % | ≥ 85 % | ok |
| `cli/tasks.py` (toccato) | 97,67 % | ≥ 85 % | ok |
| `cli/users_write.py` (nuovo) | 99,41 % | ≥ 85 % | ok |
| `models/facade/__init__.py` (toccato) | 100 % | ≥ 85 % | ok |
| `models/facade/admin_manage.py` (toccato) | 95,71 % | ≥ 85 % | ok |
| `models/facade/groups.py` (toccato) | 94,29 % | ≥ 85 % | ok |
| `models/facade/users.py` (toccato) | 100 % | ≥ 85 % | ok |

Righe scoperte nel codice nuovo: `api/groups.py` 141–144 (la `fetch` interna di
`iterate_members`, preesistente); `cli/groups_write.py` 183, 271, 354, 360, 448 (rami
`return {}` delle righe curate per un oggetto che non è la façade attesa e il `raise` di
`_require_token` senza token nel form); `cli/users_write.py` 121 (`emailNotifyRecipients` vuoto);
`models/facade/groups.py` 81–94, 124–158, 213–223, 293 (rami `None` dei getter su stub non dict,
in parte preesistenti). `cli/__init__.py` 89 % per righe preesistenti (callback del logging).

## Regole non negoziabili

| Regola | Controllo | Esito |
|---|---|---|
| Token e segreti mai nei log | `password` e `generatedPassword` sono chiavi redatte in body di richiesta e risposta prima di log, audit (anche con `audit_log_bodies`) e hook (05-C20); nessun log nuovo nel codice della spec; una risposta di creazione malformata solleva `ValueError` con i soli nomi dei campi e senza incatenare la `ValidationError` di pydantic, che metteva la password nel messaggio (trovato in T15, chiuso da `41dfd76`). La password generata compare solo nell'output di `users create`, per scelta della spec, con avviso su `--export` in `docs/cli.md`. | rispettata |
| Cache del token con permessi stretti | Codice non toccato. | n/a |
| Segreti fuori dal repository | Fixture con password finta e riconoscibile (`Xk7-fake-pw`); `.env.example` con soli nomi; nessun `.env`, `.secrets`, `audit.log` versionato. Le sonde sul tenant hanno stampato solo id, stati, codici di errore e lunghezze; nel primo lancio di T15 la password di un utente di prova è comparsa nel traceback di pytest (la causa è la stessa chiusa da `41dfd76`), l'utente è stato cancellato subito. | rispettata |
| Soglie che non scendono | Controlli e regole di ruff/mypy invariati; copertura totale salita; ogni file toccato ≥ 85 %. | rispettata |
| Dati personali fuori dai log, con eccezione audit | Nessun log nuovo; i `typer.echo` e `console.print` aggiunti stampano messaggi d'uso e id; nome e cognome compaiono solo nel prompt di conferma di `users delete`, sul terminale dell'operatore, come la spec prevede. L'integration test stampa tipo e lunghezza della password, mai il valore. | rispettata |
| Nessuna operazione ripetuta in automatico verso Interacta | Una sola richiesta per scrittura, senza `try/except` di ripetizione (05-C05, 05-C21); `409` → `ConcurrencyError` ed exit `9`; il conflitto di `edit_members` (stato `200`) solleva senza riprovare (05-C09); le patch della CLI leggono e scrivono una volta sola. | rispettata |

## Coerenza con spec, piano e PRD

- Il codice fa ciò che la spec descrive, nella versione rivista dopo T15: scritture di utenti e
  gruppi su `client.users` e `client.groups` con i soli campi passati e `occ_token` esplicito;
  façade `UserWriteResult`, `GroupSummary`, `GroupWriteResult`, `GroupMembersResult`;
  `edit_members` singolo con `ConcurrencyError` e bulk con le due liste; otto comandi CLI, patch
  per `users edit` e `groups edit`, `users edit-credentials` con i soli blocchi indicati e
  rimozione con conferma, `groups edit-members` singolo e bulk, password mai da argomento.
- Scostamenti dal piano, dichiarati in spec e task: `UserWriteResult.from_create` normalizza la
  stringa di `generatedPassword` e sanifica l'errore di forma (`41dfd76`); `users edit-credentials`
  non è più una patch e `ResourceClient._get` mappa il `204` vuoto in `NotFoundError` (T18);
  l'integration test del ciclo utenti manda nome, cognome ed email letti; nella tabella curata di
  `users create` la password generata è una stringa (la lista grezza resta in `--full`).
- Requisiti nuovi entrati nel PRD (`59c229e`): RF-023 precisato e confermato con la semantica
  del server, RF-023a, RF-023b, RF-023c, RF-023d; RF-005, RF-011, RF-013 e la voce "Dati scritti
  sul tenant" di §6 confermati. Nessun ADR necessario: le scritture admin erano già decise da
  ADR 0001; la revisione della spec non contraddice PRD né ADR.
- Voci aggiuntive della checklist: swagger invariato (la divergenza su `generatedPassword` è
  gestita nella façade, non nel modello generato); comandi via `render_output` con snapshot;
  `docs/api/users.md`, `docs/api/groups.md`, `docs/api/admin_manage.md`, `docs/cli.md`,
  `docs/testing.md`, `docs/index.md` e `README.md` aggiornati senza numeri di versione; riga
  `0.13.0 ⏳` in `ROADMAP.md` dall'apertura (diventa ✅ alla release); sezione M31 in
  `PROGRESS.md` scritta con questa verifica.

## Linea di partenza

Aggiornata: copertura totale 94,51 % → 94,94 %, `api` 97,83 % → 98,04 %, `cli` 91,75 % →
92,59 %, `models/facade` 95,77 % → 96,18 %. Nessuna violazione `P-<mm>` aperta; nessun controllo
a cricchetto.

## Problemi trovati

Nessuno nella spec. Osservazioni fuori ambito, emerse con T15, da seguire a parte:

- Il ciclo gruppi di 05-C24 crea un gruppo senza email né membri, quindi da solo non dimostra
  l'azzeramento dei campi omessi (lo ha fatto una sonda): conviene crearlo pieno e verificare
  dopo `edit(name=…)`, in un branch `bugfix_` o con la spec 06.
- `occToken` è redatto nei body dell'audit log perché la chiave contiene `token` (regola
  preesistente di `redact_body`): innocuo, ma rende meno leggibile l'audit delle scritture.
- `tests/integration/.env` creato con permessi `644`: `docs/testing.md` può suggerire
  `chmod 600` come per `sa.json`, e `set -a; source …; set +a` al posto di `export $(… | xargs)`,
  che si spezza sui valori con spazi (già nei follow-up della spec 04).
