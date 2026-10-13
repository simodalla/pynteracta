# 09 – Allineamento allo swagger live

Stato: approvata
Branch: `m35_swagger_align`
Requisiti del PRD: RF-007, RF-006, RF-021c, RF-024, RF-015, RF-019, RNF-003; toccati RF-022
e RF-023 (regola "la libreria invia solo i campi passati"), §6 "Dati scritti sul tenant"
Dipende da: spec 03 (chiusa): scritture dei post custom e `build_write_body`; spec 04 (chiusa):
`attachments.upload`, `UploadedAttachment`, ciclo di upload dell'integration test; spec 08
(chiusa): scritture dei post evento, che accettano gli stessi allegati

## Scopo

Chi usa la libreria lavora con modelli allineati allo swagger del tenant cert di oggi, raggiunge
l'unico endpoint `external_v2` ancora scoperto (le community in cui l'identità autenticata ha
una data capability di visualizzazione dei post) e trova in façade i tre campi nuovi che hanno
valore d'uso: lo stato bozza e il timestamp di pubblicazione nel dettaglio di un post, e la
possibilità di allegare a un post un file non scaricabile. Con questa spec la libreria espone i
76 endpoint su 76 dello swagger pinnato.

## Comportamento attuale

- `tests/fixtures/swagger.json` è lo swagger scaricato dal tenant cert all'ultima rigenerazione
  (`scripts/generate_models.py`). Lo swagger live, confrontato il 2026-10-13, ha gli stessi 76
  endpoint e gli stessi 219 schemi, con cinque campi opzionali in più: `draft` e
  `publicationTimestamp` nel dettaglio del post, `downloadable` nell'allegato in input di un
  post, `externalId` nell'errore di validazione di un campo custom, `subType` nella licenza
  (la descrizione del tipo di licenza aggiunge i valori 4 e 5). I modelli generati non li
  conoscono: le façade con `extra="ignore"` li scartano, quindi oggi non sono raggiungibili
  nemmeno via `.raw`.
- `client.communities.list()` chiama `GET communication/settings/communities` e restituisce
  `CommunityList`; in CLI `communities list` mostra id e nome. L'endpoint
  `GET communication/settings/communities/view-post`, con il parametro di query facoltativo
  `viewPostCapabilityLevel` (`PRIVATE`, `PUBLIC`, `ALL`) e la stessa risposta dell'elenco, non è
  esposto.
- `client.posts.get()` restituisce `Post`, con id, community, titolo, testo, timestamp di
  creazione e ultima modifica, conteggi di commenti e like; `posts get` li mostra in tabella con
  i timestamp resi come epoch in millisecondi (`creation_ts`, `last_modify_ts`).
- `client.attachments.upload(file, *, name, mime_type)` restituisce `UploadedAttachment`, che
  negli allegati delle scritture diventa `{"name", "contentRef"}` (`as_write_input`) o
  `{"attachmentId", "contentRef", "name"}` (`as_version_of`). I dict passati come allegati
  arrivano al server così come sono.
- `cli/communities.py` è coperto al 53 % dagli unit test (linea di partenza).

## Comportamento

### Modelli allineati

I modelli generati vengono rigenerati dallo swagger live, che diventa il nuovo swagger pinnato.
Ogni façade esistente continua a leggere le stesse risposte; i campi nuovi sono raggiungibili
via `.raw` e, dove questa spec lo prevede, in façade. I contract test confermano che i modelli
generati restano un sovrainsieme dello swagger pinnato.

I nomi delle classi generate restano stabili tra una rigenerazione e l'altra: il generatore
assegna i suffissi (`1`, `Model`) alle definizioni omonime nell'ordine in cui le incontra, e lo
swagger live elenca le definizioni in un ordine diverso dal pinnato (che rinominava
`EventPostDataDTOModel` in `EventPostDataDTO1`). Lo script di rigenerazione quindi riscrive il
nuovo swagger con le definizioni nell'ordine del pinnato precedente, accodando quelle nuove: il
contenuto resta quello del tenant, cambia solo l'ordine delle chiavi.

### Community per capability di visualizzazione dei post

Da Python, `client.communities.list_by_view_post_capability(level=None)` restituisce le
community in cui l'identità autenticata ha la capability indicata, nella stessa forma di
`list()` (`CommunityList`, con `items_typed` e `.raw`). Il livello è un
`ViewPostCapabilityLevel` (`PRIVATE`, `PUBLIC`, `ALL`) oppure una stringa con uno di quei nomi,
senza distinzione di maiuscole; un valore fuori dall'enum è rifiutato prima di qualunque
richiesta. Senza livello la richiesta parte senza parametro di query e la risposta è quella che
il server decide: la documentazione dice cosa risponde il tenant di prova.

