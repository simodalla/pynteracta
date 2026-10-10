# Task 05 – Anagrafiche admin, prima metà: utenti e gruppi

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (metodo, proprietà o comando inesistente, corpo diverso); poi il
codice; il commit arriva con i cinque controlli bloccanti verdi. Ogni test porta
`# criterio: 05-Cmm` sulla riga sopra. Messaggi di commit in Conventional Commits con descrizione
in italiano: `feat(users)`, `feat(groups)`, `feat(cli)`, `refactor(cli)`, `test`, `docs`. Gli
snapshot syrupy nuovi si generano con `--snapshot-update` e si leggono prima del commit.
Costanti dei test: utente `42` (form `get_user_for_edit_response.json`, `occToken: 42`;
credenziali `occToken: 12`), utente creato `1043`; gruppo `201` (form
`get_group_for_edit_response.json`, `occToken: 5`, membri `[…]` della fixture), gruppo creato
`202`; nel bulk `201` riesce e `202` è in conflitto; password finta `Xk7-fake-pw` nella fixture
e `S3gret!` nello stdin dei test. Gli id `7`, `3`, `1`, `2` dei criteri sono esempi: i test usano
le costanti qui sopra con la stessa forma.

## Elenco

### [x] T01 – Riga di ROADMAP, fixture e contract test dei DTO

- Criteri: 05-C22 (DTO; lo smoke delle façade arriva con T02 e T03)
- Dipende da: nessuno
- Test: `tests/contract/test_models.py::TestAdminUsersWriteDTOs::test_schema_superset` e
  `::TestAdminGroupsWriteDTOs::test_schema_superset` (`assert_superset` sui 13 DTO della spec e
  sui gemelli tipizzati del piano; verdi subito: caratterizzano i modelli generati) e
  `::test_fixtures_parse` (le sei fixture nuove si validano nei DTO di risposta; rossi finché le
  fixture mancano). Più i test esistenti che leggono `get_user_for_edit_response.json`
  (`test_api_users.py`, `test_cli_users.py`, contract `TestGetUserForEdit`): restano verdi dopo
  la correzione della fixture.
- Passi:
  1. `ROADMAP.md`: riga `0.13.0 | Admin write, first half: users and groups (fourth write group,
     ADR 0001) | M31 | ⏳ In progress | specs/05-admin-users-groups/spec.md`; nota "last used:
     M31".
  2. Fixture nuove in `tests/fixtures/payloads/` con i valori del piano: `create_user_response`,
     `edit_user_response`, `edit_user_credentials_response`, `create_group_response`,
     `edit_group_response`, `edit_groups_members_response` (gruppo `201` in `successGroups` con
     `occToken: 6`, `202` in `concurrencyErrorGroups`).
  3. `get_user_for_edit_response.json`: `userPreferences` con le chiavi reali del swagger
     (`defaultLanguageId`, `defaultTimezoneId`, `emailNotificationsEnabled`), `userSettings` con
     le cinque chiavi di `UserSettingsResponseDTO`; eseguire i test esistenti che la leggono.
  4. Scrivere i contract test; `uv run pytest -m contract` e controlli bloccanti; commit
     `test: fixture e contract test dei DTO di scrittura di utenti e gruppi; riga 0.13.0 in
     ROADMAP (05-T01)`.

### [ ] T02 – `occ_token` sulle façade per-edit e `UserWriteResult`

- Criteri: 05-C06 (façade), 05-C01/C02/C04 (campi del risultato), 05-C22 (smoke utenti)
- Dipende da: T01
- Test: `tests/unit/test_facade_users.py` (nuovo): `test_user_for_edit_exposes_occ_token`,
  `TestUserWriteResult` (`from_create` sulla fixture: `user_id == 1043`, `next_occ_token`,
  `generated_password == ["Xk7-fake-pw"]`, `expired_credentials`, `sent_email_notify`,
  `account_photo_url`, `.raw`; `from_edit(data, 42)`: `user_id == 42`, `generated_password is
  None`; `from_credentials(data, 42)`); `tests/unit/test_facade_groups.py` e
  `test_facade_admin_manage.py`: `test_occ_token_only_on_raw` → `test_occ_token_exposed`
  (`occ_token == raw.occToken`); contract: smoke `UserWriteResult` sulle tre fixture.
