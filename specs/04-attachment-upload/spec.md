# 04 – Upload degli allegati

Stato: approvata
Branch: `m30_attachment_upload`
Requisiti del PRD: RF-024, RF-021c, RNF-001, RNF-009; toccati RF-009, RF-015, RF-019, RF-021,
RF-022, RNF-003
Dipende da: spec 02 (chiusa): `build_write_body`, `load_json_body`, `merge_body`,
`validate_body`; spec 03 (chiusa): `edit_attachments`, `PostAttachmentsWriteResult`, i comandi
`posts create|comment|edit|copy`

Terza spec della superficie di scrittura aperta da
[ADR 0001](../adr/0001-apertura-della-superficie-di-scrittura.md): l'upload di nuovi file,
propedeutico agli allegati di post, commenti e task, e i comandi della CLI che la spec 03 aveva
rimandato (RF-021c).

## Scopo

Chi scrive automazioni con la libreria, e chi usa la CLI, può caricare un file su Interacta e
allegarlo a un post, a un commento o a un task, in un solo passo dal suo punto di vista: la
libreria chiede l'URL temporaneo di storage, invia il file e restituisce il riferimento che i
metodi di scrittura accettano. Le credenziali temporanee dello storage non compaiono mai in log,
audit log, hook o messaggi di errore; nessun caricamento viene ripetuto da solo.

## Comportamento attuale

La risorsa allegati è di sola lettura (RF-009): elenco per post, dettaglio, visibilità. I metodi
di scrittura di post (`create`, `edit`, `copy`, `add_comment`, `edit_attachments`) e di task
(`create`, `edit`) accettano allegati solo come riferimenti già noti al server (`attachmentId`,
oppure `name` + `contentRef`): non c'è modo, nella libreria, di ottenere un `contentRef` nuovo.
In CLI gli allegati si passano solo dentro `--json`; `posts edit-attachments` non esiste
(rimandato dalla spec 03). Il transport costruisce ogni URL dalla base dell'API e inietta sempre
il token Interacta: non sa inviare una richiesta a un host esterno. La redazione (RNF-001) copre
JWT, header sensibili, cookie e le chiavi `token|password|secret|privatekey|assertion|jwt` dei
body, non le firme di una policy di storage né i parametri di query di un URL firmato.

### Il meccanismo, verificato sul tenant il 2026-10-10

`POST core/storage/upload-new-attachment`, senza corpo, risponde con `contentRef`, `uploadUrl`,
`uploadMultipartRequestBodyParams` e `temporaryDownloadUrl`. L'`uploadUrl` è il bucket
temporaneo di Google Cloud Storage del tenant, senza query; i parametri sono i campi di una
**policy firmata** (`GoogleAccessId`, `key` = `temporary-uploads/<contentRef>`, `policy`,
`signature`). Il file si carica con un **form multipart `POST`** all'`uploadUrl`, con i quattro
campi seguiti dal campo `file`; lo storage risponde `204`. Un `PUT` dello stesso file è rifiutato
(`400 MissingSecurityHeader`). La policy scade dopo circa due ore, ammette da 0 a 2 GiB e non
vincola il content-type. Il `temporaryDownloadUrl` è un URL firmato con `Signature` in query, da
cui il file caricato si rilegge. L'ADR 0001 parlava, in modo descrittivo, di "`PUT` del file":
questa spec registra il meccanismo reale e il task di chiusura precisa RF-024.

## Comportamento

### Libreria

Tutto sta su `client.attachments`, con la forma delle letture: kwargs espliciti, façade con
`.raw`, errori tipizzati. Ogni passo fa **una sola richiesta**; un errore risale al chiamante,
mai un nuovo tentativo (RNF-009).

- **Caricare**: `upload(file, *, name=None, mime_type=None)` → `UploadedAttachment` con
  `content_ref`, `name`, `mime_type`, `temporary_download_url` e `.raw` (la risposta di
  `upload-new-attachment`). `file` è un `Path` o una stringa di percorso, dei `bytes` o un oggetto
  file binario già aperto. Da un percorso il nome è quello del file e il MIME è dedotto
  dall'estensione (`application/octet-stream` se ignota); il file viene letto in streaming, mai
  tutto in memoria. Con `bytes` o file-like `name` è obbligatorio: senza, `ValueError` prima di
  qualunque richiesta. `mime_type` esplicito prevale sempre. Un percorso inesistente o una
  cartella producono l'errore del sistema (`FileNotFoundError`, `IsADirectoryError`) prima di
  chiedere l'URL, così da non consumare una policy. Un file vuoto è ammesso.
