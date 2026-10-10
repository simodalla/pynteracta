# 05 – Anagrafiche admin, prima metà: utenti e gruppi

Stato: approvata
Branch: `m31_admin_users_groups`
Requisiti del PRD: RF-023, RF-025, RF-025a, RF-015, RF-015a, RNF-001, RNF-009; toccati RF-005,
RF-011, RF-013, RF-019, §6 "Dati scritti sul tenant"
Dipende da: spec 02 (conferma dei comandi distruttivi, exit code 9, `--json`), spec 03 (unione di
`--json` e flag, validazione del corpo contro il DTO), spec 04 (nessuna dipendenza di codice;
precede nella numerazione delle versioni)

Quarta spec della superficie di scrittura aperta da
[ADR 0001](../adr/0001-apertura-della-superficie-di-scrittura.md): la prima metà del gruppo admin
(8 endpoint su 15). La seconda metà (cataloghi, voci di catalogo, workspace) è la spec 06.

## Scopo

Chi scrive automazioni con la libreria, e chi usa la CLI, può creare, modificare ed eliminare
utenti e gruppi del tenant, impostare le credenziali di un utente e aggiungere o togliere membri a
uno o più gruppi, con la stessa forma delle letture: metodi tipizzati con kwargs espliciti e
varianti `*_raw`, façade con `.raw`, comandi `users create|edit|delete|edit-credentials` e
`groups create|edit|delete|edit-members` che compongono con `--output`, `--full`, `--fields`,
`--export`. La concorrenza ottimistica resta visibile al chiamante; nessuna scrittura viene
ripetuta da sola; nessuna password passa dalla riga di comando né finisce nei log.

## Comportamento attuale

Su utenti e gruppi esistono solo letture. `client.users.get_for_edit(user_id)` restituisce
`UserForEdit` (nome, cognome, email di contatto, external id, `blocked`, foto, `.raw`),
`client.groups.get_for_edit(group_id)` restituisce `GroupForEdit` (nome, email, descrizione,
visibilità, membri tipizzati, `.raw`) e `client.admin_manage.user_credentials_for_edit(user_id)`
restituisce `UserCredentialsForEdit` (quali credenziali sono configurate, username e stato di
quelle custom, `.raw`). Le tre façade non espongono `occToken`, che il server restituisce e che è
raggiungibile solo da `.raw`. La CLI ha `users get-for-edit`, `groups get` e `admin-manage
user-credentials`. Il client base sa già fare `PUT` e `DELETE` (spec 02 e 03); `409` è mappato
su `ConcurrencyError` ed esce con `9` (spec 02); i comandi distruttivi hanno il prompt con
`--yes` e il rifiuto senza terminale (spec 02). I 13 DTO di richiesta e risposta delle otto
scritture sono già nei modelli generati dal swagger pinnato: nessuna rigenerazione.

## Comportamento

### Libreria: utenti

- **Creare**: `client.users.create(*, firstname=None, lastname=None, contact_email=None,
  private_email=None, external_id=None, user_preferences=None, user_info=None,
  user_settings=None, user_credentials_configuration=None,
  reset_user_custom_credentials_command=None)` invia `POST admin/manage/users` con **solo i campi
  passati**, in camelCase, e restituisce un `UserWriteResult` con `user_id`, `next_occ_token`,
  `generated_password` (la lista di stringhe che il server restituisce quando ha generato una
  password custom), `expired_credentials`, `sent_email_notify`, `account_photo_url` e `.raw`.
  I blocchi annidati (preferenze, info, impostazioni, configurazione delle credenziali, comando di
  reset delle credenziali custom) si passano come dizionari nella forma del DTO (chiavi camelCase)
  o come DTO generati. `create_raw(req: CreateUserRequestDTO)` fa lo stesso da un DTO già
  costruito.
- **Modificare**: `client.users.edit(user_id, occ_token, *, firstname=None, lastname=None,
  contact_email=None, private_email=None, external_id=None, user_preferences=None,
  user_info=None, user_settings=None)` invia `PUT admin/manage/users/{user_id}` con l'`occToken`
  nel corpo e **solo i campi passati**; restituisce un `UserWriteResult` con `user_id` (quello
  passato), `next_occ_token` e `account_photo_url`. `edit_raw(user_id, req: EditUserRequestDTO)`
  idem, con l'`occToken` dentro il DTO. `occ_token` lo fornisce il chiamante: lo legge da
  `UserForEdit.occ_token`, che la lettura ora espone.
- **Eliminare**: `client.users.delete(user_id)` invia `DELETE admin/manage/users/{user_id}` e non
  restituisce nulla (la risposta non ha corpo).
- **Credenziali**: `client.users.edit_credentials(user_id, occ_token, *, google=None,
  microsoft=None, custom=None)` invia `PUT admin/manage/users/{user_id}/credentials` con
  `userCredentialsConfiguration` composto dai **soli blocchi passati** (ciascuno un dizionario nella
  forma del DTO o il DTO generato) e l'`occToken` nel corpo; restituisce un `UserWriteResult` con
  `user_id` e `next_occ_token`. `edit_credentials_raw(user_id, req: EditUserCredentialsRequestDTO)`
  idem. Il token si legge da `UserCredentialsForEdit.occ_token`. La password custom si imposta o
  si fa generare **solo alla creazione** (`resetUserCustomCredentialsCommand`): il DTO di modifica
  delle credenziali non la prevede.
