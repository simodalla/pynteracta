# Piano 09 – Allineamento allo swagger live

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Quattro interventi piccoli e indipendenti, nella catena consueta del progetto (façade → metodo
`api/` → CLI tramite `render_output` → test unit, contract, fixture → docs), senza toccare
transport, client base né il generatore. La rigenerazione usa `scripts/generate_models.py` così
com'è (download dal tenant cert, che ripinna `tests/fixtures/swagger.json`, poi codegen): la
prova offline del 2026-10-13 ha dato "file unchanged", quindi il diff dei modelli generati sarà
limitato ai cinque campi nuovi. L'endpoint `view-post` entra in `CommunitiesAPI` come metodo
`list_by_view_post_capability`, con l'enum `ViewPostCapabilityLevel` in `facade/communities.py`
(stringa senza distinzione di maiuscole tramite `_missing_`) e `build_query_params` per la query;
la risposta è il `CommunityList` esistente. In CLI il comando `list-by-view-post` ricalca
`communities list`, con `--level` come scelta `private|public|all` (enum di modulo, come
`ParticipationChoice` della spec 08). `Post` guadagna due proprietà e `posts get` due colonne.
`upload` guadagna il kwarg `downloadable`, che `UploadedAttachment` conserva e aggiunge ai dict di
`as_write_input` e `as_version_of` solo se non `None`: i corpi delle scritture non cambiano
altrove, perché gli allegati passano già come dict. La copertura di `cli/communities.py` sale con
unit test sui comandi `details-bulk` e `post-definitions` e sui rami di errore, oggi scoperti.
Test prima del codice.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `scripts/generate_models.py` | modificato | `stable_definitions_order(new: dict, previous: dict \| None) -> dict`: restituisce `new` con `definitions` riordinate (prima le chiavi di `previous` presenti in `new`, nell'ordine di `previous`, poi le nuove nell'ordine di `new`); il resto invariato. `download_swagger` legge il pinnato esistente prima di sovrascriverlo e scrive `json.dumps(…, separators=(",", ":"), ensure_ascii=False)`, lo stesso formato compatto di oggi (09-C18) |
| `tests/unit/test_generate_models.py` | nuovo | 09-C18: lo script caricato con `importlib.util.spec_from_file_location`; `stable_definitions_order` con ordine diverso più una definizione nuova, senza precedente, valori invariati; `download_swagger` con `httpx.get` mockato (respx) e `SWAGGER_SNAPSHOT` in `tmp_path`: file scritto nel formato compatto e nell'ordine del precedente |
| `tests/fixtures/swagger.json` | modificato (rigenerato) | swagger live del tenant cert, scaricato da `scripts/generate_models.py`, con le definizioni nell'ordine del pinnato precedente |
| `src/pynteracta/models/generated/external_v2.py` | modificato (rigenerato) | `GetPostDetailResponseDTO.draft`, `.publicationTimestamp`; `InputPostAttachmentDTO1.downloadable`; `CustomFieldValidationErrorDTO.externalId`; `LicenseDTO.subType` (e descrizione di `type`). Mai a mano |
| `src/pynteracta/models/facade/communities.py` | modificato | `ViewPostCapabilityLevel(str, Enum)`: `PRIVATE = "PRIVATE"`, `PUBLIC = "PUBLIC"`, `ALL = "ALL"`; `_missing_(value)` accetta una `str` confrontata in maiuscolo, altrimenti `None` (quindi `ValueError` dell'enum per `"privato"`, `""`, `42`); docstring in italiano |
| `src/pynteracta/api/communities.py` | modificato | `_VIEW_POST_PATH = "communication/settings/communities/view-post"`; `list_by_view_post_capability(self, level: ViewPostCapabilityLevel \| str \| None = None) -> CommunityList`: `params = build_query_params(view_post_capability_level=ViewPostCapabilityLevel(level).value if level is not None else None)` (la conversione precede `_get`: `ValueError` prima della richiesta), `CommunityList.from_dict(self._get(_VIEW_POST_PATH, params=params or None))`; docstring in italiano con il rinvio alla documentazione su cosa risponde il tenant senza livello |
| `src/pynteracta/models/facade/__init__.py` | modificato | esporta `ViewPostCapabilityLevel` |
| `src/pynteracta/cli/communities.py` | modificato | `ViewPostLevelChoice(str, Enum)` `private/public/all`; comando `list-by-view-post` con `--level` (`typer.Option`, `case_sensitive=False`, help in inglese) e le opzioni `output/full/fields/export/export_format`; corpo identico a `communities list` (`render_output` con `{"id", "name"}`, titolo `Communities`, `handle_error`), chiamando `client.communities.list_by_view_post_capability(ViewPostCapabilityLevel(level.value) if level else None)`; nessun'altra modifica ai comandi esistenti |
| `src/pynteracta/models/facade/posts.py` | modificato | `Post.draft -> bool \| None` (`raw.draft`), `Post.publication_timestamp -> int \| None` (`raw.publicationTimestamp`), docstring in italiano |
| `src/pynteracta/cli/posts.py` | modificato | in `_curated` di `posts get`: `"draft": getattr(obj, "draft", None)` e `"publication_ts": EpochMs(pts) if pts is not None else None`, dopo `last_modify_ts` |
| `src/pynteracta/models/facade/attachments.py` | modificato | `UploadedAttachment.__init__(ticket, *, name, mime_type, downloadable: bool \| None = None)`; proprietà `downloadable`; `as_write_input()` e `as_version_of()` aggiungono `"downloadable": self._downloadable` solo se non `None`; docstring aggiornate |
| `src/pynteracta/api/attachments.py` | modificato | `upload(..., downloadable: bool \| None = None)`: passa il flag a `UploadedAttachment`; le due richieste dell'upload non cambiano; docstring (`Args`) in italiano con il rinvio ai DTO che lo prevedono |
| `tests/fixtures/payloads/get_post_detail_response.json` | modificato | aggiunge `"draft": false` e `"publicationTimestamp": 1760000000000` |
| `tests/fixtures/payloads/communities_list_empty.json` | nuovo | `{"communities": []}` per il caso limite della lista vuota |
| `tests/contract/test_models.py` | modificato | 09-C01: `TestSwaggerAlignment09` con `assert_superset` su `GetPostDetailResponseDTO`, `InputPostAttachmentDTO1`, `CustomFieldValidationErrorDTO`, `LicenseDTO` e controllo esplicito che i cinque campi siano in `model_fields` e nelle `properties` del pinnato; smoke di `Post.from_dict` sulla fixture aggiornata (`draft`, `publication_timestamp`); `TestListCommunities` resta la garanzia sulla risposta di `view-post` |
| `tests/unit/test_facade_communities.py` | modificato | `TestViewPostCapabilityLevel`: enum, stringhe in ogni maiuscola, valori non validi → `ValueError` (09-C03, 09-C04) |
| `tests/unit/test_api_communities.py` | modificato | 09-C02 (nessuna query, risultato `CommunityList`), 09-C03 (`route.calls[0].request.url.params["viewPostCapabilityLevel"]` per enum e stringhe), 09-C04 (`route.called is False`), 09-C05 (`403` → `PermissionError`, `route.call_count == 1`), 09-C17 (`httpx.TimeoutException` → `TransportError`, una chiamata) |
| `tests/unit/test_cli_communities.py` | modificato | 09-C06 (snapshot tabella senza e con `--level public`, json, `--full`, `--fields id`, `--export` csv in `tmp_path`, fixture vuota), 09-C07 (`--level privato` → exit `2` e `route.called is False`; `403` → exit `4`); 09-C13: `TestCommunitiesDetailsBulk` (tabella e json, corpo con `communityIds`), `TestCommunitiesPostDefinitions` (tabella, json, `--full`, `--fields`, `--export`, `--quiet`), rami `InteractaError` di `list`, `details`, `post-definition`, `details-bulk`, `post-definitions` (`404` → exit `5`) |
| `tests/unit/test_facade_posts.py` | modificato | 09-C08: `draft`/`publication_timestamp` dalla fixture e `None` senza i campi |
| `tests/unit/test_cli_posts.py`, `tests/unit/test_cli_full_fields.py` | modificati | 09-C09: snapshot di `posts get` aggiornati (tabella e json con le due colonne), `--fields draft,publication_ts`, `--full` contiene `draft` e `publicationTimestamp` |
| `tests/unit/test_facade_attachments.py` | modificato | 09-C10, 09-C11: `UploadedAttachment(..., downloadable=False/True/None)` e i dict di `as_write_input`/`as_version_of` |
| `tests/unit/test_api_attachments.py` | modificato | 09-C10: `upload(file, downloadable=False)` fa le stesse due richieste di oggi (stesso form multipart) e restituisce `downloadable is False`; 09-C11: senza kwarg `downloadable is None` |
| `tests/unit/test_api_posts_write.py`, `tests/unit/test_api_posts_event.py` | modificati | 09-C12: `create(attachments=[uploaded_non_scaricabile])`, `edit_attachments(add=[…])`, `create_event(attachments=[…])` → la voce degli allegati nel corpo ha `"downloadable": false` e le altre chiavi invariate |
| `tests/integration/test_communities_integration.py` | modificato | 09-C15: `test_list_by_view_post_capability` (senza livello e con i tre livelli; ogni elemento ha `id`; `print("[09-T] no level → n communities")`) |
| `tests/integration/test_attachments_integration.py` | modificato | 09-C16: nel `test_full_cycle` `upload(first, downloadable=False)`; dopo la creazione `detail = client.posts.get(post_id)` con asserzioni su `draft in (False, None)` e `publication_timestamp` `int` o `None` (stampa `[09-T]`); `attached[0].downloadable is False`; resto invariato, `finally` con `delete` già presente |
| `docs/api/communities.md` | modificato | 09-C14: `list_by_view_post_capability` nei `members`; sezione "Communities by post-view capability" con esempio Python, l'enum e cosa risponde il tenant senza livello (dal task sul tenant); `::: …ViewPostCapabilityLevel` tra le façade |
| `docs/api/posts.md` | modificato | 09-C14: nota su `draft` e `publication_timestamp` nel dettaglio (sezione di lettura o "Facade Reference") |
| `docs/api/attachments.md` | modificato | 09-C14: in "Uploading files" il kwarg `downloadable`, i DTO che lo prevedono (post custom ed evento) e cosa fa il server su commenti e task (dal task sul tenant) |
| `docs/cli.md` | modificato | 09-C14: `communities list-by-view-post` dopo `communities list`; `posts get` cita le colonne `draft` e `publication_ts` |
| `tests/unit/test_docs_snippets.py` | modificato | `test_swagger_alignment_pages` con marker 09-C14: `list-by-view-post` e `--level` in `cli.md`; `list_by_view_post_capability` e `ViewPostCapabilityLevel` in `api/communities.md`; `downloadable` in `api/attachments.md`; `publication_timestamp` in `api/posts.md` |
| `specs/prd.md` | modificato (task di chiusura) | RF-007a, RF-006b, RF-024b dal provvisorio al definitivo; RF-021c e §6 aggiornati per `downloadable`; riga nella storia del documento |
| `README.md`, `docs/index.md` | invariati | nessun gruppo nuovo né cambio di scope (decisione della spec) |

## Modello dati e migrazioni

Nessuna: solo i modelli generati, rigenerati dallo swagger. Le façade leggono i campi nuovi come
opzionali; nessuna fixture esistente smette di validare (i campi sono tutti facoltativi).

## Flussi

```
list_by_view_post_capability(level)
  level is None  → params = {}                           → GET …/view-post
  level dato     → ViewPostCapabilityLevel(level)         (ValueError qui, nessuna richiesta)
                 → params = {"viewPostCapabilityLevel": "PRIVATE"|"PUBLIC"|"ALL"}
                 → GET …/view-post?viewPostCapabilityLevel=…
  200 → CommunityList.from_dict(body)
  403 → transport._map_error → PermissionError (una sola richiesta)
  timeout → TransportError (una sola richiesta)

CLI communities list-by-view-post [--level private|public|all]
  Typer valida --level (scelta non valida → usage error, exit 2, nessun client)
  → client.communities.list_by_view_post_capability(...)
  → render_output(items, {"id", "name"}, …)   exit 0
  → InteractaError → handle_error → exit 4 (403) / 5 (404) / …

upload(file, downloadable=False)
  request_upload_url() → POST core/storage/upload-new-attachment   (invariato)
  post_multipart(form firmato + file)                               (invariato)
  → UploadedAttachment(ticket, name, mime_type, downloadable=False)
  posts.create(attachments=[uploaded]) → build_write_body → as_write_input()
    → {"name", "contentRef", "downloadable": false} nel corpo
```

## Interfaccia

- CLI, testi in inglese (eccezione della sezione Lingua): `communities list-by-view-post` con
  `--level [private|public|all]` ("Post-view capability level; omitted, the server decides.");
  tabella `Communities` con `id`, `name`; stessi exit code del resto della CLI.
- `posts get`: colonne `draft` e `publication_ts` in coda alla tabella curata, prima di `web_url`.
- Libreria: `client.communities.list_by_view_post_capability(level=None)`,
  `ViewPostCapabilityLevel`, `Post.draft`, `Post.publication_timestamp`,
  `client.attachments.upload(..., downloadable=None)`, `UploadedAttachment.downloadable`.
- Nessun permesso nuovo: `403` del server mappato come per ogni lettura.

## Configurazione

Nessuna variabile nuova. Gli integration test usano `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` e le
variabili base già in `.env.example`.

## Sicurezza e dati personali

- Nessun log nuovo; il transport redige come oggi. L'URL di `view-post` non porta segreti.
- Il flag `downloadable` è un booleano nel corpo delle scritture già coperte dalla spec 03;
  nessun contenuto di file in log (RNF-011, invariato).
- Nessun retry: ogni metodo fa una richiesta e lascia salire l'eccezione (regola non negoziabile,
  verificata da 09-C05 e 09-C17).