- **I due passi, uno alla volta**: `request_upload_url()` → `UploadTicket` con `content_ref`,
  `upload_url`, `form_params`, `temporary_download_url`, `.raw`, per chi vuole caricare da sé (per
  esempio con un altro strumento). `upload` usa lo stesso ticket.
- **La richiesta allo storage** non porta il token Interacta; passa dagli hook e dall'audit log come una richiesta
  `POST` all'`upload_url`, con lo stato della risposta, **mai** con il contenuto del file né con i
  campi del form, neppure con `audit_log_bodies`. Il timeout configurato (`timeout_seconds`) vale
  per ogni operazione di rete dell'upload; nessuna configurazione nuova.
- **Errori**: una risposta non 2xx dello storage (policy scaduta, dimensione fuori limite,
  bucket negato) → `UploadError`, nuova sottoclasse di `InteractaError`, con `status_code`,
  `request_url` (redatto), `response_body` (il corpo XML dello storage com'è) e `request_id`
  assente. Timeout ed errori di rete, in entrambi i passi → `TransportError`, esito sconosciuto.
  Gli errori del primo passo sono quelli di ogni chiamata Interacta.
- **Usare il risultato**: `UploadedAttachment` si passa direttamente dove i metodi di scrittura
  accettano un riferimento ad allegato (`attachments` di `posts.create`, `posts.add_comment`,
  `tasks.create`; `add_attachments` di `posts.edit`, `posts.copy`, `tasks.edit`; `add` di
  `posts.edit_attachments`): la libreria lo traduce in `{name, contentRef}`. Per una nuova
  versione di un allegato esistente, `as_version_of(attachment_id)` dà
  `{attachmentId, contentRef, name}`, da passare a `update_attachments` o a `update`. I dict e i
  DTO già ammessi restano ammessi, anche mescolati.
- **Redazione** (RNF-001, estesa): ai nomi di chiave sensibili dei body si aggiungono
  `signature` e `policy`; negli URL i parametri di query il cui nome contiene
  `signature|token|secret|password|key` perdono il valore. Vale ovunque la redazione già vale:
  log, audit log, hook, `request_url` delle eccezioni. Così la risposta di
  `upload-new-attachment` nell'audit log con i body, e i link temporanei firmati che le letture
  degli allegati già restituiscono, non portano più la firma in chiaro.

### CLI

I testi (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando che
carica file si ferma **al primo errore** di caricamento: nessuna richiesta di scrittura parte
verso Interacta, i file già caricati nello storage temporaneo scadono da soli, il messaggio dice
quale file è fallito. `UploadError` esce con il nuovo exit code `11`; timeout e rete con `7`.

- `attachments upload PATH [--name N]`: carica il file e mostra con `render_output` la tabella
  `name`, `content_ref`, `temporary_download_url`; `--output json` e `--full` danno il DTO
  intero, `--fields` e `--export` compongono. Serve a chi costruisce `--json` da sé.
- `--attach PATH`, ripetibile, su `posts create`, `posts comment`, `tasks create` (campo
  `attachments`) e su `posts edit`, `posts copy`, `tasks edit` (campo `addAttachments`): ogni
  file è caricato nell'ordine dato, con il suo nome; i riferimenti si **accodano** a quelli già
  presenti in `--json`. La richiesta di scrittura parte solo dopo l'ultimo upload riuscito.
- `posts edit-attachments POST_ID [--add PATH]… [--remove ID]… [--update ID=PATH]…`: carica i
  file di `--add` e di `--update`, poi una sola `PUT edit-post-attachments` con
  `addAttachments`, `updateAttachments` (`attachmentId`, `contentRef`, nome del file) e
  `removeAttachmentIds`; tabella `post_id`, `added` (id e nome), `updated` (id e nome),
  `removed_ids`; `--output json` e `--full` danno la risposta intera. Senza nessuna delle tre
  opzioni il comando rifiuta con exit code `2` e non invia nulla; `--update` senza `=` o con un
  id non numerico è un errore d'uso. Il comando non porta `occToken`, come `edit-watchers`.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 04-C01 | Quando si chiama `client.attachments.upload(Path("nota.txt"))`, parte una sola `POST …/core/storage/upload-new-attachment` senza corpo e poi una sola `POST` multipart all'`uploadUrl` della risposta, con i campi `GoogleAccessId`, `key`, `policy`, `signature` seguiti dal campo `file` (nome `nota.txt`, content-type `text/plain`, i byte del file), senza header `Authorization`; il risultato ha `content_ref`, `name == "nota.txt"`, `mime_type == "text/plain"`, `temporary_download_url` e `.raw` dalla risposta. Un file di 0 byte è caricato allo stesso modo. | RF-024 |
| 04-C02 | Quando si chiama `upload(b"...", name="dati.bin")` o `upload(fileobj, name="dati.bin")`, il campo `file` ha quel nome e content-type `application/octet-stream`; con `mime_type="image/png"` il content-type è `image/png` anche se l'estensione dice altro; `upload(b"...")` senza `name` solleva `ValueError` senza che parta alcuna richiesta. | RF-024 |
| 04-C03 | Quando il percorso non esiste o è una cartella, `upload` solleva `FileNotFoundError` o `IsADirectoryError` senza che parta alcuna richiesta. | RF-024 |
| 04-C04 | Quando lo storage risponde `400` con un corpo XML, `upload` solleva `UploadError` (sottoclasse di `InteractaError`) con `status_code == 400`, `request_url` uguale all'`uploadUrl`, `response_body` con il corpo com'è; nessuna seconda richiesta parte, né allo storage né a `upload-new-attachment`. | RF-024, RF-019, RNF-009 |
| 04-C05 | Quando la richiesta allo storage va in timeout o fallisce per rete, `upload` solleva `TransportError` dopo un solo tentativo. | RF-024, RNF-009 |
| 04-C06 | Quando si chiama `request_upload_url()`, parte una sola `POST upload-new-attachment` e il risultato `UploadTicket` ha `content_ref`, `upload_url`, `form_params` (il dict dei quattro campi), `temporary_download_url` e `.raw`. | RF-024 |
| 04-C07 | Quando un `UploadedAttachment` con `content_ref="abc"` e `name="nota.txt"` è passato in `attachments` a `posts.create`, `posts.add_comment`, `tasks.create`, in `add_attachments` a `posts.edit`, `posts.copy`, `tasks.edit` e in `add` a `posts.edit_attachments`, il corpo inviato contiene `{"name": "nota.txt", "contentRef": "abc"}` in quella lista, accanto a eventuali dict già ammessi; `as_version_of(7)` restituisce `{"attachmentId": 7, "contentRef": "abc", "name": "nota.txt"}`. | RF-024, RF-021, RF-022 |
| 04-C08 | Quando un body contiene le chiavi `signature` o `policy` (anche annidate), la redazione le sostituisce con `***REDACTED***`; quando un URL contiene `?GoogleAccessId=…&Expires=…&Signature=…`, il valore di `Signature` è sostituito e gli altri restano; la stessa redazione si vede nel log, nell'audit log, negli hook e in `request_url` di un'eccezione. | RNF-001 |
| 04-C09 | Quando `upload` è eseguito con hook e audit log con i body attivi, l'hook `on_request` riceve una `RequestInfo` con `method == "POST"`, `url` uguale all'`uploadUrl` e `body is None`; `on_response` riceve `status_code == 204`; nell'audit log compaiono URL e stato e non compaiono né i byte del file né i campi del form. | RNF-001, RF-017, RF-018 |
| 04-C10 | Quando si esegue `attachments upload nota.txt`, la tabella ha `name`, `content_ref`, `temporary_download_url`; `--name altro.txt` invia quel nome; `--output json` e `--full` restituiscono il DTO intero; `--fields` ed `--export` compongono. | RF-024, RF-015 |
| 04-C11 | Quando si esegue `posts create 79 --title T --attach a.txt --attach b.pdf --json body.json` con `attachments: [{"attachmentId": 3}]` nel JSON, partono due upload nell'ordine dato e poi una sola `POST create-post` con `attachments: [{"attachmentId": 3}, {"name": "a.txt", "contentRef": …}, {"name": "b.pdf", "contentRef": …}]`. | RF-024, RF-021, RF-015 |
| 04-C12 | Quando si passa `--attach a.txt` a `posts comment` e `tasks create`, il corpo ha `attachments: [{"name": "a.txt", "contentRef": …}]`; a `posts edit`, `posts copy` e `tasks edit` il corpo ha `addAttachments` con lo stesso elemento, dopo l'upload. | RF-024, RF-021, RF-022 |
| 04-C13 | Quando si esegue `posts edit-attachments 21269 --add a.txt --update 5=b.pdf --remove 9`, partono due upload e poi una sola `PUT …/edit-post-attachments/21269` con `addAttachments: [{"name": "a.txt", "contentRef": …}]`, `updateAttachments: [{"attachmentId": 5, "contentRef": …, "name": "b.pdf"}]`, `removeAttachmentIds: [9]`; la tabella mostra `post_id`, `added`, `updated`, `removed_ids`; senza opzioni il comando esce con `2` e nessuna richiesta parte; `--update b.pdf` esce con errore d'uso. | RF-024, RF-021c, RF-015 |
| 04-C14 | Quando il secondo di due `--attach` riceve `400` dallo storage, il comando esce con `11`, il messaggio di errore contiene il nome del file e nessuna richiesta di scrittura parte verso Interacta. | RF-024, RF-015a, RNF-009 |
| 04-C15 | Quando un comando riceve `UploadError`, l'exit code è `11`; quando riceve `TransportError` durante l'upload, è `7`. | RF-019 |
| 04-C16 | I contract test dimostrano che `GetTemporaryImageUploadUrlBaseResponseDTO` copre tutte le proprietà del swagger pinnato e che la fixture JSON di risposta si legge in `UploadTicket` e `UploadedAttachment`. | RF-024, RNF-003 |
| 04-C17 | `uv run mkdocs build --strict` passa con le pagine aggiornate (`api/attachments.md`, `api/posts.md`, `api/tasks.md`, `cli.md`, `logging.md`, `testing.md`), e la home del sito e il README dicono che l'upload degli allegati c'è, senza numeri di versione. | RF-024 |
| 04-C18 | L'integration test opt-in, nella community di prova, carica un file generato, crea un post con l'allegato, lo trova nell'elenco degli allegati, ne carica una nuova versione con `edit_attachments`, lo rimuove e cancella il post; con le variabili d'ambiente assenti è saltato. | RF-024, RF-021 |

## Casi limite

- Percorso inesistente, cartella, `bytes` senza `name` → errore prima di ogni richiesta
  (04-C02, 04-C03).
- Storage non 2xx → `UploadError`, un solo tentativo (04-C04); timeout → `TransportError`
  (04-C05).
- File vuoto → caricato (la policy ammette 0 byte) (04-C01).
- Estensione ignota → `application/octet-stream` (04-C02).
- Due `--attach`, il secondo fallisce → exit `11`, nessuna scrittura a Interacta (04-C14).
- `posts edit-attachments` senza opzioni → exit `2`, nessuna richiesta (04-C13).
- `--attach` insieme a `--json` con `attachments` → i due elenchi si accodano (04-C11).
- `409` non previsto: gli endpoint di questa spec non portano `occToken`.

## Dati personali e segreti

- **Cosa passa**: il contenuto del file scelto dal chiamante (che può contenere dati personali),
  il suo nome e il MIME; vanno allo storage temporaneo del tenant e poi, con il riferimento, al
  tenant. La libreria non conserva nulla.
- **Segreti**: i campi `policy` e `signature` della risposta di `upload-new-attachment` e la
  `Signature` del `temporaryDownloadUrl` sono credenziali temporanee: redatti ovunque (04-C08).
  Il token Interacta non viaggia verso lo storage (04-C01).
- **Log e audit**: il contenuto del file non entra mai in log, audit log né hook, neppure con
  `audit_log_bodies` (04-C09). Il nome del file compare negli errori della CLI (04-C14), per
  scelta: è l'informazione che serve all'operatore.
- **Output**: `temporary_download_url` è mostrato in chiaro da `attachments upload` e da
  `--output json`: è l'output scelto dall'operatore, come già i link temporanei delle letture.
- **Conservazione**: nessuna; i file nello storage temporaneo scadono con la policy del tenant.

## Requisiti nuovi

- RF-024 (precisato). L'upload è in due passi: `POST upload-new-attachment` senza corpo, poi
  form multipart `POST` all'URL di storage con i campi della policy firmata e il file (verificato
  sul tenant il 2026-10-10: il `PUT` è rifiutato). `client.attachments.upload` li esegue e
  restituisce `UploadedAttachment`, accettato dai metodi di scrittura di post e task;
  `request_upload_url` espone il primo passo. Un errore dello storage è `UploadError`.
- RF-024a (precisa RF-024 e RF-021c). In CLI: `attachments upload PATH`; `--attach PATH`
  ripetibile su `posts create|comment|edit|copy` e `tasks create|edit`; `posts edit-attachments`
  con `--add`, `--remove`, `--update ID=PATH`; `UploadError` esce con exit code `11`; al primo
  upload fallito nessuna scrittura parte verso Interacta.
- RNF-001 (precisato). Ai nomi di chiave sensibili dei body si aggiungono `signature` e `policy`;
  negli URL i parametri di query il cui nome contiene `signature|token|secret|password|key`
  perdono il valore.
- RNF-011. Il contenuto dei file caricati non compare mai in log, audit log né hook; la
  richiesta allo storage non porta il token Interacta.

## Fuori ambito

- Allegati Drive (`type = 2`, `drive`), `hashtagIds` e `referencedAttachmentId` di
  `InputPostAttachmentDTO`: restano passabili come dict o DTO, senza helper.
- Download del contenuto degli allegati (i link temporanei sono già nelle letture).
- Post evento (spec successiva), anagrafiche admin (RF-023).
- MIME esplicito in CLI (`--attach` deduce dall'estensione; `--json` per il resto).
- Controllo lato libreria dei vincoli della policy (dimensione, scadenza): decide lo storage.
- Retry automatico (RNF-009, ADR 0001).
- Traduzione in italiano della CLI esistente.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Form multipart `POST` con policy firmata, registrato nella spec; RF-024 precisato alla chiusura, nessun ADR nuovo | ADR 0002; assumere il `PUT` e rivedere dopo; gestire entrambi i casi | Sonda sul tenant del 2026-10-10: il `PUT` risponde `400 MissingSecurityHeader`, il form `204`; il "`PUT`" dell'ADR 0001 era descrittivo, non una decisione |
| `upload` su `client.attachments`, `UploadedAttachment` accettato dai metodi di post e task | Solo `upload` con dict composto dal chiamante; solo helper sui post | L'upload serve a post, commenti e task; un agente non deve comporre `{name, contentRef}` a mano |
| Input `Path`, stringa, `bytes` o file-like; nome e MIME dedotti dal percorso; streaming | Solo `Path`; solo `bytes` | Copre gli script che hanno i byte in memoria e i file grandi (la policy ammette 2 GiB) senza caricarli tutti |
| Nessun token verso lo storage; URL firmati e campi `signature`/`policy` redatti; file e form mai in log, audit o hook | URL in chiaro; richiesta fuori dal transport, invisibile agli hook | Regola non negoziabile "token e segreti mai nei log"; gli hook devono vedere ogni richiesta |
| Redazione generale (chiavi `signature|policy`, parametri di query sensibili) | Redazione mirata al solo endpoint di upload | I link temporanei firmati compaiono già nelle letture degli allegati; una regola sola copre tutti i casi |
| `UploadError` dedicata, exit code `11`; timeout e rete `TransportError` | Mappa per stato delle chiamate Interacta; `TransportError` per tutto | Lo stato e il corpo XML dello storage restano leggibili senza confondere un `403` dello storage con un permesso Interacta |
| Al primo upload fallito ci si ferma, nulla parte verso Interacta | Continuare con i file riusciti | Esito esplicito delle scritture (ADR 0001); i file temporanei scadono da soli |
| `--attach` su tutte le creazioni e modifiche di post e task; i riferimenti si accodano a `--json` | Solo i post; solo `posts create` e `posts comment` | Lo stesso helper serve tutti; `--json` resta per i casi non coperti dai flag |
| `posts edit-attachments` con `--add`, `--remove`, `--update ID=PATH` | Solo `--add` e `--remove`; solo `--json` | Tutti e tre i rami del DTO dalla shell; `--update` invia anche il nome del file, da verificare sul tenant (04-C18) |
| `attachments upload` in CLI con `render_output` | Upload solo tramite `--attach` | Script e agenti che compongono `--json` da sé vedono il `content_ref` |
| `request_upload_url()` esposto | Solo `upload` | È il `*_raw` di questa spec: i due passi restano visibili per chi carica con altri strumenti |
| Integration test con ciclo completo nella community di prova | Solo upload e rilettura; nessuno | Dimostra che il `contentRef` è accettato da `create-post` ed `edit-post-attachments`, e la semantica di `updateAttachments` |
| Riga `0.12.0` in ROADMAP, milestone M30 | – | I `feat` producono un minor (politica pre-1.0); M29 è l'ultimo usato |

## Verifica manuale

Nessuna: ogni criterio ha un test automatico (unit con `respx` sui due host, contract,
integration opt-in per 04-C18, `mkdocs build --strict` per 04-C17).

## Domande aperte

Nessuna.