Dalla CLI, `communities list-by-view-post [--level private|public|all]` mostra id e nome come
`communities list`, e compone con `--output`, `--full`, `--fields` ed `--export`. Un `--level`
fuori dalle tre scelte è un errore d'uso: exit code `2`, nessuna richiesta.

Un `403` del server è un `PermissionError` (exit code `4` in CLI), come per ogni lettura; non
si riprova.

### Stato bozza e timestamp di pubblicazione del post

`Post.draft` (`bool | None`) e `Post.publication_timestamp` (`int | None`, epoch in
millisecondi) leggono i campi nuovi del dettaglio; sono `None` quando il server non li manda.
`posts get` li mostra nella tabella curata come `draft` e `publication_ts`, quest'ultimo reso
come gli altri timestamp; `--fields` li seleziona per nome.

### Allegati non scaricabili

`client.attachments.upload(file, *, name, mime_type, downloadable=None)` accetta il flag nuovo.
`UploadedAttachment.downloadable` lo ricorda; `as_write_input()` e `as_version_of()` aggiungono
`"downloadable"` solo quando è stato indicato, altrimenti il corpo resta quello di oggi e vale
il default del server (`true`). Il flag ha effetto negli allegati dei post custom ed evento
(creazione, modifica, copia, `edit_attachments`), gli unici il cui DTO di input lo prevede; la
documentazione lo dice e dice cosa fa il server quando lo riceve su un commento o un task
(verificato sul tenant). In CLI non c'è un flag: chi lo vuole lo passa negli allegati di
`--json`, che già arrivano al server così come sono.

### Copertura della CLI delle community