- **Lettura delle credenziali**: `client.users.get_credentials_for_edit(user_id)` è un alias di
  `client.admin_manage.user_credentials_for_edit(user_id)`, che resta: stessa richiesta, stessa
  façade.
- **`occ_token`**: `UserForEdit`, `GroupForEdit` e `UserCredentialsForEdit` espongono
  `occ_token` come proprietà, oltre che su `.raw`.
- **Campi omessi in `edit` ed `edit_credentials`**: non vengono inviati. La semantica del server
  (sostituzione come per i task, o aggiornamento parziale; un blocco di credenziali omesso
  rimosso o mantenuto) si stabilisce con la prova sul tenant (05-C26) e si documenta in
  `docs/api/users.md`; la libreria non aggiunge nulla da sola.
- **Errori**: come per le letture (`400 → ValidationError`, `403 → PermissionError`,
  `404 → NotFoundError`, `409 → ConcurrencyError`, timeout e rete → `TransportError`). Una
  scrittura che fallisce in modo incerto non si ripete: una sola richiesta per chiamata, sempre.

### Libreria: gruppi

- **Creare**: `client.groups.create(*, name=None, email=None, external_id=None, visible=None,
  member_ids=None)` invia `POST admin/manage/groups` con **solo i campi passati** e restituisce un
  `GroupWriteResult` con `group_id`, `next_occ_token`, `name`, `email`, `visible`,
  `members_count` e `.raw`. `create_raw(req: CreateGroupRequestDTO)` idem.
- **Modificare**: `client.groups.edit(group_id, occ_token, *, name=None, email=None,
  external_id=None, visible=None, member_ids=None)` invia `PUT admin/manage/groups/{group_id}` con
  l'`occToken` nel corpo e **solo i campi passati**; `member_ids`, se passato, è la lista
  **completa** dei membri. Restituisce un `GroupWriteResult` con `group_id` (quello passato) e
  `next_occ_token`. `edit_raw(group_id, req: EditGroupRequestDTO)` idem. Il token si legge da
  `GroupForEdit.occ_token`.
- **Eliminare**: `client.groups.delete(group_id)` invia `DELETE admin/manage/groups/{group_id}` e
  non restituisce nulla.
