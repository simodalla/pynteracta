# Piano 06 – Anagrafiche admin, seconda metà: cataloghi, voci di catalogo e workspace

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Si estende la catena delle scritture delle spec 02-05 senza toccare transport, client base né
`client.py`: `CatalogsAPI` guadagna `create`/`create_raw`, `edit`/`edit_raw`, `set_deleted`,
`create_entry`/`create_entry_raw`, `edit_entry`/`edit_entry_raw`, `set_entry_deleted` e gli alias
`get_for_edit`/`get_entry_for_edit`; `AdminManageAPI` guadagna `edit_workspace`/
`edit_workspace_raw`. I corpi nascono da `build_write_body` (camelCase, solo i non-`None`, dict e
DTO annidati dumpati senza `None`) o dal DTO (`model_dump(mode="json", exclude_none=True)`), come
per utenti e gruppi. Le façade `CatalogForEdit`, `CatalogEntryForEdit` e `WorkspaceForEdit`
espongono `occ_token`, `CatalogForEdit` anche `parent_catalog_id`; `Catalog` e `CatalogEntry`
(già esistenti in `facade/catalogs.py`) guadagnano i campi che il DTO ha e la façade non mostrava
(`etag`, voci; `catalog_id`, `deleted`); tre façade nuove avvolgono le risposte di scrittura
(`CatalogWriteResult`, `CatalogEntryWriteResult`, `CatalogDeletedResult`), rivalidando gli stub
`CatalogDTO`/`CatalogEntryDTO` nei gemelli tipizzati come fa `CatalogList.items_typed`.
`edit_workspace` restituisce `WorkspaceForEdit`, perché la risposta è lo stesso DTO del form.
Nella CLI i comandi stanno in due moduli nuovi, `cli/catalogs_write.py` (registrato su
`catalogs.app`) e `cli/admin_manage_write.py` (su `admin_manage.app`), come `users_write.py` e
`groups_write.py`; riusano `merge_body`, `validate_body`, `load_json_body`, `confirm_destructive`,
`handle_error(resource=…)`, `render_output` e le opzioni condivise di `cli/_write.py`, dove
arrivano due helper puri: `parse_lang_map` (coppie `LANG=TESTO` → mappa, senza coercizione dei
valori) e `parse_int_pairs` (coppie `ID=ID` → liste di interi) più `merge_lang_map` (unione
chiave per chiave di una mappa letta, di `--json` e dei flag). Le patch (`catalogs edit`,
`edit-entry`) costruiscono la base dal form riletto con funzioni pure (`_catalog_edit_base`,
`_entry_edit_base`); `edit-workspace` non è una patch: legge il form solo per l'`occToken` e
invia i soli campi indicati, caricando `--cover` e `--logo` con `client.attachments.upload`
(spec 04). Fixture JSON e contract test per i 10 DTO; integration test opt-in (cataloghi e voci
con le variabili esistenti, workspace con `PYNTERACTA_TEST_WRITE_WORKSPACE=1`), con ripristino
in `finally`; pagine `docs/`, `index.md` e `README.md`. Test prima del codice, un commit per
task.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `ROADMAP.md` | modificato (apertura) | riga `0.13.0 ⏳ M32`, "Admin write, second half: catalogs, catalog entries and workspace (fifth write group, ADR 0001)", link alla spec; nota "last used: M32" |
| `src/pynteracta/models/facade/catalogs.py` | modificato | `Catalog.etag` (`raw.etag`), `Catalog.entries_typed` (gli stub `raw.entries` rivalidati in `CatalogEntryDTO1` → `CatalogEntry`, lista vuota se `None`); `CatalogEntry.catalog_id` (`raw.catalogId`), `CatalogEntry.deleted` (`raw.deleted`); `Catalog.from_stub(stub: CatalogDTO)` e `CatalogEntry.from_stub(stub: CatalogEntryDTO)` (rivalidano con `_resolve_root` importato da `facade.admin_manage`, `ValueError` se il root non è un dict, come `GroupSummary.from_stub`); `CatalogWriteResult(raw: CreateEditCatalogResponseDTO, *, catalog_id: int \| None = None)`: `catalog` (`Catalog.from_stub(raw.catalog)` o `None`), `parent_catalog` (idem), `catalog_id` (`catalog.id` se c'è, altrimenti quello passato), `next_occ_token` (`raw.occToken`), `.raw`, `from_dict(data, catalog_id=None)`; `CatalogEntryWriteResult(raw: CreateEditCatalogEntryResponseDTO, *, catalog_id, entry_id=None)`: `entry` (`CatalogEntry.from_stub(raw.entry)` o `None`), `catalog_id` (`entry.catalog_id` se c'è, altrimenti quello passato), `entry_id` (`entry.id`, altrimenti quello passato), `next_occ_token`, `.raw`, `from_dict(data, catalog_id, entry_id=None)`; `CatalogDeletedResult(raw: EditCatalogDeletedResponseDTO \| EditCatalogEntryDeletedResponseDTO, *, catalog_id, entry_id=None)`: `catalog_id` (`getattr(raw, "catalogId", None)`, altrimenti quello passato), `entry_id` (`getattr(raw, "entryId", None)`, altrimenti quello passato), `deleted` (`raw.deleted`), `.raw`, `from_dict(data, catalog_id, entry_id=None)` che sceglie il DTO dalla chiave presente (`entryId` → `EditCatalogEntryDeletedResponseDTO`, altrimenti `EditCatalogDeletedResponseDTO`); docstring del modulo aggiornata (endpoint di scrittura) |
| `src/pynteracta/models/facade/admin_manage.py` | modificato | `WorkspaceForEdit.occ_token`, `CatalogForEdit.occ_token`, `CatalogEntryForEdit.occ_token` (`raw.occToken`); `CatalogForEdit.parent_catalog_id` (`_content.parentCatalog` rivalidato con `_resolve_root` in `CatalogDTOModel`, `.id`; `None` senza parent o senza `contentData`); docstring del modulo e delle tre classi: `occToken` non è più "solo su `.raw`"; `WorkspaceForEdit` dice che è anche la risposta di `edit_workspace` |
| `src/pynteracta/models/facade/__init__.py` | modificato | esporta `CatalogWriteResult`, `CatalogEntryWriteResult`, `CatalogDeletedResult` |
| `src/pynteracta/api/catalogs.py` | modificato | costanti `_ADMIN_CATALOGS_PATH = "admin/manage/catalogs"`, `_ADMIN_CATALOG_PATH = "admin/manage/catalogs/{catalog_id}"`, `_ADMIN_CATALOG_DELETED_PATH = "…/{catalog_id}/deleted"`, `_ADMIN_CATALOG_FOR_EDIT_PATH = "…/{catalog_id}/edit"`, `_ADMIN_ENTRIES_PATH = "…/{catalog_id}/entries"`, `_ADMIN_ENTRY_PATH = "…/entries/{entry_id}"`, `_ADMIN_ENTRY_DELETED_PATH`, `_ADMIN_ENTRY_FOR_EDIT_PATH`; `create(*, name: dict[str, str] \| None = None, parent_id: int \| None = None) -> CatalogWriteResult` (`build_write_body` → `_post` → `CatalogWriteResult.from_dict`); `create_raw(req: CreateEditCatalogRequestDTO)`; `edit(catalog_id, occ_token, *, name=None, parent_id=None)` (`build_write_body(..., occ_token=occ_token)` → `_put` → `from_dict(resp, catalog_id=catalog_id)`); `edit_raw(catalog_id, req)`; `set_deleted(catalog_id, deleted: bool) -> CatalogDeletedResult` (corpo esatto `{"deleted": deleted}` → `_put`); `create_entry(catalog_id, *, label=None, parent_ids=None, external_id=None) -> CatalogEntryWriteResult`; `create_entry_raw(catalog_id, req: CreateEditCatalogEntryRequestDTO)`; `edit_entry(catalog_id, entry_id, occ_token, *, label=None, parent_ids=None, external_id=None)`; `edit_entry_raw(catalog_id, entry_id, req)`; `set_entry_deleted(catalog_id, entry_id, deleted: bool) -> CatalogDeletedResult` (`from_dict(resp, catalog_id, entry_id)`); `get_for_edit(catalog_id) -> CatalogForEdit` e `get_entry_for_edit(catalog_id, entry_id) -> CatalogEntryForEdit` (stesse `GET` di `AdminManageAPI`, façade importate da `facade.admin_manage`); docstring di classe e metodi in italiano con "una sola richiesta, nessun nuovo tentativo", "`deleted` solo con `set_deleted`/`edit_raw`" e "campi omessi: semantica del server, vedi `docs/api/catalogs.md`" |
| `src/pynteracta/api/admin_manage.py` | modificato | costante `_WORKSPACE_EDIT_PATH = "admin/manage/workspaces/{workspace_id}/{occ_token}"`; `edit_workspace(workspace_id, occ_token, *, name=None, translations=None, description=None, new_cover_image_content_ref=None, new_logo_content_ref=None, add_user_ids=None, remove_user_ids=None, add_group_ids=None, remove_group_ids=None, add_user_role_associations=None, add_group_role_associations=None, remove_role_association_ids=None) -> WorkspaceForEdit` (`# noqa: PLR0913`; `build_write_body(**kwargs)` senza `occ_token`, che va nel path → `_put` → `WorkspaceForEdit.from_dict`); tipo locale `RoleAssociations = list[dict[str, Any] \| BaseModel] \| None`; `edit_workspace_raw(workspace_id, occ_token, req: EditWorkspaceRequestDTO)`; docstring del modulo e della classe: `occ_token` su tutte le façade, `catalog_for_edit`/`catalog_entry_for_edit` rimandano agli alias e alle scritture di `CatalogsAPI` |
| `src/pynteracta/cli/_write.py` | modificato | `parse_lang_map(values: list[str] \| None, *, option: str) -> dict[str, str]`: coppie `LANG=TESTO`, split al primo `=`, lingua `strip()`; senza `=` o con lingua vuota → `typer.BadParameter(f"{option} must be LANG=TEXT, got: {item!r}")` (exit `2`); il testo resta stringa (nessuna coercizione, a differenza di `parse_kv_values`), anche vuoto; `parse_int_pairs(values, *, option, form: str = "USER_ID=ROLE_ID") -> list[tuple[int, int]]`: senza `=` o con un lato non intero → `BadParameter(f"{option} must be {form}, got: {item!r}")`; `merge_lang_map(merged: dict, key: str, flag_map: dict[str, str]) -> None`: se `flag_map` non è vuota, `merged[key] = {**merged.get(key) or {}, **flag_map}` (unione chiave per chiave della mappa già presente, letta dal form o da `--json`, con quella dei flag); docstring del modulo: "Con la spec 06: mappe per lingua e coppie di id" |
| `src/pynteracta/cli/catalogs_write.py` | nuovo | `from pynteracta.cli.catalogs import app`; opzioni `NameOption` (`--name LANG=TEXT`, ripetibile), `ParentOption` (`--parent ID`), `LabelOption` (`--label LANG=TEXT`), `ParentEntryOption` (`--parent-entry ID`, ripetibile), `ExternalIdOption`, più `JsonBodyOption`, `OccTokenOption`, `--yes/-y`; funzioni pure: `_catalog_edit_base(form: CatalogForEdit) -> dict` (`name` se non `None`, `parentId` da `parent_catalog_id` se non `None`; mai `deleted`), `_entry_edit_base(form: CatalogEntryForEdit) -> dict` (`label`, `externalId` se non `None`; `parentIds` = `[p.id for p in parents tipizzati if p.id is not None]` solo se `raw.parents` non è `None`), `_display_name(mapping: dict[str, str] \| None) -> str` (`mapping["it"]` se c'è, altrimenti il primo valore, altrimenti `""`), `_require_token(label: str, occ_token, read_token) -> int` (come in `groups_write.py`, messaggio `{label} has no occToken in the server response: pass --occ-token explicitly.`, `EXIT_GENERIC`); righe curate `_catalog_row` (`catalog_id`, `name`, `parent_catalog_id`, `next_occ_token`) e `_entry_row` (`entry_id`, `catalog_id`, `label`, `external_id`, `next_occ_token`); comandi `catalogs create`, `catalogs edit CATALOG_ID`, `catalogs delete CATALOG_ID`, `catalogs restore CATALOG_ID`, `catalogs create-entry CATALOG_ID`, `catalogs edit-entry CATALOG_ID ENTRY_ID`, `catalogs delete-entry CATALOG_ID ENTRY_ID`, `catalogs restore-entry CATALOG_ID ENTRY_ID` secondo la spec; `render_output(..., single_command=True)` per create/edit; `delete`/`restore` stampano `Catalog 5 deleted\|restored` o il JSON `{"catalog_id", "deleted"}` (voci: `Entry 100 of catalog 5 …`, JSON con `entry_id`); `handle_error(..., resource=f"Catalog {id}" \| f"Entry {entry_id} of catalog {catalog_id}")`; help di `delete`/`delete-entry`: "Logical deletion: the catalog stays on the tenant with deleted=true and 'catalogs restore' brings it back." |
| `src/pynteracta/cli/admin_manage_write.py` | nuovo | `from pynteracta.cli.admin_manage import app`; opzioni `--name TEXT`, `--description LANG=TEXT` (ripetibile), `--add-user ID`, `--remove-user ID`, `--add-group ID`, `--remove-group ID`, `--add-user-role USER_ID=ROLE_ID`, `--add-group-role GROUP_ID=ROLE_ID`, `--remove-role-association ID` (tutti ripetibili), `--cover PATH`, `--logo PATH` (`exists=True, dir_okay=False, readable=True` come `AttachOption`), `--json`, `--occ-token`; funzione pura `_workspace_body(json_part, *, name, description, add_user, remove_user, add_group, remove_group, user_roles: list[tuple[int,int]], group_roles, remove_role_association) -> dict` (`merge_body` per le liste e `name`, `merge_lang_map` per `description`, `addUserRoleAssociations` = `[{"userId": u, "roleId": r}]`, `addGroupRoleAssociations` = `[{"groupId": g, "roleId": r}]`; le liste vuote non si mettono); comando `admin-manage edit-workspace WORKSPACE_ID`: corpo vuoto e senza `--cover`/`--logo` → `"Nothing to send: pass at least one option or --json."`, `EXIT_CONFIG` prima di `build_client`; poi `token = --occ-token` oppure `client.admin_manage.workspace_for_edit(id).occ_token` (la `GET` avviene solo senza `--occ-token`); poi `--cover` e `--logo` in quest'ordine con `client.attachments.upload(path).content_ref` in `newCoverImageContentRef`/`newLogoContentRef` (l'`UploadError` risale a `handle_error` → exit `11`, nessuna `PUT`); `req = validate_body(merged, EditWorkspaceRequestDTO)`; `client.admin_manage.edit_workspace_raw(id, token, req)`; riga `_workspace_write_row` (`id`, `name`, `admin_users_count`, `member_users_count`, `admin_groups_count`, `member_groups_count`, `occ_token`), distinta da `_workspace_to_row` della lettura, che resta senza token; `render_output(..., title=f"Workspace {id} updated", single_command=True)`; `handle_error(..., resource=f"Workspace {id}")` |
| `src/pynteracta/cli/__init__.py` | modificato | `from pynteracta.cli import catalogs_write as _catalogs_write_cli  # noqa: F401` e `admin_manage_write`, accanto a `users_write`/`groups_write` |
| `src/pynteracta/cli/catalogs.py`, `src/pynteracta/cli/admin_manage.py` | modificati (solo docstring) | il docstring del modulo elenca i comandi di scrittura registrati dai moduli `*_write.py`; in `admin_manage.py` sparisce "for the future write line" e "it lives on `.raw`": `occ_token` è una proprietà, resta fuori dalla tabella di default della lettura (gli snapshot non cambiano) |
| `tests/fixtures/payloads/create_catalog_response.json` | nuovo | `{"catalog": {"id": 6, "name": "Sedi", "etag": 1, "paged": false}, "parentCatalog": {"id": 3, "name": "Root", "etag": 4, "paged": false}, "occToken": 1}` |
| `tests/fixtures/payloads/edit_catalog_response.json` | nuovo | `{"catalog": {"id": 5, "name": "Reparti", "etag": 10, "paged": false}, "occToken": 10}` (senza `parentCatalog`) |
| `tests/fixtures/payloads/edit_catalog_deleted_response.json` | nuovo | `{"catalogId": 5, "deleted": true}` |
| `tests/fixtures/payloads/create_catalog_entry_response.json` | nuovo | `{"entry": {"id": 101, "catalogId": 5, "label": "Bologna", "externalId": "BO", "parentIds": [10], "deleted": false}, "occToken": 1}` |
| `tests/fixtures/payloads/edit_catalog_entry_response.json` | nuovo | `{"entry": {"id": 100, "catalogId": 5, "label": "Ingegneria", "externalId": "BO2", "parentIds": [1], "deleted": false}, "occToken": 5}` |
| `tests/fixtures/payloads/edit_catalog_entry_deleted_response.json` | nuovo | `{"catalogId": 5, "deleted": true}` (la forma dichiarata dal swagger; la variante `{"entryId": 100, "deleted": true}` è un dict inline nel test di 06-C06) |
| `tests/fixtures/payloads/edit_workspace_response.json` | nuovo | copia di `get_workspace_for_edit_response.json` con `occToken: 18` e `memberUsersCount: 26` |
| `tests/fixtures/payloads/get_catalog_for_edit_response.json` | invariato | il form senza `parentCatalog` è il caso "la chiave `parentId` manca"; la variante con `parentCatalog: {"id": 3, "name": "Root"}` si costruisce nei test con `copy.deepcopy` più la chiave, così gli snapshot di `admin-manage catalog` non cambiano |
| `tests/unit/test_facade_catalogs.py` | nuovo | `Catalog.etag`/`entries_typed`, `CatalogEntry.catalog_id`/`deleted`, `from_stub` (root non dict → `ValueError`); `CatalogWriteResult.from_dict` sulle due fixture (campi, `catalog_id` dalla risposta o passato, `parent_catalog` `None`), `CatalogEntryWriteResult.from_dict`, `CatalogDeletedResult.from_dict` nelle due forme (`catalogId`/`entryId`) e con gli id passati |
| `tests/unit/test_facade_admin_manage.py` | modificato | i tre `test_occ_token_only_on_raw` → `test_occ_token_exposed` (06-C07); `TestCatalogForEdit::test_parent_catalog_id` (con e senza `parentCatalog`, senza `contentData`) |
| `tests/unit/test_api_catalogs.py` | modificato | 06-C01…C07 (parte cataloghi), 06-C09: classi `TestCatalogsCreate`, `TestCatalogsEdit`, `TestCatalogsSetDeleted`, `TestCatalogEntriesCreate`, `TestCatalogEntriesEdit`, `TestCatalogEntriesSetDeleted`, `TestCatalogsForEditAliases`, `TestCatalogsWriteErrors`: route `respx` sui percorsi admin, corpo esatto da `route.calls[0].request.content`, `call_count == 1`, varianti `_raw`, `409` → `ConcurrencyError`, `404` → `NotFoundError`, `httpx.ReadTimeout` → `TransportError` |
| `tests/unit/test_api_admin_manage.py` | modificato | `TestEditWorkspace` (06-C08: corpo esatto, path con l'`occToken`, nessun `occToken` nel corpo, risultato `WorkspaceForEdit` con `occ_token == 18`, `_raw` equivalente), 06-C09 (`409`, timeout) |
| `tests/unit/test_cli_write.py` | modificato | `TestParseLangMap` (coppie valide, testo con `=`, senza `=` → `BadParameter`, lingua vuota → `BadParameter`, `None` → `{}`), `TestParseIntPairs`, `TestMergeLangMap` (mappa assente, presente, `None` nel corpo, flag vuoti) |
| `tests/unit/test_cli_catalogs_write.py` | nuovo | 06-C10…C16: `TestCatalogsCreate` (flag + `--json` da `tmp_path` con unione per chiave, snapshot tabella e `--output json`, `--name Sedi` e `--name =Sedi` → exit `2` e route non chiamata), `TestCatalogsEdit` (GET + PUT, corpo esatto con e senza `parentCatalog`, `--parent 4`, `--occ-token 8` con la GET, nessun flag → form invariato), `TestCatalogsDelete`/`TestCatalogsRestore` (prompt con il nome `it`, `y`/`n`/`--yes`/non interattivo, JSON, nome mancante → `""`, `restore` senza prompt anche non interattivo), `TestCatalogEntriesCreate`, `TestCatalogEntriesEdit` (`parentIds` letti o sostituiti, chiave assente senza `parents`), `TestCatalogEntriesDelete`/`Restore`, `TestCatalogsConflict` (`409` → exit `9`, messaggio con la risorsa, una sola PUT, per `edit` ed `edit-entry`); `test_catalog_edit_base_*`, `test_entry_edit_base_*`, `test_display_name_*` sulle funzioni pure |
| `tests/unit/test_cli_admin_manage_write.py` | nuovo | 06-C13 (workspace), 06-C17, 06-C18: `TestEditWorkspace` (GET + PUT con corpo esatto e path `88/9`, snapshot tabella con `occ_token`, `--occ-token 10` senza GET, `--add-user-role 1` → exit `2`, nessun flag → exit `2` e nessuna route chiamata, `--json` con `description` più `--description en=…` → mappa unita), `TestEditWorkspaceUploads` (route dell'upload della spec 04 riusate da `test_cli_posts_write.py`: due upload nell'ordine e i due `contentRef` nel corpo; upload della copertina in errore → exit `11`, un solo upload, nessuna PUT), `TestEditWorkspaceConflict` (`409` → exit `9`, `Workspace 88 changed since it was read…`); `test_workspace_body_*` sulla funzione pura |
| `tests/unit/test_cli_catalogs.py`, `tests/unit/test_cli_admin_manage.py` | invariati | restano verdi: le tabelle di lettura e gli snapshot non cambiano (controllo del refactor delle docstring) |
| `tests/contract/test_models.py` | modificato | 06-C19: `TestAdminCatalogsWorkspaceWriteDTOs`: `assert_superset` sui 10 DTO della spec più i gemelli tipizzati usati dalle façade (`CatalogDTOModel`, `CatalogEntryDTO1`, `CatalogEditableContentDTOModel`, `EditCatalogEntryDeletedResponseDTO`); smoke delle façade sulle sette fixture nuove |
| `tests/integration/test_catalogs_integration.py` | nuovo | 06-C21: fixture `client` locale (stessa forma degli altri file); `TestCatalogsWriteIntegration::test_create_edit_entry_delete_cycle`: `create(name={"it": f"pynteracta-it-{ts}"})` → `get_for_edit` (stampa `occ_token`, `parent_catalog_id`) → `edit(name={"en": …})` con un solo campo → rilettura (stampa della mappa del nome: sostituita o unita) → `create_entry(label=…, external_id=…)` → `get_entry_for_edit` → `edit_entry(label={"en": …})` → rilettura (stampa di `external_id` e `parents_count`: mantenuti o azzerati) → `set_entry_deleted(True)` (stampa di quale id arriva: `raw` ha `catalogId` o `entryId`) → in `finally` `set_deleted(True)` se il catalogo è stato creato → `catalogs.list([id])` (stampa se il catalogo disabilitato compare) → `get_for_edit` e `assert deleted is True`; righe `[06-C21]` |
| `tests/integration/test_admin_manage_integration.py` | modificato | 06-C22: `TestWorkspaceWriteIntegration::test_add_remove_member_cycle`: `_require_flag("PYNTERACTA_TEST_WRITE_WORKSPACE")` (salta se diverso da `1`) e `PYNTERACTA_TEST_WORKSPACE_ID`, `PYNTERACTA_TEST_USER_ID`; `workspace_for_edit` (nome, descrizione, `member_users_count` iniziali) → `edit_workspace(token, add_user_ids=[user])` → stampa `[06-C22]` se `name`/`description` sono rimasti uguali → in `finally` `edit_workspace(remove_user_ids=[user])` con il token restituito e, se nome o descrizione sono cambiati, un ultimo `edit_workspace(name=…, description=…)` di ripristino; assert finali: `member_users_count` iniziale e nome invariato |
| `tests/integration/.env.example`, `docs/testing.md` | modificati | `PYNTERACTA_TEST_WRITE_WORKSPACE=` (commento: aggiunge e toglie `PYNTERACTA_TEST_USER_ID` dal workspace `PYNTERACTA_TEST_WORKSPACE_ID`, che è condiviso con utenti reali; vuota = saltato); nota che il ciclo dei cataloghi usa le variabili di base e disabilita ciò che crea (nessuna eliminazione fisica) |
| `docs/api/catalogs.md` | modificato | pagina riscritta con "Reading", "Writing catalogs" (`create`, `edit`, `set_deleted`, `CatalogWriteResult`, `CatalogDeletedResult`, `occ_token`, `parent_catalog_id`, `deleted` solo da `set_deleted`/`edit_raw`, campi omessi e semantica del server dopo 06-C21, visibilità dei disabilitati in `list`), "Writing catalog entries" (`create_entry`, `edit_entry`, `set_entry_deleted`, `CatalogEntryWriteResult`, quale id arriva da `…/deleted`), "Edit forms" (`get_for_edit`, `get_entry_for_edit`), riferimento mkdocstrings a tutti i metodi e alle façade nuove |
| `docs/api/admin_manage.md` | modificato | "four read-form endpoints" → letture più `edit_workspace`; tabella con `edit_workspace` (`PUT admin/manage/workspaces/{workspaceId}/{occToken}`); `occ_token` su tutte le façade (D-v0.6-2 superata); `parent_catalog_id`; rimando a `catalogs.get_for_edit`/`get_entry_for_edit`; semantica dei campi omessi del workspace dopo 06-C22; snippet con `edit_workspace(add_user_ids=…)` e `--cover` via `attachments.upload` |
| `docs/cli.md` | modificato | sezioni `catalogs create\|edit\|delete\|restore\|create-entry\|edit-entry\|delete-entry\|restore-entry` dopo `catalogs entries`, con la forma `LANG=TEXT`, la patch, la cancellazione logica e l'exit `9`; `admin-manage edit-workspace` dopo `admin-manage user-credentials`, con `USER_ID=ROLE_ID`, `--cover`/`--logo` ed exit `11`; l'intro di `admin-manage` non dice più "workspace and catalog writes arrive with their own spec" né "it lives on `.raw.occToken`" |
| `docs/index.md`, `README.md` | modificati | "Write operations" cita cataloghi, voci e workspace; "Event posts and the admin catalogs and workspace follow" → "Event posts follow"; `index.md` "What's out of scope": restano i soli post evento |
| `tests/unit/test_docs_snippets.py` | modificato | 06-C20: `test_catalogs_workspace_pages_document_write_commands` (le pagine citano i nove comandi, `LANG=TEXT`, `--cover`, `restore`, `CatalogWriteResult`, `CatalogDeletedResult`, `edit_workspace`, `occ_token`, `parent_catalog_id`; `index.md` e `README.md` non contengono più "catalogs and workspace follow"); gli snippet nuovi passano dal controllo di coerenza esistente |
| `PROGRESS.md` | modificato (verifica) | sezione M32 |
| `specs/prd.md` | modificato (chiusura) | RF-023 precisato con la semantica verificata e "(spec 05, 0.12.0)"; RF-023e, RF-023f; conferma di RF-008, RF-013, RF-019 e della voce di §6 |

Non si toccano: `transport.py`, `hooks.py`, `logging.py` (nessuna chiave sensibile nuova),
`api/_base.py` (`_put` e la mappatura di `204` esistono), `api/_utils.py` (`build_write_body`
basta), `api/attachments.py` (`upload` esiste), `client.py` (`client.catalogs`,
`client.admin_manage`, `client.attachments` esistono), `exceptions.py`, `models/generated/`
(i 10 DTO sono già generati, nessuna rigenerazione), `cli/_common.py`.

## Modello dati e migrazioni

Nessuna modifica: i 10 DTO sono già generati. Gli stub `RootModel[Any]` da rivalidare nei gemelli
tipizzati sono `CatalogDTO` → `CatalogDTOModel` (`catalog`/`parentCatalog` di
`CreateEditCatalogResponseDTO`, `parentCatalog` di `CatalogEditableContentDTOModel`, `entries`
di `CatalogDTOModel`), `CatalogEntryDTO` → `CatalogEntryDTO1` (`entry` di
`CreateEditCatalogEntryResponseDTO`, `parents` di `GetCatalogEntryForEditResponseDTO`),
`CreateUserRoleAssociationDTOModel`/`CreateGroupRoleAssociationDTOModel` → dict nella forma di
`CreateUserRoleAssociationDTO`/`CreateGroupRoleAssociationDTO` (solo in ingresso: `validate_body`
accetta i dict). La risposta di `…/entries/{id}/deleted` è dichiarata `EditCatalogDeletedResponseDTO`
(`catalogId`) ma esiste anche `EditCatalogEntryDeletedResponseDTO` (`entryId`): `CatalogDeletedResult`
sceglie il DTO dalla chiave presente e completa con gli id passati.

## Flussi

```
Libreria: cataloghi e voci (client.catalogs)
create(name=, parent_id=)          → body = build_write_body(name=…, parent_id=…)
                                   → _post("admin/manage/catalogs", json=body)
                                   → CatalogWriteResult.from_dict(resp)
edit(id, occ_token, name=, parent_id=)
                                   → body = build_write_body(name=…, parent_id=…, occ_token=occ_token)
                                   → _put("admin/manage/catalogs/{id}", json=body)   (409 → ConcurrencyError dal transport)
                                   → CatalogWriteResult.from_dict(resp, catalog_id=id)
set_deleted(id, deleted)           → _put("admin/manage/catalogs/{id}/deleted", json={"deleted": deleted})
                                   → CatalogDeletedResult.from_dict(resp, catalog_id=id)
create_entry(cid, label=, parent_ids=, external_id=)
                                   → _post("admin/manage/catalogs/{cid}/entries", json=build_write_body(...))
                                   → CatalogEntryWriteResult.from_dict(resp, catalog_id=cid)
edit_entry(cid, eid, occ_token, …) → _put("admin/manage/catalogs/{cid}/entries/{eid}", json=build_write_body(..., occ_token=…))
                                   → CatalogEntryWriteResult.from_dict(resp, catalog_id=cid, entry_id=eid)
set_entry_deleted(cid, eid, deleted)
                                   → _put(".../entries/{eid}/deleted", json={"deleted": deleted})
                                   → CatalogDeletedResult.from_dict(resp, catalog_id=cid, entry_id=eid)
get_for_edit(id) / get_entry_for_edit(cid, eid)
                                   → CatalogForEdit.from_dict(_get(".../{id}/edit")) / CatalogEntryForEdit.from_dict(...)
*_raw(…, req)                      → stesso percorso con req.model_dump(mode="json", exclude_none=True)

Libreria: workspace (client.admin_manage)
edit_workspace(wid, occ_token, **kw)
                                   → body = build_write_body(**kw)                (nessun occToken nel corpo)
                                   → _put(f"admin/manage/workspaces/{wid}/{occ_token}", json=body)
                                   → WorkspaceForEdit.from_dict(resp)             (occ_token = quello successivo)
Errori: nessun try/except nei metodi; una richiesta per chiamata; il transport mappa gli stati
(409 → ConcurrencyError, 404 → NotFoundError, timeout → TransportError); 204 su una GET …/edit → NotFoundError (spec 05).

CLI: cataloghi e voci
catalogs create                    → name_map = parse_lang_map(--name)  (BadParameter → exit 2, prima di build_client)
                                   → merged = merge_body(load_json_body(--json, CreateEditCatalogRequestDTO), parent_id=--parent)
                                   → merge_lang_map(merged, "name", name_map)
                                   → req = validate_body(merged, CreateEditCatalogRequestDTO)
                                   → client.catalogs.create_raw(req) → render_output([result], _catalog_row, title="Catalog {id} created")
catalogs edit CATALOG_ID           → json_part = load_json_body(--json, CreateEditCatalogRequestDTO); name_map = parse_lang_map(--name)
                                   → form = client.catalogs.get_for_edit(CATALOG_ID)       (sempre, anche con --occ-token)
                                   → token = --occ-token or form.occ_token (None → messaggio, exit 1)
                                   → merged = merge_body({**_catalog_edit_base(form), **json_part}, parent_id=--parent)
                                   → merge_lang_map(merged, "name", name_map); merged["occToken"] = token
                                   → req = validate_body(merged, CreateEditCatalogRequestDTO)      (mai "deleted" dalla patch)
                                   → client.catalogs.edit_raw(CATALOG_ID, req) → render_output(..., title="Catalog {id} updated")
                                   → ConcurrencyError → handle_error(resource="Catalog {id}") → exit 9
catalogs delete CATALOG_ID         → form = client.catalogs.get_for_edit(CATALOG_ID)   (404/204 → exit 5, nessuna PUT)
                                   → confirm_destructive(f'Delete catalog {id} "{_display_name(form.name)}"?', yes=--yes)  False → Exit(0)
                                   → client.catalogs.set_deleted(CATALOG_ID, True) → "Catalog {id} deleted" | {"catalog_id": id, "deleted": true}
catalogs restore CATALOG_ID        → client.catalogs.set_deleted(CATALOG_ID, False), nessuna GET, nessun prompt
                                   → "Catalog {id} restored" | {"catalog_id": id, "deleted": false}
catalogs create-entry CATALOG_ID   → come create con label_map, parent_ids=--parent-entry, external_id=--external-id
                                   → client.catalogs.create_entry_raw(CATALOG_ID, req) → render_output([result], _entry_row)
catalogs edit-entry CATALOG_ID ENTRY_ID
                                   → form = client.catalogs.get_entry_for_edit(…) → token
                                   → merged = merge_body({**_entry_edit_base(form), **json_part}, parent_ids=--parent-entry, external_id=--external-id)
                                   → merge_lang_map(merged, "label", label_map); merged["occToken"] = token
                                   → client.catalogs.edit_entry_raw(…) → render_output; 409 → resource="Entry {eid} of catalog {cid}"
catalogs delete-entry / restore-entry
                                   → come delete/restore con get_entry_for_edit, prompt 'Delete entry {eid} "{label}" of catalog {cid}?',
                                     set_entry_deleted, "Entry {eid} of catalog {cid} deleted|restored" | {"catalog_id", "entry_id", "deleted"}

CLI: workspace
admin-manage edit-workspace WORKSPACE_ID
                                   → description_map = parse_lang_map(--description); user_roles = parse_int_pairs(--add-user-role)
                                     group_roles = parse_int_pairs(--add-group-role, form="GROUP_ID=ROLE_ID")   (BadParameter → exit 2)
                                   → merged = _workspace_body(load_json_body(--json, EditWorkspaceRequestDTO), name=…, …)
                                   → merged vuoto e --cover/--logo assenti → "Nothing to send…", exit 2, nessuna richiesta
                                   → token = --occ-token, altrimenti client.admin_manage.workspace_for_edit(id).occ_token  (GET solo senza --occ-token)
                                   → --cover → merged["newCoverImageContentRef"] = client.attachments.upload(cover).content_ref
                                     --logo  → merged["newLogoContentRef"] = …                       (UploadError → exit 11, nessuna PUT)
                                   → req = validate_body(merged, EditWorkspaceRequestDTO)
                                   → result = client.admin_manage.edit_workspace_raw(id, token, req)
                                   → render_output([result], _workspace_write_row, title="Workspace {id} updated")
                                   → ConcurrencyError → handle_error(resource="Workspace {id}") → exit 9
```

## Interfaccia

Comandi, opzioni e messaggi come nella sezione "CLI" della spec; testi in inglese (decisione
della spec 02). Help breve con il formato atteso (`--name LANG=TEXT (repeatable; e.g. it=Sedi)`,
`--add-user-role USER_ID=ROLE_ID (repeatable)`, `--cover PATH: upload the file and set it as the
cover image`). L'help di `catalogs delete` e `delete-entry` dice che la cancellazione è logica e
reversibile con `restore`/`restore-entry`. `catalogs edit --help` non elenca `--deleted`. Le
tabelle di `admin-manage workspace|catalog|catalog-entry` restano come oggi. Nessuna pagina web.

## Configurazione

Nessuna variabile di runtime. Solo per gli integration test, in `tests/integration/.env.example`
e `docs/testing.md`: `PYNTERACTA_TEST_WRITE_WORKSPACE` (vuota: il ciclo del workspace è saltato;
`1`: aggiunge e toglie `PYNTERACTA_TEST_USER_ID` dal workspace `PYNTERACTA_TEST_WORKSPACE_ID`).
Il ciclo dei cataloghi usa le variabili di base già presenti.

## Sicurezza e dati personali

- **Token e segreti mai nei log**: nessun log nuovo; nessun campo sensibile nei corpi (nomi e
  label di cataloghi, id, `contentRef`). L'`occToken` del workspace sta nel path: non è un
  segreto e la redazione degli URL (RNF-001) agisce sui parametri di query, come dice la spec.
  I file di `--cover`/`--logo` passano dal meccanismo della spec 04 (RNF-011: il contenuto non
  compare in log, audit log né hook).
- **Nessuna operazione ripetuta in automatico**: i metodi fanno una richiesta e lasciano salire
  le eccezioni; la CLI non riprova su `409` (06-C09, 06-C13); `edit-workspace` fa gli upload
  prima della `PUT` e si ferma al primo fallito (06-C18); un upload riuscito seguito da un `409`
  lascia il file nello storage temporaneo fino alla scadenza della policy (spec 04).
- **Dati personali**: i corpi del workspace contengono id di utenti e gruppi, non nomi; non si
  salvano. Fixture con valori finti (`Sedi`, `Bologna`, id piccoli). Gli integration test creano
  un catalogo con nome `pynteracta-it-<timestamp>` e lo disabilitano in `finally`; il ciclo del
  workspace parte solo con l'opt-in dedicato, aggiunge e toglie l'utente di prova e ripristina
  nome e descrizione se il server li avesse azzerati.
- **Conferma delle operazioni distruttive**: `confirm_destructive` riusato com'è su `delete` e
  `delete-entry`; nessuna via che disabiliti senza `y` o `--yes` (06-C14). `restore` e
  `restore-entry` non sono distruttivi e non chiedono (06-C15).
- **Soglie che non scendono**: i file nuovi (`catalogs_write.py`, `admin_manage_write.py`,
  `test_facade_catalogs.py`) e quelli toccati hanno un test per ogni ramo (errori d'uso,
  `occ_token` assente, form senza `contentData`/`name`/`parents`, corpo vuoto, upload fallito);
  copertura ≥ 85 % per file e totale ≥ 94,94 % (linea di partenza aggiornata dalla spec 05).

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `WorkspaceForEdit`, `CatalogForEdit`, `CatalogEntryForEdit` | oggi `occ_token` **non** è una proprietà (`test_occ_token_only_on_raw` ×3) | nessuno: è il comportamento che la spec cambia (RF-023e); i tre test si sostituiscono con `test_occ_token_exposed` (06-C07) nello stesso task, così il cambiamento è esplicito |
| `Catalog`, `CatalogEntry` (façade di lettura) | campi esposti e rivalidazione degli stub in `items_typed` | già fissato da `test_api_catalogs.py::TestCatalogsAPI` e dagli snapshot di `catalogs list\|entries`; le proprietà nuove si aggiungono senza toccare quelle esistenti |
| `admin-manage workspace\|catalog\|catalog-entry` (CLI) | tabella senza `occ_token`, JSON | già fissati dagli snapshot `syrupy` e da `test_occ_token_absent_from_default_table`: restano verdi dopo le modifiche alle docstring |
| `catalogs list\|entries` (CLI) | tabella e JSON | già fissati dagli snapshot; `catalogs_write.py` registra comandi nuovi sulla stessa app senza toccare quelli esistenti |
| `admin_manage.catalog_for_edit`, `catalog_entry_for_edit`, `workspace_for_edit` | richiesta e façade | già fissato da `test_api_admin_manage.py`; gli alias di 06-C07 si confrontano con le stesse route |
| `cli/_write.py` (`merge_body`, `parse_kv_values`) | unione per chiave intera; coercizione dei valori | già fissato da `test_cli_write.py`; gli helper nuovi si aggiungono accanto, senza cambiare quelli esistenti |
| `build_write_body` | dict e DTO annidati, anche in lista, dumpati senza `None` | già fissato da `test_api_utils.py::TestBuildWriteBody`: nessun test nuovo |
| `attachments.upload` | upload in due passi, `UploadError` | già fissato da `test_api_attachments.py` e `test_cli_posts_write.py` (spec 04); `edit-workspace` riusa le stesse route mock |

Nessun test di caratterizzazione nuovo: tutto il codice esistente che il piano modifica ha già
test che ne fissano il comportamento.

## Strategia di test

Ordine: test prima del codice, rossi per il motivo giusto (metodo o comando inesistente,
proprietà mancante, corpo diverso), poi il codice. Ogni test porta `# criterio: 06-Cmm`. Le
fixture nuove si scrivono con il test che le usa. Gli snapshot nuovi si generano con
`--snapshot-update` e si leggono prima del commit. Costanti dei test: catalogo `5` (form
`get_catalog_for_edit_response.json`, `occToken: 9`; la variante con `parentCatalog: {"id": 3}`
si costruisce nel test), catalogo creato `6`, parent `3`; voce `100` (form
`get_catalog_entry_for_edit_response.json`, `occToken: 4`, `parents: [{"id": 1}]`), voce creata
`101`; workspace `88` (form `occToken: 17`, risposta della `PUT` `occToken: 18`); utente `1`,
gruppo `2`, ruolo `4`, associazione `9`. Gli id dei criteri (`7`, `2`, `9`, `10`, `11`) sono
esempi: i test usano le costanti qui sopra con la stessa forma.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 06-C01 | `test_api_catalogs.py::TestCatalogsCreate::test_create_sends_only_given_fields_and_wraps_response` (corpo esatto `{"name", "parentId"}`, `call_count == 1`, `catalog_id == 6`, `catalog.name`, `parent_catalog.id == 3`, `next_occ_token`, `.raw`), `::test_create_raw_equivalent`, `::test_create_without_parent_omits_key` | unitario |
| 06-C02 | `::TestCatalogsEdit::test_edit_sends_given_fields_and_occ_token` (PUT, corpo `{"name": {"en": …}, "occToken": 9}`, `catalog_id == 5`, `next_occ_token == 10`), `::test_edit_raw_equivalent_with_deleted_in_dto` | unitario |
| 06-C03 | `::TestCatalogsSetDeleted::test_true_sends_exact_body` (`{"deleted": true}`, `catalog_id == 5`, `entry_id is None`, `deleted is True`), `::test_false_sends_exact_body` | unitario |
| 06-C04 | `::TestCatalogEntriesCreate::test_create_entry_sends_only_given_fields_and_wraps_response` (corpo `{"label", "parentIds", "externalId"}`, `entry_id == 101`, `entry.label`, `entry.external_id`, `next_occ_token`, `.raw`), `::test_create_entry_raw_equivalent` | unitario |
| 06-C05 | `::TestCatalogEntriesEdit::test_edit_entry_sends_given_fields_and_occ_token` (`{"externalId": "BO2", "occToken": 4}`, `entry_id == 100`, `next_occ_token == 5`), `::test_edit_entry_raw_equivalent` | unitario |
| 06-C06 | `::TestCatalogEntriesSetDeleted::test_true_sends_exact_body_and_reads_catalog_id` (risposta con `catalogId`), `::test_reads_entry_id_form` (risposta inline con `entryId`), `::test_false`; `test_facade_catalogs.py::TestCatalogDeletedResult` (le due forme, id passati come fallback) | unitario |
| 06-C07 | `test_facade_admin_manage.py::TestWorkspaceForEdit::test_occ_token_exposed`, `::TestCatalogForEdit::test_occ_token_exposed`, `::test_parent_catalog_id_with_parent`, `::test_parent_catalog_id_without_parent`, `::test_parent_catalog_id_without_content_data`, `::TestCatalogEntryForEdit::test_occ_token_exposed`; `test_api_catalogs.py::TestCatalogsForEditAliases::test_get_for_edit_same_route_and_facade`, `::test_get_entry_for_edit_same_route_and_facade` (stesse route delle fixture esistenti, stesso tipo, `occ_token`) | unitario |
| 06-C08 | `test_api_admin_manage.py::TestEditWorkspace::test_edit_sends_given_fields_with_token_in_path` (route `admin/manage/workspaces/88/17`, corpo esatto senza `occToken`, risultato `WorkspaceForEdit` con `id`, `name`, `occ_token == 18`), `::test_edit_raw_equivalent` (DTO con associazioni come dict) | unitario |
| 06-C09 | `test_api_catalogs.py::TestCatalogsWriteErrors::test_edit_409_raises_concurrency_error_once`, `::test_edit_entry_409_raises_concurrency_error_once`, `::test_set_deleted_404_raises_not_found`, `::test_set_entry_deleted_404_raises_not_found`, `::test_create_timeout_raises_transport_error_once` (`side_effect=httpx.ReadTimeout`, `call_count == 1`); `test_api_admin_manage.py::TestEditWorkspace::test_409_raises_concurrency_error_once`, `::test_timeout_raises_transport_error_once` | unitario |
| 06-C10 | `test_cli_catalogs_write.py::TestCatalogsCreate::test_flags_and_json_merge_name_key_by_key` (corpo esatto `{"name": {"it": "Sedi", "de": "Standorte", "en": "Sites"}, "parentId": 3}`), `::test_table_output` (snapshot con `catalog_id`, `name`, `parent_catalog_id`, `next_occ_token`), `::test_json_output` (snapshot), `::test_name_without_eq_exits_2`, `::test_name_with_empty_lang_exits_2` (route non chiamata); `test_cli_write.py::TestParseLangMap`, `::TestMergeLangMap` | unitario |
| 06-C11 | `::TestCatalogsEdit::test_edit_reads_form_then_puts_patched_body` (form con `parentCatalog` costruito nel test e `--name en=Sites`: corpo esatto `{"name": {"en": "Sites", "it": "Reparti"}, "parentId": 3, "occToken": 9}`, nessun `deleted`), `::test_parent_flag_wins` (`--parent 4`), `::test_occ_token_overrides_but_get_still_happens` (`--occ-token 8`, `route_get.called`), `::test_form_without_parent_omits_parent_id` (fixture com'è), `::test_no_flags_resends_form`; `test_catalog_edit_base_with_parent`, `test_catalog_edit_base_without_name` (form senza `contentData` → `{}`) | unitario |
| 06-C12 | `::TestCatalogEntriesEdit::test_edit_entry_reads_form_then_puts_patched_body` (con `--label en=Bologna --parent-entry 11`: corpo esatto `{"label": {"en": "Bologna", "it": "Ingegneria"}, "parentIds": [11], "externalId": "ENG", "occToken": 4}`), `::test_parent_ids_from_form_without_flag` (`[1]`), `::test_form_without_parents_omits_key`; `test_entry_edit_base_*` | unitario |
| 06-C13 | `test_cli_catalogs_write.py::TestCatalogsConflict::test_edit_409_exits_9` (`Catalog 5 changed since it was read…`, una sola PUT), `::test_edit_entry_409_exits_9` (`Entry 100 of catalog 5 …`); `test_cli_admin_manage_write.py::TestEditWorkspaceConflict::test_409_exits_9` (`Workspace 88 …`) | unitario |
| 06-C14 | `::TestCatalogsDelete::test_prompt_shows_id_and_it_name_and_y_deletes` (monkeypatch `_stdin_is_interactive`, `input="y\n"`, prompt `Delete catalog 5 "Reparti"?`, `{"deleted": true}`, `Catalog 5 deleted`), `::test_prompt_n_does_nothing`, `::test_yes_skips_prompt`, `::test_json_output`, `::test_non_interactive_without_yes_refuses` (exit `2`, PUT non chiamata), `::test_name_missing_shows_empty_string`; `::TestCatalogEntriesDelete` con gli stessi casi su `Delete entry 100 "Ingegneria" of catalog 5?` e `Entry 100 of catalog 5 deleted`; `test_display_name_*` | unitario |
| 06-C15 | `::TestCatalogsRestore::test_restore_puts_false_without_prompt_even_non_interactive` (`{"deleted": false}`, nessuna GET, `Catalog 5 restored`), `::test_json_output`; `::TestCatalogEntriesRestore` (`Entry 100 of catalog 5 restored`, JSON con `entry_id`) | unitario |
| 06-C16 | `::TestCatalogEntriesCreate::test_flags_body_and_table` (corpo `{"label": {"it": "Bologna"}, "parentIds": [10, 11], "externalId": "BO"}`, snapshot con `entry_id`, `catalog_id`, `label`, `external_id`, `next_occ_token`), `::test_json_label_merged_with_flag` | unitario |
| 06-C17 | `test_cli_admin_manage_write.py::TestEditWorkspace::test_flags_read_token_then_put_exact_body` (GET `…/88/edit`, PUT `…/88/17` con il corpo esatto del criterio, snapshot tabella con `occ_token`), `::test_occ_token_skips_get` (path `…/88/10`, GET non chiamata), `::test_add_user_role_without_eq_exits_2`, `::test_no_flags_exits_2_without_requests`, `::test_json_description_merged_with_flag`; `test_workspace_body_*`; `test_cli_write.py::TestParseIntPairs` | unitario |
| 06-C18 | `::TestEditWorkspaceUploads::test_cover_and_logo_uploaded_in_order_then_put` (route della spec 04: due ticket e due PUT allo storage nell'ordine, corpo con i due `contentRef`), `::test_cover_upload_failure_exits_11_without_put` (storage in errore sul primo file: exit `11`, un solo tentativo di upload, PUT del workspace non chiamata) | unitario |
| 06-C19 | `tests/contract/test_models.py::TestAdminCatalogsWorkspaceWriteDTOs::test_schema_superset` (`assert_superset` sui 10 DTO della spec e sui gemelli tipizzati), `::test_fixtures_parse` (le sette fixture nuove nelle façade `CatalogWriteResult`, `CatalogEntryWriteResult`, `CatalogDeletedResult`, `WorkspaceForEdit`) | contract |
| 06-C20 | `test_docs_snippets.py::test_catalogs_workspace_pages_document_write_commands`; `uv run mkdocs build --strict` nei controlli di verifica; gli snippet Python delle pagine passano da `test_doc_snippet_is_consistent_with_the_api` | unitario + verifica |
| 06-C21 | `test_catalogs_integration.py::TestCatalogsWriteIntegration::test_create_edit_entry_delete_cycle`: skip senza le variabili di base; `set_deleted(True)` in `finally`; dopo il ciclo `get_for_edit(...).deleted is True`; righe `[06-C21]` con la semantica dei campi omessi, l'id della risposta di `…/entries/{id}/deleted` e la visibilità in `catalogs.list`; esecuzione sul tenant in un task manuale dedicato (come 05-T15), esito in `docs/api/catalogs.md` e `verifica.md` | integrazione (opt-in) + manuale |
| 06-C23 | `test_facade_admin_manage.py::TestNullLanguageValues`, `test_cli_admin_manage.py::TestAdminManageWorkspace::test_null_description_exits_0`, `test_api_admin_manage.py::TestEditWorkspace::test_response_with_null_description` | unitario |
| 06-C24 | `test_cli_admin_manage_write.py::TestEditWorkspacePatch`, `test_workspace_edit_base_*`, `test_apply_form_*` | unitario |
| 06-C22 | `test_admin_manage_integration.py::TestWorkspaceWriteIntegration::test_add_remove_member_cycle`: skip senza `PYNTERACTA_TEST_WRITE_WORKSPACE=1`; rimozione e ripristino in `finally`; assert su `member_users_count` e nome; righe `[06-C22]` su nome e descrizione dopo la `PUT`; esecuzione nello stesso task manuale, esito in `docs/api/admin_manage.md` e `verifica.md`; se nome o descrizione risultano azzerati, la spec si rivede prima della chiusura | integrazione (opt-in dedicato) + manuale |

Verifica manuale (dalla spec): nessuna oltre all'esecuzione opt-in di 06-C21 e 06-C22 sul tenant
di prova. Se il tenant sostituisce la mappa del nome per intero, la CLI è già una patch e la
libreria resta esplicita: cambia solo la documentazione. Se il server rifiuta un corpo che la spec
dà per buono (per esempio `parentIds` vuota o `name` con una sola lingua), la correzione passa da
una revisione della spec, non da un aggiustamento silenzioso.

## Revisione dopo la prova sul tenant (T14, 2026-10-12)

- `models/facade/admin_manage.py`: helper `_drop_null_values(mapping)` che toglie le chiavi con
  valore `None` da un dict (ogni altro valore passa com'è). `WorkspaceForEdit._typed_content`
  copia il `root` di `contentData` e pulisce `translations` e `description` prima di validare in
  `WorkspaceEditableContentDataDTO1`; `CatalogForEdit._typed_content` pulisce `name`;
  `CatalogEntryForEdit.from_dict` pulisce `label` su una copia di `data` prima di validare la
  risposta, perché lì la mappa è tipizzata al primo livello (`.raw` non ha le lingue `null`).
  Gli altri campi non cambiano.
- Test: `test_facade_admin_manage.py::TestNullLanguageValues` (06-C23) con le tre forme e una
  lingua stringa accanto alla `null`; `test_cli_admin_manage.py::TestAdminManageWorkspace::
  test_null_description_exits_0` sulla CLI di lettura; `test_api_admin_manage.py::TestEditWorkspace::
  test_response_with_null_description` sulla scrittura. Fixture costruite nei test con
  `copy.deepcopy`, senza toccare quelle esistenti.
- `tests/integration/test_catalogs_integration.py`: testi diversi per lingua, così la prova
  distingue sostituzione e unione; il `400` di `catalogs.list([id])` si registra invece di far
  fallire il test; via la riga su `catalogs.list()` senza id, che non dimostra nulla.

### Seconda revisione: `edit-workspace` come patch (2026-10-12)

- `cli/admin_manage_write.py`: `_workspace_body` resta la parte dei flag e di `--json` (serve
  al controllo "Nothing to send", che avviene prima di ogni richiesta). Funzioni pure nuove:
  `_workspace_edit_base(form: WorkspaceForEdit) -> dict` (`name`, `translations`, `description`
  dal contenuto tipizzato, se non `None`) e `_apply_form(base, body) -> dict` (`{**base,
  **body}`, con `translations` e `description` unite per lingua: lette, poi `--json` e flag). Il
  comando legge sempre `workspace_for_edit`; il token è `--occ-token` o quello letto.
  `WorkspaceForEdit` guadagna `translations` (dal contenuto tipizzato), che serve alla base.
- Test: `test_cli_admin_manage_write.py` adeguato (corpi con la base del form, `--occ-token` con
  la `GET`, 06-C24) più `test_workspace_edit_base_*` e `test_apply_form_*`;
  `test_facade_admin_manage.py::TestWorkspaceForEdit::test_translations`.
- `tests/integration/test_admin_manage_integration.py`: le due `edit_workspace` passano
  `name`, `translations` e `description` letti dal form; il ripristino finale resta.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| Scritture dentro `api/catalogs.py` e `api/admin_manage.py` | moduli `api/catalogs_write.py` | Sette metodi più due alias in un modulo di 127 righe; la divisione dei post serviva per quindici endpoint (stessa scelta della spec 05) |
| Comandi CLI in `cli/catalogs_write.py` e `cli/admin_manage_write.py`, registrati sulle app esistenti | inline in `cli/catalogs.py` e `cli/admin_manage.py` | Convenzione di `posts_write.py`, `users_write.py`, `groups_write.py`; i moduli di lettura restano leggibili; un solo `app` per gruppo di comandi |
| Façade di scrittura in `facade/catalogs.py`, accanto a `Catalog` e `CatalogEntry`, che guadagnano `etag`, `entries_typed`, `catalog_id`, `deleted` e `from_stub` | modulo `facade/catalogs_write.py`; façade nuove `CatalogSummary`/`CatalogEntrySummary` per le risposte | La risposta di scrittura contiene lo stesso `CatalogDTO`/`CatalogEntryDTO` delle letture: una façade sola per entità, come `GroupSummary` nella 05 ma senza classe in più |
| `CatalogDeletedResult` unica per catalogo e voce, DTO scelto dalla chiave della risposta, id passati come fallback | due façade; rivalidare sempre in `EditCatalogDeletedResponseDTO` | Il swagger dichiara `catalogId` per entrambi gli endpoint ma definisce anche `entryId`: `.raw` conserva ciò che arriva e il chiamante ha sempre i due id (06-C06); 06-C21 registra la forma reale |
| `edit_workspace` restituisce `WorkspaceForEdit` | façade `WorkspaceWriteResult` | La risposta è `GetWorkspaceForEditResponseDTO`: stessa façade, `occ_token` già quello successivo (decisione della spec) |
| `occ_token` del workspace nel path con `_put(f"…/{workspace_id}/{occ_token}")` | parametro di query; corpo | È il contratto del swagger; non è un segreto (spec, sezione dati personali) |
| `parse_lang_map` nuovo, senza coercizione, accanto a `parse_kv_values` | riusare `parse_kv_values` | `parse_kv_values` tipizza i valori (`"true"` → `True`, `"12"` → `12`): un'etichetta `12` o `true` deve restare testo; la lingua vuota è un errore che `parse_kv_values` non controlla |
| `merge_lang_map` per l'unione chiave per chiave di form, `--json` e flag | `merge_body` (sostituzione della chiave intera) | 06-C10, 06-C12 e 06-C16 chiedono l'unione per lingua anche tra `--json` e flag; la stessa funzione serve alle patch e a `create`/`edit-workspace` |
| `edit-workspace`: GET del token prima degli upload, poi la `PUT` | upload prima della GET | Un workspace inesistente esce `5` senza caricare file; un upload fallito esce `11` senza `PUT` in entrambi gli ordini (06-C18) |
| `edit-workspace` senza alcun input → exit `2` prima di `build_client` | inviare un corpo vuoto | La spec lo chiede (06-C17); un `PUT` vuoto non ha senso e consumerebbe l'`occToken` |
| `_workspace_write_row` distinta da `_workspace_to_row` | aggiungere `occ_token` alla riga di lettura | `test_occ_token_absent_from_default_table` e gli snapshot fissano la tabella di lettura; la spec chiede il token solo nella tabella di `edit-workspace` |
| Form con `parentCatalog` costruito nei test con `deepcopy` della fixture | modificare `get_catalog_for_edit_response.json`; seconda fixture | La fixture senza parent è il caso "chiave assente" (06-C11) e alimenta gli snapshot di `admin-manage catalog`; una variante in-test non tocca nulla di esistente |
| `_require_token` e `_usage_error` copiati in `catalogs_write.py` (e il primo in `admin_manage_write.py`) con il nome della risorsa come parametro | spostarli in `cli/_write.py` | Sono sei righe ciascuno; spostarli toccherebbe `users_write.py` e `groups_write.py` fuori dall'ambito della spec; se una terza copia arriva, la spec dei post evento li unifica |
| Integration: ciclo dei cataloghi in `tests/integration/test_catalogs_integration.py` nuovo, ciclo del workspace in `test_admin_manage_integration.py` | tutto in `test_admin_manage_integration.py` | Un file per risorsa (convenzione); il workspace non ha un file proprio e la lettura del form sta già lì |
| Integration del workspace: ripristino in `finally` anche di nome e descrizione | solo rimozione dell'utente | Il workspace di prova è condiviso con utenti reali: se la `PUT` azzerasse i campi omessi (06-C22), il test li rimette e la spec si rivede, ma il tenant non resta sporco |
| Commit `feat(catalogs):`, `feat(admin-manage):`, `feat(cli):`, `test:`, `docs:` | `feat(admin):` | Scope per risorsa come la storia del progetto; semantic-release calcola 0.13.0 |

## Rischi

- **Semantica del server sui campi omessi diversa da quella di utenti e gruppi** → l'integration
  test lo scopre (06-C21, 06-C22); `catalogs edit` ed `edit-entry` sono già patch e la libreria
  resta esplicita: cambia solo la documentazione. Per il workspace, se nome o descrizione
  risultano azzerati, `edit-workspace` diventa una patch con revisione della spec (decisione
  della spec), e il `finally` del test ripristina i valori letti.
- **Risposta di `…/entries/{id}/deleted` con una forma diversa da entrambe** (per esempio senza
  id) → `CatalogDeletedResult` completa con gli id passati; 06-C21 registra la forma reale e il
  contract test mostra se il DTO non la copre.
- **`parentCatalog` del form in una forma diversa da `CatalogDTO`** → `parent_catalog_id` passa
  da `_resolve_root` e `CatalogDTOModel`, che ignora le chiavi sconosciute; senza `id` vale
  `None` e la patch non manda `parentId` (il server decide).
- **Catalogo disabilitato ancora visibile in `catalogs.list`** → non è un errore: 06-C21 lo
  registra e `docs/api/catalogs.md` lo dice; il test del ciclo asserisce solo `deleted is True`
  sul form.
- **Upload di `--cover`/`--logo` mockato nei test della CLI** → si riusano le route dello storage
  di `test_cli_posts_write.py` (ticket + `PUT` firmato); il ramo di errore usa uno stato `4xx`
  dello storage, mai la rete.
- **Prompt di `delete` con nome in una lingua sola o assente** → `_display_name` ha un test per
  ogni ramo (`it`, prima lingua, mappa vuota, `None`); la stringa vuota è il comportamento della
  spec, non un errore.
- **Copertura di `catalogs_write.py` e `admin_manage_write.py`** → otto comandi con pochi rami
  ciascuno; ogni ramo di errore (`--json` non valido, coppie malformate, `occ_token` assente,
  form senza `contentData`, corpo vuoto, upload fallito) ha un test dedicato.
- **Integration test del workspace eseguito per sbaglio** → gating su `=1`, nessuna modifica a
  nome e descrizione, rimozione dell'utente in `finally`; il test salta se la `GET` iniziale
  fallisce prima di scrivere.
- **Catalogo di prova che resta abilitato se `create` riesce ma il test crolla prima del
  `finally`** → l'id si salva subito dopo `create` e il `finally` parte da lì; il nome
  `pynteracta-it-<timestamp>` lo rende riconoscibile per una pulizia a mano.