Il comando nuovo tocca `cli/communities.py`, che la configurazione SDD vuole almeno all'85 %
per i file toccati: la spec porta quel file sopra soglia con unit test sui comandi esistenti.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 09-C01 | Quando si esegue `scripts/generate_models.py` (con download), `tests/fixtures/swagger.json` contiene `draft` e `publicationTimestamp` in `GetPostDetailResponseDTO`, `downloadable` in `InputPostAttachmentDTO`, `externalId` in `CustomFieldValidationErrorDTO` e `subType` in `LicenseDTO`; i modelli generati li espongono; `uv run pytest -m contract` è verde. | RNF-003 |
| 09-C02 | Quando si chiama `client.communities.list_by_view_post_capability()` senza livello, parte una sola `GET …/communication/settings/communities/view-post` senza parametri di query e, con una risposta `ListCommunitiesResponseDTO`, il risultato è un `CommunityList` con `items_typed` (id e nome) e `.raw`. | RF-007 |
| 09-C03 | Quando si chiama `list_by_view_post_capability(ViewPostCapabilityLevel.PRIVATE)`, oppure con `"private"`, `"Private"` o `"PRIVATE"`, la richiesta ha la query `viewPostCapabilityLevel=PRIVATE`; lo stesso vale per `PUBLIC` e `ALL`. | RF-007 |
| 09-C04 | Quando il livello non è uno dei tre (`"privato"`, `""`, `42`), `list_by_view_post_capability` solleva `ValueError` e nessuna richiesta parte. | RF-007 |
| 09-C05 | Quando il server risponde `403`, `list_by_view_post_capability` solleva `PermissionError` dopo una sola richiesta. | RF-019 |
| 09-C06 | Quando si esegue `communities list-by-view-post`, senza o con `--level public`, la tabella ha le colonne `id` e `name` e il titolo `Communities`; `--output json|yaml`, `--full`, `--fields id`, `--export FILE` producono gli stessi dati di `communities list` (snapshot). | RF-007, RF-015 |
| 09-C07 | Quando si esegue `communities list-by-view-post --level privato`, il comando esce con codice `2` senza fare richieste; con un `403` del server esce con `4`. | RF-007, RF-019 |
| 09-C08 | Quando il dettaglio del post ha `draft: true` e `publicationTimestamp: 1760000000000`, `client.posts.get(...)` espone `draft == True` e `publication_timestamp == 1760000000000`; senza quei campi entrambi sono `None`. | RF-006 |
| 09-C09 | Quando si esegue `posts get ID`, la tabella curata ha le colonne `draft` e `publication_ts`, con il timestamp reso come `creation_ts`; `--fields draft,publication_ts` le seleziona; `--full` mostra anche i campi grezzi nuovi (snapshot). | RF-006, RF-015 |
| 09-C10 | Quando si chiama `client.attachments.upload(file, downloadable=False)`, le due richieste dell'upload sono quelle di oggi (il flag non va allo storage), `UploadedAttachment.downloadable` è `False`, `as_write_input()` è `{"name": …, "contentRef": …, "downloadable": false}` e `as_version_of(5)` è `{"attachmentId": 5, "contentRef": …, "name": …, "downloadable": false}`; con `downloadable=True` i dict hanno `"downloadable": true`. | RF-024 |
| 09-C11 | Quando si chiama `upload(file)` senza `downloadable`, `UploadedAttachment.downloadable` è `None` e `as_write_input()` e `as_version_of()` non contengono la chiave `downloadable` (corpo identico a oggi). | RF-024 |
| 09-C12 | Quando un `UploadedAttachment` con `downloadable=False` è passato a `posts.create(attachments=[…])`, `posts.edit_attachments(add=[…])` e `posts.create_event(attachments=[…])`, il corpo della richiesta contiene `"downloadable": false` in quella voce degli allegati e nient'altro cambia. | RF-021c, RF-024 |
| 09-C13 | `uv run pytest -m "not integration and not contract" --cov` riporta `src/pynteracta/cli/communities.py` ad almeno l'85 % e la copertura totale non scende sotto la linea di partenza. | RNF-006 |
| 09-C14 | `docs/cli.md` documenta `communities list-by-view-post` e le colonne nuove di `posts get`; `docs/api/communities.md`, `docs/api/posts.md` e `docs/api/attachments.md` documentano metodo, enum, proprietà e flag nuovi, con cosa risponde il tenant senza livello e con `downloadable` su commenti e task; `uv run mkdocs build --strict` è verde e il test dei frammenti dei docs li trova. | RF-007, RF-006, RF-024 |
| 09-C15 | L'integration test delle community chiama `list_by_view_post_capability` senza livello e con `PRIVATE`, `PUBLIC` e `ALL`: ogni risposta è un `CommunityList` i cui elementi hanno un id, e quella senza livello è registrata nel log del test; sul tenant di prova è verde. | RF-007 |
| 09-C16 | Il ciclo di upload dell'integration test carica il primo file con `downloadable=False`, crea il post, rilegge il dettaglio e verifica `draft` è `False` o `None` e `publication_timestamp` è un intero (o `None` se il tenant non lo manda, registrato nel log), e che l'allegato letto abbia `downloadable == False`; sul tenant di prova è verde e il post è eliminato alla fine, anche se un passo fallisce. | RF-006, RF-024 |
| 09-C17 | Quando si chiama `list_by_view_post_capability` e la richiesta va in timeout, la libreria solleva `TransportError` dopo una sola richiesta. | RF-019, RNF-008 |
| 09-C18 | Quando lo script di rigenerazione riceve uno swagger con le stesse definizioni del pinnato in ordine diverso più una definizione nuova, il pinnato scritto ha le definizioni nell'ordine del precedente con la nuova in coda, gli stessi valori dello swagger ricevuto e lo stesso formato JSON compatto; senza pinnato precedente l'ordine è quello ricevuto. Dopo la rigenerazione del 2026-10-13 i modelli generati hanno gli stessi nomi di classe di prima (nessuna rinominata) e cambiano solo `GetPostDetailResponseDTO`, `InputPostAttachmentDTO1`, `CustomFieldValidationErrorDTO`, `LicenseDTO`. | RNF-003 |

## Casi limite

- Livello passato come enum, come stringa in qualunque maiuscola, o omesso → 09-C02, 09-C03.
- Livello non valido, stringa vuota, tipo sbagliato → `ValueError` prima della richiesta, 09-C04;
  in CLI exit `2`, 09-C07.
- Server che risponde una lista vuota → `CommunityList` con `items_typed == []`, tabella vuota
  (coperto dallo snapshot di 09-C06 con fixture vuota).
- `403` o timeout → `PermissionError`, `TransportError`, una sola richiesta, 09-C05, 09-C17.
- Dettaglio del post di un tenant che non manda ancora i campi nuovi → `None`, 09-C08.
- `downloadable` non indicato → chiave assente, corpo identico a oggi, 09-C11; indicato `True` →
  inviato esplicitamente, 09-C10.
- `UploadedAttachment` con `downloadable` passato a un commento o a un task → la libreria lo
  invia come per i post; cosa fa il server è verificato a mano e documentato (verifica manuale).
- Swagger live irraggiungibile al momento della rigenerazione → `scripts/generate_models.py`
  esce con errore e il pinnato resta quello di oggi (comportamento esistente dello script).

## Dati personali e segreti

La lettura nuova restituisce id, nome e descrizione delle community, già restituiti da
`communities list`; vanno al chiamante e nell'output della CLI, non nei log applicativi (solo
metodo, URL redatto e stato). I campi nuovi del post (stato bozza, timestamp) non sono dati
personali. Il flag `downloadable` viaggia nel corpo delle scritture già previste dalla spec 03,
senza contenuto del file (RNF-011). Nessun segreto nuovo; lo swagger scaricato non contiene
credenziali. Gli integration test usano la community e il post di prova già configurati
(`PYNTERACTA_TEST_WRITE_COMMUNITY_ID`) e cancellano il post creato.