- **Membri di un gruppo**: `client.groups.edit_members(group_id, occ_token, *, add_user_ids=None,
  remove_user_ids=None)` invia `PUT admin/manage/groups/members` con un solo elemento in
  `groupMembers` (`id`, `occToken`, `addUserIds`, `deleteUserIds`, solo le chiavi passate). Il
  server risponde `200` con due liste: se il gruppo è in `successGroups`, il metodo restituisce un
  `GroupWriteResult` con `group_id`, `next_occ_token` (l'`occToken` del gruppo restituito) e i
  dati del gruppo; se è in `concurrencyErrorGroups`, solleva `ConcurrencyError` (stato `200`,
  corpo della risposta allegato); se non è in nessuna delle due, solleva `InteractaError` con il
  corpo. Una sola richiesta in ogni caso.
- **Membri di più gruppi**: `client.groups.edit_members_bulk(groups)` prende una lista di elementi
  nella forma del DTO (`{"id", "occToken", "addUserIds", "deleteUserIds"}`, dizionari o DTO
  generati), invia **una sola** `PUT admin/manage/groups/members` e restituisce un
  `GroupMembersResult` con `success_groups` e `concurrency_error_groups` (liste di façade con
  `id`, `name`, `email`, `occ_token`, `members_count`, `.raw`) e `.raw`; **non solleva** per i
  conflitti: decide il chiamante. `edit_members_bulk_raw(req: EditMultipleGroupsMembersRequestDTO)`
  idem.

### CLI: utenti

- `pynteracta users create [--first-name N] [--last-name C] [--contact-email E]
  [--private-email E] [--external-id X] [--google-account EMAIL] [--microsoft-account EMAIL]
  [--username U] [--generate-password | --password-stdin] [--force-password-change]
  [--notify-email ADDR]… [--json FILE|-]` crea l'utente e mostra il risultato con `render_output`
  (tabella curata: `user_id`, `next_occ_token`, `generated_password`, `expired_credentials`,
  `sent_email_notify`; `--output json`, `--full`, `--fields`, `--export` come per gli altri
  comandi). `--json` prende il DTO completo da file o da stdin (`-`): serve per preferenze, info,
  impostazioni e foto profilo; se compaiono anche i flag, i flag prevalgono campo per campo.
  `--google-account` e `--microsoft-account` riempiono i blocchi `google` e `microsoft` di
  `userCredentialsConfiguration` con `enabled: true`; `--username` riempie `custom.username` con
  `active: true`; `--generate-password`, `--password-stdin`, `--force-password-change` e
  `--notify-email` riempiono `resetUserCustomCredentialsCommand` (`generatePassword`,
  `password: [<valore>]`, `forceCredentialsExpiration`, `emailNotifyRecipients`).
- **Password**: non esiste un flag `--password VALORE`. `--password-stdin` legge la password
  dallo standard input (prima riga, senza il fine riga) quando non è un terminale, altrimenti la
  chiede con un prompt nascosto, ripetuto per conferma; `--generate-password` la fa generare al
  server. I due flag insieme → errore d'uso (exit `2`), nessuna richiesta. `--password-stdin` e
  `--json -` insieme → errore d'uso (exit `2`): lo stdin serve a uno solo. La password generata
  compare nell'output del comando (tabella e `json`), perché l'operatore deve consegnarla;
  `docs/cli.md` avverte che `--export` la scrive su file.
- `pynteracta users edit USER_ID [--first-name N] [--last-name C] [--contact-email E]
  [--private-email E] [--external-id X] [--json FILE|-] [--occ-token N]` è una **patch**: legge
  il form di modifica, costruisce il corpo dai valori letti che il DTO di modifica accetta
  (`firstname`, `lastname`, `contactEmail`, `privateEmail`, `externalId`, `userPreferences`,
  `userInfo`, `userSettings` ridotto alle quattro chiavi del DTO di richiesta), vi sovrappone il
  corpo di `--json` e poi i flag, e invia la modifica con l'`occToken` letto. Un campo assente nel
  form non viene inventato. `--occ-token N` impone il token; la lettura avviene comunque, perché
  serve per il corpo. Su `409` esce con `9` e il messaggio `User USER_ID changed since it was
  read: fetch it again and retry`. Mai un secondo tentativo. Mostra il risultato con
  `render_output` (`user_id`, `next_occ_token`, `account_photo_url`).
- `pynteracta users edit-credentials USER_ID [--google-account EMAIL | --no-google]
  [--microsoft-account EMAIL | --no-microsoft] [--username U] [--custom-active/--custom-inactive]
  [--no-custom] [--json FILE|-] [--occ-token N]` è una **patch** sul form delle credenziali:
  legge `userCredentialsConfiguration`, vi sovrappone `--json` e i flag (`--google-account` e
  `--microsoft-account` impostano l'account id e `enabled: true`; `--username` e
  `--custom-active/--custom-inactive` toccano il blocco `custom`; `--no-google`, `--no-microsoft`,
  `--no-custom` tolgono il blocco dal corpo) e invia con l'`occToken` letto; i campi di sola
  lettura del form (`profilePhotoUrl`, `canManageProfilePhoto`) non vengono rimandati. Esito e
  `409` come per `users edit`.
- `pynteracta users delete USER_ID [--yes|-y]` legge il form, mostra `Delete user USER_ID
  "<nome cognome>"? [y/N]` e procede solo con `y`; con `--yes` non chiede; senza terminale
  interattivo e senza `--yes` rifiuta con `--yes is required when not running interactively`
  (exit `2`) e nessuna richiesta di eliminazione parte. In caso di successo stampa `User USER_ID
  deleted` e, con `--output json`, `{"user_id": …}`.

### CLI: gruppi

- `pynteracta groups create --name N [--email E] [--external-id X] [--visible/--system]
  [--member ID]… [--json FILE|-]` crea il gruppo e mostra il risultato con `render_output`
  (`group_id`, `name`, `email`, `visible`, `members_count`, `next_occ_token`). `--member`
  ripetibile riempie `memberIds`; i flag prevalgono su `--json`.
- `pynteracta groups edit GROUP_ID [--name N] [--email E] [--external-id X] [--visible/--system]
  [--json FILE|-] [--occ-token N]` è una **patch**: legge il form, costruisce il corpo da `name`,
  `email`, `externalId`, `visible` e `memberIds` (gli id dei membri letti), vi sovrappone `--json`
  e i flag e invia con l'`occToken` letto. Non ha flag sui membri: un `groups edit` non li cambia
  mai; `memberIds` in `--json` li sostituisce per intero. `409` → exit `9`, `Group GROUP_ID
  changed since it was read: fetch it again and retry`.
- `pynteracta groups delete GROUP_ID [--yes|-y]`: come `users delete`, con `Delete group GROUP_ID
  "<name>"? [y/N]`, `Group GROUP_ID deleted` e `{"group_id": …}`.
- `pynteracta groups edit-members GROUP_ID [--add ID]… [--remove ID]… [--occ-token N]` legge il
  form del gruppo per l'`occToken` (o usa `--occ-token`, senza lettura: qui il corpo non ne ha
  bisogno), invia la modifica dei membri del solo gruppo e mostra il gruppo restituito con
  `render_output` (`group_id`, `name`, `members_count`, `next_occ_token`). Senza `--add` né
  `--remove` → errore d'uso (exit `2`), nessuna richiesta. Conflitto → exit `9` con il messaggio
  di `groups edit`.
- `pynteracta groups edit-members --json FILE|-` (senza `GROUP_ID`, né `--add`/`--remove`) invia
  il DTO bulk così com'è e mostra una riga per gruppo con la colonna `result` (`success` o
  `concurrency_error`); se almeno un gruppo è in conflitto l'exit code è `9`, l'output resta
  completo. `GROUP_ID` e `--json` insieme → errore d'uso (exit `2`).

### Regole comuni della CLI

- I testi (help, prompt, messaggi) sono in inglese, come il resto della CLI.
- `--json` con JSON non valido, stdin vuoto o chiavi sconosciute al DTO → exit `2`, nessuna
  richiesta (comportamento delle spec 02 e 03).
