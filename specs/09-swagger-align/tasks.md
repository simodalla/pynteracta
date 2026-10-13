# Task 09 – Allineamento allo swagger live

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (campo, metodo o comando inesistente); poi il codice; il commit arriva
con i cinque controlli bloccanti verdi. Ogni test porta `# criterio: 09-Cmm` sulla riga sopra.
Messaggi di commit in Conventional Commits con descrizione in italiano: `feat(models)`,
`feat(communities)`, `feat(cli)`, `feat(posts)`, `feat(attachments)`, `test`, `docs`. Gli
snapshot syrupy nuovi o cambiati si generano con `--snapshot-update` e si leggono nel diff prima
del commit. Costanti dei test: community `10` e `20` (fixture `communities_list.json`), post
`21269`, `publicationTimestamp: 1760000000000`, `contentRef` finto della fixture di upload.

## Elenco

### [x] T01 – Rigenerazione dei modelli dallo swagger live

- Criteri: 09-C01, 09-C18
- Dipende da: nessuno
- Test: `tests/contract/test_models.py::TestSwaggerAlignment09`: `assert_superset` su
  `GetPostDetailResponseDTO`, `InputPostAttachmentDTO1`, `CustomFieldValidationErrorDTO`,
  `LicenseDTO`; `draft`, `publicationTimestamp`, `downloadable`, `externalId`, `subType` presenti
  sia nelle `properties` del pinnato sia in `model_fields` dei modelli generati;
  `tests/unit/test_generate_models.py` (09-C18): riordino delle definizioni e formato compatto.
- Passi:
  1. Scrivere i test; eseguirli: rossi (campi assenti dal pinnato e dai modelli; funzione
     `stable_definitions_order` inesistente).
  1b. `scripts/generate_models.py`: `stable_definitions_order` e scrittura del pinnato riordinato
     nel formato compatto, come nel piano (revisione del 2026-10-13).
  2. `uv run python scripts/generate_models.py` (con download). Confrontare con AST i nomi di
     classe generati prima e dopo: nessuna rinomina, cambiano solo i quattro DTO attesi. Confrontare il nuovo pinnato con
     quello precedente (`git stash`/`git show HEAD:tests/fixtures/swagger.json` e lo script di
     confronto in scratchpad): stessi 76 endpoint, stessi 219 schemi, solo le cinque differenze
     attese. Se ce ne sono altre, fermarsi e tornare alla spec.
  3. `git diff --stat src/pynteracta/models/generated/external_v2.py`: solo i cinque campi e la
     descrizione di `LicenseDTO.type`.
  4. `tests/fixtures/payloads/get_post_detail_response.json`: `"draft": false`,
     `"publicationTimestamp": 1760000000000`.
  5. Controlli bloccanti (contract compresi); commit `feat(models): rigenerazione dei modelli
     dallo swagger live del tenant cert`.

### [x] T02 – Test di caratterizzazione della CLI delle community

- Criteri: 09-C13 (prima metà: i comandi esistenti)
- Dipende da: nessuno
- Test: `tests/unit/test_cli_communities.py`: `TestCommunitiesDetailsBulk` (tabella e json con
  snapshot, corpo `communityIds == [10, 20]`), `TestCommunitiesPostDefinitions` (tabella, json,
  `--full`, `--fields community_id,label`, `--export FILE.csv` in `tmp_path` con il messaggio
  `Wrote … records`, `--quiet` senza messaggio), `TestCommunitiesErrors` (una risposta `404` per
  `list`, `details`, `details-bulk`, `post-definition`, `post-definitions` → exit `5`).
