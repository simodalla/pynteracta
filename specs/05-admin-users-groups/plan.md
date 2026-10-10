# Piano 05 – Anagrafiche admin, prima metà: utenti e gruppi

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Si estende la catena delle scritture già costruita dalle spec 02-04, senza toccare transport né
client base: `UsersAPI` guadagna `create`/`create_raw`, `edit`/`edit_raw`, `delete`,
`edit_credentials`/`edit_credentials_raw` e l'alias `get_credentials_for_edit`; `GroupsAPI`
guadagna `create`/`create_raw`, `edit`/`edit_raw`, `delete`, `edit_members`,
`edit_members_bulk`/`edit_members_bulk_raw`. I corpi nascono da `build_write_body` (camelCase,
solo i non-`None`, dict e DTO annidati dumpati senza `None`) o dal DTO (`model_dump(mode="json",
exclude_none=True)`), come per i task. Le façade `UserForEdit`, `GroupForEdit` e
`UserCredentialsForEdit` espongono `occ_token`; tre façade nuove avvolgono le risposte
(`UserWriteResult`, `GroupWriteResult`, `GroupMembersResult` con `GroupSummary`), rivalidando lo
stub `GroupDTO` in `GroupDTOModel` come `TaskWriteResult` fa con `TaskDetailDTO1`. `edit_members`
è l'unico metodo con logica propria: legge le due liste della risposta `200` e solleva
`ConcurrencyError` se il gruppo è tra i conflitti. Nella CLI i comandi di scrittura stanno in due
moduli nuovi, `cli/users_write.py` e `cli/groups_write.py`, registrati sulle app esistenti come
`posts_write.py`; riusano `merge_body`, `validate_body`, `load_json_body`, `confirm_destructive`,
`handle_error(resource=…)` e `render_output`. Le patch (`users edit`, `users edit-credentials`,
`groups edit`) costruiscono la base dal form riletto con funzioni pure (`_edit_base`,
`_credentials_base`, `_group_edit_base`) che filtrano i blocchi annidati con i DTO di richiesta
tipizzati. La password custom entra solo da `--password-stdin` (helper `read_password` in
`cli/_write.py`: `typer.prompt` nascosto con conferma se c'è un terminale, altrimenti prima riga
dello stdin) o da `--generate-password`. Fixture JSON e contract test per i 13 DTO; integration
test opt-in (gruppi con le variabili esistenti, utenti con `PYNTERACTA_TEST_WRITE_USERS=1`);
pagine `docs/`, `index.md` e `README.md`. Test prima del codice, un commit per task.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `ROADMAP.md` | modificato (apertura) | riga `0.13.0 ⏳ M31`, "Admin write, first half: users and groups (fourth write group, ADR 0001)", link alla spec; nota "last used: M31" |
| `src/pynteracta/models/facade/users.py` | modificato | `UserForEdit.occ_token` (`raw.occToken`); `UserWriteResult(raw: CreateUserResponseDTO \| EditUserResponseDTO \| EditUserCredentialsResponseDTO, *, user_id: int \| None = None)`: `user_id` (da `raw.userId` se c'è, altrimenti quello passato), `next_occ_token`, `generated_password: list[str] \| None`, `expired_credentials`, `sent_email_notify`, `account_photo_url` (tutti via `getattr(raw, …, None)` perché i tre DTO non li hanno tutti), `.raw`; `from_create(data)`, `from_edit(data, user_id)`, `from_credentials(data, user_id)`; docstring del modulo aggiornata (endpoint di scrittura) |
| `src/pynteracta/models/facade/groups.py` | modificato | `GroupForEdit.occ_token`; `GroupSummary(raw: GroupDTOModel)`: `id`, `name`, `email`, `visible`, `deleted`, `members_count`, `occ_token`, `from_stub(stub)` (rivalida `GroupDTO` → `GroupDTOModel` con `_resolve_root`, come `GroupMember.from_stub`); `GroupWriteResult(raw: CreateGroupResponseDTO \| EditGroupResponseDTO \| GroupDTOModel, *, group_id=None)`: `group_id` (`groupId`, poi `id`, poi quello passato), `next_occ_token` (`nextOccToken`, altrimenti `occToken` per il `GroupDTOModel` di `edit_members`), `name`, `email`, `visible`, `members_count` via `getattr`, `.raw`; `from_create(data)`, `from_edit(data, group_id)`, `from_member_edit(summary: GroupSummary)`; `GroupMembersResult(raw: EditMultipleGroupsMembersResponseDTO)`: `success_groups`, `concurrency_error_groups` (liste di `GroupSummary`), `from_dict` |
| `src/pynteracta/models/facade/admin_manage.py` | modificato | `UserCredentialsForEdit.occ_token`; docstring del modulo e della classe: `occToken` non è più "solo su `.raw`" |
| `src/pynteracta/models/facade/__init__.py` | modificato | esporta `UserWriteResult`, `GroupWriteResult`, `GroupSummary`, `GroupMembersResult` |
| `src/pynteracta/api/users.py` | modificato | costanti `_CREATE_PATH = "admin/manage/users"`, `_EDIT_PATH = "admin/manage/users/{user_id}"`, `_DELETE_PATH` (idem), `_CREDENTIALS_PATH = "admin/manage/users/{user_id}/credentials"`, `_CREDENTIALS_FOR_EDIT_PATH`; `create(*, firstname, lastname, contact_email, private_email, external_id, user_preferences, user_info, user_settings, user_credentials_configuration, reset_user_custom_credentials_command) -> UserWriteResult` (`build_write_body` → `_post`); `create_raw(req)`; `edit(user_id, occ_token, *, firstname, …, user_settings)` (`build_write_body(..., occ_token=occ_token)` → `_put`); `edit_raw(user_id, req: EditUserRequestDTO)`; `delete(user_id) -> None` (`_delete`, risposta ignorata); `edit_credentials(user_id, occ_token, *, google, microsoft, custom)` (corpo `{"userCredentialsConfiguration": build_write_body(google=…, microsoft=…, custom=…), "occToken": occ_token}` → `_put`); `edit_credentials_raw(user_id, req)`; `get_credentials_for_edit(user_id) -> UserCredentialsForEdit` (stessa `GET` di `AdminManageAPI`, importa la façade da `facade.admin_manage`); tipo `WriteBlock = dict[str, Any] \| BaseModel \| None` per i blocchi annidati; docstring Google in italiano con la nota "una sola richiesta, nessun nuovo tentativo" e "campi omessi: semantica del server, vedi docs" |
| `src/pynteracta/api/groups.py` | modificato | costanti `_CREATE_PATH = "admin/manage/groups"`, `_EDIT_PATH = "admin/manage/groups/{group_id}"`, `_MEMBERS_PATH = "admin/manage/groups/members"`; `create(*, name, email, external_id, visible, member_ids)`, `create_raw`; `edit(group_id, occ_token, *, name, email, external_id, visible, member_ids)`, `edit_raw(group_id, req)`; `delete(group_id) -> None`; `edit_members(group_id, occ_token, *, add_user_ids, remove_user_ids) -> GroupWriteResult`: corpo `{"groupMembers": [build_write_body(id=group_id, occ_token=occ_token, add_user_ids=…, delete_user_ids=remove_user_ids)]}` → `_put` → `GroupMembersResult.from_dict` → se `group_id` in `concurrency_error_groups` → `raise ConcurrencyError(f"Group {group_id} changed since it was read: members not changed", status_code=200, request_method="PUT", request_url=_MEMBERS_PATH, response_body=body)`; se in `success_groups` → `GroupWriteResult.from_member_edit(summary)`; altrimenti `raise InteractaError(f"Group {group_id} missing from the members edit response", status_code=200, request_method="PUT", request_url=_MEMBERS_PATH, response_body=body)`; `edit_members_bulk(groups: list[dict[str, Any] \| EditGroupMembersRequestDTOModel]) -> GroupMembersResult` (`{"groupMembers": [_dump(g) for g in groups]}` via `build_write_body(group_members=groups)`); `edit_members_bulk_raw(req)` |
| `src/pynteracta/api/admin_manage.py` | modificato (solo docstring) | `user_credentials_for_edit` rimanda a `UsersAPI.get_credentials_for_edit` ed `edit_credentials`; la nota "deferred to v1.0+" sparisce |
| `src/pynteracta/cli/_write.py` | modificato | `read_password(*, option: str = "--password-stdin") -> str`: se `_common._stdin_is_interactive()` → `typer.prompt("Password", hide_input=True, confirmation_prompt=True)`; altrimenti `sys.stdin.readline().rstrip("\r\n")`; stringa vuota → `typer.echo(f"{option}: no password read from stdin.", err=True)` ed `Exit(EXIT_CONFIG)`; `JsonBodyOption` e `OccTokenOption` generici spostati qui da `cli/tasks.py` (help senza "task"), riusati da `tasks.py`, `users_write.py`, `groups_write.py` |
| `src/pynteracta/cli/users_write.py` | nuovo | `from pynteracta.cli.users import app`; opzioni `--first-name`, `--last-name`, `--contact-email`, `--private-email`, `--external-id`, `--google-account`, `--microsoft-account`, `--username`, `--generate-password`, `--password-stdin`, `--force-password-change`, `--notify-email` (ripetibile), `--no-google`, `--no-microsoft`, `--no-custom`, `--custom-active/--custom-inactive`, `--json`, `--occ-token`, `--yes`; funzioni pure: `_credentials_flags(google, microsoft, username) -> dict` (blocchi `google`/`microsoft` con `enabled: true`, `custom` con `active: true`), `_reset_command(generate, password, force, notify) -> dict \| None`, `_edit_base(user: UserForEdit) -> dict` (chiavi `firstname`, `lastname`, `contactEmail`, `privateEmail`, `externalId` se non `None`; `userPreferences` → `AdminUserPreferencesDTO.model_validate(root).model_dump(exclude_none=True)`; `userInfo` → `UserInfoDTO1` idem; `userSettings` → `UserSettingsRequestDTO1` idem, che scarta `editPrivateEmailEnabled`; blocchi vuoti non si mettono), `_credentials_base(form: UserCredentialsForEdit) -> dict` (`google`/`microsoft`/`custom` dal `root` di `userCredentialsConfiguration`, ciascuno rivalidato nel suo DTO tipizzato e dumpato senza `None`, senza `profilePhotoUrl` e `canManageProfilePhoto`), `_apply_credentials_flags(base, …)` (set degli account id ed `enabled`, `username`, `active`; `--no-*` → `pop`); comandi `users create`, `users edit`, `users delete`, `users edit-credentials` secondo la spec; righe curate `_create_row` (`user_id`, `next_occ_token`, `generated_password` come stringa unita da spazio, `expired_credentials`, `sent_email_notify`) e `_edit_row` (`user_id`, `next_occ_token`, `account_photo_url`); errori d'uso (`--generate-password` con `--password-stdin`, `--password-stdin` con `--json -`) → messaggio ed `EXIT_CONFIG` prima di `build_client`; `handle_error(exc, console=console, resource=f"User {user_id}")`; `--occ-token` assente e `occ_token` `None` dal server → messaggio ed `EXIT_GENERIC` come `tasks edit` |
| `src/pynteracta/cli/groups_write.py` | nuovo | `from pynteracta.cli.groups import app`; opzioni `--name`, `--email`, `--external-id`, `--visible/--system`, `--member` (ripetibile, solo `create`), `--add`, `--remove`, `--json`, `--occ-token`, `--yes`; `_group_edit_base(group: GroupForEdit) -> dict` (`name`, `email`, `externalId`, `visible`, `memberIds` = `[m.id for m in group.members_typed if m.id is not None]`; chiavi `None` omesse; `memberIds` sempre presente, anche vuota, perché la lista è il contratto del `PUT`); comandi `groups create`, `groups edit`, `groups delete`, `groups edit-members GROUP_ID?` (`group_id: Annotated[int \| None, typer.Argument()] = None`): con `GROUP_ID` → `--add`/`--remove` obbligatori (`"--add or --remove is required."`, `EXIT_CONFIG`), `--json` vietato; senza `GROUP_ID` → `--json` obbligatorio; singolo: `token = --occ-token` oppure `client.groups.get_for_edit(id).occ_token` (la `GET` avviene solo senza `--occ-token`), `client.groups.edit_members(...)`, `render_output([result], _group_row, title=f"Members of group {id} updated")`; bulk: `client.groups.edit_members_bulk_raw(validate_body(body, EditMultipleGroupsMembersRequestDTO))`, righe `_MembersRow(group: GroupSummary, result: str)` (dataclass locale con proprietà `raw` → `group.raw` così `--full`/`--fields` funzionano) per `success_groups` (`"success"`) e `concurrency_error_groups` (`"concurrency_error"`), `render_output`, poi `Exit(EXIT_CONFLICT)` se ci sono conflitti; righe curate `_group_row` (`group_id`, `name`, `email`, `visible`, `members_count`, `next_occ_token`); `handle_error(..., resource=f"Group {group_id}")` |
| `src/pynteracta/cli/__init__.py` | modificato | `from pynteracta.cli import users_write as _users_write_cli  # noqa: F401` e `groups_write`, accanto a `posts_write` |
| `src/pynteracta/cli/tasks.py` | modificato (refactor minimo) | importa `JsonBodyOption` e `OccTokenOption` da `_write.py` invece di definirli; nessun cambiamento di comportamento (snapshot e test esistenti restano verdi; l'help di `--json` perde "sub-tasks and attachments", che resta nella docstring del comando) |
| `tests/fixtures/payloads/create_user_response.json` | nuovo | `userId: 1043`, `accountPhotoUrl`, `generatedPassword: ["Xk7-fake-pw"]`, `expiredCredentials: true`, `sentEmailNotify: false`, `nextOccToken: 1` |
| `tests/fixtures/payloads/edit_user_response.json`, `edit_user_credentials_response.json` | nuovi | `{"accountPhotoUrl": …, "nextOccToken": 43}`; `{"nextOccToken": 13}` |
| `tests/fixtures/payloads/create_group_response.json`, `edit_group_response.json` | nuovi | `CreateGroupResponseDTO` completo con `groupId: 202`, `id: 202`, `name: "QA"`, `visible`, `membersCount: 2`, `occToken: 1`, `nextOccToken: 1`, `tags: []`; `{"nextOccToken": 6}` |
| `tests/fixtures/payloads/edit_groups_members_response.json` | nuovo | `successGroups: [GroupDTO del gruppo 201 con occToken 6, membersCount 3]`, `concurrencyErrorGroups: [GroupDTO del gruppo 202 con occToken 2]` |
| `tests/fixtures/payloads/get_user_for_edit_response.json` | modificato | `userPreferences` con le chiavi reali (`defaultLanguageId: "it"`, `defaultTimezoneId: 1`, `emailNotificationsEnabled: true`); `userSettings` con le cinque chiavi di `UserSettingsResponseDTO` (`editPrivateEmailEnabled` compreso); `userInfo` com'è. Le tabelle curate di `users get-for-edit` non mostrano questi blocchi: gli snapshot restano uguali (si verifica eseguendo `test_cli_users.py` prima del commit) |
| `tests/unit/test_facade_users.py` | nuovo | `UserForEdit.occ_token` (05-C06); `UserWriteResult` dalle tre fixture: campi, `user_id` dalla risposta o passato, `.raw` |
| `tests/unit/test_facade_groups.py` | modificato | `test_occ_token_only_on_raw` → `test_occ_token_exposed` (05-C06); `GroupSummary.from_stub`, `GroupWriteResult.from_create/from_edit/from_member_edit`, `GroupMembersResult.from_dict` sulla fixture (liste e stub rivalidati) |
| `tests/unit/test_facade_admin_manage.py` | modificato | `test_occ_token_only_on_raw` → `test_occ_token_exposed` (05-C06) |
| `tests/unit/test_api_users.py` | modificato | 05-C01…C06 (parte utenti), 05-C21: route `respx` sui quattro percorsi, corpo esatto da `route.calls[0].request.content`, `call_count == 1`, `409` → `ConcurrencyError`, `404` → `NotFoundError`, timeout → `TransportError`; `get_credentials_for_edit` sulla stessa route della fixture esistente |
| `tests/unit/test_api_groups.py` | modificato | 05-C05 (groups.edit), 05-C06 (`GroupForEdit.occ_token` via API), 05-C07…C10, 05-C21: corpi esatti, `edit_members` nei tre esiti (successo, conflitto → `ConcurrencyError` con `status_code == 200`, assente → `InteractaError`), `edit_members_bulk` senza eccezione, varianti `_raw` |
| `tests/unit/test_transport.py` | modificato | 05-C20: `test_password_keys_redacted_in_audit_and_hooks`: `POST` con `json={"resetUserCustomCredentialsCommand": {"password": ["S3gret!"]}}` e risposta `{"generatedPassword": ["Xk7"]}`, `audit=True, audit_bodies=True`, hook di cattura: `audit.request.body` e `on_request.body` hanno `***REDACTED***` sotto `password`, `audit.response.body` e `on_response.body` sotto `generatedPassword`; `"S3gret!"` e `"Xk7"` assenti da `repr(logs)` |
| `tests/unit/test_cli_write.py` | modificato | `read_password`: interattivo (monkeypatch `_stdin_is_interactive` → True, `typer.prompt` sostituito), non interattivo con riga, stdin vuoto → `Exit(2)` |
| `tests/unit/test_cli_users_write.py` | nuovo | 05-C11…C16 (utenti): `TestUsersCreate` (flag + `--json` da `tmp_path`, corpo esatto, snapshot tabella con `generated_password`, `--output json`; `--password-stdin` con `input="S3gret!\n"` e `_stdin_is_interactive` → False: corpo con `password: ["S3gret!"]`, password assente da `result.output`; interattivo con `typer.prompt` monkeypatchato; coppie vietate → exit `2` e route non chiamata; `--help` senza `--password`), `TestUsersEdit` (GET + PUT, corpo = base dalla fixture corretta + flag; `--json` < flag; `--occ-token 6` con GET; fixture senza `privateEmail` tramite `copy` del payload con la chiave tolta), `TestUsersEditCredentials` (GET + PUT, `--google-account` e `--no-custom`, nessun `profilePhotoUrl`), `TestUsersDelete` (prompt con `"Maria Rossi"`, `y`/`n`/`--yes`/non interattivo, `{"user_id": 42}`), `TestUsersConflict` (PUT → `409` → exit `9`, messaggio `User 42 changed since it was read…`, una sola PUT) |
| `tests/unit/test_cli_groups_write.py` | nuovo | 05-C15…C19 (gruppi): `TestGroupsCreate` (corpo con `visible: false` da `--system`, snapshot), `TestGroupsEdit` (base dalla fixture `get_group_for_edit_response.json`: `memberIds: [id letti]`, `--json` con `memberIds` che sostituisce), `TestGroupsDelete` (prompt `Delete group 201 "Engineering"?`), `TestGroupsEditMembers` (singolo con GET, con `--occ-token` senza GET, conflitto → `9`, senza flag → `2`, `GROUP_ID` + `--json` → `2`), `TestGroupsEditMembersBulk` (snapshot con colonna `result`, exit `9` con un conflitto, `0` senza) |
| `tests/unit/test_cli_tasks.py` | invariato | resta verde dopo lo spostamento delle opzioni condivise (controllo del refactor) |
| `tests/contract/test_models.py` | modificato | 05-C22: `TestAdminUsersWriteDTOs` e `TestAdminGroupsWriteDTOs`: `assert_superset` per i 13 DTO della spec più i gemelli tipizzati usati dalle façade e dalle patch (`GroupDTOModel`, `UserCredentialsConfigurationDTO1`, `ResetUserCustomCredentialsCommandDTO1`, `AdminUserPreferencesDTO`, `UserInfoDTO1`, `UserSettingsRequestDTO1`, `CustomUserCredentialsConfigurationDTOModel`, `EditGroupMembersRequestDTOModel`); smoke delle façade sulle sei fixture nuove |
| `tests/integration/test_groups_hashtags_integration.py` | modificato | 05-C24: `TestGroupsWriteIntegration::test_create_edit_members_delete_cycle` con `finally` che elimina il gruppo; stampe `[05-C26]` di `occToken` restituito da `edit_members`, dei campi dopo `edit` con un solo campo e dell'esito della rilettura dopo `delete` (`NotFoundError` o `deleted: true`) |
| `tests/integration/test_users_integration.py` | nuovo | 05-C25: fixture `client` locale (stessa forma degli altri file), `_require_flag("PYNTERACTA_TEST_WRITE_USERS")` che salta se diverso da `1`; ciclo `create` (credenziali custom, `generatePassword`) → `get_for_edit` → `edit` (un campo) → `get_credentials_for_edit` → `edit_credentials` → `delete` in `finally`; stampe `[05-C26]` di `generated_password` (lunghezza e tipo, **non il valore**), dei campi dopo `edit`, dei blocchi dopo `edit_credentials`, dell'esito della rilettura dopo `delete` |
| `tests/integration/.env.example`, `docs/testing.md` | modificati | `PYNTERACTA_TEST_WRITE_USERS=` (commento: crea ed elimina un utente reale, licenza ed email), `PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN=` (default `example.com`); nota che il ciclo dei gruppi usa `PYNTERACTA_TEST_USER_ID` |
| `docs/api/users.md` | modificato | pagina riscritta con sezioni "Reading", "Writing users" (metodi, `UserWriteResult`, `occ_token`, blocchi annidati come dict, password solo alla creazione, campi omessi e semantica del server dopo 05-C26, `blocked` in sola lettura, foto profilo via `contentRef`), "Credentials", riferimento mkdocstrings a `UsersAPI` e alle façade |
| `docs/api/groups.md` | modificato | "three read endpoints" → letture e scritture; sezione "Writing groups" (`create`, `edit` con `member_ids` completo, `delete`, `edit_members` contro `edit_members_bulk`, `ConcurrencyError` dal `200`), membri nel riferimento, façade `GroupWriteResult`, `GroupSummary`, `GroupMembersResult`; la frase "occToken only on .raw" sparisce |
| `docs/api/admin_manage.md` | modificato | "propaedeutic to the future write surface (deferred to v1.0+)" → rimando a `users.edit_credentials`/`get_credentials_for_edit`; D-v0.6-2 aggiornata: `occ_token` è una proprietà da questa spec |
| `docs/cli.md` | modificato | sezioni `users create|edit|delete|edit-credentials` dopo `users get-for-edit`; `groups create|edit|delete|edit-members` dopo `groups get`; la frase "occToken is only accessible via .raw" di `groups get` sparisce; nota su `--export` e la password generata; `--json`, patch, exit `9` |
| `docs/index.md`, `README.md` | modificati | "Write operations" cita utenti e gruppi (create, edit, delete, credentials, members); "More write groups (event posts, admin) follow" → "event posts, catalogs and workspace"; `index.md` "What's out of scope": "the admin area" → "catalogs, catalog entries and the workspace" |
| `tests/unit/test_docs_snippets.py` | modificato | 05-C23: `test_users_groups_pages_document_write_commands` (le pagine citano gli otto comandi, `--password-stdin`, `--generate-password`, `UserWriteResult`, `GroupMembersResult`, `occ_token`; `index.md` e `README.md` non contengono più "event posts, admin"); gli snippet nuovi passano dal controllo di coerenza esistente |
| `PROGRESS.md` | modificato (verifica) | sezione M31 |
| `specs/prd.md` | modificato (chiusura) | RF-023 precisato con la semantica verificata; RF-023a, RF-023b, RF-023c; conferma di RF-023, RF-005, RF-011, RF-013 e della voce di §6 |

Non si toccano: `transport.py`, `hooks.py`, `logging.py` (le chiavi `password` e `generatedPassword`
sono già coperte da `_SENSITIVE_KEY_RE`), `api/_base.py` (`_put` e `_delete` esistono),
`api/_utils.py` (`build_write_body` basta), `client.py` (`client.users` e `client.groups`
esistono), `exceptions.py`, `models/generated/`, `cli/_common.py`.

## Modello dati e migrazioni

Nessuna modifica: i 13 DTO sono già generati. Gli stub `RootModel[Any]` da rivalidare nei gemelli
tipizzati sono `GroupDTO` → `GroupDTOModel` (liste di `EditMultipleGroupsMembersResponseDTO`),
`UserInfoDTO` → `UserInfoDTO1`, `UserSettingsRequestDTO` → `UserSettingsRequestDTO1`,
`UserCredentialsConfigurationDTO` → `UserCredentialsConfigurationDTO1`,
`CustomUserCredentialsConfigurationDTO` → `CustomUserCredentialsConfigurationDTOModel`. I modelli
generati non hanno `model_config`: pydantic ignora le chiavi sconosciute, quindi rivalidare un
blocco letto nel DTO di richiesta scarta i campi di sola lettura.

## Flussi

```
Libreria: utenti
create(**kw)                  → body = build_write_body(**kw)        (dict/DTO annidati dumpati)
                              → _post("admin/manage/users", json=body)
                              → UserWriteResult.from_create(resp)
edit(user_id, occ_token, **kw)→ body = build_write_body(**kw, occ_token=occ_token)
                              → _put("admin/manage/users/{user_id}", json=body)   (409 → ConcurrencyError dal transport)
                              → UserWriteResult.from_edit(resp, user_id)
delete(user_id)               → _delete("admin/manage/users/{user_id}") → None
edit_credentials(user_id, occ_token, google=, microsoft=, custom=)
                              → body = {"userCredentialsConfiguration": build_write_body(google=…, microsoft=…, custom=…),
                                        "occToken": occ_token}
                              → _put("admin/manage/users/{user_id}/credentials", json=body)
                              → UserWriteResult.from_credentials(resp, user_id)
get_credentials_for_edit(id)  → UserCredentialsForEdit.from_dict(_get("admin/manage/users/{id}/credentials/edit"))
*_raw(req)                    → stesso percorso con req.model_dump(mode="json", exclude_none=True)

Libreria: gruppi
create / edit / delete        → come per gli utenti su "admin/manage/groups[/{group_id}]"
edit_members(group_id, occ_token, add_user_ids=, remove_user_ids=)
                              → body = {"groupMembers": [build_write_body(id=group_id, occ_token=occ_token,
                                                              add_user_ids=…, delete_user_ids=…)]}
                              → resp = _put("admin/manage/groups/members", json=body)
                              → result = GroupMembersResult.from_dict(resp)
                              → group_id in {g.id for g in result.concurrency_error_groups} → raise ConcurrencyError(status 200, body)
                              → summary = next(g for g in result.success_groups if g.id == group_id) → GroupWriteResult.from_member_edit(summary)
                              → nessuna delle due → raise InteractaError(status 200, body)
edit_members_bulk(groups)     → body = build_write_body(group_members=groups) → _put(...) → GroupMembersResult.from_dict(resp)
Errori: nessun try/except nei metodi; una richiesta per chiamata; il transport mappa gli stati.

CLI: utenti
users create                  → errori d'uso (--generate-password+--password-stdin, --password-stdin+--json -) → Exit(2)
                              → json_part = load_json_body(--json, CreateUserRequestDTO)
                              → password = read_password() se --password-stdin
                              → merged = merge_body(json_part, firstname=…, lastname=…, contact_email=…, private_email=…, external_id=…,
                                                    user_credentials_configuration=_credentials_flags(...) or None,
                                                    reset_user_custom_credentials_command=_reset_command(...) or None)
                              → req = validate_body(merged, CreateUserRequestDTO)
                              → client.users.create_raw(req) → render_output([result], _create_row, title="User {id} created")
users edit USER_ID            → json_part = load_json_body(--json, EditUserRequestDTO)
                              → user = client.users.get_for_edit(USER_ID)       (sempre)
                              → token = --occ-token or user.occ_token (None → messaggio, Exit(1))
                              → merged = merge_body({**_edit_base(user), **json_part}, firstname=…, …, external_id=…)
                              → merged["occToken"] = token → req = validate_body(merged, EditUserRequestDTO)
                              → client.users.edit_raw(USER_ID, req) → render_output([result], _edit_row, title="User {id} updated")
                              → ConcurrencyError → handle_error(resource="User {id}") → exit 9
users edit-credentials USER_ID→ config = _credentials_blocks(json_part, google_account, microsoft_account, username, no_google, no_microsoft, no_custom)
                              →   (flag contrastanti o config vuota → usage error, exit 2; rivisto dopo T15: niente patch)
                              → per ogni blocco rimosso: confirm_destructive(f"Remove the {block} credentials of user {id}?", yes=--yes)  False → Exit(0)
                              → token = --occ-token, altrimenti client.users.get_credentials_for_edit(USER_ID).occ_token (404/204 → exit 5)
                              → req = validate_body({"userCredentialsConfiguration": config, "occToken": token}, EditUserCredentialsRequestDTO)
                              → client.users.edit_credentials_raw(USER_ID, req) → render_output
users delete USER_ID          → user = client.users.get_for_edit(USER_ID)
                              → confirm_destructive(f'Delete user {id} "{first} {last}"?', yes=--yes)  False → Exit(0)
                              → client.users.delete(USER_ID) → "User {id} deleted" | {"user_id": id}

CLI: gruppi
groups create                 → merged = merge_body(json_part, name=…, email=…, external_id=…, visible=…, member_ids=--member)
                              → client.groups.create_raw(req) → render_output([result], _group_row)
groups edit GROUP_ID          → group = client.groups.get_for_edit(GROUP_ID) → token
                              → merged = merge_body({**_group_edit_base(group), **json_part}, name=…, email=…, external_id=…, visible=…)
                              → merged["occToken"] = token → client.groups.edit_raw(GROUP_ID, req) → render_output
groups delete GROUP_ID        → come users delete con group.name
groups edit-members GROUP_ID --add/--remove [--occ-token]
                              → senza --add/--remove → Exit(2); con --json → Exit(2)
                              → token = --occ-token or client.groups.get_for_edit(GROUP_ID).occ_token   (GET solo senza --occ-token)
                              → client.groups.edit_members(GROUP_ID, token, add_user_ids=…, remove_user_ids=…) → render_output
                              → ConcurrencyError (dal 200 o dal 409) → handle_error(resource="Group {id}") → exit 9
groups edit-members --json    → body = load_json_body(--json, EditMultipleGroupsMembersRequestDTO)
                              → result = client.groups.edit_members_bulk_raw(validate_body(body, …))
                              → rows = [_MembersRow(g, "success") …] + [_MembersRow(g, "concurrency_error") …]
                              → render_output(rows, _members_row) → Exit(9) se concurrency_error_groups, altrimenti Exit(0)
```

## Interfaccia

Comandi, opzioni e messaggi come nella sezione "CLI" della spec; testi in inglese. Help breve con
il formato atteso (`--notify-email ADDR (repeatable)`, `--password-stdin: read the password from
stdin, or prompt for it on a terminal; never pass it as an argument`). `users create --help` non
elenca `--password`. Nessuna pagina web.

## Configurazione

Nessuna variabile di runtime. Solo per gli integration test, in `tests/integration/.env.example`
e `docs/testing.md`: `PYNTERACTA_TEST_WRITE_USERS` (vuota: il ciclo utente è saltato; `1`: crea ed
elimina un utente reale) e `PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN` (default `example.com`).

## Sicurezza e dati personali

- **Token e segreti mai nei log**: nessun log nuovo. `password` e `generatedPassword` sono già
  coperte da `_SENSITIVE_KEY_RE`; 05-C20 lo dimostra sui due canali (audit con body e hook) con
  le chiavi reali di questa spec. La CLI non logga la password letta; `read_password` non la
  stampa e il prompt è `hide_input=True`. Nelle fixture la password generata è una stringa
  riconoscibilmente finta (`"Xk7-fake-pw"`); l'integration test stampa solo lunghezza e tipo.
- **Nessuna operazione ripetuta in automatico**: i metodi fanno una richiesta e lasciano salire le
  eccezioni; `edit_members` legge una risposta, non ne manda una seconda; la CLI non riprova su
  `409` né sul conflitto del `200` (05-C05, 05-C09, 05-C15, 05-C18, 05-C21).
- **Dati personali**: i corpi contengono nomi, email, account id; non si salvano. Fixture con
  valori finti (`m.rossi@example.it`, `a@b.it`, id piccoli). Gli integration test creano entità con
  nome `pynteracta-it-<timestamp>` ed email su dominio di prova, e le eliminano in `finally`; il
  ciclo utente parte solo con l'opt-in dedicato.
- **Conferma delle operazioni distruttive**: `confirm_destructive` riusato com'è; nessuna via che
  elimini senza `y` o `--yes` (05-C16).
- **Soglie che non scendono**: i file nuovi (`users_write.py`, `groups_write.py`,
  `test_facade_users.py`) e quelli toccati hanno un test per ogni ramo (errori d'uso, `occ_token`
  assente, blocchi assenti nel form); copertura ≥ 85 % per file e totale ≥ 94,51 %.

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `GroupForEdit`, `UserCredentialsForEdit` | oggi `occ_token` **non** è una proprietà (`test_occ_token_only_on_raw`) | nessuno: è il comportamento che la spec cambia (RF-023a); i due test si sostituiscono con `test_occ_token_exposed` (05-C06) nello stesso task, così il cambiamento è esplicito |
| `UserForEdit` | campi esposti | già fissato da `test_api_users.py::test_get_for_edit` e dagli snapshot di `users get-for-edit`: nessun test nuovo |
| `users get-for-edit`, `groups get`, `admin-manage user-credentials` (CLI) | tabella e JSON | già fissati dagli snapshot `syrupy`; si rieseguono dopo la correzione della fixture di `get_user_for_edit` (le tabelle curate non mostrano i blocchi toccati) |
| `cli/tasks.py` (`--json`, `--occ-token`) | help e comportamento dopo lo spostamento delle opzioni in `_write.py` | già fissato da `test_cli_tasks.py` (02-C08, 02-C17): resta verde, nessun test nuovo |
| `build_write_body` | dict e DTO annidati dumpati senza `None` | già fissato da `test_api_utils.py::TestBuildWriteBody`: nessun test nuovo |
| `admin_manage.user_credentials_for_edit` | richiesta e façade | già fissato da `test_api_admin_manage.py`; l'alias di 05-C06 si confronta con la stessa route |

Nessun test di caratterizzazione nuovo: tutto il codice esistente che il piano modifica ha già
test che ne fissano il comportamento.

## Strategia di test

Ordine: test prima del codice, rossi per il motivo giusto (metodo o comando inesistente, proprietà
mancante, corpo diverso), poi il codice. Ogni test porta `# criterio: 05-Cmm`. Le fixture nuove si
scrivono con il test che le usa. Gli snapshot nuovi si generano con `--snapshot-update` e si
leggono prima del commit.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 05-C01 | `test_api_users.py::TestUsersCreate::test_create_sends_only_given_fields_and_wraps_response` (corpo esatto con i due blocchi annidati, `call_count == 1`, campi di `UserWriteResult` da `create_user_response.json`), `::test_create_raw_equivalent` | unitario |
| 05-C02 | `::TestUsersEdit::test_edit_sends_given_fields_and_occ_token` (PUT, corpo `{"lastname", "userSettings", "occToken"}`, `user_id == 42`, `next_occ_token`, `account_photo_url`), `::test_edit_raw_equivalent` | unitario |
| 05-C03 | `::TestUsersDelete::test_delete_sends_one_request_and_returns_none`, `::test_delete_404_raises_not_found` | unitario |
| 05-C04 | `::TestUsersEditCredentials::test_edit_credentials_wraps_blocks_and_occ_token`, `::test_edit_credentials_raw_equivalent` | unitario |
| 05-C05 | `test_api_users.py::test_edit_409_raises_concurrency_error_once`, `::test_edit_credentials_409_raises_concurrency_error_once`, `test_api_groups.py::TestGroupsEdit::test_edit_409_raises_concurrency_error_once` (`status_code == 409`, `call_count == 1`) | unitario |
| 05-C06 | `test_facade_users.py::test_user_for_edit_exposes_occ_token`, `test_facade_groups.py::TestGroupForEdit::test_occ_token_exposed`, `test_facade_admin_manage.py::TestUserCredentialsForEdit::test_occ_token_exposed`; `test_api_users.py::test_get_credentials_for_edit_is_alias` (stessa route della fixture esistente, stesso tipo) | unitario |
| 05-C07 | `test_api_groups.py::TestGroupsCreate::test_create_sends_only_given_fields_and_wraps_response`, `::test_create_raw_equivalent` | unitario |
| 05-C08 | `::TestGroupsEdit::test_edit_sends_given_fields_and_occ_token`, `::test_edit_raw_equivalent`; `::TestGroupsDelete::test_delete_sends_one_request_and_returns_none` | unitario |
| 05-C09 | `::TestGroupsEditMembers::test_success_returns_group_with_next_occ_token`, `::test_conflict_raises_concurrency_error` (`status_code == 200`, `response_body` presente, `call_count == 1`), `::test_missing_group_raises_interacta_error`; corpo esatto in tutti e tre | unitario |
| 05-C10 | `::TestGroupsEditMembersBulk::test_returns_both_lists_without_raising`, `::test_bulk_raw_equivalent`; `test_facade_groups.py::TestGroupMembersResult` sulla fixture | unitario |
| 05-C11 | `test_cli_users_write.py::TestUsersCreate::test_flags_and_json_merge_flags_win` (corpo esatto), `::test_table_output_shows_generated_password` (snapshot), `::test_json_output` (snapshot) | unitario |
| 05-C12 | `::TestUsersCreate::test_password_stdin_non_interactive` (`input="S3gret!\n"`, corpo con `password: ["S3gret!"]`, `"S3gret!" not in result.output`), `::test_password_prompt_interactive` (`typer.prompt` monkeypatchato, `hide_input=True` verificato sugli argomenti), `::test_generate_and_stdin_together_exit_2`, `::test_stdin_and_json_dash_exit_2` (route non chiamata), `::test_help_has_no_password_option`; `test_cli_write.py::TestReadPassword` (tre rami) | unitario |
| 05-C13 | `::TestUsersEdit::test_edit_reads_form_then_puts_patched_body` (corpo == base dalla fixture corretta + `lastname`, `userSettings` con quattro chiavi, `occToken` letto), `::test_json_then_flags_precedence` (`externalId`), `::test_occ_token_overrides_but_get_still_happens`, `::test_missing_private_email_not_invented`; `test_edit_base_*` sulla funzione pura | unitario |
| 05-C14 | `::TestUsersEditCredentials::test_google_flag_and_no_custom` (corpo esatto senza `custom` e senza i campi di sola lettura), `::test_no_google_when_absent_is_fine`; `test_credentials_base_drops_read_only_fields` | unitario |
| 05-C15 | `test_cli_users_write.py::TestUsersConflict::test_edit_409_exits_9` e `::test_edit_credentials_409_exits_9` (messaggio `User 42 changed since it was read…`, una sola PUT); `test_cli_groups_write.py::TestGroupsEdit::test_409_exits_9` (`Group 201 …`) | unitario |
| 05-C16 | `::TestUsersDelete::test_prompt_shows_id_and_full_name_and_y_deletes` (monkeypatch `_stdin_is_interactive`, `input="y\n"`, `User 42 deleted`), `::test_prompt_n_does_nothing`, `::test_yes_skips_prompt`, `::test_json_output`, `::test_non_interactive_without_yes_refuses` (exit `2`, route non chiamata); `test_cli_groups_write.py::TestGroupsDelete` con gli stessi cinque casi su `Delete group 201 "Engineering"?` | unitario |
| 05-C17 | `test_cli_groups_write.py::TestGroupsCreate::test_flags_body_and_table` (corpo con `visible: false`, snapshot), `::TestGroupsEdit::test_edit_reads_form_then_puts_patched_body` (`memberIds: [id letti]`, `occToken: 5`), `::test_json_member_ids_replace_read_list`; `test_group_edit_base_*` | unitario |
| 05-C18 | `::TestGroupsEditMembers::test_add_remove_reads_occ_token_then_puts` (corpo esatto, output con `members_count` e `next_occ_token`), `::test_occ_token_skips_get`, `::test_conflict_exits_9`, `::test_without_add_or_remove_exits_2` | unitario |
| 05-C19 | `::TestGroupsEditMembersBulk::test_json_rows_and_exit_9_on_conflict` (snapshot con colonna `result`), `::test_all_success_exits_0`, `::test_group_id_with_json_exits_2` | unitario |
| 05-C20 | `test_transport.py::test_password_keys_redacted_in_audit_and_hooks` (corpo di richiesta con `password`, risposta con `generatedPassword`, `audit_bodies=True`, hook di cattura; i valori in chiaro non compaiono in nessun record) | unitario |
| 05-C21 | `test_api_users.py::test_create_timeout_raises_transport_error_once`, `test_api_groups.py::test_create_timeout_raises_transport_error_once` (`side_effect=httpx.ReadTimeout`, `call_count == 1`) | unitario |
| 05-C22 | `tests/contract/test_models.py::TestAdminUsersWriteDTOs`, `::TestAdminGroupsWriteDTOs` (`assert_superset` sui 13 DTO e sui gemelli tipizzati; smoke `UserWriteResult.from_create/from_edit/from_credentials`, `GroupWriteResult.from_create/from_edit`, `GroupMembersResult.from_dict` sulle fixture) | contract |
| 05-C23 | `test_docs_snippets.py::test_users_groups_pages_document_write_commands`; `uv run mkdocs build --strict` nei controlli di verifica; gli snippet Python delle pagine passano da `test_doc_snippet_is_consistent_with_the_api` | unitario + verifica |
| 05-C24 | `test_groups_hashtags_integration.py::TestGroupsWriteIntegration::test_create_edit_members_delete_cycle`: skip senza `PYNTERACTA_TEST_USER_ID`; `create` (`visible=False`, nome con timestamp) → `get_for_edit` → `edit(name=…)` → `edit_members(add)` → `edit_members(remove)` → `delete` in `finally`; dopo il delete `get_for_edit` → `NotFoundError` oppure `deleted is True` (stampa dell'esito) | integrazione (opt-in) |
| 05-C25 | `test_users_integration.py::TestUsersWriteIntegration::test_create_edit_credentials_delete_cycle`: skip senza `PYNTERACTA_TEST_WRITE_USERS=1`; email dal dominio configurato; `delete` in `finally`; `generated_password` mai stampata per intero | integrazione (opt-in dedicato) |
| 05-C26 | esecuzione manuale di 05-C24 e 05-C25 sul tenant di prova; esito registrato in `docs/api/users.md`, `docs/api/groups.md` e `verifica.md` (task manuale dedicato, come 02-T11 e 04-T15) | manuale |

Verifica manuale (dalla spec): se il tenant azzera i campi omessi, la CLI è già una patch e la
libreria resta com'è (decisione della spec); se rimuove i blocchi di credenziali omessi, idem,
perché `edit-credentials` rimanda i blocchi letti. Se invece il server rifiuta un corpo che la spec
dà per buono (per esempio `userSettings` con quattro chiavi, o `memberIds` vuota), la correzione
passa da una revisione della spec, non da un aggiustamento silenzioso.

## Revisione dopo la prova sul tenant (T15, 2026-10-10)

- `api/_base.py`: `_get` con `204` senza corpo solleva `NotFoundError(status_code=204,
  request_method="GET", request_url=path)`; gli hook non vedono l'errore (non passa dal transport),
  come per il `TypeError` sul corpo non-oggetto. Caratterizzazione: `test_api_base.py`.
- `cli/users_write.py`: via `_credentials_base`, `_apply_credentials_flags`, `_CREDENTIAL_DTOS`
  e `_READ_ONLY_CREDENTIAL_KEYS`; al loro posto `_credentials_blocks(...)`, funzione pura dai
  flag e da `--json`, e il comando legge il form solo per l'`occToken`. `--yes/-y` e la conferma
  per blocco rimosso come in `users delete`.
- `test_users_integration.py`: `edit` con `firstname`, `lastname` e `contact_email` letti dal
  form; `edit_credentials` prima con `custom={"username", "canUserManageCustomCredentials": True,
  "active": True}` e poi con `custom={"active": False}` (rimozione); dopo `delete` il form
  risponde `204` → `NotFoundError`.
- Strategia di test aggiunta: 05-C27 `test_api_base.py::TestResourceClientEmptyBodies::
  test_get_204_raises_not_found` e `test_cli_users.py::TestUsersGetForEdit::test_204_exits_5`;
  05-C28 `test_cli_users_write.py::TestUsersEditCredentials` riscritta (corpo esatto per ogni
  flag, `--json` per blocco, `--occ-token` senza `GET`, flag contrastanti e corpo vuoto → exit
  `2`); 05-C29 `::TestUsersEditCredentialsConfirm` con `_stdin_is_interactive` monkeypatchato.
  05-C14 è sostituito: i test della patch se ne vanno con il codice.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| Scritture dentro `api/users.py` e `api/groups.py` | moduli `api/users_write.py` e `api/groups_write.py` come i post | Quattro o cinque metodi per modulo: la divisione dei post serviva per quindici endpoint; i task sono inline |
| Comandi CLI in `cli/users_write.py` e `cli/groups_write.py`, registrati sull'app esistente | inline in `cli/users.py` (389 righe) e `cli/groups.py` | Convenzione già usata da `posts_write.py`; i moduli di lettura restano leggibili; un solo `app` per gruppo di comandi |
| `UserWriteResult` unico per `create`, `edit`, `edit_credentials`, con `user_id` passato dove la risposta non lo ha | tre façade; restituire solo `next_occ_token` | Stessa forma di `TaskWriteResult` e `PostWriteResult`; un oggetto con `.raw` anche per le risposte minime |
| `GroupWriteResult` anche per `edit_members` (dal `GroupDTOModel` restituito) e `GroupSummary` per le liste del bulk | façade distinte per il singolo; dict grezzi nel bulk | Il chiamante vede `group_id` e `next_occ_token` nello stesso posto per tutte le scritture di gruppo |
| `ConcurrencyError` costruita nell'API con `status_code=200` e il corpo | sottoclasse nuova; `status_code=409` finto | È lo stesso concetto (RF-025): la CLI lo mappa su `9` senza righe in più; lo stato reale resta visibile a chi fa debug |
| Patch con funzioni pure che rivalidano i blocchi letti nei DTO di richiesta (`AdminUserPreferencesDTO`, `UserInfoDTO1`, `UserSettingsRequestDTO1`, `*CredentialsConfigurationDTO*`) e dumpano senza `None` | passare i dict letti così come sono; filtrare a mano per nome di chiave | Il filtro segue il swagger, non un elenco scritto a mano; i campi di sola lettura cadono da soli; testabile senza CLI |
| `memberIds` sempre presente nella base di `groups edit`, anche vuota | ometterla quando il gruppo non ha membri | La lista è il contratto del `PUT`; un gruppo vuoto deve restare vuoto, non "non specificato" |
| `read_password` in `cli/_write.py` con `_stdin_is_interactive` di `_common.py` | `typer.Option(prompt=True, hide_input=True)` | Con `prompt=True` Typer chiederebbe sempre, anche negli script: serve il ramo stdin non interattivo; l'helper si testa senza TTY |
| `--password-stdin` e `--json -` mutuamente esclusivi | leggere la password dalla prima riga e il JSON dal resto | Due consumatori dello stesso stream sono una fonte di errori silenziosi; il caso d'uso non esiste |
| `groups edit-members` con `GROUP_ID` opzionale e due modalità | due comandi (`edit-members` e `edit-members-bulk`) | Un comando per un'operazione, come la spec; le due modalità si escludono con messaggi chiari |
| Bulk: righe `_MembersRow` con `raw` → `GroupSummary.raw` | due tabelle; solo `--output json` | `render_output` resta l'unico renderer; `--full`/`--fields`/`--export` compongono (voce di checklist) |
| `JsonBodyOption` e `OccTokenOption` spostati in `_write.py` | copiarli in ogni modulo | Tre moduli li usano; `tasks.py` li importa senza cambiare comportamento |
| Fixture `get_user_for_edit_response.json` corretta alla forma del swagger | fixture nuova per la patch | Una sola fixture per `users get-for-edit` e `users edit`; le chiavi inventate (`language`, `timezone`) non esistono nel DTO |
| Integration: ciclo utente in `tests/integration/test_users_integration.py` nuovo, gating con una variabile a `1` | nel file di `admin_manage`; gating sulla sola presenza della variabile | Un file per risorsa (convenzione); `=1` rende l'opt-in intenzionale, una riga vuota nel `.env` non basta |
| Commit `feat(users):`, `feat(groups):`, `feat(cli):`, `test:`, `docs:` | `feat(admin):` | Scope per risorsa come la storia del progetto; semantic-release calcola 0.13.0 |

## Rischi

- **Semantica del server sui campi omessi diversa dai task** → l'integration test lo scopre
  (05-C26); la CLI è già una patch e la libreria resta esplicita: cambia solo la documentazione.
- **`userSettings` o `userPreferences` con chiavi inattese nella risposta reale** → i DTO
  tipizzati ignorano le chiavi sconosciute; la patch rimanda solo ciò che il DTO di richiesta
  conosce. Se il server esige una chiave che il DTO non ha, lo dice la prova sul tenant.
- **Form del gruppo con elenco membri troncato** → la patch di `groups edit` potrebbe ridurre il
  gruppo. L'integration test lo verifica su un gruppo piccolo; `docs/cli.md` avverte di usare
  `edit-members` per i gruppi grandi finché la prova non dice il contrario.
- **`occToken` del `GroupDTO` restituito da `edit_members` non è il token successivo** → 05-C26
  lo accerta (edit con quel token subito dopo); se non lo è, `docs/api/groups.md` dice di
  rileggere il form.
- **Password letta da stdin nei test con `CliRunner`** → `input=` di `CliRunner` alimenta
  `sys.stdin`; il ramo interattivo si testa sostituendo `_stdin_is_interactive` e `typer.prompt`,
  mai leggendo un TTY.
- **Password in output di test o snapshot** → gli snapshot contengono solo la password finta della
  fixture (`Xk7-fake-pw`); l'integration test stampa lunghezza e tipo.
- **Refactor di `JsonBodyOption`/`OccTokenOption`** → `test_cli_tasks.py` e gli snapshot di
  `tasks --help` (se esistono) si eseguono subito dopo lo spostamento; l'help di `--json` cambia
  testo, non comportamento.
- **Copertura di `users_write.py` e `groups_write.py`** → ogni ramo di errore (`--json` non
  valido, coppie di flag vietate, `occ_token` assente, blocchi assenti nel form, gruppo assente
  dalla risposta) ha un test dedicato.
- **`GroupDTO` stub nelle liste del bulk** → rivalidazione in `GroupDTOModel` con `_resolve_root`;
  il contract test (05-C22) mostra se `GroupDTOModel` non copre tutte le proprietà.
- **Integration test degli utenti eseguito per sbaglio** → gating su `=1` e nome riconoscibile;
  `delete` in `finally` anche se un passo intermedio fallisce; il test salta se la creazione
  stessa fallisce prima di restituire un id.