- Exit code: `9` su `ConcurrencyError` (RF-015a), gli altri come oggi (`4` permessi, `5` non
  trovato, `6` validazione, `7` trasporto).

### Documentazione e test

`docs/api/users.md` (metodi, `UserWriteResult`, `occ_token`, credenziali, semantica dei campi
omessi verificata sul tenant), `docs/api/groups.md` (metodi, `GroupWriteResult`,
`GroupMembersResult`, singolo contro bulk), `docs/api/admin_manage.md` (rimando a
`users.get_credentials_for_edit`), `docs/cli.md` (otto comandi, password, `--json`, exit `9`),
`docs/testing.md` e `tests/integration/.env.example` (`PYNTERACTA_TEST_WRITE_USERS`,
`PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN`). `docs/index.md` e `README.md` dicono che le scritture
admin su utenti e gruppi ci sono e che restano da fare i post evento, i cataloghi e il workspace,
senza numeri di versione. Fixture JSON e contract test per i 13 DTO. Snapshot `syrupy` per gli
otto comandi. Integration test opt-in: ciclo del gruppo e, con opt-in dedicato, ciclo
dell'utente, entrambi con pulizia garantita.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 05-C01 | Quando si chiama `client.users.create(firstname="A", lastname="B", contact_email="a@b.it", user_credentials_configuration={"custom": {"username": "ab", "active": True}}, reset_user_custom_credentials_command={"generatePassword": True})`, parte una sola `POST …/admin/manage/users` con corpo `{"firstname": "A", "lastname": "B", "contactEmail": "a@b.it", "userCredentialsConfiguration": {"custom": {"username": "ab", "active": true}}, "resetUserCustomCredentialsCommand": {"generatePassword": true}}` (nessun'altra chiave) e, con una risposta `CreateUserResponseDTO`, il risultato ha `user_id`, `next_occ_token`, `generated_password`, `expired_credentials`, `sent_email_notify`, `account_photo_url` e `.raw` valorizzati dalla risposta; `create_raw` con il DTO equivalente produce la stessa richiesta. | RF-023 |
| 05-C02 | Quando si chiama `client.users.edit(42, 5, lastname="C", user_settings={"reducedProfile": True})`, parte una sola `PUT …/admin/manage/users/42` con corpo `{"lastname": "C", "userSettings": {"reducedProfile": true}, "occToken": 5}` e il risultato ha `user_id == 42`, `next_occ_token` e `account_photo_url` dalla risposta `EditUserResponseDTO`; `edit_raw(42, EditUserRequestDTO(...))` produce la stessa richiesta. | RF-023, RF-025 |
| 05-C03 | Quando si chiama `client.users.delete(42)`, parte una sola `DELETE …/admin/manage/users/42` e il metodo restituisce `None`; con risposta `404` solleva `NotFoundError`. | RF-023, RF-019 |
| 05-C04 | Quando si chiama `client.users.edit_credentials(42, 5, google={"googleAccountId": "a@b.it", "enabled": True})`, parte una sola `PUT …/admin/manage/users/42/credentials` con corpo `{"userCredentialsConfiguration": {"google": {"googleAccountId": "a@b.it", "enabled": true}}, "occToken": 5}` e il risultato ha `user_id == 42` e `next_occ_token` dalla risposta; `edit_credentials_raw` con il DTO equivalente produce la stessa richiesta. | RF-023, RF-025 |
| 05-C05 | Quando il server risponde `409` a `users.edit`, `users.edit_credentials` o `groups.edit`, viene sollevata `ConcurrencyError` con `status_code == 409` e il server ha ricevuto **esattamente una** richiesta. | RF-025, RNF-009 |
| 05-C06 | Quando `users.get_for_edit(42)`, `groups.get_for_edit(7)` e `admin_manage.user_credentials_for_edit(42)` ricevono risposte con `occToken: 5`, le façade hanno `occ_token == 5`; `client.users.get_credentials_for_edit(42)` fa la stessa `GET …/admin/manage/users/42/credentials/edit` e restituisce la stessa façade. | RF-023a, RF-005, RF-011, RF-013 |
| 05-C07 | Quando si chiama `client.groups.create(name="G", visible=True, member_ids=[1, 2])`, parte una sola `POST …/admin/manage/groups` con corpo `{"name": "G", "visible": true, "memberIds": [1, 2]}` e il risultato ha `group_id`, `next_occ_token`, `name`, `visible`, `members_count` e `.raw` dalla risposta `CreateGroupResponseDTO`; `create_raw` produce la stessa richiesta. | RF-023 |
| 05-C08 | Quando si chiama `client.groups.edit(7, 3, name="G2")`, parte una sola `PUT …/admin/manage/groups/7` con corpo `{"name": "G2", "occToken": 3}` e il risultato ha `group_id == 7` e `next_occ_token` dalla risposta; `edit_raw(7, EditGroupRequestDTO(...))` produce la stessa richiesta; `client.groups.delete(7)` fa una sola `DELETE …/admin/manage/groups/7` e restituisce `None`. | RF-023, RF-025 |
| 05-C09 | Quando si chiama `client.groups.edit_members(7, 3, add_user_ids=[1], remove_user_ids=[2])`, parte una sola `PUT …/admin/manage/groups/members` con corpo `{"groupMembers": [{"id": 7, "occToken": 3, "addUserIds": [1], "deleteUserIds": [2]}]}`; con una risposta che ha il gruppo 7 in `successGroups` con `occToken: 4`, il risultato ha `group_id == 7` e `next_occ_token == 4`; con il gruppo 7 in `concurrencyErrorGroups` solleva `ConcurrencyError`; con il gruppo in nessuna delle due solleva `InteractaError`. In tutti i casi il server ha ricevuto una sola richiesta. | RF-023, RF-023c, RF-025, RNF-009 |
| 05-C10 | Quando si chiama `client.groups.edit_members_bulk([{"id": 7, "occToken": 3, "addUserIds": [1]}, {"id": 8, "occToken": 1, "deleteUserIds": [2]}])`, parte una sola `PUT …/admin/manage/groups/members` con quei due elementi in `groupMembers` e, con una risposta che ha il 7 in `successGroups` e l'8 in `concurrencyErrorGroups`, il risultato ha `success_groups[0].id == 7`, `concurrency_error_groups[0].id == 8` e nessuna eccezione; `edit_members_bulk_raw` con il DTO equivalente produce la stessa richiesta. | RF-023, RF-023c |
| 05-C11 | Quando si esegue `users create --first-name A --last-name B --contact-email a@b.it --username ab --generate-password --json body.json` con `body.json` = `{"firstname": "X", "userPreferences": {"defaultLanguageId": "it"}}`, il corpo inviato è `{"firstname": "A", "lastname": "B", "contactEmail": "a@b.it", "userPreferences": {"defaultLanguageId": "it"}, "userCredentialsConfiguration": {"custom": {"username": "ab", "active": true}}, "resetUserCustomCredentialsCommand": {"generatePassword": true}}` (i flag prevalgono) e l'output tabella mostra `user_id`, `next_occ_token` e `generated_password` della risposta; `--output json` restituisce la risposta serializzata con `generated_password`. | RF-023, RF-023b, RF-015 |
| 05-C12 | Quando si esegue `users create --username ab --password-stdin` con stdin non interattivo che contiene `S3gret!\n`, il corpo ha `resetUserCustomCredentialsCommand.password == ["S3gret!"]` e la password non compare in stdout né in stderr; con stdin interattivo la password è chiesta con un prompt nascosto e confermata; `--generate-password --password-stdin` insieme, oppure `--password-stdin --json -`, → exit `2` e nessuna richiesta; `users create --help` non elenca alcuna opzione `--password`. | RF-023b, RNF-001 |
| 05-C13 | Quando si esegue `users edit 42 --last-name C` e la `GET …/admin/manage/users/42/edit` restituisce un form con `firstname`, `lastname`, `contactEmail`, `privateEmail`, `externalId`, `userPreferences`, `userInfo`, `userSettings` (con `editPrivateEmailEnabled`) e `occToken: 5`, la `PUT …/admin/manage/users/42` ha corpo `{"firstname": <letto>, "lastname": "C", "contactEmail": <letto>, "privateEmail": <letto>, "externalId": <letto>, "userPreferences": <letto>, "userInfo": <letto>, "userSettings": {le quattro chiavi del DTO di richiesta}, "occToken": 5}` e nessun'altra chiave; con `--json body.json` = `{"externalId": "E9"}` e `--external-id E10` vince `E10`; con `--occ-token 6` la `GET` avviene lo stesso e la `PUT` usa `6`; quando il form non ha `privateEmail`, la chiave manca dal corpo. | RF-023, RF-023b, RF-025 |
| 05-C14 | Quando si esegue `users edit-credentials 42 --google-account a@b.it --no-custom` e la `GET …/admin/manage/users/42/credentials/edit` restituisce `google`, `microsoft` e `custom` (con `profilePhotoUrl` e `canManageProfilePhoto`) e `occToken: 5`, la `PUT …/admin/manage/users/42/credentials` ha corpo `{"userCredentialsConfiguration": {"google": {"googleAccountId": "a@b.it", "enabled": true}, "microsoft": <letto senza i campi di sola lettura>}, "occToken": 5}`: nessun `custom`, nessun `profilePhotoUrl`. | RF-023, RF-023b, RF-025 |
| 05-C15 | Quando la `PUT` di `users edit`, `users edit-credentials` o `groups edit` risponde `409`, il comando termina con exit code `9`, stampa `User 42 changed since it was read: fetch it again and retry` (o `Group 7 …`) e il server ha ricevuto una sola `PUT`. | RF-025, RF-015a, RNF-009 |
| 05-C16 | Quando si esegue `users delete 42` in un terminale interattivo, il prompt è `Delete user 42 "A B"? [y/N]` (nome e cognome dal form letto); con `y` parte la `DELETE` e il comando stampa `User 42 deleted` (`--output json`: `{"user_id": 42}`); con `n` nessuna `DELETE` parte ed exit `0`; con `--yes` nessun prompt; senza terminale e senza `--yes` nessuna `DELETE`, exit `2` e il messaggio dice che serve `--yes`. `groups delete 7` si comporta allo stesso modo con `Delete group 7 "G"? [y/N]` e `Group 7 deleted`. | RF-025, RF-025a |
| 05-C17 | Quando si esegue `groups create --name G --member 1 --member 2 --system`, il corpo è `{"name": "G", "memberIds": [1, 2], "visible": false}` e l'output tabella mostra `group_id`, `name`, `members_count`, `next_occ_token`; quando si esegue `groups edit 7 --name G2` e il form letto ha `name`, `email`, `externalId`, `visible`, `members` con id `[1, 2]` e `occToken: 3`, la `PUT …/admin/manage/groups/7` ha corpo `{"name": "G2", "email": <letto>, "externalId": <letto>, "visible": <letto>, "memberIds": [1, 2], "occToken": 3}`. | RF-023, RF-023b, RF-015 |
| 05-C18 | Quando si esegue `groups edit-members 7 --add 1 --remove 2` e il form letto ha `occToken: 3`, parte una sola `PUT …/admin/manage/groups/members` con corpo `{"groupMembers": [{"id": 7, "occToken": 3, "addUserIds": [1], "deleteUserIds": [2]}]}` e l'output mostra `group_id`, `members_count`, `next_occ_token` del gruppo restituito; con `--occ-token 4` nessuna `GET` avviene e il corpo usa `4`; se il gruppo torna in `concurrencyErrorGroups` l'exit code è `9`; senza `--add` né `--remove` exit `2` e nessuna richiesta. | RF-023, RF-023b, RF-023c, RF-025 |
| 05-C19 | Quando si esegue `groups edit-members --json body.json` con due gruppi e la risposta ne ha uno in `successGroups` e uno in `concurrencyErrorGroups`, l'output ha una riga per gruppo con `result` `success` e `concurrency_error` e l'exit code è `9`; con tutti in `successGroups` l'exit code è `0`; `groups edit-members 7 --json body.json` → exit `2`, nessuna richiesta. | RF-023b, RF-023c, RF-015a |
| 05-C20 | Quando una richiesta ha nel corpo `resetUserCustomCredentialsCommand.password` e la risposta ha `generatedPassword`, i body che raggiungono log applicativi, audit log (anche con `audit_log_bodies`) e hook hanno `***REDACTED***` al posto di entrambi i valori; il valore in chiaro non compare in nessun record. | RNF-001 |
| 05-C21 | Quando `users.create` o `groups.create` va in timeout o errore di rete, viene sollevata `TransportError` e il server ha ricevuto al più una richiesta. | RNF-009 |
| 05-C22 | I contract test dimostrano che i modelli generati `CreateUserRequestDTO`, `CreateUserResponseDTO`, `EditUserRequestDTO`, `EditUserResponseDTO`, `EditUserCredentialsRequestDTO`, `EditUserCredentialsResponseDTO`, `CreateGroupRequestDTO`, `CreateGroupResponseDTO`, `EditGroupRequestDTO`, `EditGroupResponseDTO`, `EditMultipleGroupsMembersRequestDTO`, `EditGroupMembersRequestDTO`, `EditMultipleGroupsMembersResponseDTO` coprono tutte le proprietà del swagger pinnato, e le fixture JSON di risposta si leggono nelle façade. | RF-023, RNF-003 |
| 05-C23 | `docs/cli.md` documenta gli otto comandi, i flag della password e l'exit `9`; `docs/api/users.md` e `docs/api/groups.md` documentano i metodi, le façade di risultato, `occ_token` e la semantica dei campi omessi verificata sul tenant; `docs/index.md` e `README.md` non dicono più che le scritture admin su utenti e gruppi sono da fare; `uv run mkdocs build --strict` e `test_docs_snippets` sono verdi. | RF-015 |
| 05-C24 | Quando `PYNTERACTA_TEST_USER_ID` e l'ambiente integration sono impostati (opt-in), il ciclo `groups.create` (nome `pynteracta-it-<timestamp>`, `visible=False`) → `get_for_edit` (`occ_token`) → `edit` → `edit_members` (aggiunta e rimozione dell'utente di prova) → `delete` termina senza errori sul tenant e il gruppo non esiste più al termine, anche se un passo intermedio fallisce; senza le variabili il test è saltato. | RF-023, RF-025 |
| 05-C25 | Quando, oltre all'ambiente integration, `PYNTERACTA_TEST_WRITE_USERS=1` è impostata (opt-in dedicato), il ciclo `users.create` (nome `pynteracta-it`, cognome `<timestamp>`, email `pynteracta-it-<timestamp>@<PYNTERACTA_TEST_WRITE_USER_EMAIL_DOMAIN, default example.com>`, credenziali custom con password generata) → `get_for_edit` (`occ_token`) → `edit` → `get_credentials_for_edit` → `edit_credentials` → `delete` termina senza errori e l'utente non esiste più al termine, anche se un passo intermedio fallisce; senza la variabile il test è saltato. | RF-023, RF-025 |
| 05-C26 | L'esecuzione di 05-C24 e 05-C25 stabilisce e registra in `docs/api/users.md`, `docs/api/groups.md` e `verifica.md`: l'effetto dei campi omessi in `users.edit`, `groups.edit` ed `edit_credentials` (azzerati o mantenuti; blocco di credenziali omesso rimosso o mantenuto), l'effetto di `delete` (l'utente o il gruppo sparisce dall'elenco o resta con `deleted: true`), il formato di `generated_password` e il significato dell'`occToken` del gruppo restituito da `edit_members`. | RF-023, RF-025 |

