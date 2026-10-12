# Verifica 06 – Anagrafiche admin, seconda metà: cataloghi, voci di catalogo e workspace

Data: 2026-10-12
Commit verificato: `c05317b` sul branch `m32_admin_catalogs_workspace` (spec `f1e8110`, piano
`5e1ba3d`, task `72a138a`; T01–T13: `4b248a6` … `f4c5ba9`; revisioni della spec dopo la
prova sul tenant `24b98dc`, `9447bb5`, `1197bd9`; T17 `09b967e`; T18 `9adc5e8`; T14
`f7620cf`; T19 `8855901`; T15 `e065c29`; T16 `c05317b`)
Esito: **nessun problema**. Spec chiusa.

## Task

19 su 19 spuntati, compreso T14 (`manuale`) con l'esito compilato: eseguito da Claude su
richiesta del maintainer sul tenant di prova. Le esecuzioni hanno mostrato tre divergenze dalla
spec, ciascuna con una revisione approvata dal maintainer:

- il form reale del workspace ha `description: {"it": null}` e la façade falliva (`24b98dc`,
  criterio 06-C23, task T17);
- la `PUT` del workspace esige `name` (`400` `REQUIRED_FIELD`): `edit-workspace` è diventato
  una patch (`9447bb5`, criterio 06-C24, task T18);
- la risposta della `PUT` del workspace ha i conteggi a `0`: `edit-workspace` rilegge il form
  dopo la modifica (`1197bd9`, criterio 06-C25, task T19).

