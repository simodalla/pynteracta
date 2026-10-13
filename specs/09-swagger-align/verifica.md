# Verifica 09 – Allineamento allo swagger live

Data: 2026-10-13
Commit verificato: `3dd9fed` sul branch `m35_swagger_align` (spec `efe1487`, piano `886ac41`,
task `c2fe036`; revisione della spec `4ec1648`; T01 `31e8425` e `4d4c1a0`, T02 `6960e22`, T03
`b22d34f`, T04 `48a0e3f`, T05 `78b882f`, T06 `b78b6d6`, T07 `5e86607`, T08 `a1afd19`, T09
`3dd9fed`), più lo spostamento di due marker con il commit di questa verifica
Esito: **nessun problema**. Spec chiusa.

## Task

9 su 9 spuntati, compreso T08 (`manuale`) con l'esito compilato: eseguito da Claude su richiesta
del maintainer sulla community di prova. Durante il lavoro tre correzioni:

- T01: la rigenerazione dallo swagger live rinominava `EventPostDataDTOModel` in
  `EventPostDataDTO1`, perché il tenant elenca le definizioni in un altro ordine. Scelta del
  maintainer: ordine stabile nello script di rigenerazione, nuovo criterio 09-C18 (revisione
  `4ec1648`). Con l'ordine stabile il diff dei modelli generati tocca solo i quattro DTO attesi.
- T05: il testo di 09-C09 citava `--fields draft,publication_ts`; `--fields` seleziona sui nomi
  dei campi grezzi in tutta la CLI, quindi è diventato `--fields draft,publicationTimestamp`.
  Nessun comportamento nuovo; registrato nella sezione "Revisioni" della spec.
- T09: lo script di T01 scriveva il pinnato senza a capo finale, che il hook
  `end-of-file-fixer` pretende e che il pinnato su `main` aveva; corretto in `4d4c1a0` con il
  test di 09-C18 prima rosso.