## Casi limite

- `create` senza alcun campo → corpo `{}` inviato così com'è; decide il server (05-C01: nessuna
  chiave in più oltre a quelle passate).
- `edit` con tutti i kwargs a `None` → `PUT` con corpo `{"occToken": N}` (05-C02, 05-C08).
- `occ_token` sbagliato → `409 → ConcurrencyError`, una sola richiesta (05-C05); in
  `edit_members` il conflitto arriva con `200` e il gruppo in `concurrencyErrorGroups` →
  `ConcurrencyError` lo stesso (05-C09).
- `edit_members` con gruppo in nessuna delle due liste (risposta inattesa) → `InteractaError`
  con il corpo (05-C09).
- `edit_members_bulk` con lista vuota → corpo `{"groupMembers": []}` inviato così com'è; decide il
  server (05-C10: solo ciò che è passato).
- `delete` di un utente o gruppo inesistente → `404 → NotFoundError`, exit `5` in CLI (05-C03;
  mapping esistente).
- `users edit`, `users edit-credentials`, `groups edit`, `groups edit-members GROUP_ID` su un
  form che la `GET` non trova → exit `5`, nessuna `PUT`, anche con `--occ-token` dove la lettura
  avviene comunque (05-C13, 05-C14, 05-C17); `groups edit-members GROUP_ID --occ-token N` non
  legge nulla (05-C18).