Dopo le correzioni i due cicli sono verdi, e una prova della CLI sul workspace di prova
(`edit-workspace --add-user`, poi `--remove-user`) ha mostrato i conteggi veri, 2 → 3 → 2.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 06-C01 | `test_api_catalogs.py::TestCatalogsCreate::test_create_sends_only_given_fields_and_wraps_response`; `test_api_catalogs.py::TestCatalogsCreate::test_create_raw_equivalent`; `test_api_catalogs.py::TestCatalogsCreate::test_create_without_parent_omits_key`; `test_facade_catalogs.py::TestCatalogWriteResult::test_from_create` | verde |
| 06-C02 | `test_api_catalogs.py::TestCatalogsEdit::test_edit_sends_given_fields_and_occ_token`; `test_api_catalogs.py::TestCatalogsEdit::test_edit_raw_equivalent_with_deleted_in_dto`; `test_facade_catalogs.py::TestCatalogWriteResult::test_from_edit` | verde |
| 06-C03 | `test_api_catalogs.py::TestCatalogsSetDeleted::test_true_sends_exact_body`; `test_api_catalogs.py::TestCatalogsSetDeleted::test_false_sends_exact_body`; `test_facade_catalogs.py::TestCatalogDeletedResult::test_catalog_has_no_entry_id` | verde |
| 06-C04 | `test_api_catalogs.py::TestCatalogEntriesCreate::test_create_entry_sends_only_given_fields_and_wraps_response`; `test_api_catalogs.py::TestCatalogEntriesCreate::test_create_entry_raw_equivalent`; `test_facade_catalogs.py::TestCatalogEntryWriteResult::test_from_create` | verde |
| 06-C05 | `test_api_catalogs.py::TestCatalogEntriesEdit::test_edit_entry_sends_given_fields_and_occ_token`; `test_api_catalogs.py::TestCatalogEntriesEdit::test_edit_entry_raw_equivalent` | verde |
| 06-C06 | `test_api_catalogs.py::TestCatalogEntriesSetDeleted::test_true_sends_exact_body_and_reads_catalog_id`; `test_api_catalogs.py::TestCatalogEntriesSetDeleted::test_reads_entry_id_form`; `test_api_catalogs.py::TestCatalogEntriesSetDeleted::test_false`; `test_facade_catalogs.py::TestCatalogDeletedResult::test_catalog_id_form` (+1) | verde |
| 06-C07 | `test_api_catalogs.py::TestCatalogsForEditAliases::test_get_for_edit_same_route_and_facade`; `test_api_catalogs.py::TestCatalogsForEditAliases::test_get_entry_for_edit_same_route_and_facade`; `test_facade_admin_manage.py::TestWorkspaceForEdit::test_occ_token_exposed`; `test_facade_admin_manage.py::TestCatalogForEdit::test_occ_token_exposed` (+4) | verde |
| 06-C08 | `test_api_admin_manage.py::TestEditWorkspace::test_edit_sends_given_fields_with_token_in_path`; `test_api_admin_manage.py::TestEditWorkspace::test_edit_raw_equivalent` | verde |
| 06-C09 | `test_api_admin_manage.py::TestEditWorkspace::test_409_raises_concurrency_error_once`; `test_api_admin_manage.py::TestEditWorkspace::test_timeout_raises_transport_error_once`; `test_api_catalogs.py::TestCatalogsWriteErrors::test_edit_409_raises_concurrency_error_once`; `test_api_catalogs.py::TestCatalogsWriteErrors::test_set_deleted_404_raises_not_found` (+4) | verde |
| 06-C10 | `test_cli_catalogs_write.py::TestCatalogsCreate::test_flags_and_json_merge_name_key_by_key`; `test_cli_catalogs_write.py::TestCatalogsCreate::test_table_output`; `test_cli_catalogs_write.py::TestCatalogsCreate::test_json_output`; `test_cli_catalogs_write.py::TestCatalogsCreate::test_malformed_name_exits_2_without_requests` (+8) | verde |
| 06-C11 | `test_cli_catalogs_write.py::test_catalog_edit_base_with_parent`; `test_cli_catalogs_write.py::test_catalog_edit_base_without_parent`; `test_cli_catalogs_write.py::test_catalog_edit_base_without_content_data`; `test_cli_catalogs_write.py::TestCatalogsEdit::test_edit_reads_form_then_puts_patched_body` (+5) | verde |
| 06-C12 | `test_cli_catalogs_write.py::test_entry_edit_base_with_parents`; `test_cli_catalogs_write.py::test_entry_edit_base_without_parents`; `test_cli_catalogs_write.py::test_entry_edit_base_skips_parents_without_id`; `test_cli_catalogs_write.py::TestCatalogEntriesEdit::test_edit_entry_reads_form_then_puts_patched_body` (+3) | verde |
| 06-C13 | `test_cli_admin_manage_write.py::TestEditWorkspace::test_409_exits_9`; `test_cli_catalogs_write.py::TestCatalogsEdit::test_409_exits_9`; `test_cli_catalogs_write.py::TestCatalogEntriesEdit::test_409_exits_9` | verde |
| 06-C14 | `test_cli_catalogs_write.py::TestCatalogsDelete::test_prompt_shows_id_and_it_name_and_y_deletes`; `test_cli_catalogs_write.py::TestCatalogsDelete::test_prompt_n_does_nothing`; `test_cli_catalogs_write.py::TestCatalogsDelete::test_yes_skips_prompt`; `test_cli_catalogs_write.py::TestCatalogsDelete::test_json_output` (+7) | verde |
| 06-C15 | `test_cli_catalogs_write.py::TestCatalogsRestore::test_restore_puts_false_without_prompt_even_non_interactive`; `test_cli_catalogs_write.py::TestCatalogsRestore::test_json_output`; `test_cli_catalogs_write.py::TestCatalogEntriesRestore::test_restore_without_prompt`; `test_cli_catalogs_write.py::TestCatalogEntriesRestore::test_json_output` | verde |
| 06-C16 | `test_cli_catalogs_write.py::TestCatalogEntriesCreate::test_flags_body_and_table`; `test_cli_catalogs_write.py::TestCatalogEntriesCreate::test_json_label_merged_with_flag` | verde |
| 06-C17 | `test_cli_admin_manage_write.py::test_workspace_body_all_inputs`; `test_cli_admin_manage_write.py::test_workspace_body_empty_without_inputs`; `test_cli_admin_manage_write.py::TestEditWorkspace::test_flags_read_token_then_put_exact_body`; `test_cli_admin_manage_write.py::TestEditWorkspace::test_json_output` (+7) | verde |
| 06-C18 | `test_cli_admin_manage_write.py::TestEditWorkspaceUploads::test_cover_and_logo_uploaded_in_order_then_put`; `test_cli_admin_manage_write.py::TestEditWorkspaceUploads::test_cover_upload_failure_exits_11_without_put`; `test_cli_admin_manage_write.py::TestEditWorkspaceUploads::test_cover_alone_counts_as_input` | verde |
| 06-C19 | `test_models.py::TestAdminCatalogsWorkspaceWriteDTOs::test_schema_superset` (11 DTO); `test_models.py::TestAdminCatalogsWorkspaceWriteDTOs::test_typed_stub_superset`; `test_models.py::TestAdminCatalogsWorkspaceWriteDTOs::test_fixtures_parse`; `test_models.py::TestAdminCatalogsWorkspaceWriteDTOs::test_facade_smoke` | verde |
| 06-C20 | `test_docs_snippets.py::test_catalogs_workspace_pages_document_write_commands` | verde |
| 06-C21 | `test_catalogs_integration.py::TestCatalogsWriteIntegration::test_create_edit_entry_delete_cycle` | verde sul tenant (T14); saltato senza variabili |
| 06-C22 | `test_admin_manage_integration.py::TestWorkspaceWriteIntegration::test_add_remove_member_cycle` | verde sul tenant (T14, dopo T17 e T18); saltato senza `PYNTERACTA_TEST_WRITE_WORKSPACE=1` |
| 06-C23 | `test_api_admin_manage.py::TestEditWorkspace::test_response_with_null_description`; `test_cli_admin_manage.py::TestAdminManageWorkspace::test_null_description_exits_0`; `test_facade_admin_manage.py::TestNullLanguageValues::test_workspace_drops_null_languages`; `test_facade_admin_manage.py::TestNullLanguageValues::test_catalog_drops_null_languages` (+1) | verde |
| 06-C24 | `test_cli_admin_manage_write.py::test_workspace_edit_base_reads_name_and_maps`; `test_cli_admin_manage_write.py::test_workspace_edit_base_skips_missing_keys`; `test_cli_admin_manage_write.py::test_apply_form_body_wins_and_maps_merge_per_language`; `test_cli_admin_manage_write.py::test_apply_form_without_base_maps` (+6) | verde |
| 06-C25 | `test_cli_admin_manage_write.py::TestEditWorkspaceReread::test_table_shows_reread_counts`; `test_cli_admin_manage_write.py::TestEditWorkspaceReread::test_reread_failure_warns_and_exits_0`; `test_cli_admin_manage_write.py::TestEditWorkspaceReread::test_409_does_not_reread` | verde |