## Requisiti nuovi

- RF-007a (provvisorio). Community per capability di visualizzazione dei post:
  `communities.list_by_view_post_capability(level=None)` con `ViewPostCapabilityLevel`
  (`PRIVATE`, `PUBLIC`, `ALL`) o stringa senza distinzione di maiuscole, livello omesso non
  inviato; in CLI `communities list-by-view-post [--level]`. Con questa spec tutti i 76 endpoint
  dello swagger pinnato sono esposti.
- RF-006b (provvisorio). Il dettaglio del post espone `draft` e `publication_timestamp`, mostrati
  da `posts get`.
- RF-024b (provvisorio). `attachments.upload(..., downloadable=…)`: `UploadedAttachment` lo
  invia negli allegati dei post solo se indicato; in CLI solo tramite `--json`.

## Fuori ambito

- Façade per `subType` della licenza e per `externalId` dell'errore di validazione dei campi
  custom: restano via `.raw`.
- `downloadable` sugli allegati di commenti e task: i loro DTO di input non lo prevedono.
- Un flag CLI per `downloadable` (`--attach` resta scaricabile, `--json` lo permette).
- Il kwarg `calculate_total_items_count` su `attachments.list_for_post` e le altre letture con lo
  stesso vuoto: follow-up aperto, spec a parte.
- Allineamento periodico allo swagger di produzione: il tenant cert resta la fonte (decisione
  legacy M3).

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Perimetro completo (rigenerazione, `view-post`, campi del post, `downloadable`) in una minor, 0.15.0 | Solo rigenerazione e `view-post`; solo rigenerazione come patch | I tre campi hanno valore d'uso e sono piccoli; una spec sola li porta con la rigenerazione che li rende visibili |
| Metodo e comando dedicati per `view-post`, senza variante `_raw` | Opzione su `communities.list()` / `communities list --view-post-capability` | Un metodo, una forma: un'opzione cambierebbe endpoint sotto il cofano; non c'è DTO di richiesta (una `GET` con un parametro di query), come per `list()` |
| Livello omesso non inviato | Default `ALL` deciso dalla libreria | La libreria non aggiunge nulla da sola; il tenant decide e la documentazione lo riporta |
| Livello come enum o stringa senza distinzione di maiuscole, `ValueError` prima della richiesta | Solo enum | Comodo per script e agenti, come `ParticipationAnswer` nella spec 08; il valore inviato è sempre il nome dell'enum |
| `downloadable` su `upload` e `UploadedAttachment`, CLI via `--json` | Flag CLI `--attach-not-downloadable`; solo dict/`--json` senza kwarg | Caso raro: il kwarg copre la libreria senza un'opzione CLI in più; i dict passavano già |
| Verifica sul tenant con integration test estesi (lettura `view-post`, ciclo di upload esistente) | Solo `view-post` in integration; solo unit con fixture | Nelle spec precedenti il tenant ha smentito lo swagger ogni volta; il ciclo di upload esiste già e cancella ciò che crea |
| Copertura di `cli/communities.py` portata sopra l'85 % con unit test sui comandi esistenti | Lasciarla al 53 % | Regola della configurazione SDD sui file toccati |
| Ordine stabile delle definizioni nello script di rigenerazione (revisione del 2026-10-13, in T01) | Accettare la rinomina `EventPostDataDTOModel` → `EventPostDataDTO1` aggiornando i riferimenti; rinomina più alias | I nomi generati dipendono dall'ordine dello swagger: senza ordine stabile ogni rigenerazione può rinominare classi usate dalle façade e raggiungibili via `.raw` |

## Verifica manuale

- 09-C15 e 09-C16 sono test automatici opt-in (`-m integration`): un task della spec li esegue
  sul tenant di prova e registra cosa risponde il server senza livello, se manda `draft` e
  `publicationTimestamp`, e se accetta, ignora o rifiuta `downloadable` su un commento e su un
  task (una sonda in sola scrittura nella community di prova, con pulizia). Non si può fare in
  unit test: è il comportamento del server a essere in questione.

## Revisioni

- 2026-10-13, durante T01: la rigenerazione dallo swagger live rinominava `EventPostDataDTOModel`
  in `EventPostDataDTO1` (definizioni in ordine diverso). Scelta del maintainer: ordine stabile
  nello script di rigenerazione; nuovo criterio 09-C18, coperto da T01.

## Domande aperte

Nessuna.