- Passi:
  1. Scrivere i test sul comportamento attuale; generare gli snapshot; eseguirli: verdi (sono
     di caratterizzazione, nessun codice da scrivere).
  2. `uv run pytest tests/unit/test_cli_communities.py --cov=pynteracta.cli.communities
     --cov-report=term-missing`: annotare la copertura raggiunta (attesa sopra l'85 % già qui).
  3. Controlli bloccanti; commit `test(cli): caratterizzazione dei comandi delle community`.

### [x] T03 – Enum del livello e `list_by_view_post_capability`

- Criteri: 09-C02, 09-C03, 09-C04, 09-C05, 09-C17
- Dipende da: nessuno (T01 non è necessario: la risposta è `ListCommunitiesResponseDTO`, già
  nei modelli)
- Test: `tests/unit/test_facade_communities.py::TestViewPostCapabilityLevel` (`"private"`,
  `"Private"`, `"PRIVATE"`, l'enum stesso → membro; `"privato"`, `""`, `42` → `ValueError`);
  `tests/unit/test_api_communities.py::TestViewPostCapability`: senza livello una `GET`
  `…/communities/view-post` senza query e `CommunityList` con `items_typed` (id `10`, `20`) e
  `.raw`; con enum e con le tre grafie la query `viewPostCapabilityLevel=PRIVATE` (e `PUBLIC`,
  `ALL`); livello non valido → `ValueError` e `route.called is False`; `403` → `PermissionError`
  con `call_count == 1`; `httpx.TimeoutException` → `TransportError` con `call_count == 1`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (`ImportError` su `ViewPostCapabilityLevel`,
     `AttributeError` sul metodo).
  2. `models/facade/communities.py`: `ViewPostCapabilityLevel(str, Enum)` con `_missing_`;
     esportarla da `models/facade/__init__.py`.
  3. `api/communities.py`: `_VIEW_POST_PATH` e `list_by_view_post_capability(level=None)` come
     nel piano; docstring in italiano.
  4. Controlli bloccanti; commit `feat(communities): elenco delle community per capability di
     visualizzazione dei post`.

### [x] T04 – Comando `communities list-by-view-post`

- Criteri: 09-C06, 09-C07, 09-C13 (seconda metà: il file sopra l'85 % con il comando nuovo)
- Dipende da: T02, T03
- Test: `tests/unit/test_cli_communities.py::TestCommunitiesListByViewPost`: snapshot della
  tabella senza livello e con `--level public` (query `PUBLIC` nella richiesta mockata), `--level
  Private` (maiuscole ignorate), fixture vuota `communities_list_empty.json`, `--output json`,
  `--full`, `--fields id`, `--export FILE.csv`; `--level privato` → exit `2` e nessuna richiesta;
  `403` → exit `4`; `communities --help` elenca `list-by-view-post`.
- Passi:
  1. Scrivere i test e la fixture vuota; eseguirli: rossi (comando inesistente, exit `2` con
     "No such command").
  2. `cli/communities.py`: `ViewPostLevelChoice` e il comando come nel piano; help in inglese.
  3. Snapshot con `--snapshot-update`, letti nel diff.
  4. Copertura di `cli/communities.py` ≥ 85 % (`--cov-report=term-missing`), totale ≥ 95,40 %.
  5. Controlli bloccanti; commit `feat(cli): communities list-by-view-post`.

### [x] T05 – `draft` e `publication_timestamp` nel dettaglio del post

- Criteri: 09-C08, 09-C09; smoke di `Post` per 09-C01
- Dipende da: T01
- Test: `tests/unit/test_facade_posts.py`: `Post.from_dict` sulla fixture aggiornata → `draft is
  False`, `publication_timestamp == 1760000000000`; `{"id": 1}` → entrambi `None`;
  `tests/contract/test_models.py::TestGetPostDetail::test_facade_smoke` esteso con i due campi;
  `tests/unit/test_cli_posts.py::TestPostsGet` e `tests/unit/test_cli_full_fields.py`: snapshot
  di tabella e json con `draft` e `publication_ts` (reso come `creation_ts`), `--fields
  draft,publicationTimestamp` → solo quelle chiavi, `--full` contiene `publicationTimestamp`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (`AttributeError` sulle proprietà, snapshot senza le
     colonne).
  2. `models/facade/posts.py`: le due proprietà, docstring in italiano.
  3. `cli/posts.py`: `draft` e `publication_ts` in `_curated` di `posts get`, dopo
     `last_modify_ts`.
  4. Snapshot aggiornati con `--snapshot-update`, letti nel diff (cambiano tutte le varianti di
     `posts get`).
  5. Controlli bloccanti; commit `feat(posts): draft e publication_timestamp nel dettaglio del
     post`.

### [x] T06 – Flag `downloadable` sugli allegati caricati

- Criteri: 09-C10, 09-C11, 09-C12
- Dipende da: T01 (il campo esiste nel pinnato; i corpi passano comunque come dict)
- Test: `tests/unit/test_facade_attachments.py::TestUploadedAttachment`: `downloadable=False` →
  `as_write_input() == {"name", "contentRef", "downloadable": False}` e `as_version_of(7)` con
  la chiave; `True` → `True`; senza kwarg → `downloadable is None` e dict identici a oggi (il
  test esistente `test_as_write_input_and_as_version_of` resta com'è);
  `tests/unit/test_api_attachments.py`: `upload(path, downloadable=False)` fa le stesse due
  richieste (stesso form multipart, nessun campo in più) e restituisce `downloadable is False`;
  senza kwarg `None`; `tests/unit/test_api_posts_write.py`: `create(79, attachments=[…])` ed
  `edit_attachments(21269, add=[…])` con un `UploadedAttachment` non scaricabile → la voce degli
  allegati nel corpo ha `"downloadable": false` e le altre chiavi invariate;
  `tests/unit/test_api_posts_event.py`: lo stesso per `create_event`.
- Passi:
  1. Scrivere i test; eseguirli: rossi (`TypeError` sul kwarg, chiave assente nei corpi).
  2. `models/facade/attachments.py`: kwarg e proprietà `downloadable`, chiave aggiunta ai due
     dict solo se non `None`; docstring aggiornate.
  3. `api/attachments.py`: kwarg `downloadable` di `upload`, passato a `UploadedAttachment`;
     docstring `Args` in italiano.
  4. Controlli bloccanti; commit `feat(attachments): flag downloadable sugli allegati caricati`.

### [x] T07 – Integration test: `view-post` e allegato non scaricabile

- Criteri: 09-C15, 09-C16 (scrittura dei test; l'esecuzione sul tenant è T08)
- Dipende da: T03, T05, T06
- Test: `tests/integration/test_communities_integration.py::TestCommunitiesIntegration::
  test_list_by_view_post_capability` (senza livello e con `PRIVATE`, `PUBLIC`, `ALL`: ogni
  risultato è un `CommunityList`, ogni elemento ha `id`; stampa `[09-T08] no level → N
  communities`); `tests/integration/test_attachments_integration.py::TestAttachmentsUploadIntegration::
  test_full_cycle` esteso: `upload(first, downloadable=False)`, dopo la creazione
  `client.posts.get(post_id)` con `draft in (False, None)` e `publication_timestamp` `int` o
  `None` (stampa `[09-T08] draft=… publication_timestamp=…`), `attached[0].downloadable is
  False`; `finally` con `delete` invariato.
- Passi:
  1. Scrivere i test; `uv run pytest -m integration tests/integration/test_communities_integration.py
     tests/integration/test_attachments_integration.py --collect-only`: raccolti; senza `.env`
     si auto-skippano.
  2. Controlli bloccanti (gli integration test non girano nei controlli); commit
     `test(integration): view-post e allegato non scaricabile`.

### [x] T08 – Prova sul tenant (manuale)

- Criteri: 09-C15, 09-C16; esito per 09-C14 (cosa risponde il tenant)
- Chi: maintainer (o Claude su richiesta del maintainer, con `tests/integration/.env` e la
  chiave del service account presenti, come nelle spec 05–08)
- Cosa fare:
  1. `set -a; source tests/integration/.env; set +a` e
     `uv run pytest -m integration tests/integration/test_communities_integration.py
     tests/integration/test_attachments_integration.py -v -s`: entrambi i test nuovi verdi;
     annotare quante community risponde `view-post` senza livello rispetto a `communities
     list` e ai tre livelli, e se il dettaglio del post creato porta `draft` e
     `publicationTimestamp`.
  2. Sonda in scratchpad (fuori dal repo, non committata): nella community di prova creare un
     post, caricare un file con `downloadable=False` e allegarlo a un commento
     (`posts.add_comment`) e a un task (`tasks.create`) del post; registrare se il server
     accetta, ignora (allegato letto con `downloadable` vero) o rifiuta (`400`) il campo;
     eliminare il post alla fine (i task e i commenti vanno con lui).
  3. Se `view-post` senza livello risponde con un errore, o se `downloadable` cambia qualcosa
     nelle scritture dei post rispetto alla spec, fermarsi: si rivede la spec prima di T09.
- Esito (2026-10-13, eseguito da Claude su richiesta del maintainer, community di prova):
  - integration test verdi: `test_list_by_view_post_capability` e `test_full_cycle` (12 test
    nei due file, 9,2 s);
  - `view-post` con il service account: 15 community senza livello e 15 con `PRIVATE`,
    `PUBLIC` e `ALL`; `communities list` (dove si può pubblicare) ne dà 9. Senza livello il
    server risponde come con `ALL`;
  - il dettaglio del post creato porta `draft: false` e `publicationTimestamp` (epoch ms);
  - `downloadable: false` su un post (`edit_attachments`) è applicato: l'allegato letto ha
    `downloadable` falso, quello caricato senza flag vero;
  - su un commento e su un task il server risponde `400` "Unrecognized field downloadable
    (InputPostCommentAttachmentDTO / InputTaskAttachmentDTO), not marked as ignorable": il
    campo non è ignorato, è rifiutato. Va detto nei docs (09-C14);
  - i due post di prova (23397, 23398) sono stati eliminati; la sonda è rimasta fuori dal
    repository.

### [ ] T09 – Documentazione e PRD (chiusura)

- Criteri: 09-C14; chiusura dei "Requisiti nuovi" della spec
- Dipende da: T04, T05, T06, T08
- Test: `tests/unit/test_docs_snippets.py::test_swagger_alignment_pages` (marker 09-C14):
  `list-by-view-post` e `--level` in `docs/cli.md`; `list_by_view_post_capability` e
  `ViewPostCapabilityLevel` in `docs/api/communities.md`; `downloadable` in
  `docs/api/attachments.md`; `publication_timestamp` in `docs/api/posts.md`; i blocchi Python
  nuovi passano il controllo statico dei frammenti; `uv run mkdocs build --strict` verde.
- Passi:
  1. Scrivere il test; eseguirlo: rosso (testi assenti).
  2. `docs/api/communities.md`: metodo nei `members`, sezione con esempio, enum e cosa risponde
     il tenant senza livello (da T08); `::: …ViewPostCapabilityLevel`.
  3. `docs/api/posts.md`: `draft` e `publication_timestamp` nel dettaglio;
     `docs/api/attachments.md`: `downloadable` in "Uploading files", DTO che lo prevedono ed
     esito di T08 su commenti e task; `docs/cli.md`: `communities list-by-view-post` e le
     colonne nuove di `posts get`.
  4. `specs/prd.md`: RF-007a, RF-006b, RF-024b definitivi con la semantica verificata in T08;
     RF-021c e §6 "Dati scritti sul tenant" aggiornati per `downloadable`; §1 e RF-007 dicono
     che tutti gli endpoint dello swagger pinnato sono esposti; riga nella storia del documento.
  5. `uv run mkdocs build --strict`, `uv run pre-commit run --all-files`, controlli bloccanti;
     commit `docs: allineamento allo swagger live, pagine e PRD (09-T09)`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 09-C01 | T01 (T05 per lo smoke di `Post`) |
| 09-C02 | T03 |
| 09-C03 | T03 |
| 09-C04 | T03 |
| 09-C05 | T03 |
| 09-C06 | T04 |
| 09-C07 | T04 |
| 09-C08 | T05 |
| 09-C09 | T05 |
| 09-C10 | T06 |
| 09-C11 | T06 |
| 09-C12 | T06 |
| 09-C13 | T02, T04 |
| 09-C14 | T09 |
| 09-C15 | T07, T08 |
| 09-C16 | T07, T08 |
| 09-C17 | T03 |
| 09-C18 | T01 |