- `users edit` su un form senza `privateEmail` (o altri campi) → la chiave manca dal corpo, non
  viene inventata (05-C13).
- `users edit-credentials` con `--no-google` quando il form non ha `google` → nessun errore, il
  blocco resta assente (05-C14).
- `users create --password-stdin` con stdin vuoto → errore d'uso, exit `2`, nessuna richiesta
  (05-C12); con prompt interattivo e conferma diversa → nuovo prompt, come `typer.prompt` con
  conferma.
- `users create --generate-password` senza `--username` → inviato così com'è; decide il server
  (la libreria e la CLI non conoscono le regole del tenant).
- `groups edit --json` con `memberIds` → sostituisce per intero la lista letta (05-C17: `--json`
  prevale sul form).
- `groups edit` su un gruppo con molti membri: la patch rimanda tutti gli id letti dal form; se il
  form li tronca, lo dice la prova sul tenant (05-C26) e `docs/cli.md` avverte.
- `groups edit-members --json` con `--add` o `--remove` → exit `2`, nessuna richiesta (05-C19).
- `--json -` con stdin vuoto o JSON non valido, o `--json` con chiavi sconosciute → exit `2`,
  nessuna richiesta (comportamento delle spec 02 e 03).
- `users delete` o `groups delete` con risposta al prompt diversa da `y`/`Y` → nessuna richiesta,
  exit `0` (05-C16).