- Passi:
  1. Scrivere i test; eseguire: rossi (`AttributeError`, `ImportError`). I due test sostituiti
     sono rossi per il motivo opposto: lo si annota nel commit.
  2. `models/facade/users.py`: `UserForEdit.occ_token`, `UserWriteResult` come nel piano;
     `models/facade/groups.py`: `GroupForEdit.occ_token`; `models/facade/admin_manage.py`:
     `UserCredentialsForEdit.occ_token` e docstring senza "solo su `.raw`";
     `models/facade/__init__.py` esporta `UserWriteResult`.
  3. Controlli bloccanti; commit `feat(users): occ_token sulle façade per-edit e façade
     UserWriteResult (05-T02)`.

### [ ] T03 – Façade dei gruppi: `GroupSummary`, `GroupWriteResult`, `GroupMembersResult`

- Criteri: 05-C07/C08/C09 (campi del risultato), 05-C10 (façade), 05-C22 (smoke gruppi)
- Dipende da: T01
- Test: `tests/unit/test_facade_groups.py`: `TestGroupSummary::test_from_stub` (rivalida un
  `GroupDTO` stub: `id`, `name`, `email`, `visible`, `deleted`, `members_count`, `occ_token`),
  `TestGroupWriteResult` (`from_create`: `group_id == 202` da `groupId`, `next_occ_token`,
  `name`, `visible`, `members_count`; `from_edit(data, 201)`: `group_id == 201`,
  `next_occ_token == 6`, `name is None`; `from_member_edit(summary)`: `next_occ_token` dall'
  `occToken` del gruppo), `TestGroupMembersResult::test_from_dict_splits_lists` (ids `201` e
  `202` nelle due liste, elementi `GroupSummary`); contract: smoke sulle tre fixture dei gruppi.
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `models/facade/groups.py`: le tre classi come nel piano; `__init__.py` le esporta.
  3. Controlli bloccanti; commit `feat(groups): façade GroupSummary, GroupWriteResult e
     GroupMembersResult (05-T03)`.

### [ ] T04 – Scritture degli utenti in `UsersAPI`

- Criteri: 05-C01, 05-C02, 05-C03, 05-C04, 05-C05 (utenti), 05-C06 (alias), 05-C21 (utenti)
- Dipende da: T02
- Test: `tests/unit/test_api_users.py`: `TestUsersCreate` (corpo esatto di 05-C01 letto da
  `route.calls[0].request.content`, `call_count == 1`, risultato dalla fixture; `create_raw`
  equivalente; timeout → `TransportError` con una sola chiamata), `TestUsersEdit` (PUT su
  `admin/manage/users/42`, corpo `{"lastname": "C", "userSettings": {"reducedProfile": true},
  "occToken": 5}`, `user_id == 42`; `edit_raw`; `409` → `ConcurrencyError`, `status_code == 409`,
  una richiesta), `TestUsersDelete` (una `DELETE`, `None`; `404` → `NotFoundError`),
  `TestUsersEditCredentials` (corpo di 05-C04; `edit_credentials_raw`; `409`),
  `test_get_credentials_for_edit_is_alias` (stessa route e fixture di `test_api_admin_manage`,
  tipo `UserCredentialsForEdit`, `occ_token == 12`).
- Passi:
  1. Scrivere i test; eseguire: rossi (`AttributeError` sui metodi).
  2. `api/users.py`: costanti dei percorsi, `WriteBlock`, i sette metodi e l'alias come nel
     piano; docstring in italiano con "una sola richiesta" e la nota sui campi omessi.
     `api/admin_manage.py`: solo docstring.
  3. Controlli bloccanti (`mypy` strict sui tipi dei blocchi annidati); commit `feat(users):
     creazione, modifica, eliminazione e credenziali degli utenti su client.users (05-T04)`.

