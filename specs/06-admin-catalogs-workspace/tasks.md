# Task 06 – Anagrafiche admin, seconda metà: cataloghi, voci di catalogo e workspace

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (metodo, proprietà o comando inesistente, corpo diverso); poi il
codice; il commit arriva con i cinque controlli bloccanti verdi. Ogni test porta
`# criterio: 06-Cmm` sulla riga sopra. Messaggi di commit in Conventional Commits con descrizione
in italiano: `feat(catalogs)`, `feat(admin-manage)`, `feat(cli)`, `test`, `docs`. Gli snapshot
syrupy nuovi si generano con `--snapshot-update` e si leggono prima del commit.
Costanti dei test (dal piano): catalogo `5` (form `get_catalog_for_edit_response.json`,
`occToken: 9`, nome `{"en": "Departments", "it": "Reparti"}`, senza `parentCatalog`; la variante
con `parentCatalog: {"id": 3, "name": "Root"}` si costruisce nel test con `copy.deepcopy`),
catalogo creato `6`, parent `3`; voce `100` (form `get_catalog_entry_for_edit_response.json`,
`occToken: 4`, label `{"en": "Engineering", "it": "Ingegneria"}`, `externalId: "ENG"`,
`parents: [{"id": 1}]`), voce creata `101`; workspace `88` (form `occToken: 17`, risposta della
`PUT` `occToken: 18`); utente `1`, gruppo `2`, ruolo `4`, associazione `9`. Gli id dei criteri
(`7`, `2`, `9`, `10`, `11`) sono esempi: i test usano le costanti qui sopra con la stessa forma.

## Elenco

### [x] T01 – Riga di ROADMAP, fixture e contract test dei DTO

- Criteri: 06-C19 (DTO; lo smoke delle façade arriva con T02 e T03)
- Dipende da: nessuno
- Test: `tests/contract/test_models.py::TestAdminCatalogsWorkspaceWriteDTOs::test_schema_superset`
  (`assert_superset` sui 10 DTO della spec e sui gemelli tipizzati del piano: `CatalogDTOModel`,
  `CatalogEntryDTO1`, `CatalogEditableContentDTOModel`, `EditCatalogEntryDeletedResponseDTO`;
  verde subito: caratterizza i modelli generati) e `::test_fixtures_parse` (le sette fixture
  nuove si validano nei DTO di risposta; rosso finché le fixture mancano).
- Passi:
  1. `ROADMAP.md`: riga `0.13.0 | Admin write, second half: catalogs, catalog entries and
     workspace (fifth write group, ADR 0001) | M32 | ⏳ In progress |
     specs/06-admin-catalogs-workspace/spec.md`; nota "last used: M32".
  2. Fixture nuove in `tests/fixtures/payloads/` con i valori del piano:
     `create_catalog_response`, `edit_catalog_response`, `edit_catalog_deleted_response`,
     `create_catalog_entry_response`, `edit_catalog_entry_response`,
     `edit_catalog_entry_deleted_response`, `edit_workspace_response`.
  3. Scrivere i contract test; `uv run pytest -m contract` e controlli bloccanti; commit
     `test: fixture e contract test dei DTO di scrittura di cataloghi, voci e workspace; riga
     0.13.0 in ROADMAP (06-T01)`.

### [x] T02 – `occ_token` e `parent_catalog_id` sulle façade per-edit