- Timeout **dopo** l'invio di `users.create` o `groups.create`: l'utente o il gruppo potrebbe
  esistere; la libreria solleva `TransportError` e non riprova (05-C21); il chiamante lo cerca con
  l'elenco filtrato per email o nome.
- `403` su qualunque scrittura (service account senza permessi admin) → `PermissionError`, exit
  `4` (mapping esistente).

## Dati personali e segreti

Passano al tenant: nome, cognome, email di contatto e privata, external id, preferenze,
impostazioni, area e business unit degli utenti; account Google e Microsoft, username e password
custom; nome, email e membri dei gruppi. La libreria li inoltra e non li conserva; l'audit log
opzionale li registra solo con `audit_log_bodies` (eccezione documentata), **tranne le password**:
`resetUserCustomCredentialsCommand.password` nella richiesta e `generatedPassword` nella risposta
sono chiavi che contengono `password`, quindi la redazione di RNF-001 le sostituisce con
`***REDACTED***` in log, audit log (anche con i body) e hook (05-C20); solo `audit_log_raw`, che
disattiva la redazione sul solo canale di logging con avviso, le lascerebbe passare (eccezione
già documentata da RF-017). Nei log applicativi compaiono solo metodo, URL redatto e stato. La
password custom arriva alla CLI da stdin o da prompt nascosto, mai da un argomento (niente history
della shell, niente `ps`); la password generata va solo su stdout, per l'operatore, e su file solo
se l'operatore chiede `--export`. Gli integration test creano un gruppo e, con opt-in dedicato, un
utente con nome ed email riconoscibili (`pynteracta-it-<timestamp>`, dominio di prova) e li
eliminano sempre al termine.

## Requisiti nuovi

- RF-023a (precisa RF-005, RF-011, RF-013). Le letture per la modifica (`UserForEdit`,
  `GroupForEdit`, `UserCredentialsForEdit`) espongono `occ_token`, il token di concorrenza da
  passare alla scrittura; `users.get_credentials_for_edit` è l'alias di
  `admin_manage.user_credentials_for_edit`.
- RF-023b (precisa RF-023 in CLI). `users edit`, `users edit-credentials` e `groups edit` sono
  patch che rileggono il form e rimandano i campi non indicati; `groups edit` non tocca i membri,
  che si cambiano con `groups edit-members`; la password custom arriva solo da stdin o da prompt
  (`--password-stdin`) o è generata dal server (`--generate-password`), mai da un argomento; la
  password generata compare nell'output di `users create`.