25 criteri su 25 con almeno un test; nessun marker cita un criterio inesistente.

## Controlli automatici

| Comando | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde |
| `uv run mypy src` | verde (60 file) |
| `uv run pytest -m "not integration and not contract"` | verde (1350 test) |
| `uv run pytest -m contract` | verde (201 test) |
| `uv run mkdocs build --strict` | verde, nessun warning |
| `uv run pre-commit run --all-files` | verde |
| `uv run pytest -m integration tests/integration/test_catalogs_integration.py` (T14, sul tenant) | verde |
| `PYNTERACTA_TEST_WRITE_WORKSPACE=1 uv run pytest -m integration tests/integration/test_admin_manage_integration.py` (T14, sul tenant) | verde |

Nessun controllo a cricchetto configurato.

## Copertura

| Ambito | Linea di partenza | Ora |
|---|---|---|
| Totale | 94,94 % | **95,18 %** (5998/6302 righe) |
| `api` | 98,04 % | 98,19 % |
| `cli` | 92,59 % | 93,11 % |
| `models/facade` | 96,18 % | 96,33 % |

File toccati dalla spec, soglia 85 %:

| File | Copertura | Righe scoperte |
|---|---|---|
| `api/catalogs.py` | 100 % | – |
| `api/admin_manage.py` | 100 % | – |
| `cli/_write.py` | 100 % | – |
| `cli/admin_manage_write.py` | 100 % | – |
| `cli/catalogs_write.py` | 96 % | 127, 243, 294, 436, 454, 485, 506 (ramo `--quiet` di delete/restore; `handle_error` di create, create-entry e dei quattro comandi delete/restore, senza test di errore HTTP) |
| `cli/admin_manage.py` | 94 % | 116, 158, 201, 243 (rami di errore preesistenti) |
| `cli/catalogs.py` | 89 % | 76, 117, 119, 121, 150 (preesistenti, solo docstring toccata) |
| `cli/__init__.py` | 90 % | 165-171, 183-187 (preesistenti) |
| `models/facade/catalogs.py` | 98 % | 63, 133, 148 (`from_raw` e `parent_ids` preesistenti) |
| `models/facade/admin_manage.py` | 95 % | 35, 75, 119, 123, 159, 182, 279, 290 (rami con root non dict e timestamp preesistenti; ramo non dict di `_drop_null_values`) |
| `models/facade/__init__.py` | 100 % | – |