Esiti sul tenant (T08): `view-post` restituisce 15 community con ogni livello e senza livello
(contro le 9 di `communities list`); il dettaglio del post porta `draft` e `publicationTimestamp`;
`downloadable: false` è applicato agli allegati dei post e rifiutato con `400` ("Unrecognized
field") su commenti e task. Tutto documentato.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 09-C01 | `test_models.py::TestSwaggerAlignment09::test_new_field_pinned_and_generated` (5 casi); `test_models.py::TestSwaggerAlignment09::test_dto_superset` (4 casi); `test_models.py::TestGetPostDetail::test_facade_smoke` | verde |
| 09-C02 | `test_api_communities.py::TestViewPostCapability::test_without_level_sends_no_query` | verde |
| 09-C03 | `test_api_communities.py::TestViewPostCapability::test_level_sent_as_query` (8 casi); `test_facade_communities.py::TestViewPostCapabilityLevel::test_accepted_values` (6 casi) | verde |
| 09-C04 | `test_api_communities.py::TestViewPostCapability::test_invalid_level_raises_before_request`; `test_facade_communities.py::TestViewPostCapabilityLevel::test_invalid_values_raise` | verde |
| 09-C05 | `test_api_communities.py::TestViewPostCapability::test_403_raises_permission_error_once` | verde |
| 09-C06 | `test_cli_communities.py::TestCommunitiesListByViewPost::test_table_without_level`; `::test_level_sent`; `::test_empty_table`; `::test_json_same_as_list` (+3) | verde |
| 09-C07 | `test_cli_communities.py::TestCommunitiesListByViewPost::test_invalid_level_exits_usage_without_requests`; `::test_forbidden_exits_permission` | verde |
| 09-C08 | `test_facade_posts.py::TestPostDraftAndPublication::test_fields_from_fixture`; `::test_draft_true`; `::test_absent_fields_are_none` | verde |
| 09-C09 | `test_cli_posts.py::TestPostsGet::test_table_output`; `::test_json_output`; `test_cli_full_fields.py::TestPostsGetFull::test_fields_draft_and_publication`; `::test_full_contains_new_fields` (+1) | verde |
| 09-C10 | `test_facade_attachments.py::TestUploadedAttachmentDownloadable::test_flag_in_write_input_and_version`; `test_api_attachments.py::TestUploadDownloadable::test_flag_kept_and_not_sent_to_storage` | verde |
| 09-C11 | `test_facade_attachments.py::TestUploadedAttachmentDownloadable::test_without_flag_dicts_unchanged`; `test_api_attachments.py::TestUploadDownloadable::test_without_flag_is_none` | verde |
| 09-C12 | `test_api_posts_write.py::TestPostsNotDownloadableAttachments::test_create`; `::test_edit_attachments_add`; `test_api_posts_event.py::TestEventNotDownloadableAttachments::test_create_event` | verde |
| 09-C13 | `test_cli_communities.py::TestCommunitiesDetailsBulk` (2), `::TestCommunitiesPostDefinitions` (6), `::TestCommunitiesErrors::test_not_found_exits_5` (5 casi); copertura di `cli/communities.py` 99 % | verde |
| 09-C14 | `test_docs_snippets.py::test_swagger_alignment_pages`; `uv run mkdocs build --strict` | verde |
| 09-C15 | `test_communities_integration.py::TestCommunitiesIntegration::test_list_by_view_post_capability` (eseguito sul tenant in T08: verde) | verde |
| 09-C16 | `test_attachments_integration.py::TestAttachmentsUploadIntegration::test_full_cycle` (eseguito sul tenant in T08: verde) | verde |
| 09-C17 | `test_api_communities.py::TestViewPostCapability::test_timeout_raises_transport_error_once` | verde |
| 09-C18 | `test_generate_models.py::TestStableDefinitionsOrder` (3), `::TestDownloadSwagger` (2); confronto AST dei nomi delle classi generate in T01 (336 classi, nessuna rinominata) | verde |

18 criteri su 18 con almeno un test; nessun marker cita un criterio inesistente. Durante la
verifica due marker (09-C01 nello smoke del dettaglio post, 09-C16 nel ciclo di upload) erano
dentro il corpo del test: spostati sulla riga sopra il test, come vuole la configurazione.

## Controlli automatici

| Comando | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (136 file) |
| `uv run mypy src` | verde (64 file) |
| `uv run pytest -m "not integration and not contract"` | verde (1616 test, 104 snapshot) |
| `uv run pytest -m contract` | verde (238 test) |
| `uv run mkdocs build --strict` | verde, nessun warning |
| `uv run pre-commit run --all-files` | verde |
| `uv run pytest -m integration` sui file delle community e degli allegati (T08, sul tenant) | verde (12 test) |

Nessun controllo a cricchetto configurato.

## Copertura

| Ambito | Linea di partenza | Ora |
|---|---|---|
| Totale | 95,40 % | **96,18 %** (6680/6945 righe) |
| `api` | 98,44 % | 98,45 % |
| `cli` | 93,53 % | 95,29 % |
| `models/facade` | 96,35 % | 96,39 % |

File toccati dalla spec, soglia 85 %:

| File | Copertura | Righe scoperte |
|---|---|---|
| `api/communities.py` | 100 % | – |
| `api/attachments.py` | 100 % | – |
| `cli/communities.py` | 99 % (53 % alla partenza) | 164 (`_extra` di `details` con `--web-url` e `--full`, preesistente) |
| `cli/posts.py` | 94 % | 51, 117, 427-428, 506, 525, 582, 642, 692, 744-745, 762, 814, 844-845, 873 (preesistenti, nessuna nel `_curated` di `posts get`) |
| `models/facade/communities.py` | 95 % | 89, 176, 186, 217, 242, 257, 262, 280, 285, 323 (preesistenti) |
| `models/facade/posts.py` | 98 % | 166, 176, 328 (preesistenti) |
| `models/facade/attachments.py` | 95 % | 54, 58, 62, 78, 82, 86, 98-99, 134, 138, 152 (preesistenti) |
| `models/facade/__init__.py` | 100 % | – |

`scripts/generate_models.py` non rientra nella misura (`src/` soltanto); le sue funzioni nuove
sono coperte da `test_generate_models.py`. La linea di partenza è aggiornata (totale, aree,
conteggi dei test, file meno coperto).

## Regole non negoziabili

| Regola | Verifica | Esito |
|---|---|---|
| Token e segreti mai nei log | Nessun log nuovo nella libreria; l'URL di `view-post` porta solo il livello; lo swagger è un documento pubblico del tenant. | rispettata |
| Cache del token con permessi stretti | Non toccata. | rispettata |
| Segreti fuori dal repository | Fixture con valori finti; nessun `.env`, `.secrets` o `audit.log` versionato; la sonda di T08 è rimasta in una cartella temporanea fuori dal repo ed è stata cancellata. | rispettata |
| Soglie che non scendono | Copertura totale e per area in salita; regole di ruff e mypy invariate. | rispettata |
| Dati personali fuori dai log | Nessun log nuovo; nomi delle community e campi del post vanno solo nell'output della CLI, come le letture esistenti. | rispettata |
| Nessuna operazione ripetuta in automatico | `list_by_view_post_capability` fa una richiesta e lascia salire `PermissionError` e `TransportError` (09-C05, 09-C17); `upload` invariato nel numero di richieste (09-C10). | rispettata |

## Coerenza

- Il codice fa ciò che dicono spec e piano, nella versione rivista: rigenerazione con ordine
  stabile, metodo e comando `view-post`, due proprietà e due colonne del post, flag
  `downloadable` su `upload` e `UploadedAttachment`. `posts get-by-client-uid`, che usa la stessa
  façade, non mostra le colonne nuove: la spec nomina solo `posts get` (vedi sotto).
- Nessun ADR nuovo: la spec non cambia decisioni del PRD. I "Requisiti nuovi" sono nel PRD
  (`3dd9fed`): RF-006b, RF-007a, RF-024b con la semantica verificata sul tenant; RF-021c e §6
  aggiornati per `downloadable`; §1 dice che tutti i 76 endpoint dello swagger pinnato sono
  esposti.
- README e home del sito invariati, come deciso nella spec (nessun gruppo nuovo).

## Debiti aperti della linea di partenza

Nessuna violazione `P-<mm>` aperta; nessun controllo a cricchetto. Copertura misurata.

## Problemi trovati

Nessuno nella spec. Osservazioni fuori ambito, da seguire a parte:

- `posts get-by-client-uid` potrebbe mostrare `draft` e `publication_ts` come `posts get`.
- La libreria potrebbe rifiutare prima della richiesta un `UploadedAttachment` con
  `downloadable` passato a un commento o a un task, invece di lasciare il `400` al server.
- Con il service account i tre livelli di `view-post` danno lo stesso risultato: con utenti
  dai permessi diversi potrebbero differire, non verificato.