- Lo swagger scaricato è un documento pubblico del tenant cert, senza credenziali; resta in
  `tests/fixtures/`.
- Gli integration test creano e cancellano un post nella community di prova, con `client_uid`
  riconoscibile; nessun dato reale.

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `cli/communities.py` `details-bulk`, `post-definitions` | output tabella/json, corpo inviato, `--full`/`--fields`/`--export`, rami di errore (oggi senza test: righe 142-165, 229-276) | `TestCommunitiesDetailsBulk`, `TestCommunitiesPostDefinitions` e i test di errore, scritti e verdi **prima** di toccare il modulo (09-C13) |
| `UploadedAttachment.as_write_input` / `as_version_of` | dict senza `downloadable` quando non indicato | già fissato da `test_facade_attachments.py::test_as_write_input_and_as_version_of`; 09-C11 lo ribadisce |
| `posts get` | colonne curate attuali | già fissato dagli snapshot di `test_cli_posts.py` e `test_cli_full_fields.py`, aggiornati con le due colonne |
| `communities list` | tabella e json | già fissato dagli snapshot di `test_cli_communities.py` |

## Strategia di test

| Criterio | Test previsto | Tipo |
|---|---|---|
| 09-C01 | contract: superset dei quattro DTO e presenza dei cinque campi in `model_fields` e nel pinnato; smoke di `Post` sulla fixture aggiornata; `uv run pytest -m contract` verde | contract |
| 09-C02 | `test_api_communities.py`: `list_by_view_post_capability()` → una `GET` senza query, `CommunityList` con `items_typed` e `.raw` | unitario |
| 09-C03 | `test_api_communities.py`: query `viewPostCapabilityLevel=PRIVATE/PUBLIC/ALL` da enum e da `"private"`, `"Private"`, `"PRIVATE"`; `test_facade_communities.py`: `_missing_` | unitario |
| 09-C04 | `test_api_communities.py`: `"privato"`, `""`, `42` → `ValueError`, `route.called is False` | unitario |
| 09-C05 | `test_api_communities.py`: `403` → `PermissionError`, `call_count == 1` | unitario |
| 09-C06 | `test_cli_communities.py`: snapshot tabella (senza livello, `--level public`, fixture vuota), json, `--full`, `--fields id`, `--export FILE.csv` | unitario (snapshot) |
| 09-C07 | `test_cli_communities.py`: `--level privato` → exit 2 senza richieste; `403` → exit 4 | unitario |
| 09-C08 | test della façade `Post`: fixture con i campi → valori; fixture senza → `None` | unitario |
| 09-C09 | `test_cli_posts.py` / `test_cli_full_fields.py`: snapshot tabella e json di `posts get`; `--fields draft,publication_ts`; `--full` contiene `publicationTimestamp` | unitario (snapshot) |
| 09-C10 | `test_facade_attachments.py` (dict con `downloadable` false/true) e `test_api_attachments.py` (`upload(..., downloadable=False)`: stesse due richieste, `downloadable is False`) | unitario |
| 09-C11 | `test_facade_attachments.py` e `test_api_attachments.py`: senza kwarg, `None` e chiave assente | unitario |
| 09-C12 | `test_api_posts_write.py` (`create`, `edit_attachments`), `test_api_posts_event.py` (`create_event`): voce degli allegati con `"downloadable": false` | unitario |
| 09-C13 | copertura: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing` → `cli/communities.py` ≥ 85 %, totale ≥ 95,40 % | copertura |
| 09-C14 | `test_docs_snippets.py::test_swagger_alignment_pages`; `uv run mkdocs build --strict` | unitario + controllo |
| 09-C15 | `test_communities_integration.py::test_list_by_view_post_capability`, eseguito sul tenant nel task manuale | integrazione |
| 09-C16 | `test_attachments_integration.py::test_full_cycle` esteso, eseguito sul tenant nel task manuale | integrazione |
| 09-C17 | `test_api_communities.py`: `httpx.TimeoutException` → `TransportError`, una chiamata | unitario |
| 09-C18 | `test_generate_models.py` (riordino e formato); confronto AST dei nomi di classe generati prima e dopo la rigenerazione, in T01 | unitario + controllo |

Verifica manuale (dalla spec): un task esegue i due integration test sul tenant, più una sonda in
scratchpad (fuori dal repo) che allega un `UploadedAttachment` con `downloadable=False` a un
commento e a un task del post di prova e registra la risposta del server; l'esito va nella
documentazione (`docs/api/attachments.md`, `docs/api/communities.md`) e nella sezione
`M35` di `PROGRESS.md`.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| `ViewPostCapabilityLevel(str, Enum)` con `_missing_` per le stringhe in qualunque maiuscola | Funzione `coerce_level()` a parte; `Literal["PRIVATE", …]` | L'enum vale da sola come validatore (`ViewPostCapabilityLevel("private")`), come `ParticipationAnswer(2)`; il `.value` è ciò che va in query |
| La conversione del livello avviene nel metodo, prima di `_get` | Lasciare la stringa passare al server | `ValueError` prima della richiesta è un criterio della spec (09-C04) e la regola della libreria |
| `_get(path, params=params or None)` con `build_query_params` | Costruire l'URL a mano | Helper esistente, `None` omesso; `params=None` evita un `?` vuoto |
| Scelta CLI `ViewPostLevelChoice` in minuscolo, `case_sensitive=False`, tradotta nell'enum della libreria | Usare `ViewPostCapabilityLevel` direttamente come tipo di `--level` | Stesso schema di `ParticipationChoice` (spec 08): help con `private|public|all`, errore d'uso gestito da Typer con exit 2 |
| `downloadable` conservato in `UploadedAttachment` e aggiunto ai dict solo se non `None` | Parametro di `as_write_input(downloadable=…)`; mutare il dict nelle API dei post | Il flag è una proprietà del file caricato e viaggia con esso ovunque lo si alleghi; i corpi delle scritture non cambiano altrove |
| Rigenerazione con download (non `--offline`) in un task dedicato, primo della lista | Modificare a mano il pinnato | Il punto della spec è ripinnare lo swagger live; lo script esiste per questo; il diff è idempotente con il generatore in lock |
| Ordine stabile delle definizioni nello script (revisione di T01) | Rinominare i riferimenti a `EventPostDataDTOModel`; alias | Scelta del maintainer: i nomi generati non devono cambiare per un riordino del tenant |
| Test di caratterizzazione sui comandi scoperti prima di toccare `cli/communities.py` | Alzare la copertura solo con il comando nuovo | Il comando nuovo non basta a raggiungere l'85 % (113 righe, 53 scoperte); le righe scoperte sono tutte nei comandi esistenti |

## Rischi

- Il tenant cert potrebbe aver cambiato lo swagger tra la verifica e il task di rigenerazione →
  il task confronta endpoint e schemi prima del commit (stesso script di confronto della
  verifica del 2026-10-13, in scratchpad) e si ferma se compaiono differenze oltre le cinque
  attese: tornerebbe alla spec.
- `view-post` senza livello potrebbe rispondere `400` invece di una lista → il task sul tenant
  lo registra; la libreria non aggiunge un default (decisione della spec), la documentazione lo
  dice e l'integration test, in quel caso, aspetta l'eccezione.
- Il server potrebbe rifiutare `downloadable` su commenti e task (`400`) → nessun impatto sul
  codice (la libreria lo invia solo se chiesto); la documentazione lo dice.
- Gli snapshot di `posts get` cambiano per tutte le varianti → aggiornamento con
  `--snapshot-update` nello stesso task, rivisto a occhio nel diff.
- La copertura del file `cli/communities.py` dipende dai rami di errore (`handle_error`) →
  un test per comando con una risposta `404` mockata li copre tutti.