- RF-023c (precisa RF-025). `groups.edit_members` su un singolo gruppo solleva `ConcurrencyError`
  quando il server lo mette in `concurrencyErrorGroups`, anche se lo stato è `200`;
  `edit_members_bulk` restituisce le due liste senza sollevare.
- La semantica del server sui campi omessi, sull'eliminazione e sulla password generata entra in
  RF-023 alla chiusura, dopo 05-C26, come RF-022 per i task.

## Fuori ambito

- Cataloghi, voci di catalogo e workspace (seconda metà di RF-023): spec 06.
- Blocco e sblocco di un utente: il DTO di modifica non ha `blocked`; `UserForEdit.blocked`
  resta in sola lettura e `docs/api/users.md` lo dice.
- Foto profilo delle credenziali custom (`custom.profilePhoto.newContentRef`): passa come
  campo di `--json` o del dizionario `custom`; nessun flag e nessun upload dedicato (il
  `contentRef` si ottiene con `attachments upload`, spec 04).
- Reset della password di un utente esistente: l'API non lo prevede in `credentials`; si
  documenta.
- Post evento (RF-021), retry automatico e risoluzione automatica del `409` (RNF-009, ADR 0001).
- Comando di lettura `users credentials` in CLI: la lettura resta `admin-manage user-credentials`.
- Traduzione in italiano della CLI esistente.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Scritture su `client.users` e `client.groups`, credenziali comprese; alias `users.get_credentials_for_edit`, lettura su `admin_manage` mantenuta | Tutto su `admin_manage`; misto (credenziali solo su `admin_manage`) | Un agente cerca `users.create` accanto a `users.get_for_edit`; `admin_manage` resta per workspace e cataloghi (spec 06) |
| `edit_members` singolo che solleva `ConcurrencyError` + `edit_members_bulk` che restituisce le due liste | Solo singolo (bulk via `_raw`); solo bulk | Il caso comune (un gruppo) ha la stessa forma delle altre scritture; il bulk espone l'esito parziale del server senza nasconderlo |
| Edit "come i task": libreria con i soli campi passati e `occ_token` esplicito; CLI patch che rilegge il form | Patch anche in libreria (due richieste, token implicito); solo i campi passati anche in CLI | RF-025: la concorrenza resta visibile al chiamante; in CLI nessun `--last-name` deve azzerare il resto se il server sostituisce (lezione di 02-T11) |
| Riga `0.13.0`, milestone M31 | Dentro la `0.12.0` ancora aperta | La 0.12.0 (upload) è verificata e aspetta solo il tag; i `feat` producono un minor |
| Password da `--generate-password` o `--password-stdin` (stdin o prompt nascosto); nessun `--password VALORE` | `--password VALORE` documentato come sconsigliato; solo `--json` | Un argomento finisce in history e `ps`; `--json` da solo rende scomodo il caso comune |
| Password generata nell'output di `users create` | Solo con `--show-password`; mai in CLI | L'operatore deve consegnarla; log, audit e hook la redigono già (RNF-001); avviso su `--export` |
| Flag piatti più credenziali; preferenze, info, settings, foto via `--json` | Solo campi anagrafici; un flag per ogni campo del DTO | Copre i casi comuni dalla shell senza decine di opzioni; `--json` resta il DTO completo |
| Integration: gruppi con le variabili esistenti; utenti solo con `PYNTERACTA_TEST_WRITE_USERS=1` | Entrambi con le variabili esistenti; solo i gruppi | Creare un utente consuma una licenza e può mandare email: serve un consenso esplicito; senza la prova la semantica dell'edit utente resterebbe ignota |
| `users edit-credentials` in CLI, nessun alias di lettura | Alias `users credentials`; tutto sotto `admin-manage` | La patch rilegge il form da sé; un comando di lettura in più non serve |
| Membri solo da `groups edit-members` (`--add`/`--remove`); `groups edit` rimanda la lista letta | `--member` su `groups edit` che sostituisce la lista; solo via `groups edit` | Nessun `groups edit` può svuotare un gruppo per sbaglio; add/remove è l'operazione che gli script fanno davvero |
| Ritorno = façade sulla risposta (`UserWriteResult`, `GroupWriteResult`, `GroupMembersResult`); `delete` → `None` | Rileggere e restituire il form; solo gli id | Nessuna chiamata in più; `DELETE` non ha corpo, non c'è nulla da restituire |
| Testi della CLI in inglese | Italiano | Decisione della spec 02, sezione Lingua del `CLAUDE.md` |

## Verifica manuale

- La semantica del server sui campi omessi in `users.edit`, `groups.edit` ed `edit_credentials`,
  l'effetto di `delete` (sparizione o `deleted: true`), il formato di `generated_password` e il
  significato dell'`occToken` del gruppo restituito da `edit_members` non sono documentati dallo
  swagger: si stabiliscono eseguendo 05-C24 e 05-C25 contro il tenant di prova (05-C26). L'esito
  si registra in `docs/api/users.md`, `docs/api/groups.md` e `verifica.md`; se il server azzera i
  campi omessi o rimuove i blocchi di credenziali omessi, la documentazione lo dice come avviso.
  05-C25 richiede l'opt-in `PYNTERACTA_TEST_WRITE_USERS=1`: fino a quell'esecuzione vale come
  saltato e la semantica dell'edit utente resta dichiarata "non verificata" nei docs.

## Domande aperte

Nessuna.