Unit test 1208 → 1350, contract test 185 → 201. La linea di partenza è aggiornata.

## Regole non negoziabili

| Regola | Verifica | Esito |
|---|---|---|
| Token e segreti mai nei log | Nessun log nuovo nel codice della spec. L'`occToken` del workspace sta nel path: è un contatore di versione, non un segreto, e la redazione degli URL agisce sulle query. L'avviso della rilettura fallita stampa il messaggio dell'eccezione, che il transport costruisce già redatto. | rispettata |
| Cache del token con permessi stretti | Non toccata. | rispettata |
| Segreti fuori dal repository | Fixture con valori finti; `.env.example` con soli nomi; nessun `.env`, `.secrets` o `audit.log` versionato. Le sonde sul tenant hanno stampato solo id, conteggi, stati e codici di errore. | rispettata |
| Soglie che non scendono | Copertura totale e per area in salita; regole di ruff e mypy invariate. | rispettata |
| Dati personali fuori dai log | Nomi di cataloghi e voci non sono dati personali; del workspace passano solo id di utenti e gruppi. Nessun log nuovo. | rispettata |
| Nessuna operazione ripetuta in automatico | Ogni metodo fa una richiesta e lascia salire le eccezioni; la CLI non riprova sul `409`. La `GET` dopo `edit-workspace` è una lettura, non un nuovo tentativo: se fallisce, la modifica resta riuscita e il comando lo dice. Gli upload di `--cover`/`--logo` partono prima della `PUT` e si fermano al primo errore. | rispettata |

## Coerenza

- Il codice fa ciò che dicono spec e piano, nella versione rivista dopo T14: scritture di
  cataloghi e voci su `client.catalogs`, `edit_workspace` su `client.admin_manage`, `occ_token`
  su tutte le façade dei form, nove comandi CLI con patch, cancellazione logica e upload.
- Oltre il piano, solo nei test: il ciclo integration del workspace salta se l'utente di prova è
  già membro, e decide sempre su una lettura nuova del form, perché la risposta della `PUT` ha i
  conteggi a `0`.
- Nessun ADR nuovo: la spec resta dentro ADR 0001. I "Requisiti nuovi" sono nel PRD (`c05317b`):
  RF-023 precisato con la semantica verificata e con la versione della spec 05 corretta in 0.12.0,
  RF-023e, RF-023f; RF-023, RF-008, RF-013, RF-019 e la voce "Dati scritti sul tenant" di §6
  confermati.

## Debiti aperti della linea di partenza

Nessuna violazione `P-<mm>` aperta; nessun controllo a cricchetto. Copertura misurata.

## Problemi trovati

Nessuno nella spec. Osservazioni fuori ambito, da seguire a parte:

- Le prove sul tenant hanno lasciato i cataloghi 33, 34, 35 e le voci 8490-8492, tutti
  disabilitati: l'API non li elimina, va fatto dall'amministrazione di Interacta se serve.
- `catalogs.list()` senza id restituisce una lista vuota sul tenant di prova: conviene dirlo in
  `docs/api/catalogs.md` o capire se dipende dal service account.
- La `GET` del form di una voce risponde con qualunque `catalogId` nel path.
- Se traduzioni e descrizione omesse dal `PUT` del workspace vengano azzerate non si è provato,
  per non toccare il workspace condiviso; la CLI le rimanda comunque.
