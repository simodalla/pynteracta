# 06 – Anagrafiche admin, seconda metà: cataloghi, voci di catalogo e workspace

Stato: approvata
Branch: `m32_admin_catalogs_workspace`
Requisiti del PRD: RF-023, RF-025, RF-025a, RF-015, RF-015a, RF-024 (upload di copertina e
logo), RNF-001, RNF-009; toccati RF-008, RF-013, RF-019, §6 "Dati scritti sul tenant"
Dipende da: spec 02 (conferma dei comandi distruttivi, exit code 9, `--json`), spec 03 (unione di
`--json` e flag, validazione del corpo contro il DTO, coppie `CHIAVE=VALORE`), spec 04 (upload dei
file per `--cover` e `--logo`, exit code 11), spec 05 (forma delle scritture admin, patch della
CLI, opzioni condivise in `cli/_write.py`, `204` → `NotFoundError`)

Quinta spec della superficie di scrittura aperta da
[ADR 0001](../adr/0001-apertura-della-superficie-di-scrittura.md): la seconda metà del gruppo
admin (7 endpoint su 15), che chiude RF-023. Minor **0.13.0**, milestone **M32**.

## Scopo

Chi scrive automazioni con la libreria, e chi usa la CLI, può creare e modificare cataloghi e
voci di catalogo, disabilitarli e ripristinarli con il flag logico `deleted`, e modificare un
workspace (nome, descrizione, immagini, membri e amministratori), con la stessa forma delle
letture e della spec 05: metodi tipizzati con kwargs espliciti e varianti `*_raw`, façade con
`.raw`, comandi `catalogs create|edit|delete|restore`,
`catalogs create-entry|edit-entry|delete-entry|restore-entry` e `admin-manage edit-workspace`
che compongono con `--output`, `--full`, `--fields`, `--export`. La concorrenza ottimistica resta
visibile al chiamante; nessuna scrittura viene ripetuta da sola.

## Comportamento attuale

Su cataloghi, voci e workspace esistono solo letture. `client.catalogs.list(catalog_ids,
load_entries=…)` ed `entries(catalog_id, …)` leggono gli endpoint pubblici
`communication/settings/post-definition/catalogs…` e restituiscono `Catalog` (id, nome come
stringa, `paged`) e `CatalogEntry` (id, label come stringa, external id, parent ids).
`client.admin_manage.catalog_for_edit(catalog_id)` restituisce `CatalogForEdit` (id, nome come
mappa per lingua, `deleted`, numero di community associate), `catalog_entry_for_edit(catalog_id,
entry_id)` restituisce `CatalogEntryForEdit` (id, label come mappa, external id, `deleted`, numero
di parent) e `workspace_for_edit(workspace_id)` restituisce `WorkspaceForEdit` (id, nome,
descrizione, conteggi di utenti e gruppi, timestamp). Le tre façade non espongono `occToken`,
raggiungibile solo da `.raw`; `CatalogForEdit` non espone il catalogo parent. La CLI ha
`catalogs list|entries` e `admin-manage workspace|catalog|catalog-entry`. Il client base sa già
fare `POST` e `PUT` con corpo (spec 02–05); `409` è mappato su `ConcurrencyError` ed esce con `9`;
`204` senza corpo su una `GET` è `NotFoundError` (spec 05); i comandi distruttivi hanno il prompt
con `--yes` e il rifiuto senza terminale (spec 02); `--cover`/`--logo` possono riusare l'upload
della spec 04. I 10 DTO di richiesta e risposta delle sette scritture sono già nei modelli
generati dal swagger pinnato: nessuna rigenerazione.

## Comportamento

### Libreria: cataloghi e voci (`client.catalogs`)