- Criteri: 06-C07 (façade)
- Dipende da: nessuno
- Test: `tests/unit/test_facade_admin_manage.py`: i tre `test_occ_token_only_on_raw` →
  `test_occ_token_exposed` (`occ_token == raw.occToken`: `17`, `9`, `4`);
  `TestCatalogForEdit::test_parent_catalog_id_with_parent` (fixture con `parentCatalog`
  aggiunto → `3`), `::test_parent_catalog_id_without_parent` (fixture com'è → `None`),
  `::test_parent_catalog_id_without_content_data` (`None`). I tre test sostituiti sono rossi per
  il motivo opposto: lo si annota nel commit.
- Passi:
  1. Scrivere i test; eseguire: rossi (`AttributeError`).
  2. `models/facade/admin_manage.py`: `occ_token` su `WorkspaceForEdit`, `CatalogForEdit`,
     `CatalogEntryForEdit`; `CatalogForEdit.parent_catalog_id` via `_resolve_root` e
     `CatalogDTOModel`; docstring del modulo e delle classi senza "solo su `.raw`".
  3. Controlli bloccanti (gli snapshot di `admin-manage …` restano verdi); commit
     `feat(admin-manage): occ_token sulle façade per-edit e parent_catalog_id del catalogo (06-T02)`.

### [x] T03 – Façade dei cataloghi: campi nuovi di `Catalog`/`CatalogEntry` e façade di scrittura

- Criteri: 06-C01, 06-C02, 06-C04 (campi del risultato), 06-C06 (façade), 06-C19 (smoke)
- Dipende da: T01
- Test: `tests/unit/test_facade_catalogs.py` (nuovo): `TestCatalog` (`etag`, `entries_typed`
  da stub e lista vuota senza `entries`, `from_stub`, root non dict → `ValueError`),
  `TestCatalogEntry` (`catalog_id`, `deleted`, `from_stub`), `TestCatalogWriteResult`
  (`from_dict` su `create_catalog_response.json`: `catalog_id == 6`, `catalog.name == "Sedi"`,
  `parent_catalog.id == 3`, `next_occ_token == 1`, `.raw`; su `edit_catalog_response.json` con
  `catalog_id=5`: `parent_catalog is None`; senza `catalog` nella risposta → `catalog_id`
  passato), `TestCatalogEntryWriteResult` (`entry_id == 101`, `catalog_id == 5` dall'`entry`,
  `entry.label`, `entry.external_id`, `next_occ_token`; senza `entry` → id passati),
  `TestCatalogDeletedResult` (forma `catalogId` → `catalog_id == 5`, `entry_id` passato;
  forma `entryId` → `entry_id == 100`, `catalog_id` passato; `.raw` del tipo giusto; `deleted`);
  contract: smoke delle tre façade sulle fixture di T01.
- Passi:
  1. Scrivere i test; eseguire: rossi (`AttributeError`, `ImportError`).
  2. `models/facade/catalogs.py`: proprietà nuove, `from_stub`, le tre façade come nel piano;
     `models/facade/__init__.py` le esporta; docstring del modulo con gli endpoint di scrittura.
  3. Controlli bloccanti; commit `feat(catalogs): façade CatalogWriteResult,
     CatalogEntryWriteResult e CatalogDeletedResult; etag, voci, catalog_id e deleted su Catalog e
     CatalogEntry (06-T03)`.

### [x] T04 – Scritture dei cataloghi in `CatalogsAPI` e alias dei form

- Criteri: 06-C01, 06-C02, 06-C03, 06-C07 (alias), 06-C09 (cataloghi)
- Dipende da: T02, T03
- Test: `tests/unit/test_api_catalogs.py`: `TestCatalogsCreate`
  (`test_create_sends_only_given_fields_and_wraps_response`: corpo esatto `{"name": {"it":
  "Sedi", "en": "Sites"}, "parentId": 3}` da `route.calls[0].request.content`, `call_count ==
  1`, risultato dalla fixture; `test_create_raw_equivalent`;
  `test_create_without_parent_omits_key`), `TestCatalogsEdit`
  (`test_edit_sends_given_fields_and_occ_token`: PUT su `admin/manage/catalogs/5`, corpo
  `{"name": {"en": "Sites"}, "occToken": 9}`, `catalog_id == 5`, `next_occ_token == 10`;
  `test_edit_raw_equivalent_with_deleted_in_dto`), `TestCatalogsSetDeleted`
  (`test_true_sends_exact_body`: `{"deleted": true}`, `catalog_id == 5`, `entry_id is None`,
  `deleted is True`; `test_false_sends_exact_body`), `TestCatalogsForEditAliases`
  (`test_get_for_edit_same_route_and_facade`, `test_get_entry_for_edit_same_route_and_facade`:
  stesse route e fixture di `test_api_admin_manage.py`, tipo e `occ_token`),
  `TestCatalogsWriteErrors` (`test_edit_409_raises_concurrency_error_once` con
  `status_code == 409` e una richiesta, `test_set_deleted_404_raises_not_found`,
  `test_create_timeout_raises_transport_error_once` con `side_effect=httpx.ReadTimeout`).
- Passi:
  1. Scrivere i test; eseguire: rossi (`AttributeError` sui metodi).
  2. `api/catalogs.py`: costanti dei percorsi admin, `create`/`create_raw`, `edit`/`edit_raw`,
     `set_deleted`, `get_for_edit`, `get_entry_for_edit`; docstring di classe e metodi in
     italiano con "una sola richiesta", "`deleted` solo con `set_deleted`/`edit_raw`" e la nota
     sui campi omessi. `api/admin_manage.py`: solo docstring (rimando agli alias).
  3. Controlli bloccanti; commit `feat(catalogs): creazione, modifica e disabilitazione dei
     cataloghi su client.catalogs, alias get_for_edit e get_entry_for_edit (06-T04)`.

### [x] T05 – Scritture delle voci di catalogo in `CatalogsAPI`

- Criteri: 06-C04, 06-C05, 06-C06, 06-C09 (voci)
- Dipende da: T04
- Test: `tests/unit/test_api_catalogs.py`: `TestCatalogEntriesCreate`
  (`test_create_entry_sends_only_given_fields_and_wraps_response`: POST su
  `admin/manage/catalogs/5/entries`, corpo `{"label": {"it": "Bologna"}, "parentIds": [10],
  "externalId": "BO"}`, `entry_id == 101`, `entry.label`, `entry.external_id`,
  `next_occ_token`, `.raw`; `test_create_entry_raw_equivalent`), `TestCatalogEntriesEdit`
  (`test_edit_entry_sends_given_fields_and_occ_token`: PUT su `…/entries/100`, corpo
  `{"externalId": "BO2", "occToken": 4}`, `entry_id == 100`, `next_occ_token == 5`;
  `test_edit_entry_raw_equivalent`), `TestCatalogEntriesSetDeleted`
  (`test_true_sends_exact_body_and_reads_catalog_id`: PUT su `…/entries/100/deleted`, corpo
  `{"deleted": true}`, risposta dalla fixture → `catalog_id == 5`, `entry_id == 100`,
  `deleted is True`; `test_reads_entry_id_form`: risposta inline `{"entryId": 100, "deleted":
  true}` → stessi valori; `test_false`), `TestCatalogsWriteErrors`
  (`test_edit_entry_409_raises_concurrency_error_once`,
  `test_set_entry_deleted_404_raises_not_found`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `api/catalogs.py`: `create_entry`/`create_entry_raw`, `edit_entry`/`edit_entry_raw`,
     `set_entry_deleted`.
  3. Controlli bloccanti; commit `feat(catalogs): creazione, modifica e disabilitazione delle
     voci di catalogo su client.catalogs (06-T05)`.

### [x] T06 – `edit_workspace` in `AdminManageAPI`

- Criteri: 06-C08, 06-C09 (workspace)
- Dipende da: T02
- Test: `tests/unit/test_api_admin_manage.py::TestEditWorkspace`:
  `test_edit_sends_given_fields_with_token_in_path` (route `admin/manage/workspaces/88/17`,
  corpo esatto `{"name": "WS", "addUserIds": [1], "removeGroupIds": [2],
  "addUserRoleAssociations": [{"userId": 1, "roleId": 4}], "newCoverImageContentRef":
  "ref-1"}`, `"occToken" not in body`, risultato `WorkspaceForEdit` con `id == 88`, `name`,
  `occ_token == 18` da `edit_workspace_response.json`), `test_edit_raw_equivalent` (DTO con le
  associazioni come dict), `test_409_raises_concurrency_error_once`,
  `test_timeout_raises_transport_error_once`.
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `api/admin_manage.py`: `_WORKSPACE_EDIT_PATH`, `RoleAssociations`, `edit_workspace`
     (`# noqa: PLR0913`), `edit_workspace_raw`; docstring del modulo e della classe (`occ_token`
     su tutte le façade).
  3. Controlli bloccanti (`mypy` strict sulle liste di dict o DTO); commit
     `feat(admin-manage): modifica del workspace con occToken nel path (06-T06)`.

### [x] T07 – Helper della CLI: mappe per lingua e coppie di id

- Criteri: 06-C10 (helper), 06-C17 (helper)
- Dipende da: nessuno
- Test: `tests/unit/test_cli_write.py`: `TestParseLangMap` (`["it=Sedi", "en=Sites"]` →
  `{"it": "Sedi", "en": "Sites"}`; testo con `=` dentro resta intero; `"12"` e `"true"` restano
  stringhe; `"Sedi"` → `BadParameter` con `LANG=TEXT` e il nome dell'opzione; `"=Sedi"` e
  `" =Sedi"` → `BadParameter`; `None` → `{}`), `TestParseIntPairs` (`["1=4"]` → `[(1, 4)]`;
  `"1"`, `"a=4"`, `"1="` → `BadParameter` con la forma passata), `TestMergeLangMap` (chiave
  assente → la mappa dei flag; presente → unione con i flag che vincono per chiave; valore
  `None` nel corpo → la mappa dei flag; flag vuoti → corpo invariato).
- Passi:
  1. Scrivere i test; eseguire: rossi (`ImportError`).
  2. `cli/_write.py`: `parse_lang_map`, `parse_int_pairs`, `merge_lang_map`; docstring del
     modulo con la spec 06.
  3. Controlli bloccanti; commit `feat(cli): helper per mappe LANG=TESTO e coppie di id in
     cli/_write.py (06-T07)`.

### [x] T08 – `catalogs create` e `catalogs create-entry`

- Criteri: 06-C10, 06-C16
- Dipende da: T04, T05, T07
- Test: `tests/unit/test_cli_catalogs_write.py` (nuovo): `TestCatalogsCreate`
  (`test_flags_and_json_merge_name_key_by_key`: `body.json` in `tmp_path` con `{"name": {"it":
  "X", "de": "Standorte"}}`, `--name it=Sedi --name en=Sites --parent 3` → corpo esatto
  `{"name": {"it": "Sedi", "de": "Standorte", "en": "Sites"}, "parentId": 3}`;
  `test_table_output` e `test_json_output` con snapshot (`catalog_id`, `name`,
  `parent_catalog_id`, `next_occ_token`); `test_name_without_eq_exits_2`,
  `test_name_with_empty_lang_exits_2` con route non chiamata; `test_json_unknown_key_exits_2`),
  `TestCatalogEntriesCreate` (`test_flags_body_and_table`: `--label it=Bologna --parent-entry 10
  --parent-entry 11 --external-id BO` → corpo `{"label": {"it": "Bologna"}, "parentIds": [10,
  11], "externalId": "BO"}`, snapshot con `entry_id`, `catalog_id`, `label`, `external_id`,
  `next_occ_token`; `test_json_label_merged_with_flag`).
- Passi:
  1. Scrivere i test; eseguire: rossi (`No such command`).
  2. `cli/catalogs_write.py`: modulo, opzioni, `_catalog_row`, `_entry_row`, comandi `create` e
     `create-entry`; `cli/__init__.py` importa il modulo; docstring di `cli/catalogs.py`.
  3. Snapshot, controlli bloccanti (gli snapshot di `catalogs list|entries` restano verdi);
     commit `feat(cli): comandi catalogs create e create-entry con mappe LANG=TESTO (06-T08)`.

### [x] T09 – `catalogs edit` e `catalogs edit-entry` come patch

- Criteri: 06-C11, 06-C12, 06-C13 (cataloghi e voci)
- Dipende da: T08
- Test: `tests/unit/test_cli_catalogs_write.py`: `test_catalog_edit_base_with_parent`,
  `test_catalog_edit_base_without_parent`, `test_catalog_edit_base_without_content_data`
  (`{}`), `test_entry_edit_base_with_parents`, `test_entry_edit_base_without_parents` (chiave
  assente), `test_entry_edit_base_skips_parents_without_id`; `TestCatalogsEdit`
  (`test_edit_reads_form_then_puts_patched_body`: form con `parentCatalog` e `--name en=Sites`
  → corpo esatto `{"name": {"en": "Sites", "it": "Reparti"}, "parentId": 3, "occToken": 9}`,
  nessun `deleted`; `test_parent_flag_wins` (`--parent 4`);
  `test_occ_token_overrides_but_get_still_happens` (`--occ-token 8`, `get_route.called`);
  `test_form_without_parent_omits_parent_id`; `test_no_flags_resends_form`;
  `test_json_then_flags_precedence`; `test_missing_occ_token_exits_1`; `test_409_exits_9` con
  `Catalog 5 changed since it was read: fetch it again and retry` e una sola PUT;
  `test_404_exits_5_without_put`), `TestCatalogEntriesEdit`
  (`test_edit_entry_reads_form_then_puts_patched_body`: `--label en=Bologna --parent-entry 11`
  → `{"label": {"en": "Bologna", "it": "Ingegneria"}, "parentIds": [11], "externalId": "ENG",
  "occToken": 4}`; `test_parent_ids_from_form_without_flag` (`[1]`);
  `test_form_without_parents_omits_key`; `test_409_exits_9` con `Entry 100 of catalog 5
  changed since it was read…`).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `cli/catalogs_write.py`: `_catalog_edit_base`, `_entry_edit_base`, `_require_token`,
     comandi `edit` ed `edit-entry` con `handle_error(resource=…)`.
  3. Controlli bloccanti; commit `feat(cli): catalogs edit ed edit-entry come patch con occToken
     letto o imposto (06-T09)`.

### [x] T10 – `catalogs delete|restore` e `delete-entry|restore-entry`

- Criteri: 06-C14, 06-C15
- Dipende da: T08
- Test: `tests/unit/test_cli_catalogs_write.py`: `test_display_name_*` (`it` presente, prima
  lingua, mappa vuota, `None` → `""`); `TestCatalogsDelete`
  (`test_prompt_shows_id_and_it_name_and_y_deletes`: `_stdin_is_interactive` → `True`,
  `input="y\n"`, prompt `Delete catalog 5 "Reparti"? [y/N]`, PUT con `{"deleted": true}`,
  `Catalog 5 deleted`; `test_prompt_n_does_nothing` (exit `0`, PUT non chiamata);
  `test_yes_skips_prompt`; `test_json_output` (`{"catalog_id": 5, "deleted": true}`);
  `test_non_interactive_without_yes_refuses` (exit `2`, messaggio con `--yes`, PUT non
  chiamata); `test_name_missing_shows_empty_string` (form senza `contentData`);
  `test_help_says_logical_and_reversible`), `TestCatalogsRestore`
  (`test_restore_puts_false_without_prompt_even_non_interactive`: nessuna GET, `{"deleted":
  false}`, `Catalog 5 restored`; `test_json_output`), `TestCatalogEntriesDelete` (gli stessi
  cinque casi su `Delete entry 100 "Ingegneria" of catalog 5? [y/N]`, `Entry 100 of catalog 5
  deleted`, JSON con `entry_id`), `TestCatalogEntriesRestore` (`Entry 100 of catalog 5
  restored`, JSON).
- Passi:
  1. Scrivere i test; eseguire: rossi.
  2. `cli/catalogs_write.py`: `_display_name`, comandi `delete`, `restore`, `delete-entry`,
     `restore-entry` con `confirm_destructive` e l'help sulla cancellazione logica.
  3. Controlli bloccanti; commit `feat(cli): cancellazione logica e ripristino di cataloghi e
     voci con conferma su delete (06-T10)`.

### [x] T11 – `admin-manage edit-workspace`

- Criteri: 06-C17, 06-C13 (workspace)
- Dipende da: T06, T07
- Test: `tests/unit/test_cli_admin_manage_write.py` (nuovo): `test_workspace_body_*`
  (liste e `name` via `merge_body`, `description` unita per chiave, associazioni come dict,
  liste vuote assenti, corpo vuoto senza input); `TestEditWorkspace`
  (`test_flags_read_token_then_put_exact_body`: GET `…/88/edit` dalla fixture, PUT `…/88/17`
  con il corpo esatto di 06-C17 (`removeRoleAssociationIds: [9]`), snapshot tabella con `id`,
  `name`, i quattro conteggi e `occ_token == 18`; `test_json_output` (snapshot);
  `test_occ_token_skips_get` (path `…/88/10`, GET non chiamata);
  `test_add_user_role_without_eq_exits_2`; `test_no_flags_exits_2_without_requests`;
  `test_json_description_merged_with_flag`; `test_missing_occ_token_exits_1`;
  `test_409_exits_9` con `Workspace 88 changed since it was read…` e una sola PUT).
- Passi:
  1. Scrivere i test; eseguire: rossi (`No such command`).
  2. `cli/admin_manage_write.py`: modulo, opzioni (senza `--cover`/`--logo`, che arrivano con
     T12), `_workspace_body`, `_workspace_write_row`, `_require_token`, comando
     `edit-workspace`; `cli/__init__.py` importa il modulo; docstring di `cli/admin_manage.py`.
  3. Snapshot, controlli bloccanti (`test_occ_token_absent_from_default_table` e gli snapshot
     di `admin-manage workspace` restano verdi); commit `feat(cli): admin-manage edit-workspace
     con i soli campi indicati e occToken letto o imposto (06-T11)`.

### [x] T12 – `edit-workspace --cover` e `--logo`

- Criteri: 06-C18
- Dipende da: T11
- Test: `tests/unit/test_cli_admin_manage_write.py::TestEditWorkspaceUploads`:
  `test_cover_and_logo_uploaded_in_order_then_put` (route dello storage riusate da
  `test_cli_posts_write.py`: due ticket e due PUT firmate nell'ordine copertina → logo; corpo
  della PUT del workspace con `newCoverImageContentRef` e `newLogoContentRef` dai `contentRef`
  restituiti), `test_cover_upload_failure_exits_11_without_put` (storage in errore `4xx` sul
  primo file: exit `11`, un solo tentativo di upload, PUT del workspace non chiamata),
  `test_cover_alone_counts_as_input` (nessun altro flag: nessun exit `2`).
- Passi:
  1. Scrivere i test; eseguire: rossi (`No such option`).
  2. `cli/admin_manage_write.py`: opzioni `--cover`/`--logo` con `exists=True`, upload con
     `client.attachments.upload(path).content_ref` dopo la GET del token e prima della PUT; il
     controllo "nothing to send" tiene conto dei due flag.
  3. Controlli bloccanti; commit `feat(cli): copertina e logo del workspace da file con
     l'upload della spec 04 (06-T12)`.

### [x] T13 – Integration test opt-in dei cicli di catalogo e di workspace

- Criteri: 06-C21, 06-C22 (test; l'esecuzione è T14)
- Dipende da: T05, T06
- Test: `tests/integration/test_catalogs_integration.py::TestCatalogsWriteIntegration::
  test_create_edit_entry_delete_cycle` e `tests/integration/test_admin_manage_integration.py::
  TestWorkspaceWriteIntegration::test_add_remove_member_cycle`, come nel piano, con `finally`
  (disabilitazione del catalogo; rimozione dell'utente e ripristino di nome e descrizione) e
  stampe `[06-C21]`/`[06-C22]`; senza le variabili si auto-saltano (verificato con
  `uv run pytest -m integration` senza `.env`: `skipped`).
- Passi:
  1. Scrivere i due test; `tests/integration/.env.example` e `docs/testing.md` con
     `PYNTERACTA_TEST_WRITE_WORKSPACE` e la nota sul ciclo dei cataloghi.
  2. `uv run pytest -m integration -q` senza ambiente → tutti saltati; controlli bloccanti;
     commit `test: integration test opt-in dei cicli di scrittura di cataloghi e workspace
     (06-T13)`.

### [ ] T14 – Esecuzione degli integration test sul tenant di prova (manuale)

- Criteri: 06-C21, 06-C22 (esecuzione e registrazione)
- Chi: maintainer
- Cosa fare: con `tests/integration/.env` compilato, eseguire
  `uv run pytest -m integration tests/integration/test_catalogs_integration.py -s` e, dopo aver
  impostato `PYNTERACTA_TEST_WRITE_WORKSPACE=1`, `uv run pytest -m integration
  tests/integration/test_admin_manage_integration.py -s -k Write`. Riportare qui le righe
  `[06-C21]` e `[06-C22]`: effetto dei campi omessi in `edit` ed `edit_entry` (mappa del nome
  sostituita o unita; parent ed external id azzerati o mantenuti), quale id arriva nella risposta
  di `…/entries/{id}/deleted`, se il catalogo disabilitato compare in `catalogs.list`, se nome e
  descrizione del workspace omessi sono mantenuti o azzerati. Se nome o descrizione risultano
  azzerati, o se il server rifiuta un corpo che la spec dà per buono, si rivede la spec con
  l'approvazione del maintainer prima di T15.
- Esito: <compilato a mano>

### [ ] T15 – Documentazione

- Criteri: 06-C20
- Dipende da: T10, T12, T14, T17
- Test: `tests/unit/test_docs_snippets.py::test_catalogs_workspace_pages_document_write_commands`
  (`docs/cli.md` cita i nove comandi, `LANG=TEXT`, `USER_ID=ROLE_ID`, `--cover`, `restore`,
  `| 9 |` e non dice più "workspace and catalog writes arrive with their own spec" né "it lives
  on `.raw.occToken`"; `docs/api/catalogs.md` cita `create(`, `edit(`, `set_deleted(`,
  `create_entry(`, `edit_entry(`, `set_entry_deleted(`, `get_for_edit`, `CatalogWriteResult`,
  `CatalogEntryWriteResult`, `CatalogDeletedResult`, `occ_token`, `parent_catalog_id`;
  `docs/api/admin_manage.md` cita `edit_workspace(`, `occ_token`, `new_cover_image_content_ref`
  e non dice più "keep it on `.raw`"; `index.md` e `README.md` non contengono più "catalogs and
  workspace follow"); rosso prima delle pagine. Più `uv run mkdocs build --strict` e gli snippet
  nuovi nel controllo di coerenza.
- Passi:
  1. Scrivere il test; eseguirlo: rosso.
  2. `docs/api/catalogs.md` (riscritta: letture, scritture di cataloghi e voci, form, semantica
     del server da T14), `docs/api/admin_manage.md` (`edit_workspace`, `occ_token` ovunque,
     `parent_catalog_id`, semantica da T14), `docs/cli.md` (nove comandi, exit `9` e `11`, intro
     di `admin-manage`), `docs/testing.md` se T13 non l'ha già coperto, `docs/index.md`,
     `README.md`.
  3. `uv run mkdocs build --strict`, controlli bloccanti; commit `docs: scritture admin di
     cataloghi, voci e workspace in libreria e CLI (06-T15)`.

### [ ] T16 – Chiusura: PRD

- Criteri: nessuno nuovo (chiude i "Requisiti nuovi" della spec)
- Dipende da: T14, T15
- Verifica: rilettura del PRD; `uv run pre-commit run --all-files` verde.
- Passi:
  1. `specs/prd.md`: RF-023 precisato con la semantica verificata in T14 (campi omessi, id di
     `…/entries/{id}/deleted`, visibilità dei disabilitati in `list`) e "(spec 05, 0.12.0)" al
     posto di "(spec 05, 0.13.0)"; RF-023e, RF-023f come sotto-voci; "Confermato dal maintainer
     il <data>, spec 06" su RF-023, RF-008, RF-013, RF-019 e sulla voce "Dati scritti sul tenant"
     di §6 (cataloghi, voci, workspace, immagini); riga nella "Storia del documento".
  2. Commit `docs: PRD con RF-023 precisato, RF-023e e RF-023f (06-T16)`.

### [x] T17 – Lingue `null` nei form admin; correzione del test dei cataloghi

Numerato dopo T16 per non rinumerare, si esegue prima di T14: nasce dalla prima esecuzione di
T14 (2026-10-12), con la decisione del maintainer registrata nella spec.

- Criteri: 06-C23; 06-C21 (test adeguato)
- Dipende da: T13; T14, T15 e T16 dipendono anche da questo
- Test: `tests/unit/test_facade_admin_manage.py::TestNullLanguageValues` (workspace con
  `description: {"it": null, "en": "Ops"}` e `translations: {"it": null}`; catalogo con
  `name: {"it": null, "en": "X"}`; voce con `label: {"it": null}`: le façade si costruiscono e le
  lingue `null` mancano), `tests/unit/test_cli_admin_manage.py::TestAdminManageWorkspace::
  test_null_description_exits_0`, `tests/unit/test_api_admin_manage.py::TestEditWorkspace::
  test_response_with_null_description`; rossi prima della correzione (`ValidationError`).
- Passi:
  1. Scrivere i test; eseguirli: rossi.
  2. `models/facade/admin_manage.py`: `_drop_null_values` e pulizia delle tre mappe come nel
     piano. `tests/integration/test_catalogs_integration.py` come nel piano.
  3. Controlli bloccanti; commit `fix(admin-manage): le façade dei form scartano le lingue null
     (06-T17)`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 06-C01 | T03, T04 |
| 06-C02 | T03, T04 |
| 06-C03 | T04 |
| 06-C04 | T03, T05 |
| 06-C05 | T05 |
| 06-C06 | T03, T05 |
| 06-C07 | T02, T04 |
| 06-C08 | T06 |
| 06-C09 | T04, T05, T06 |
| 06-C10 | T07, T08 |
| 06-C11 | T09 |
| 06-C12 | T09 |
| 06-C13 | T09, T11 |
| 06-C14 | T10 |
| 06-C15 | T10 |
| 06-C16 | T08 |
| 06-C17 | T07, T11 |
| 06-C18 | T12 |
| 06-C19 | T01, T03 |
| 06-C20 | T15 |
| 06-C21 | T13, T14, T17 |
| 06-C22 | T13, T14 |
| 06-C23 | T17 |