### [ ] T05 – Creazione, modifica ed eliminazione dei gruppi in `GroupsAPI`

- Criteri: 05-C05 (gruppi), 05-C06 (`GroupForEdit.occ_token` via API), 05-C07, 05-C08, 05-C21
  (gruppi)
- Dipende da: T03
- Test: `tests/unit/test_api_groups.py`: `TestGroupsCreate` (corpo `{"name": "G", "visible":
  true, "memberIds": [1, 2]}`, risultato dalla fixture, `create_raw`, timeout), `TestGroupsEdit`
  (PUT su `admin/manage/groups/201`, corpo `{"name": "G2", "occToken": 5}`, `edit_raw`, `409`
  una volta), `TestGroupsDelete` (una `DELETE`, `None`), `test_get_for_edit_exposes_occ_token`
  (fixture esistente, `occ_token == 5`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `api/groups.py`: costanti, `create`/`create_raw`, `edit`/`edit_raw`, `delete`.
  3. Controlli bloccanti; commit `feat(groups): creazione, modifica ed eliminazione dei gruppi su
     client.groups (05-T05)`.

### [ ] T06 – Membri dei gruppi: `edit_members` ed `edit_members_bulk`

- Criteri: 05-C09, 05-C10
- Dipende da: T05
- Test: `tests/unit/test_api_groups.py::TestGroupsEditMembers`: `test_success_returns_group_with_
  next_occ_token` (corpo `{"groupMembers": [{"id": 201, "occToken": 5, "addUserIds": [1],
  "deleteUserIds": [2]}]}`, `group_id == 201`, `next_occ_token == 6`),
  `test_conflict_raises_concurrency_error` (fixture con `201` spostato in
  `concurrencyErrorGroups`: `ConcurrencyError`, `status_code == 200`, `response_body` presente,
  `call_count == 1`), `test_missing_group_raises_interacta_error` (risposta con liste vuote);
  `TestGroupsEditMembersBulk::test_returns_both_lists_without_raising` (due elementi nel corpo,
  `success_groups[0].id == 201`, `concurrency_error_groups[0].id == 202`),
  `::test_bulk_raw_equivalent`.
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `api/groups.py`: `_MEMBERS_PATH`, `edit_members` con i tre esiti, `edit_members_bulk`,
     `edit_members_bulk_raw`, come nel piano.
  3. Controlli bloccanti; commit `feat(groups): modifica dei membri di uno o più gruppi, conflitto
     del 200 come ConcurrencyError (05-T06)`.

### [ ] T07 – Prova della redazione delle password nei due canali

- Criteri: 05-C20
- Dipende da: nessuno
- Test: `tests/unit/test_transport.py::test_password_keys_redacted_in_audit_and_hooks` (corpo
  di richiesta con `resetUserCustomCredentialsCommand.password: ["S3gret!"]`, risposta con
  `generatedPassword: ["Xk7"]`, `audit=True, audit_bodies=True`, hook di cattura: `***REDACTED***`
  sotto le due chiavi in `audit.request`/`audit.response` e in `on_request`/`on_response`; i
  valori in chiaro assenti da `repr(logs)` e dagli `*Info` catturati). Verde subito: dimostra che
  la regola non negoziabile copre le chiavi di questa spec senza modifiche a `logging.py`.
- Passi:
  1. Scrivere il test; eseguirlo: verde. Se è rosso, fermarsi e segnalarlo: la redazione non
     copre le password e serve una revisione del piano.
  2. Controlli bloccanti; commit `test: redazione di password e generatedPassword in audit log e
     hook (05-T07)`.

### [ ] T08 – Helper della CLI: `read_password` e opzioni condivise

- Criteri: 05-C12 (helper)
- Dipende da: nessuno
- Test: `tests/unit/test_cli_write.py::TestReadPassword` (interattivo: `_stdin_is_interactive`
  → `True` e `typer.prompt` sostituito, chiamato con `hide_input=True` e
  `confirmation_prompt=True`; non interattivo: `sys.stdin` sostituito da `io.StringIO("S3gret!\n")`
  → `"S3gret!"`; stdin vuoto → `typer.Exit` con codice `2` e messaggio); `tests/unit/
  test_cli_tasks.py` intero e `tests/unit/test_cli_posts_write.py` restano verdi dopo lo
  spostamento delle opzioni.
- Passi:
  1. Scrivere i test di `read_password`; eseguire: rossi (`ImportError`).
  2. `cli/_write.py`: `read_password`; `JsonBodyOption` e `OccTokenOption` con help generico;
     `cli/tasks.py` li importa da lì e cancella le proprie definizioni.
  3. Controlli bloccanti e i test dei task; commit `refactor(cli): read_password e opzioni --json e
     --occ-token condivise in cli/_write.py (05-T08)`.

### [ ] T09 – `users create`

- Criteri: 05-C11, 05-C12
- Dipende da: T04, T08
- Test: `tests/unit/test_cli_users_write.py::TestUsersCreate`:
  `test_flags_and_json_merge_flags_win` (corpo esatto di 05-C11 con `body.json` in `tmp_path`),
  `test_table_output_shows_generated_password` (snapshot), `test_json_output` (snapshot con
  `generated_password`), `test_password_stdin_non_interactive` (`input="S3gret!\n"`,
  `_stdin_is_interactive` → `False`, corpo con `password: ["S3gret!"]`, valore assente da
  `result.output`), `test_password_prompt_interactive` (`typer.prompt` sostituito),
  `test_generate_and_stdin_together_exit_2`, `test_stdin_and_json_dash_exit_2` (route non
  chiamata in entrambi), `test_help_has_no_password_option` (`--password-stdin` presente,
  `--password ` assente), `test_json_unknown_key_exits_2`.
- Passi:
  1. Scrivere i test; eseguire: rossi (`No such command`).
  2. `cli/users_write.py`: modulo, opzioni, `_credentials_flags`, `_reset_command`, comando
     `create` con `_create_row`; `cli/__init__.py` importa il modulo.
  3. Snapshot, controlli bloccanti; commit `feat(cli): comando users create con credenziali e
     password da stdin o generata (05-T09)`.

### [ ] T10 – `users edit` e `users edit-credentials`

- Criteri: 05-C13, 05-C14, 05-C15 (utenti)
- Dipende da: T09
- Test: `tests/unit/test_cli_users_write.py`: `test_edit_base_*` sulla funzione pura (blocchi
  rivalidati, `userSettings` a quattro chiavi, chiavi `None` omesse), `TestUsersEdit`
  (`test_edit_reads_form_then_puts_patched_body`, `test_json_then_flags_precedence`,
  `test_occ_token_overrides_but_get_still_happens`, `test_missing_private_email_not_invented`,
  `test_409_exits_9` con il messaggio `User 42 changed since it was read: fetch it again and
  retry` e una sola PUT, `test_missing_occ_token_exits_1`), `test_credentials_base_drops_read_
  only_fields`, `TestUsersEditCredentials` (`test_google_flag_and_no_custom`,
  `test_no_google_when_absent_is_fine`, `test_409_exits_9`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `cli/users_write.py`: `_edit_base`, `_credentials_base`, `_apply_credentials_flags`,
     comandi `edit` ed `edit-credentials` con `_edit_row`, `handle_error(resource=f"User {id}")`.
  3. Controlli bloccanti; commit `feat(cli): users edit ed edit-credentials come patch con occToken
     letto o imposto (05-T10)`.

### [ ] T11 – `users delete`

- Criteri: 05-C16 (utenti)
- Dipende da: T09
- Test: `tests/unit/test_cli_users_write.py::TestUsersDelete`:
  `test_prompt_shows_id_and_full_name_and_y_deletes` (`Delete user 42 "Maria Rossi"?`, `User 42
  deleted`), `test_prompt_n_does_nothing`, `test_yes_skips_prompt`, `test_json_output`
  (`{"user_id": 42}`), `test_non_interactive_without_yes_refuses` (exit `2`, nessuna `DELETE`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `cli/users_write.py`: comando `delete` con `confirm_destructive`.
  3. Controlli bloccanti; commit `feat(cli): users delete con conferma (05-T11)`.

### [ ] T12 – `groups create`, `groups edit`, `groups delete`

- Criteri: 05-C15 (gruppi), 05-C16 (gruppi), 05-C17
- Dipende da: T05, T08
- Test: `tests/unit/test_cli_groups_write.py`: `TestGroupsCreate::test_flags_body_and_table`
  (corpo `{"name": "G", "memberIds": [1, 2], "visible": false}` da `--system`, snapshot),
  `test_group_edit_base_*` (`memberIds` dagli id letti, presente anche vuota),
  `TestGroupsEdit` (`test_edit_reads_form_then_puts_patched_body` con il corpo di 05-C17 e
  `occToken: 5`, `test_json_member_ids_replace_read_list`, `test_409_exits_9` con `Group 201
  changed since it was read…`), `TestGroupsDelete` (i cinque casi di T11 su `Delete group 201
  "Engineering"?`, `Group 201 deleted`, `{"group_id": 201}`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `cli/groups_write.py`: modulo, opzioni, `_group_edit_base`, `_group_row`, i tre comandi;
     `cli/__init__.py` importa il modulo.
  3. Snapshot, controlli bloccanti; commit `feat(cli): comandi groups create, edit (patch) e
     delete con conferma (05-T12)`.

### [ ] T13 – `groups edit-members`, singolo e bulk

- Criteri: 05-C18, 05-C19
- Dipende da: T06, T12
- Test: `tests/unit/test_cli_groups_write.py::TestGroupsEditMembers`
  (`test_add_remove_reads_occ_token_then_puts` con corpo esatto e output con `members_count` e
  `next_occ_token`, `test_occ_token_skips_get` (`get_route.call_count == 0`),
  `test_conflict_exits_9`, `test_without_add_or_remove_exits_2`, `test_group_id_with_json_exits_2`)
  e `TestGroupsEditMembersBulk` (`test_json_rows_and_exit_9_on_conflict` con snapshot della
  tabella e colonna `result`, `test_all_success_exits_0`, `test_json_output_full`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `cli/groups_write.py`: comando `edit-members` con `GROUP_ID` opzionale, le due modalità,
     `_MembersRow`, `_members_row`, exit `9` sul bulk con conflitti.
  3. Snapshot, controlli bloccanti; commit `feat(cli): groups edit-members per un gruppo o in
     blocco da --json (05-T13)`.

### [ ] T14 – Integration test opt-in dei cicli di gruppo e di utente

- Criteri: 05-C24, 05-C25
- Dipende da: T04, T06
- Test: `tests/integration/test_groups_hashtags_integration.py::TestGroupsWriteIntegration::
  test_create_edit_members_delete_cycle` e `tests/integration/test_users_integration.py::
  TestUsersWriteIntegration::test_create_edit_credentials_delete_cycle`, come nel piano, con
  `finally` e stampe `[05-C26]`; senza le variabili si auto-saltano (verificato con
  `uv run pytest -m integration` senza `.env`: `skipped`).
- Passi:
  1. Scrivere i due test; `tests/integration/.env.example` e `docs/testing.md` con
     `PYNTERACTA_TEST_WRITE_USERS` e `PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN`.
  2. `uv run pytest -m integration -q` senza ambiente → tutti saltati; controlli bloccanti;
     commit `test: integration test opt-in dei cicli di scrittura di gruppi e utenti (05-T14)`.

### [ ] T15 – Esecuzione degli integration test sul tenant di prova (manuale)

- Criteri: 05-C26
- Chi: maintainer
- Cosa fare: con `tests/integration/.env` compilato, eseguire
  `uv run pytest -m integration tests/integration/test_groups_hashtags_integration.py -s -k Write`
  e, dopo aver impostato `PYNTERACTA_TEST_WRITE_USERS=1`, `uv run pytest -m integration
  tests/integration/test_users_integration.py -s`. Riportare qui le righe `[05-C26]`: effetto dei
  campi omessi in `edit` ed `edit_credentials`, esito della rilettura dopo `delete`, formato di
  `generated_password` (lunghezza e tipo), `occToken` restituito da `edit_members` e se vale per
  l'edit successivo. Se il server rifiuta un corpo che la spec dà per buono, si rivede la spec con
  l'approvazione del maintainer prima di T16.
- Esito: *da compilare*.

### [ ] T16 – Documentazione

- Criteri: 05-C23
- Dipende da: T10, T11, T13, T15
- Test: `tests/unit/test_docs_snippets.py::test_users_groups_pages_document_write_commands`
  (le pagine citano gli otto comandi, `--password-stdin`, `--generate-password`,
  `UserWriteResult`, `GroupMembersResult`, `occ_token`; `index.md` e `README.md` non contengono
  più "event posts, admin" e non citano numeri di versione nelle frasi nuove); rosso prima delle
  pagine. Più `uv run mkdocs build --strict` e gli snippet nuovi nel controllo di coerenza.
- Passi:
  1. Scrivere il test; eseguirlo: rosso.
  2. `docs/api/users.md` (riscritta: letture, scritture, credenziali, semantica del server da
     T15, `blocked` in sola lettura), `docs/api/groups.md`, `docs/api/admin_manage.md`,
     `docs/cli.md` (otto comandi, password, nota su `--export`, exit `9`; via la frase su
     `occToken` solo su `.raw`), `docs/testing.md` se T14 non l'ha già coperto, `docs/index.md`,
     `README.md`.
  3. `uv run mkdocs build --strict`, controlli bloccanti; commit `docs: scritture admin di utenti
     e gruppi in libreria e CLI (05-T16)`.

### [ ] T17 – Chiusura: PRD

- Criteri: nessuno nuovo (chiude i "Requisiti nuovi" della spec)
- Dipende da: T15, T16
- Verifica: rilettura del PRD; `uv run pre-commit run --all-files` verde.
- Passi:
  1. `specs/prd.md`: RF-023 precisato con la semantica verificata in T15 (campi omessi,
     eliminazione, password generata, `occToken` dei membri); RF-023a, RF-023b, RF-023c come
     sotto-voci; "Confermato dal maintainer il <data>, spec 05" su RF-023, RF-005, RF-011, RF-013
     e sulla voce "Dati scritti sul tenant" di §6 (credenziali comprese); riga nella "Storia del
     documento".
  2. Commit `docs: PRD con RF-023 precisato, RF-023a, RF-023b e RF-023c (05-T17)`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 05-C01 | T02, T04 |
| 05-C02 | T02, T04 |
| 05-C03 | T04 |
| 05-C04 | T02, T04 |
| 05-C05 | T04, T05 |
| 05-C06 | T02, T04, T05 |
| 05-C07 | T03, T05 |
| 05-C08 | T03, T05 |
| 05-C09 | T03, T06 |
| 05-C10 | T03, T06 |
| 05-C11 | T09 |
| 05-C12 | T08, T09 |
| 05-C13 | T10 |
| 05-C14 | T10 |
| 05-C15 | T10, T12 |
| 05-C16 | T11, T12 |
| 05-C17 | T12 |
| 05-C18 | T13 |
| 05-C19 | T13 |
| 05-C20 | T07 |
| 05-C21 | T04, T05 |
| 05-C22 | T01, T02, T03 |
| 05-C23 | T16 |
| 05-C24 | T14, T15 |
| 05-C25 | T14, T15 |
| 05-C26 | T15 |