- **Creare un catalogo**: `client.catalogs.create(*, name=None, parent_id=None)` invia
  `POST admin/manage/catalogs` con **solo i campi passati** (`name` è la mappa per lingua
  `{"it": "Sedi", "en": "Sites"}`, `parent_id` l'id del catalogo parent) e restituisce un
  `CatalogWriteResult` con `catalog` (façade `Catalog`: id, nome, `paged`, `etag`, voci se
  presenti), `parent_catalog` (idem, o `None`), `catalog_id`, `next_occ_token` e `.raw`.
  `create_raw(req: CreateEditCatalogRequestDTO)` fa lo stesso da un DTO già costruito.
- **Modificare un catalogo**: `client.catalogs.edit(catalog_id, occ_token, *, name=None,
  parent_id=None)` invia `PUT admin/manage/catalogs/{catalog_id}` con l'`occToken` nel corpo e
  solo i campi passati; restituisce un `CatalogWriteResult`. `edit_raw(catalog_id, req)` idem,
  con l'`occToken` dentro il DTO. Il flag `deleted` del DTO non è un argomento di `edit`: si
  cambia con `set_deleted`; chi lo vuole nel corpo del `PUT` usa `edit_raw`.
- **Disabilitare o ripristinare un catalogo**: `client.catalogs.set_deleted(catalog_id,
  deleted: bool)` invia `PUT admin/manage/catalogs/{catalog_id}/deleted` con corpo
  `{"deleted": …}` (nessun `occToken`: l'endpoint non lo prevede) e restituisce un
  `CatalogDeletedResult` con `catalog_id`, `entry_id` (`None` per il catalogo), `deleted` e
  `.raw`. Il catalogo non viene eliminato: resta sul tenant con `deleted: true` e si ripristina
  con `deleted=False`.
- **Creare una voce**: `client.catalogs.create_entry(catalog_id, *, label=None, parent_ids=None,
  external_id=None)` invia `POST admin/manage/catalogs/{catalog_id}/entries` con solo i campi
  passati (`label` è la mappa per lingua) e restituisce un `CatalogEntryWriteResult` con `entry`
  (façade `CatalogEntry`: id, catalog id, label, external id, parent ids, `deleted`),
  `entry_id`, `next_occ_token` e `.raw`. `create_entry_raw(catalog_id, req:
  CreateEditCatalogEntryRequestDTO)` idem.
- **Modificare una voce**: `client.catalogs.edit_entry(catalog_id, entry_id, occ_token, *,
  label=None, parent_ids=None, external_id=None)` invia
  `PUT admin/manage/catalogs/{catalog_id}/entries/{entry_id}` con l'`occToken` nel corpo e solo i
  campi passati; restituisce un `CatalogEntryWriteResult`. `edit_entry_raw(catalog_id, entry_id,
  req)` idem. `deleted` non è un argomento: `set_entry_deleted` o `edit_entry_raw`.
- **Disabilitare o ripristinare una voce**: `client.catalogs.set_entry_deleted(catalog_id,
  entry_id, deleted: bool)` invia `PUT admin/manage/catalogs/{catalog_id}/entries/{entry_id}/deleted`
  con corpo `{"deleted": …}` e restituisce un `CatalogDeletedResult` con `catalog_id`,
  `entry_id`, `deleted`. Lo swagger pinnato dichiara per questo endpoint la risposta del
  catalogo (`catalogId`, `deleted`) ma definisce anche un DTO con `entryId`: la façade legge
  l'id che c'è e, se manca, usa quello passato dal chiamante; la prova sul tenant (06-C21)
  registra quale arriva.
- **Letture per la modifica**: `client.catalogs.get_for_edit(catalog_id)` e
  `client.catalogs.get_entry_for_edit(catalog_id, entry_id)` sono alias di
  `client.admin_manage.catalog_for_edit` e `catalog_entry_for_edit`, che restano: stessa
  richiesta, stessa façade.
- **`occ_token` e parent**: `CatalogForEdit`, `CatalogEntryForEdit` e `WorkspaceForEdit`
  espongono `occ_token` come proprietà, oltre che su `.raw`. `CatalogForEdit` espone
  `parent_catalog_id` (l'id del catalogo parent letto da `contentData.parentCatalog`, o `None`).
- **Campi omessi in `edit` ed `edit_entry`**: non vengono inviati; la libreria non aggiunge nulla
  da sola. Cosa ne fa il server (mappa del nome sostituita per intero o unita per lingua; parent
  ed external id omessi azzerati o mantenuti) lo stabilisce la prova sul tenant (06-C21) e lo
  registrano `docs/api/catalogs.md` e il PRD alla chiusura, come la spec 05 per utenti e gruppi.

### Libreria: workspace (`client.admin_manage`)

- **Modificare un workspace**: `client.admin_manage.edit_workspace(workspace_id, occ_token, *,
  name=None, translations=None, description=None, new_cover_image_content_ref=None,
  new_logo_content_ref=None, add_user_ids=None, remove_user_ids=None, add_group_ids=None,
  remove_group_ids=None, add_user_role_associations=None, add_group_role_associations=None,
  remove_role_association_ids=None)` invia `PUT admin/manage/workspaces/{workspace_id}/{occ_token}`
  (l'`occToken` sta **nel path**, non nel corpo) con solo i campi passati, e restituisce un
  `WorkspaceForEdit`: la risposta è lo stesso DTO del form di lettura, quindi `occ_token` è già
  quello da usare per la modifica successiva. Le associazioni di ruolo si passano come liste di
  dizionari nella forma del DTO (`{"userId": 1, "roleId": 2}`, `{"groupId": 3, "roleId": 2}`) o
  di DTO generati; i `contentRef` di copertina e logo si ottengono da
  `client.attachments.upload` (spec 04). `edit_workspace_raw(workspace_id, occ_token, req:
  EditWorkspaceRequestDTO)` idem.
- **Campi omessi**: non vengono inviati. Se il nome o la descrizione omessi vengono mantenuti o
  azzerati lo stabilisce la prova sul tenant (06-C22); se risultassero azzerati, `edit-workspace`
  in CLI diventa una patch come `catalogs edit`, con revisione della spec (come la 05 dopo
  T15). Nessuna creazione né eliminazione di workspace: l'API non le ha.

### CLI: cataloghi e voci

I testi della CLI restano in inglese (decisione della spec 02). Tutti i comandi usano
`render_output`, quindi `--output`, `--full`, `--fields`, `--export` compongono come altrove;
`--json FILE|-` fornisce il corpo completo e i flag prevalgono sulle chiavi corrispondenti;
`--occ-token` impone il token; `409` → exit `9`; nessuna richiesta viene ripetuta.

- **Mappe per lingua**: `--name LANG=TESTO` (cataloghi), `--label LANG=TESTO` (voci) e
  `--description LANG=TESTO` (workspace) sono ripetibili: `--name it=Sedi --name en=Sites` →
  `{"it": "Sedi", "en": "Sites"}`. Un valore senza `=` o con la lingua vuota → exit `2`, nessuna
  richiesta. Nelle patch la mappa letta dal form è aggiornata **chiave per chiave** (come
  `--custom-data` della spec 03): `--name en=Sites` su un form con `{"it": "Sedi"}` invia
  `{"it": "Sedi", "en": "Sites"}`.
- `catalogs create --name LANG=TESTO… [--parent ID] [--json]`: tabella con `catalog_id`, `name`,
  `parent_catalog_id`, `next_occ_token`.
- `catalogs edit CATALOG_ID [--name LANG=TESTO…] [--parent ID] [--json] [--occ-token N]`: patch.
  Rilegge `catalog_for_edit`, prende l'`occToken`, rimanda `name` (mappa letta, aggiornata per
  chiave) e `parentId` (letto, o quello di `--parent`); con `--occ-token` la `GET` avviene lo
  stesso (serve per la patch) e la `PUT` usa il token imposto. Non rimanda `deleted`: si cambia
  con `delete`/`restore`.
- `catalogs delete CATALOG_ID [--yes]`: rilegge il form, chiede
  `Delete catalog 5 "Sedi"? [y/N]` (il nome nella lingua `it` se c'è, altrimenti il primo della
  mappa; `""` se manca), con `y` invia `set_deleted(True)` e stampa `Catalog 5 deleted`
  (`--output json`: `{"catalog_id": 5, "deleted": true}`); con `n` esce `0` senza richieste;
  `--yes` salta il prompt; senza terminale e senza `--yes` exit `2` e nessuna richiesta. L'help
  dice che la cancellazione è logica e reversibile con `restore`.
- `catalogs restore CATALOG_ID`: invia `set_deleted(False)` senza conferma e stampa
  `Catalog 5 restored` (`--output json`: `{"catalog_id": 5, "deleted": false}`).
- `catalogs create-entry CATALOG_ID --label LANG=TESTO… [--parent-entry ID…] [--external-id X]
  [--json]`: tabella con `entry_id`, `catalog_id`, `label`, `external_id`, `next_occ_token`.
- `catalogs edit-entry CATALOG_ID ENTRY_ID [--label LANG=TESTO…] [--parent-entry ID…]
  [--external-id X] [--json] [--occ-token N]`: patch. Rilegge `catalog_entry_for_edit`, rimanda
  `label` (mappa letta, aggiornata per chiave), `parentIds` (gli id dei `parents` letti, o quelli
  di `--parent-entry`, che sostituiscono la lista) ed `externalId` (letto, o `--external-id`).
- `catalogs delete-entry CATALOG_ID ENTRY_ID [--yes]` e `catalogs restore-entry CATALOG_ID
  ENTRY_ID`: come `delete`/`restore`, con prompt `Delete entry 100 "Bologna" of catalog 5? [y/N]`
  e messaggi `Entry 100 of catalog 5 deleted|restored` (`--output json`: `{"catalog_id": 5,
  "entry_id": 100, "deleted": …}`).

### CLI: workspace

- `admin-manage edit-workspace WORKSPACE_ID [--name TESTO] [--description LANG=TESTO…]
  [--add-user ID…] [--remove-user ID…] [--add-group ID…] [--remove-group ID…]
  [--add-user-role USER_ID=ROLE_ID…] [--add-group-role GROUP_ID=ROLE_ID…]
  [--remove-role-association ID…] [--cover PATH] [--logo PATH] [--json] [--occ-token N]`.
  Rilegge il form **solo per l'`occToken`** (con `--occ-token` nessuna `GET`) e invia i soli
  campi indicati: non è una patch. `--cover` e `--logo` caricano il file con
  `attachments.upload` (spec 04) e mettono il `contentRef` in `newCoverImageContentRef` /
  `newLogoContentRef`; al primo upload fallito il comando esce `11` e nessuna `PUT` parte.
  `--translations` non esiste: la mappa delle traduzioni passa da `--json`. Senza alcun flag e
  senza `--json` → exit `2`, nessuna richiesta. Tabella: `id`, `name`, `admin_users_count`,
  `member_users_count`, `admin_groups_count`, `member_groups_count`, `occ_token` (la riga della
  lettura più il token). `USER_ID=ROLE_ID` malformato → exit `2`.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 06-C01 | Quando si chiama `client.catalogs.create(name={"it": "Sedi", "en": "Sites"}, parent_id=3)`, parte una sola `POST …/admin/manage/catalogs` con corpo `{"name": {"it": "Sedi", "en": "Sites"}, "parentId": 3}` (nessun'altra chiave) e, con una risposta `CreateEditCatalogResponseDTO`, il risultato ha `catalog_id`, `catalog.name`, `parent_catalog.id`, `next_occ_token` e `.raw` dalla risposta; `create_raw` con il DTO equivalente produce la stessa richiesta. | RF-023 |
| 06-C02 | Quando si chiama `client.catalogs.edit(5, 7, name={"en": "Sites"})`, parte una sola `PUT …/admin/manage/catalogs/5` con corpo `{"name": {"en": "Sites"}, "occToken": 7}` e il risultato ha `catalog_id == 5` e `next_occ_token` dalla risposta; `edit_raw(5, CreateEditCatalogRequestDTO(...))` produce la stessa richiesta, anche con `deleted` nel DTO. | RF-023, RF-025 |
| 06-C03 | Quando si chiama `client.catalogs.set_deleted(5, True)`, parte una sola `PUT …/admin/manage/catalogs/5/deleted` con corpo esatto `{"deleted": true}` e il risultato ha `catalog_id == 5`, `entry_id is None`, `deleted is True` dalla risposta; `set_deleted(5, False)` invia `{"deleted": false}`. | RF-023 |
| 06-C04 | Quando si chiama `client.catalogs.create_entry(5, label={"it": "Bologna"}, parent_ids=[10], external_id="BO")`, parte una sola `POST …/admin/manage/catalogs/5/entries` con corpo `{"label": {"it": "Bologna"}, "parentIds": [10], "externalId": "BO"}` e il risultato ha `entry_id`, `entry.label`, `entry.external_id`, `next_occ_token` e `.raw` dalla risposta `CreateEditCatalogEntryResponseDTO`; `create_entry_raw` produce la stessa richiesta. | RF-023 |
| 06-C05 | Quando si chiama `client.catalogs.edit_entry(5, 100, 2, external_id="BO2")`, parte una sola `PUT …/admin/manage/catalogs/5/entries/100` con corpo `{"externalId": "BO2", "occToken": 2}` e il risultato ha `entry_id == 100` e `next_occ_token` dalla risposta; `edit_entry_raw` produce la stessa richiesta. | RF-023, RF-025 |
| 06-C06 | Quando si chiama `client.catalogs.set_entry_deleted(5, 100, True)`, parte una sola `PUT …/admin/manage/catalogs/5/entries/100/deleted` con corpo esatto `{"deleted": true}`; con risposta `{"catalogId": 5, "deleted": true}` il risultato ha `catalog_id == 5`, `entry_id == 100`, `deleted is True`; con risposta `{"entryId": 100, "deleted": true}` lo stesso. | RF-023 |
| 06-C07 | Quando `admin_manage.catalog_for_edit(5)`, `catalog_entry_for_edit(5, 100)` e `workspace_for_edit(88)` ricevono risposte con `occToken: 7`, le façade hanno `occ_token == 7`; `CatalogForEdit.parent_catalog_id` vale l'id di `contentData.parentCatalog` (o `None` senza parent); `client.catalogs.get_for_edit(5)` e `get_entry_for_edit(5, 100)` fanno le stesse `GET …/edit` e restituiscono le stesse façade. | RF-023e, RF-008, RF-013 |
| 06-C08 | Quando si chiama `client.admin_manage.edit_workspace(88, 9, name="WS", add_user_ids=[1], remove_group_ids=[2], add_user_role_associations=[{"userId": 1, "roleId": 4}], new_cover_image_content_ref="ref-1")`, parte una sola `PUT …/admin/manage/workspaces/88/9` con corpo `{"name": "WS", "addUserIds": [1], "removeGroupIds": [2], "addUserRoleAssociations": [{"userId": 1, "roleId": 4}], "newCoverImageContentRef": "ref-1"}` (nessun `occToken` nel corpo) e il risultato è un `WorkspaceForEdit` con `id`, `name` e `occ_token` dalla risposta; `edit_workspace_raw(88, 9, EditWorkspaceRequestDTO(...))` produce la stessa richiesta. | RF-023, RF-025 |
| 06-C09 | Quando il server risponde `409` a `catalogs.edit`, `catalogs.edit_entry` o `admin_manage.edit_workspace`, viene sollevata `ConcurrencyError` con `status_code == 409` e il server ha ricevuto **esattamente una** richiesta; quando risponde `404` a `set_deleted` o `set_entry_deleted`, `NotFoundError`; quando `catalogs.create` o `edit_workspace` va in timeout o errore di rete, `TransportError` e al più una richiesta. | RF-025, RF-019, RNF-009 |
| 06-C10 | Quando si esegue `catalogs create --name it=Sedi --name en=Sites --parent 3 --json body.json` con `body.json` = `{"name": {"it": "X", "de": "Standorte"}}`, il corpo inviato è `{"name": {"it": "Sedi", "de": "Standorte", "en": "Sites"}, "parentId": 3}` (le chiavi dei flag prevalgono una per una) e l'output tabella mostra `catalog_id`, `name`, `parent_catalog_id`, `next_occ_token`; `--name Sedi` (senza `=`) o `--name =Sedi` → exit `2` e nessuna richiesta. | RF-023, RF-023f, RF-015 |
| 06-C11 | Quando si esegue `catalogs edit 5 --name en=Sites` e la `GET …/admin/manage/catalogs/5/edit` restituisce `contentData` con `name: {"it": "Sedi"}`, `parentCatalog: {"id": 3}`, `deleted: false` e `occToken: 7`, la `PUT …/admin/manage/catalogs/5` ha corpo esatto `{"name": {"it": "Sedi", "en": "Sites"}, "parentId": 3, "occToken": 7}` (nessun `deleted`); con `--parent 4` vince `4`; con `--occ-token 8` la `GET` avviene lo stesso e la `PUT` usa `8`; quando il form non ha `parentCatalog`, la chiave `parentId` manca. | RF-023, RF-023f, RF-025 |
| 06-C12 | Quando si esegue `catalogs edit-entry 5 100 --label en=Bologna --parent-entry 11` e la `GET …/entries/100/edit` restituisce `label: {"it": "Bologna"}`, `parents: [{"id": 10}]`, `externalId: "BO"`, `occToken: 2`, la `PUT …/admin/manage/catalogs/5/entries/100` ha corpo esatto `{"label": {"it": "Bologna", "en": "Bologna"}, "parentIds": [11], "externalId": "BO", "occToken": 2}`; senza `--parent-entry` `parentIds` vale `[10]`; senza `parents` nel form e senza flag la chiave manca. | RF-023, RF-023f, RF-025 |
| 06-C13 | Quando la `PUT` di `catalogs edit`, `catalogs edit-entry` o `admin-manage edit-workspace` risponde `409`, il comando termina con exit code `9`, stampa `Catalog 5 changed since it was read: fetch it again and retry` (o `Entry 100 of catalog 5 …`, `Workspace 88 …`) e il server ha ricevuto una sola `PUT`. | RF-025, RF-015a, RNF-009 |
| 06-C14 | Quando si esegue `catalogs delete 5` in un terminale interattivo e il form ha `name: {"it": "Sedi", "en": "Sites"}`, il prompt è `Delete catalog 5 "Sedi"? [y/N]`; con `y` parte una sola `PUT …/catalogs/5/deleted` con `{"deleted": true}` e il comando stampa `Catalog 5 deleted` (`--output json`: `{"catalog_id": 5, "deleted": true}`); con `n` nessuna `PUT` ed exit `0`; con `--yes` nessun prompt; senza terminale e senza `--yes` nessuna `PUT`, exit `2` e il messaggio dice che serve `--yes`. `catalogs delete-entry 5 100` si comporta allo stesso modo con `Delete entry 100 "Bologna" of catalog 5? [y/N]` e `Entry 100 of catalog 5 deleted`. | RF-025, RF-025a, RF-023f |
| 06-C15 | Quando si esegue `catalogs restore 5` o `catalogs restore-entry 5 100`, senza alcun prompt parte una sola `PUT …/deleted` con `{"deleted": false}`, anche senza terminale, e il comando stampa `Catalog 5 restored` o `Entry 100 of catalog 5 restored` (`--output json`: `{"catalog_id": 5, "deleted": false}` / `{"catalog_id": 5, "entry_id": 100, "deleted": false}`). | RF-023f |
| 06-C16 | Quando si esegue `catalogs create-entry 5 --label it=Bologna --parent-entry 10 --parent-entry 11 --external-id BO`, il corpo è `{"label": {"it": "Bologna"}, "parentIds": [10, 11], "externalId": "BO"}` e la tabella mostra `entry_id`, `catalog_id`, `label`, `external_id`, `next_occ_token`; `--json` con `label` più `--label en=Bologna` produce la mappa unita. | RF-023, RF-023f, RF-015 |
| 06-C17 | Quando si esegue `admin-manage edit-workspace 88 --name WS --description it=Desc --add-user 1 --remove-group 2 --add-user-role 1=4 --remove-role-association 9` e la `GET …/workspaces/88/edit` restituisce `occToken: 9`, parte una sola `PUT …/admin/manage/workspaces/88/9` con corpo esatto `{"name": "WS", "description": {"it": "Desc"}, "addUserIds": [1], "removeGroupIds": [2], "addUserRoleAssociations": [{"userId": 1, "roleId": 4}], "removeRoleAssociationIds": [9]}` (nulla del form rimandato) e la tabella mostra `id`, `name`, i quattro conteggi e `occ_token`; con `--occ-token 10` nessuna `GET` e il path usa `10`; `--add-user-role 1` (senza `=`) → exit `2`; nessun flag e nessun `--json` → exit `2`, nessuna richiesta. | RF-023, RF-023f, RF-025, RF-015 |
| 06-C18 | Quando si esegue `admin-manage edit-workspace 88 --cover cover.png --logo logo.png`, i due file sono caricati nell'ordine con il meccanismo della spec 04 e il corpo della `PUT` ha `newCoverImageContentRef` e `newLogoContentRef` con i `contentRef` restituiti; quando l'upload della copertina fallisce (`UploadError`), il comando esce `11`, il logo non viene caricato e nessuna `PUT` parte. | RF-024, RF-024a, RF-023f |
| 06-C19 | I contract test dimostrano che i modelli generati `CreateEditCatalogRequestDTO`, `CreateEditCatalogResponseDTO`, `EditCatalogDeletedRequestDTO`, `EditCatalogDeletedResponseDTO`, `CreateEditCatalogEntryRequestDTO`, `CreateEditCatalogEntryResponseDTO`, `EditCatalogEntryDeletedRequestDTO`, `EditWorkspaceRequestDTO`, `CreateUserRoleAssociationDTO`, `CreateGroupRoleAssociationDTO` coprono tutte le proprietà del swagger pinnato, e le fixture JSON di risposta si leggono nelle façade `CatalogWriteResult`, `CatalogEntryWriteResult`, `CatalogDeletedResult`, `WorkspaceForEdit`. | RF-023, RNF-003 |
| 06-C20 | `docs/cli.md` documenta i nove comandi, la forma `LANG=TESTO`, la cancellazione logica e l'exit `9`; `docs/api/catalogs.md` e `docs/api/admin_manage.md` documentano i metodi, le façade di risultato, `occ_token`, `parent_catalog_id` e la semantica dei campi omessi verificata sul tenant; `docs/testing.md` le nuove variabili; `docs/index.md` e `README.md` non dicono più che le scritture su cataloghi e workspace sono da fare; `uv run mkdocs build --strict` e `test_docs_snippets` sono verdi. | RF-015 |
| 06-C21 | Quando l'ambiente integration è impostato (opt-in), il ciclo `catalogs.create` (nome `{"it": "pynteracta-it-<timestamp>"}`) → `get_for_edit` (`occ_token`, `parent_catalog_id`) → `edit` → `create_entry` → `get_entry_for_edit` → `edit_entry` → `set_entry_deleted(True)` → `set_deleted(True)` termina senza errori sul tenant e al termine il catalogo è `deleted: true`, anche se un passo intermedio fallisce; senza le variabili il test è saltato. L'esecuzione stabilisce e registra in `docs/api/catalogs.md` e `verifica.md`: l'effetto dei campi omessi in `edit` ed `edit_entry` (mappa del nome sostituita o unita, parent ed external id azzerati o mantenuti), quale id arriva nella risposta di `…/entries/{id}/deleted`, e se un catalogo disabilitato compare ancora in `catalogs.list`. | RF-023, RF-025 |
| 06-C22 | Quando, oltre all'ambiente integration, `PYNTERACTA_TEST_WRITE_WORKSPACE=1` è impostata (opt-in dedicato), il ciclo `workspace_for_edit(PYNTERACTA_TEST_WORKSPACE_ID)` → `edit_workspace(add_user_ids=[PYNTERACTA_TEST_USER_ID])` → `edit_workspace(remove_user_ids=[…])` termina senza errori, il conteggio dei membri torna quello iniziale e il nome del workspace è invariato al termine; senza la variabile il test è saltato. L'esecuzione stabilisce e registra in `docs/api/admin_manage.md` e `verifica.md` se il nome e la descrizione omessi sono mantenuti o azzerati; se azzerati, `edit-workspace` diventa una patch e la spec si rivede prima della chiusura. | RF-023, RF-025 |
| 06-C23 | Quando le risposte di `admin_manage.workspace_for_edit` ed `edit_workspace` hanno valori `null` nelle mappe per lingua di `contentData` (`translations`, `description`), e quelle di `catalog_for_edit` e `catalog_entry_for_edit` in `contentData.name` e `label`, la façade si costruisce senza errori e le lingue con valore `null` sono scartate (`{"it": null}` → `{}`); i valori stringa restano; `admin-manage workspace` esce `0`. | RF-023e, RF-008, RF-013 |

## Casi limite

- `409` su una `PUT` → `ConcurrencyError`, una sola richiesta, exit `9` in CLI (06-C09, 06-C13).
- `404` su `set_deleted`, `set_entry_deleted` o una `GET …/edit` → `NotFoundError`, exit `5`;
  `204` vuoto su una `GET …/edit` → `NotFoundError` (spec 05, RF-023d), quindi `catalogs edit 5`
  e `catalogs delete 5` su un catalogo inesistente escono `5` senza `PUT` (06-C09).
- `403` (il service account non è amministratore) → `PermissionError`, exit `4`.
- `400` con `validationErrors` (nome mancante, parent inesistente, external id duplicato) →
  `ValidationError`, exit `6`; la libreria non valida in anticipo ciò che il server valida.
- Timeout o errore di rete dopo l'invio → `TransportError`, esito sconosciuto, nessun nuovo
  tentativo (06-C09).
- `--name`/`--label`/`--description` senza `=` o con lingua vuota; `--add-user-role` senza `=`
  o con id non interi → exit `2`, nessuna richiesta (06-C10, 06-C17).
- `--json` con chiavi fuori dal DTO, JSON non valido o non oggetto → exit `2` (spec 05).
- `catalogs edit 5` senza alcun flag e senza `--json` → la patch rimanda il form invariato: è
  ammesso (rinnova l'`occToken`), come `users edit`; `edit-workspace` senza flag → exit `2`
  perché non c'è nulla da rimandare (06-C17).
- Form del catalogo senza `contentData` o senza `name` → la patch non manda `name`; il prompt di
  `delete` mostra `""` (06-C11, 06-C14).
- `delete` su un catalogo già `deleted: true` → la `PUT` parte lo stesso (il server è
  idempotente sul flag); `restore` idem.
- Risposta di `…/entries/{id}/deleted` con `catalogId` o con `entryId` → la façade legge l'uno o
  l'altro e completa con gli id passati (06-C06).
- Upload di `--cover` fallito → exit `11`, nessuna `PUT`; upload riuscito ma `PUT` in `409` →
  exit `9`, il file resta nello storage temporaneo fino alla scadenza della policy (spec 04).
- `edit-workspace --add-user 1 --remove-user 1` → inviato così com'è; decide il server.
- Catalogo disabilitato: `catalogs list` può continuare a elencarlo o no; lo stabilisce 06-C21 e
  lo dicono i docs.

## Dati personali e segreti

Passano al tenant: nomi e label di cataloghi e voci (dati non personali), external id delle voci;
nome, traduzioni e descrizione del workspace; id di utenti, gruppi e ruoli aggiunti o tolti al
workspace; i file di copertina e logo, che vanno allo storage temporaneo del tenant con il
meccanismo della spec 04 (RNF-011: il contenuto non compare mai in log, audit log né hook). La
libreria inoltra e non conserva; l'audit log opzionale registra i body solo con `audit_log_bodies`
(eccezione documentata). Nessuna password e nessun segreto nuovo. L'`occToken` del workspace sta
nel path dell'URL: non è un segreto (è un contatore di versione) e la redazione degli URL di
RNF-001 non lo tocca, perché agisce sui parametri di query. Gli integration test creano un
catalogo e una voce con nomi riconoscibili (`pynteracta-it-<timestamp>`), li disabilitano al
termine (non esiste eliminazione fisica) e, con opt-in dedicato, aggiungono e tolgono l'utente di
prova dal workspace di prova senza toccarne nome e descrizione.

## Requisiti nuovi

- RF-023e (precisa RF-008, RF-013). Le letture per la modifica di catalogo, voce e workspace
  (`CatalogForEdit`, `CatalogEntryForEdit`, `WorkspaceForEdit`) espongono `occ_token`;
  `CatalogForEdit` espone `parent_catalog_id`; `catalogs.get_for_edit` e
  `catalogs.get_entry_for_edit` sono alias di `admin_manage.catalog_for_edit` e
  `catalog_entry_for_edit`.
- RF-023f (precisa RF-023 in CLI). `catalogs create|edit|delete|restore` e
  `catalogs create-entry|edit-entry|delete-entry|restore-entry`; `admin-manage edit-workspace`.
  Le mappe per lingua si passano con `--name|--label|--description LANG=TESTO` ripetibili e nelle
  patch aggiornano la mappa letta chiave per chiave. `catalogs edit` ed `edit-entry` sono patch
  che rileggono il form; `edit-workspace` rilegge solo per l'`occToken` e invia i soli campi
  indicati; `--cover` e `--logo` caricano i file (RF-024a). `delete` e `delete-entry` sono
  cancellazioni logiche con conferma (RF-025a), reversibili con `restore` e `restore-entry`,
  che non chiedono conferma. Il flag `deleted` non passa da `edit`: solo dagli endpoint dedicati
  (`set_deleted`, `set_entry_deleted`) o da `*_raw`/`--json`.
- La semantica del server sui campi omessi di `edit`, `edit_entry` ed `edit_workspace`, l'id
  restituito da `…/entries/{id}/deleted` e la visibilità dei cataloghi disabilitati in
  `catalogs.list` entrano in RF-023 alla chiusura, dopo 06-C21 e 06-C22. Alla chiusura RF-023
  corregge anche "(spec 05, 0.13.0)" in "(spec 05, 0.12.0)": la 05 è uscita nella 0.12.0 con la
  04 (nota di release in `PROGRESS.md`, M31).

## Fuori ambito

- Post evento (RF-021): prossima spec.
- `deleted` come argomento di `edit`/`edit_entry` e come flag di `catalogs edit`: solo
  `set_deleted`/`set_entry_deleted`, `*_raw` e `--json`.
- Creazione ed eliminazione fisica di cataloghi, voci e workspace: l'API non le prevede.
- `translations` del workspace in CLI: solo da `--json`.
- Paginazione di `adminUsers`, `memberUsers`, `members`… dentro il form del workspace: restano
  su `.raw` come oggi.
- Comandi di lettura nuovi (`catalogs get-for-edit`): la lettura resta `admin-manage catalog` e
  `admin-manage catalog-entry`; gli alias sono solo in libreria.
- `--web-url` sui form admin (decisione della v0.6).
- Redazione di `occToken` nei body dell'audit log (follow-up di M31): resta com'è.
- Retry automatico e risoluzione automatica del `409` (RNF-009, ADR 0001).
- Traduzione in italiano della CLI esistente.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Scritture di cataloghi e voci su `client.catalogs`, alias `get_for_edit`/`get_entry_for_edit`; letture admin mantenute su `admin_manage` | Tutto su `admin_manage`; risorsa `catalog_entries` dedicata | Un agente cerca `catalogs.create` accanto a `catalogs.list`, come `users.create` nella spec 05; nessuna classe in più |
| Modifica del workspace su `client.admin_manage.edit_workspace` | Nuova risorsa `client.workspaces` | Non esiste una lettura pubblica dei workspace; la lettura del form è già lì; una risorsa per un solo endpoint non vale |
| `deleted` solo con l'endpoint dedicato (`set_deleted`, `set_entry_deleted`); non è un argomento di `edit` | Anche in `edit`; solo in `edit` | Due vie per la stessa cosa confondono; l'endpoint dedicato non chiede `occToken` ed è l'operazione che gli script fanno; `edit_raw` e `--json` restano per chi lo vuole nel `PUT` |
| Mappe per lingua con `--name|--label|--description LANG=TESTO` ripetibile, unione chiave per chiave nelle patch | `--name TESTO --lang it`; solo `--json` | Un catalogo ha di norma più lingue; la forma `CHIAVE=VALORE` è già quella di `--custom-data` |
| `catalogs edit` ed `edit-entry` patch che rileggono il form; libreria con i soli campi passati e `occ_token` esplicito | Solo i campi indicati anche in CLI | RF-025 e RF-023b: nessun `--name en=…` deve azzerare le altre lingue se il server sostituisce la mappa |
| `edit-workspace` senza patch: rilegge solo per l'`occToken`; semantica dei campi omessi da provare (06-C22), con revisione se azzerati | Patch completa su nome, traduzioni, descrizione | Il corpo è quasi tutto add/remove; `contentData` arriva come stub non tipizzato; la prova sul tenant decide, come per `edit-credentials` nella 05 |
| Nomi `delete`/`restore` (e `delete-entry`/`restore-entry`), con conferma solo su `delete` | `disable`/`enable` | Stesso verbo del campo `deleted` che l'operatore vede nelle tabelle e dei comandi di users e groups; l'help dice che è logico e reversibile; il ripristino non è distruttivo |
| Comandi delle voci sotto `catalogs` con suffisso `-entry` | Gruppo `catalog-entries` | Accanto alla lettura `catalogs entries`; nessun gruppo in più |
| `edit-workspace` sotto `admin-manage` | Gruppo `workspaces` | Accanto alla lettura `admin-manage workspace`, coerente con la libreria |
| `--cover PATH`/`--logo PATH` con upload (spec 04), stop al primo upload fallito | Solo `--json` con un `contentRef` già ottenuto | Riusa `upload_all`; un passo solo per l'operatore |
| Un solo comando `edit-workspace` con flag add/remove | `edit-workspace` + `edit-workspace-members` | Un solo `PUT` e un solo `occToken`: dividerlo in due comandi non aggiunge sicurezza |
| Ritorno = façade sulla risposta (`CatalogWriteResult`, `CatalogEntryWriteResult`, `CatalogDeletedResult`); `edit_workspace` → `WorkspaceForEdit` | Rileggere il form; solo gli id | Nessuna chiamata in più; la risposta del workspace è già il form |
| Integration: cataloghi e voci con le variabili esistenti; workspace solo con `PYNTERACTA_TEST_WRITE_WORKSPACE=1` | Tutto con le variabili esistenti; solo cataloghi | Il workspace di prova è condiviso con utenti reali: serve un consenso esplicito; senza la prova la semantica del `PUT` resterebbe ignota |
| Riga `0.13.0`, milestone M32 | Patch sulla 0.12.0 | Sette `feat` producono un minor; il numero 0.13.0 è libero (nota di release di M31) |
| Testi della CLI in inglese | Italiano | Decisione della spec 02, sezione Lingua del `CLAUDE.md` |

## Verifica manuale

Nessuna: 06-C21 e 06-C22 sono test automatici opt-in contro il tenant di prova; gli altri
criteri sono unit, contract o snapshot test.

## Revisione dopo la prova sul tenant (T14, 2026-10-12)

Prima esecuzione degli integration test sul tenant di prova, su richiesta del maintainer.

- **Cataloghi e voci (06-C21)**: ciclo verde. Un `edit` o `edit_entry` con la sola lingua `en`
  **sostituisce** la mappa del nome o della label: le altre lingue perdono il loro testo e la
  lingua `it` riceve quello passato. `externalId` e parent omessi in `edit_entry` sono
  **azzerati**. `…/entries/{id}/deleted` risponde con `entryId`. Un catalogo disabilitato chiesto
  per id a `catalogs.list` dà `400` `NOT_EXISTS` sul campo `catalogIds`; `catalogs.list()` senza
  id restituisce una lista vuota su questo tenant, quindi non dice nulla sulla visibilità. La
  `GET` del form di una voce risponde con qualunque `catalogId` nel path. Le patch di
  `catalogs edit` ed `edit-entry` in CLI proteggono già dalla sostituzione; in libreria
  `edit`/`edit_entry` restano espliciti e i docs dicono di passare la mappa completa.
- **Workspace (06-C22)**: il ciclo non parte. Il form reale ha `contentData.description:
  {"it": null}` e la façade `WorkspaceForEdit` solleva la `ValidationError` di pydantic, perché il
  modello generato accetta solo stringhe. Il difetto è della lettura (v0.6) ma blocca
  `edit-workspace` e soprattutto `edit_workspace`, la cui risposta ha la stessa forma: la `PUT`
  riuscirebbe e il chiamante vedrebbe un errore, con esito apparentemente sconosciuto.
- **Decisione del maintainer (2026-10-12)**: le façade dei form scartano le lingue con valore
  `null` prima di validare (06-C23), per il workspace e, a parità di forma, per nome del catalogo
  e label della voce; poi si rilancia il ciclo del workspace. Task T17, eseguito prima di T14.

## Domande aperte

Nessuna.
