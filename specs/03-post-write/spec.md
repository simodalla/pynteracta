# 03 – Scrittura dei post custom, commenti e workflow

Stato: approvata
Branch: `m29_post_write`
Requisiti del PRD: RF-021, RF-025, RNF-009, RNF-010; toccati RF-006, RF-015, RF-015a, RF-019
Dipende da: spec 02 (chiusa): `_put`/`_delete` del client base, `build_write_body`,
`zoned_datetime_input`, `confirm_destructive`, `load_json_body`, `EXIT_CONFLICT`

Seconda spec della superficie di scrittura aperta da
[ADR 0001](../adr/0001-apertura-della-superficie-di-scrittura.md): i post **custom** (tipo 1), i
commenti e il workflow, con le letture propedeutiche. I post **evento** (tipo 2) restano per una spec
successiva: stessi schemi, DTO diversi.

## Scopo

Chi scrive automazioni con la libreria, e chi usa la CLI, può creare un post in una community,
modificarne i dati e i campi custom, copiarlo, cambiarne i watcher e gli allegati, eliminarlo o
marcarlo per la cancellazione, commentarlo ed eseguire le transizioni di workflow con i dati di
screen, con la stessa forma delle letture e dei task: metodi tipizzati con kwargs espliciti e
varianti `*_raw`, façade con `.raw`, comandi `posts …` che compongono con `--output`, `--full`,
`--fields`, `--export`. La concorrenza ottimistica resta visibile al chiamante; nessuna scrittura
viene ripetuta da sola.

## Comportamento attuale

Sui post esiste solo la lettura (RF-006): dettaglio per id e per client uid, capabilities, storia,
stream globale, elenchi in community con filtri, visibilità, commenti. Il dettaglio del post
(`Post`) non contiene l'`occToken`, che il server restituisce solo dalle letture propedeutiche
`post-data-for-edit` e `post-data-for-copy`, oggi non esposte. `PostCapabilities` espone sette
flag ma non `canCopy`, `canEditAttachments`, `canEditWorkflowScreenData` né le operazioni di
workflow permesse (`workflowPermittedOperations`), che il DTO ha già. Il client base sa fare
`GET`, `POST`, `PUT` e `DELETE`; la CLI ha la conferma dei comandi distruttivi, `--json FILE|-`,
l'exit code `9` e la patch di `tasks edit` (spec 02). Tutti i DTO di richiesta e risposta di questa
spec sono già nei modelli generati dal swagger pinnato: nessuna rigenerazione. Un'anomalia di
nome: il DTO di creazione è `CreateCustomPostRequest`, senza suffisso `DTO`, perché nel swagger si
chiama "Create Custom Post Request".

## Comportamento

### Libreria

Tutti i metodi stanno su `client.posts`. Ogni scrittura invia **una sola richiesta** con **solo i
campi passati**, in camelCase (ogni kwarg corrisponde a un campo del DTO, con lo stesso nome in
snake_case); un errore del server o di rete risale al chiamante, mai un nuovo tentativo. Ogni
metodo ha la variante `*_raw(…, req: DTO)` con gli stessi argomenti di percorso. Gli errori sono
quelli delle letture (`400 → ValidationError`, `403 → PermissionError`, `404 → NotFoundError`,
`409 → ConcurrencyError`, timeout e rete → `TransportError`); il `400` dei campi custom
(`CustomFieldValidationErrorResponseDTO`) arriva in `ValidationError.response_body` così com'è.

- **Letture propedeutiche** (RF-021a): `get_for_create(community_id)` restituisce `PostForCreate`
  (`content_data`, `.raw`); `get_for_edit(post_id, *, load_attachments=None)` restituisce
  `PostForEdit` con `occ_token`, `community_id`, `custom_id`, `current_workflow_state`,
  `content_data` (titolo, descrizione delta e testo, visibilità, annuncio, `custom_data`, dati di
  screen, allegati, watcher, hashtag, bozza, pubblicazione programmata) e `.raw`;
  `get_for_copy(post_id, *, load_attachments=None)` restituisce `PostForCopy` con `occ_token` e
  `content_data`. `load_attachments` va in query solo se passato.
- **Creare**: `create(community_id, *, announcement=False, title=None, description=None,
  description_format=None, custom_data=None, delta_area_format=None, attachments=None,
  watcher_user_ids=None, workflow_init_state_id=None, visibility=None, client_uid=None,
  draft=None, scheduled_publication=None)` → `PostWriteResult` con `post_id`, `next_occ_token`,
  `post` (i dati del post appena scritto, tipizzati), `.raw`. `announcement` è l'unico campo che
  il DTO dichiara obbligatorio: viene sempre inviato. `custom_data` è un `dict` con chiave l'id
  del campo custom, inviato com'è: valida il server. `attachments` accetta solo riferimenti già
  noti al server (`attachmentId`, oppure `name` + `contentRef`, oppure dati `drive`), nella forma
  di `InputPostAttachmentDTO` (dict o modello).
- **Modificare**: `edit(post_id, occ_token, *, title=None, description=None,
  description_format=None, custom_data=None, delta_area_format=None, add_attachments=None,
  update_attachments=None, remove_attachment_ids=None, add_watcher_user_ids=None,
  remove_watcher_user_ids=None, visibility=None, workflow_init_state_id=None, draft=None,
  scheduled_publication=None)` → `PostWriteResult` con il `next_occ_token` per la modifica
  successiva. `occ_token` lo fornisce il chiamante, da `PostForEdit.occ_token`.
- **Modificare i soli campi custom**: `edit_custom_data(post_id, occ_token, *, custom_data=None,
  delta_area_format=None, tables=None)` → `PostWriteResult`; `tables` nella forma di
  `CreateEditPostTableRequestDTO`.
- **Copiare**: `copy(post_id, occ_token, *, …gli stessi kwargs di edit più announcement=None…)`
  → `PostWriteResult` con il `post_id` del post nuovo. `occ_token` viene da `PostForCopy`.
- **Watcher e allegati**: `edit_watchers(post_id, *, add_user_ids=None, remove_user_ids=None)`
  → `None` (il server risponde senza corpo); `edit_attachments(post_id, *, add=None, update=None,
  remove_ids=None)` → `PostAttachmentsWriteResult` con `post_id`, `added`, `updated`,
  `removed_ids`, `.raw`. Nessuno dei due porta `occToken`.
- **Eliminare**: `delete(post_id)` → `post_id` dalla risposta; `mark_as_erasable(post_id)` →
  `post_id` dalla risposta. Il secondo elimina il post e lo marca per la cancellazione fisica
  futura (descrizione del swagger); la differenza osservabile sul tenant si verifica a mano e si
  documenta.
- **Commentare**: `add_comment(post_id, *, comment=None, comment_format=None, client_uid=None,
  attachments=None, parent_comment_id=None)` → `PostComment` con `id`, `comment_plain_text`,
  `comment_delta`, `creator_user`, `creation_timestamp`, `parent_comment_id`, `.raw`.
- **Workflow**: `get_workflow_screen(post_id, *, operation_id=None)` → `WorkflowScreen` con
  `screen_data`, `screen_occ_token`, `screen` (metadati dei campi), `current_workflow_state`,
  `.raw`; senza `operation_id` è lo screen dello stato corrente, con `operation_id` quello della
  transizione. `execute_workflow_operation(post_id, operation_id, *, screen_data=None,
  delta_area_format=None, screen_occ_token=None)` → `WorkflowOperationResult` con
  `new_current_state`, `new_screen_data`, `new_permitted_operations`,
  `new_can_edit_workflow_screen_data`, `post_data_has_changed`, `.raw`.
  `edit_workflow_screen(post_id, screen_occ_token, *, screen_data=None, delta_area_format=None)`
  → `WorkflowScreenWriteResult` con `next_screen_occ_token`, `new_screen_data`,
  `post_data_has_changed`, `.raw`.
- **Date**: `scheduled_publication` è un `datetime` **con fuso orario**, tradotto nella coppia
  `{datetime, timezone}` come `expiration` dei task (RNF-010); senza fuso → `ValueError` prima di
  qualunque chiamata.
- **Capabilities** (RF-006a): `PostCapabilities` espone anche `can_copy`,
  `can_edit_attachments`, `can_edit_workflow_screen_data` e `workflow_permitted_operations`
  (lista tipizzata delle transizioni permesse, con `id`, `name`, `from_state`, `to_state`): è il
  modo in cui un chiamante scopre l'`operation_id` da passare a `execute_workflow_operation`.

### CLI

Tutti i comandi stanno sotto `posts` e mostrano il risultato con `render_output` (`--output`,
`--full`, `--fields`, `--export`; `--web-url` dove c'è un post da linkare). I testi (help, prompt,
messaggi) sono in inglese, come il resto della CLI. `--json FILE|-` prende il DTO completo da file
o da stdin e vale per i campi senza flag (allegati, tabelle); se compaiono anche i flag, i flag
prevalgono campo per campo. `--custom-data ID=VALORE` e `--screen-data ID=VALORE` sono ripetibili,
con i valori tipizzati come `--filter` (`true`/`false`, interi, altrimenti stringa); un valore
JSON si passa con `--json`. `--description` e `--text` inviano testo semplice (formato `2`).
`--scheduled-publication` è una data-ora ISO 8601 interpretata nel fuso di `--timezone`
(predefinito `Europe/Rome`), con un offset esplicito `--timezone` è ignorato. Su `409` il comando
esce con exit code `9` e il messaggio `Post POST_ID changed since it was read: fetch it again and
retry`; mai un secondo tentativo.

- `posts create COMMUNITY_ID [--title T] [--description TEXT] [--custom-data ID=V]…
  [--watcher-user ID]… [--visibility N] [--announcement] [--draft] [--scheduled-publication ISO]
  [--timezone IANA] [--workflow-init-state ID] [--client-uid UID] [--json FILE|-]`: crea il post;
  tabella curata con id, community_id, title, visibility, stato di workflow corrente e
  next_occ_token.
- `posts edit POST_ID [stessi flag di create tranne --announcement e --client-uid]
  [--remove-watcher-user ID]… [--occ-token N]` è una **patch**: legge `post-data-for-edit`,
  costruisce il corpo dai dati letti (`title`, `description` dal delta letto con
  `descriptionFormat: 1`, `customData`, `visibility`), vi sovrappone `--json` e poi i flag, e
  invia con l'`occToken` letto. `--custom-data` sovrascrive le sole chiavi indicate, le altre
  restano quelle lette. `--description` sostituisce la descrizione con testo semplice (formato
  `2`). Bozza, pubblicazione programmata, stato iniziale di workflow, watcher e allegati non
  compaiono nel corpo se non con i flag o `--json`. `--occ-token N` impone solo il token; la
  lettura avviene comunque. Un campo assente nel post letto non viene inventato.
- `posts edit-custom-data POST_ID --custom-data ID=V… [--json FILE|-] [--occ-token N]`: legge
  `post-data-for-edit`, parte dai `customData` letti, sovrascrive le chiavi indicate e invia
  `edit-post-custom-data` con il token letto.
- `posts copy POST_ID [stessi flag di create] [--occ-token N]` è una patch come `posts edit`, con
  base dai dati di `post-data-for-copy` (`title`, `description`, `customData`, `visibility`,
  `announcement`) e invio di `copy-post` con il token letto. Mostra il post nuovo.
- `posts edit-watchers POST_ID [--add ID]… [--remove ID]…`: una `PUT`; stampa
  `Watchers of post POST_ID updated` e, con `--output json`, `{"post_id", "added_user_ids",
  "removed_user_ids"}`. Senza né `--add` né `--remove` esce con exit `2` e nessuna richiesta.
- `posts delete POST_ID [--yes|-y]` e `posts mark-erasable POST_ID [--yes|-y]`: leggono il post,
  mostrano `Delete post POST_ID "<title>"? [y/N]` (rispettivamente `Mark post POST_ID "<title>"
  as erasable? [y/N]`) e procedono solo con `y`; con `--yes` non chiedono; senza terminale
  interattivo e senza `--yes` rifiutano con exit `2` e nessuna richiesta parte. In caso di
  successo stampano `Post POST_ID deleted` (`Post POST_ID marked as erasable`) e, con
  `--output json`, `{"post_id": …}`.
- `posts comment POST_ID --text TEXT [--parent COMMENT_ID] [--client-uid UID] [--json FILE|-]`:
  crea il commento; tabella con id, creatore, testo, creation_timestamp.
- `posts get-for-create COMMUNITY_ID`, `posts get-for-edit POST_ID [--no-attachments]`,
  `posts get-for-copy POST_ID [--no-attachments]`: mostrano i dati propedeutici; la tabella di
  `get-for-edit` e `get-for-copy` ha in testa `occ_token`.
- `posts workflow-screen POST_ID [--operation ID]`: mostra `screen_occ_token`, stato corrente,
  nome dello screen e i campi di `screen_data`.
- `posts workflow-execute POST_ID OPERATION_ID [--screen-data ID=V]… [--json FILE|-]
  [--screen-occ-token N]`: con dati di screen (flag o `--json` senza `screenOccToken`) legge
  prima lo screen della transizione per il token, parte dai `screenData` letti, sovrascrive le
  chiavi indicate e invia `{"screenData": …, "screenOccToken": <letto>}`; senza dati invia `{}`
  e non legge nulla (transizione senza screen). `--screen-occ-token` impone il token. Mostra il
  nuovo stato e le transizioni permesse.
- `posts workflow-edit-screen POST_ID [--screen-data ID=V]… [--json FILE|-]
  [--screen-occ-token N]`: legge lo screen dello stato corrente, parte dai dati letti,
  sovrascrive e invia `edit-post-workflow-screen-data` con il token letto.

### Documentazione e test

`docs/api/posts.md` (metodi, façade, `occ_token` dalle letture propedeutiche, formato delle date,
semantica dei campi omessi come verificata sul tenant), `docs/cli.md` (quattordici comandi, exit
code `9`), `docs/testing.md` e `tests/integration/.env.example` (variabili
`PYNTERACTA_TEST_WRITE_COMMUNITY_ID` e `PYNTERACTA_TEST_WORKFLOW_POST_ID`), `docs/index.md` e
`README.md` (la superficie di scrittura comprende anche i post, senza numeri di versione).
Fixture JSON e contract test per i DTO delle scritture e delle letture propedeutiche. Integration
test opt-in con il ciclo completo su una community di prova, con pulizia garantita.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 03-C01 | Quando si chiama `client.posts.create(79, title="T", description="D", description_format=2, custom_data={"1411": 226}, watcher_user_ids=[7])`, parte una sola `POST …/communication/posts/manage/create-post/79` con corpo `{"announcement": false, "title": "T", "description": "D", "descriptionFormat": 2, "customData": {"1411": 226}, "watcherUserIds": [7]}` (nessun'altra chiave) e, con una risposta `CreatePostResponseDTO`, il risultato ha `post_id`, `next_occ_token`, `post.title` e `.raw` valorizzati dalla risposta. | RF-021 |
| 03-C02 | Quando si chiama `create_raw(79, CreateCustomPostRequest(announcement=False, title="T"))`, la richiesta e il risultato sono gli stessi di 03-C01 con quel corpo; lo stesso vale per ogni altra coppia metodo/`*_raw` di questa spec con il DTO equivalente. | RF-021 |
| 03-C03 | Quando `scheduled_publication` è `datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome"))`, il corpo di `create`, `edit` e `copy` contiene `"scheduledPublication": {"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"}`; quando è senza fuso, i tre metodi sollevano `ValueError` e nessuna richiesta parte. | RF-021, RNF-010 |
| 03-C04 | Quando si chiama `client.posts.edit(21269, 5, title="T2", remove_watcher_user_ids=[7])`, parte una sola `PUT …/communication/posts/manage/edit-post/21269/5` con corpo `{"title": "T2", "removeWatcherUserIds": [7]}` e il risultato ha `next_occ_token` e `post` dalla risposta `EditPostResponseDTO`; con tutti i kwargs a `None` il corpo è `{}`. | RF-021, RF-025 |
| 03-C05 | Quando si chiama `client.posts.edit_custom_data(21269, 5, custom_data={"1411": 226})`, parte una sola `PUT …/edit-post-custom-data/21269/5` con corpo `{"customData": {"1411": 226}}` e il risultato è un `PostWriteResult` con `next_occ_token` dalla risposta. | RF-021, RF-025 |
| 03-C06 | Quando si chiama `client.posts.copy(21269, 5, title="Copia")`, parte una sola `PUT …/copy-post/21269/5` con corpo `{"title": "Copia"}` e il risultato ha `post_id` (del post nuovo) e `next_occ_token` dalla risposta `CopyPostResponseDTO`. | RF-021, RF-025 |
| 03-C07 | Quando il server risponde `409` a `edit`, `edit_custom_data`, `copy`, `execute_workflow_operation` o `edit_workflow_screen`, viene sollevata `ConcurrencyError` con `status_code == 409` e il server ha ricevuto **esattamente una** richiesta. | RF-025, RNF-009 |
| 03-C08 | Quando si chiama `client.posts.edit_watchers(21269, add_user_ids=[7], remove_user_ids=[8])`, parte una sola `PUT …/edit-post-watchers/21269` con corpo `{"addWatcherUserIds": [7], "removeWatcherUserIds": [8]}` e il metodo restituisce `None` su risposta `200` senza corpo; quando si chiama `edit_attachments(21269, remove_ids=[3])`, parte una sola `PUT …/edit-post-attachments/21269` con corpo `{"removeAttachmentIds": [3]}` e il risultato ha `post_id`, `added`, `updated`, `removed_ids` dalla risposta `EditPostAttachmentsResponseDTO`. | RF-021 |
| 03-C09 | Quando si chiama `client.posts.delete(21269)`, parte una sola `DELETE …/delete-post/21269` e il valore restituito è il `postId` della risposta; quando si chiama `mark_as_erasable(21269)`, parte una sola `PUT …/mark-post-as-erasable/21269` senza corpo e il valore restituito è il `postId` della risposta. | RF-021 |
| 03-C10 | Quando si chiama `client.posts.add_comment(21269, comment="Ciao", comment_format=2, parent_comment_id=5)`, parte una sola `POST …/create-comment/21269` con corpo `{"comment": "Ciao", "commentFormat": 2, "parentCommentId": 5}` e il risultato è un `PostComment` con `id`, `comment_plain_text`, `creator_user`, `parent_comment_id` e `.raw` dalla risposta `CreatePostCommentResponseDTO`. | RF-021 |
| 03-C11 | Quando si chiama `get_for_create(79)`, parte una `GET …/post-data-for-create/79` e il risultato ha `content_data`; quando si chiama `get_for_edit(21269)`, parte una `GET …/post-data-for-edit/21269` senza query (con `load_attachments=False` la query è `loadAttachments=false`) e il risultato ha `occ_token`, `community_id`, `current_workflow_state` e `content_data.title`, `content_data.custom_data` dalla risposta; quando si chiama `get_for_copy(21269)`, parte una `GET …/post-data-for-copy/21269` e il risultato ha `occ_token` e `content_data`. | RF-021, RF-021a |
| 03-C12 | Quando si chiama `get_workflow_screen(21269)`, parte una `GET …/post-workflow-screen-data-for-edit/21269` senza query; con `operation_id=12` la query è `workflowOperationId=12`; il risultato ha `screen_data`, `screen_occ_token`, `screen.name`, `current_workflow_state.name` dalla risposta. | RF-021 |
| 03-C13 | Quando si chiama `execute_workflow_operation(21269, 12, screen_data={"5": "x"}, screen_occ_token=3)`, parte una sola `POST …/execute-post-workflow-operation/21269/12` con corpo `{"screenData": {"5": "x"}, "screenOccToken": 3}`; senza kwargs il corpo è `{}`; il risultato ha `new_current_state.name`, `new_screen_data`, `new_permitted_operations` e `post_data_has_changed` dalla risposta. | RF-021, RF-025 |
| 03-C14 | Quando si chiama `edit_workflow_screen(21269, 3, screen_data={"5": "x"})`, parte una sola `PUT …/edit-post-workflow-screen-data/21269/3` con corpo `{"screenData": {"5": "x"}}` e il risultato ha `next_screen_occ_token` e `new_screen_data` dalla risposta. | RF-021, RF-025 |
| 03-C15 | Quando `posts.capabilities(21269)` riceve un `GetPostCapabilitiesResponseDTO` con `canCopy`, `canEditAttachments`, `canEditWorkflowScreenData` e `workflowPermittedOperations: [{"id": 12, "name": "Approva", …}]`, `PostCapabilities` espone `can_copy`, `can_edit_attachments`, `can_edit_workflow_screen_data` e `workflow_permitted_operations[0].id == 12`; `posts capabilities` in CLI mostra i tre flag e gli id e nomi delle operazioni. | RF-006, RF-006a |
| 03-C16 | Quando il server risponde `400` con un `CustomFieldValidationErrorResponseDTO` a `create`, viene sollevata `ValidationError` con `status_code == 400` e `response_body` che contiene `validationErrors`, e il server ha ricevuto una sola richiesta; in CLI l'exit code è `6` e il messaggio riporta il body. | RF-019, RF-021 |
| 03-C17 | Quando `create` o `add_comment` va in timeout o errore di rete, viene sollevata `TransportError` e il server ha ricevuto al più una richiesta. | RNF-009 |
| 03-C18 | Quando si esegue `posts create 79 --title T --description D --custom-data 1411=226 --watcher-user 7 --announcement --json body.json` con `body.json` = `{"title": "X", "visibility": 1}`, il corpo inviato è `{"announcement": true, "title": "T", "description": "D", "descriptionFormat": 2, "customData": {"1411": 226}, "watcherUserIds": [7], "visibility": 1}` (i flag prevalgono) e la tabella mostra id, community_id, title, visibility, stato corrente e next_occ_token del post creato; `--output json` restituisce la risposta serializzata. Senza `--announcement` il corpo ha `"announcement": false`. | RF-021, RF-015 |
| 03-C19 | Quando si esegue `posts edit 21269 --title T2` e la `GET …/post-data-for-edit/21269` restituisce `occToken: 5` e `contentData` con `descriptionDelta`, `customData`, `visibility`, la `PUT …/edit-post/21269/5` ha corpo `{"title": "T2", "description": <delta letto>, "descriptionFormat": 1, "customData": <letto>, "visibility": <letta>}` e nessun'altra chiave; con `--occ-token 3` la `GET` avviene lo stesso e la `PUT` usa `3`; quando il post letto non ha descrizione o custom data, le chiavi corrispondenti mancano. | RF-021, RF-025, RF-021b |
| 03-C20 | Quando si esegue `posts edit 21269 --description X --custom-data 1411=300 --json body.json` con `body.json` = `{"visibility": 2, "customData": {"1412": "a"}}` sul post di 03-C19 (letto con `customData: {"1411": 226, "1413": true}`), il corpo contiene `description: "X"` con `descriptionFormat: 2` (il delta letto non viene inviato), `visibility: 2` (json > letto), `customData: {"1411": 300, "1412": "a", "1413": true}` (flag > json > letto, chiave per chiave). | RF-021, RF-021b |
| 03-C21 | Quando si esegue `posts edit-custom-data 21269 --custom-data 1411=300` sul post di 03-C19, la CLI fa la `GET …/post-data-for-edit/21269` e poi `PUT …/edit-post-custom-data/21269/5` con corpo `{"customData": {"1411": 300, "1413": true}}`; senza né `--custom-data` né `--json` esce con exit `2` e nessuna richiesta parte. | RF-021, RF-021b |
| 03-C22 | Quando si esegue `posts copy 21269 --title Copia` e la `GET …/post-data-for-copy/21269` restituisce `occToken: 5` e `contentData` con `title`, `descriptionDelta`, `customData`, `visibility`, `announcement`, la `PUT …/copy-post/21269/5` ha corpo `{"title": "Copia", "description": <delta letto>, "descriptionFormat": 1, "customData": <letto>, "visibility": <letta>, "announcement": <letto>}` e la tabella mostra il post nuovo con il suo id. | RF-021, RF-021b |
| 03-C23 | Quando si esegue `posts edit-watchers 21269 --add 7 --remove 8`, parte una sola `PUT …/edit-post-watchers/21269` con corpo `{"addWatcherUserIds": [7], "removeWatcherUserIds": [8]}` e il comando stampa `Watchers of post 21269 updated`; con `--output json` stampa `{"post_id": 21269, "added_user_ids": [7], "removed_user_ids": [8]}`; senza `--add` né `--remove` esce con exit `2` e nessuna richiesta parte. | RF-021, RF-015 |
| 03-C24 | Quando si esegue `posts delete 21269` in un terminale interattivo, il prompt riporta id e titolo letti con `GET …/post-detail-by-id/21269`; con risposta `y` parte la `DELETE` e il comando stampa `Post 21269 deleted`; con risposta `n` nessuna `DELETE` parte e l'exit code è `0`; con `--yes` nessun prompt; senza terminale e senza `--yes` nessuna richiesta di scrittura parte, exit `2` e il messaggio dice che serve `--yes`. Lo stesso vale per `posts mark-erasable 21269` con il prompt `Mark post 21269 "<title>" as erasable? [y/N]`, la `PUT …/mark-post-as-erasable/21269` e il messaggio `Post 21269 marked as erasable`. | RF-025, RF-025a |
| 03-C25 | Quando si esegue `posts comment 21269 --text Ciao --parent 5`, parte una sola `POST …/create-comment/21269` con corpo `{"comment": "Ciao", "commentFormat": 2, "parentCommentId": 5}` e la tabella mostra id, creatore, testo e creation_timestamp del commento; `--output json` restituisce la risposta serializzata; senza `--text` e senza `--json` esce con exit `2`. | RF-021, RF-015 |
| 03-C26 | Quando si esegue `posts get-for-edit 21269`, la tabella ha in testa `occ_token` seguito da community_id, title, visibility e stato corrente; `posts get-for-copy 21269` mostra `occ_token` e title; `posts get-for-create 79` mostra i dati di `content_data`; `--no-attachments` manda `loadAttachments=false`; `--output json` e `--full` restituiscono il DTO intero. | RF-021a, RF-015 |
| 03-C27 | Quando si esegue `posts workflow-execute 21269 12 --screen-data 5=x` e la `GET …/post-workflow-screen-data-for-edit/21269?workflowOperationId=12` restituisce `screenOccToken: 3` e `screenData: {"5": "a", "6": 1}`, la `POST …/execute-post-workflow-operation/21269/12` ha corpo `{"screenData": {"5": "x", "6": 1}, "screenOccToken": 3}`; senza `--screen-data` né `--json` non c'è alcuna `GET` e il corpo è `{}`; `--screen-occ-token 9` impone `9`. `posts workflow-edit-screen 21269 --screen-data 5=x` fa la `GET` senza query e la `PUT …/edit-post-workflow-screen-data/21269/3` con corpo `{"screenData": {"5": "x", "6": 1}}`. `posts workflow-screen 21269 --operation 12` mostra screen_occ_token, stato corrente, nome dello screen e i campi di screen_data. | RF-021, RF-025, RF-015 |
| 03-C28 | Quando la `PUT` di `posts edit`, `posts edit-custom-data`, `posts copy`, `posts workflow-edit-screen` o la `POST` di `posts workflow-execute` risponde `409`, il comando termina con exit code `9`, stampa `Post 21269 changed since it was read: fetch it again and retry` e il server ha ricevuto una sola richiesta di scrittura. | RF-025, RF-015a, RNF-009 |
| 03-C29 | I contract test dimostrano che i modelli generati `CreateCustomPostRequest`, `EditCustomPostRequestDTO`, `EditPostCustomDataRequestDTO`, `CopyCustomPostRequestDTO`, `EditPostWatchersRequestDTO`, `EditPostAttachmentsRequestDTO`, `CreatePostCommentRequestDTO`, `ExecutePostWorkflowOperationRequestDTO`, `EditPostWorkflowScreenDataRequestDTO`, `CreatePostResponseDTO`, `EditPostResponseDTO`, `CopyPostResponseDTO`, `EditPostAttachmentsResponseDTO`, `MarkPostAsErasableResponseDTO`, `DeletePostResponseDTO`, `CreatePostCommentResponseDTO`, `ExecutePostWorkflowOperationResponseDTO`, `EditPostWorkflowScreenDataResponseDTO`, `GetPostWorkflowScreenDataForEditResponseDTO`, `GetCustomPostForCreateResponseDTO`, `GetCustomPostForEditResponseDTO`, `GetCustomPostForCopyResponseDTO` coprono tutte le proprietà del swagger pinnato, e le fixture JSON di risposta si leggono nelle façade. | RF-021, RNF-003 |
| 03-C30 | `docs/cli.md` documenta i quattordici comandi `posts` di questa spec; `docs/api/posts.md` documenta i metodi, le façade, `occ_token` dalle letture propedeutiche, il formato delle date e la semantica dei campi omessi; `docs/index.md` e `README.md` citano i post tra le scritture senza numeri di versione; `uv run mkdocs build --strict` e `test_docs_snippets` sono verdi. | RF-015 |
| 03-C31 | Quando `PYNTERACTA_TEST_WRITE_COMMUNITY_ID` e `PYNTERACTA_TEST_USER_ID` sono impostate (integration, opt-in), il ciclo `create` (con `client_uid` riconoscibile) → `get_by_client_uid` → `get_for_edit` (occ_token) → `edit` → `edit_watchers` → `add_comment` → `get_for_copy` → `copy` → `delete` della copia → `delete` dell'originale termina senza errori sul tenant e i due post rispondono `404` al termine; la pulizia avviene anche se un passo intermedio fallisce; senza una delle variabili il test è saltato. Quando `PYNTERACTA_TEST_WORKFLOW_POST_ID` è impostata, `get_workflow_screen` restituisce `screen_occ_token` e `current_workflow_state` senza eseguire transizioni; senza la variabile è saltato. | RF-021, RF-025 |

## Casi limite

- `create` senza alcun kwarg → corpo `{"announcement": false}`; decide il server (03-C01, 03-C18).
- `custom_data` con valori non validi per il campo → `400 → ValidationError` con il body leggibile,
  una sola richiesta (03-C16); la libreria non valida contro la definizione.
- `edit` con tutti i kwargs a `None` → `PUT` con corpo `{}` (03-C04).
- `occ_token` sbagliato → `409 → ConcurrencyError`, una sola richiesta (03-C07); in CLI exit `9`
  (03-C28).
- `delete`, `mark_as_erasable`, `edit` di un post inesistente → `404 → NotFoundError`, exit `5`
  in CLI (mapping esistente).
- `posts edit`, `posts copy`, `posts edit-custom-data` su un post che la lettura propedeutica non
  trova → exit `5`, nessuna scrittura, anche con `--occ-token` (03-C19, 03-C22, 03-C21).
- `posts edit` con `--json` che contiene `description` → vince sul delta letto; `descriptionFormat`
  resta `1` se non indicato (03-C20: il formato `2` arriva solo da `--description`).
- `posts edit` con `--json` che contiene `customData` → unione chiave per chiave con i dati letti,
  poi i flag (03-C20).
- `--custom-data` senza `=` o con id non numerico → exit `2`, nessuna richiesta.
- `--json -` con stdin vuoto o JSON non valido, o chiavi sconosciute al DTO → exit `2`, nessuna
  richiesta (`load_json_body` esistente).
- `--scheduled-publication` con offset esplicito → fuso dell'offset; `--timezone` non IANA → exit
  `2` (03-C03, comportamento di `tasks create`).
- `posts delete` o `posts mark-erasable` con risposta al prompt diversa da `y`/`Y` → nessuna
  richiesta, exit `0` (03-C24).
- `posts workflow-execute` di una transizione senza screen → corpo `{}`, nessuna `GET` (03-C27);
  se il tenant richiede `"screenData": null` esplicito, lo si scopre nella verifica manuale e
  `execute_workflow_operation_raw` lo permette.
- `edit_watchers` senza argomenti → `PUT` con corpo `{}` dalla libreria (una richiesta, campi
  espliciti); la CLI rifiuta con exit `2` (03-C23).
- Timeout **dopo** l'invio di `create` o `add_comment`: il post o il commento potrebbe esistere;
  la libreria solleva `TransportError` e non riprova (03-C17); il chiamante può cercare il post
  con `get_by_client_uid`, se ha passato `client_uid`.
- `add_comment` con `parent_comment_id` inesistente → decide il server (`400`/`404`), una sola
  richiesta.

## Dati personali e segreti

Passano al tenant: titolo, descrizione e campi custom del post (che possono contenere dati
personali scelti dal chiamante), testo dei commenti, id di watcher, riferimenti ad allegati,
`client_uid`. La libreria li inoltra e non li conserva; l'audit log opzionale li registra solo con
`audit_log_bodies` (eccezione documentata). Nei log applicativi compaiono solo metodo, URL redatto
e stato. L'output dei comandi mostra nomi di creatori e watcher, come già `posts get`: è output
per l'operatore, non log. Nessun segreto nuovo. Gli integration test usano una community di prova
dedicata (`PYNTERACTA_TEST_WRITE_COMMUNITY_ID`), mai la community dei test di lettura, un
`client_uid` riconoscibile (`pynteracta-it-<timestamp>`) e un post di workflow di prova
(`PYNTERACTA_TEST_WORKFLOW_POST_ID`) su cui non eseguono transizioni.

## Requisiti nuovi

- RF-021a (precisa RF-021). Le letture propedeutiche `get_for_create`, `get_for_edit`,
  `get_for_copy` sono esposte come letture e restituiscono `occ_token` (dove il server lo dà) e i
  dati editabili del post; `edit`, `edit_custom_data` e `copy` ricevono l'`occ_token` dal
  chiamante.
- RF-021b (precisa RF-025b). `posts edit`, `posts edit-custom-data` e `posts copy` in CLI sono
  patch: rileggono i dati propedeutici e rimandano i campi non indicati; `--custom-data` e
  `--screen-data` sovrascrivono chiave per chiave; `--occ-token` e `--screen-occ-token` impongono
  solo il token.
- RF-021c (precisa RF-021). `edit_attachments` e gli `attachments` di `create`, `edit`, `copy`,
  `add_comment` accettano solo riferimenti già noti al server; `posts edit-attachments` in CLI è
  rimandato a dopo l'upload (RF-024).
- RF-006a (precisa RF-006). `PostCapabilities` espone `can_copy`, `can_edit_attachments`,
  `can_edit_workflow_screen_data` e le operazioni di workflow permesse, con cui il chiamante
  scopre l'`operation_id` delle transizioni.

## Fuori ambito

- Post evento: `create-event-post`, `edit-event-post`, `copy-event-post`,
  `post-event/{postId}/partecipate` e gli helper `event-post-data-for-*` (spec successiva).
- `posts edit-attachments` in CLI (RF-021c) e l'upload di nuovi allegati (RF-024).
- Validazione dei campi custom contro la definizione della community prima dell'invio.
- Retry automatico e risoluzione automatica del `409` (RNF-009, ADR 0001).
- Modifica ed eliminazione dei commenti: nessun endpoint in `posts/manage`.
- Esecuzione di transizioni di workflow negli integration test (solo lettura dello screen).
- Traduzione in italiano della CLI esistente.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Taglio: post custom, commenti e workflow; post evento rimandati | Tutto il gruppo (22 endpoint); solo post custom e commenti; nucleo minimo | Una spec gestibile che chiude i post più usati e il workflow, senza raddoppiare i DTO degli eventi |
| `occ_token` esplicito, letto dagli helper esposti (`get_for_edit`, `get_for_copy`) | `edit` che rilegge da solo; nessun helper | La concorrenza resta visibile al chiamante (RF-025, spec 02); senza helper il token non è ottenibile |
| CLI `posts edit`, `posts edit-custom-data`, `posts copy` come patch, semantica verificata sul tenant | Solo i campi passati; decidere dopo la prova | Sui task il server azzera i campi omessi (T11 della spec 02): la patch evita la trappola; se il server dei post non azzera, la spec si rivede riducendo la base |
| `custom_data` dict passante, valida il server | Validazione opzionale con `PostDefinition`; validazione sempre | Nessuna chiamata in più, nessuna duplicazione delle regole del server; il `400` è leggibile |
| Kwargs specchio del DTO (`description` + `description_format`); `announcement` sempre inviato | Kwargs come i task (`description_delta`/`description_plain_text`) | Un kwarg per campo (spec 02); `announcement` è l'unico campo obbligatorio del DTO |
| Tre metodi e tre comandi per il workflow, `screen_occ_token` esplicito in libreria e letto dalla CLI | Solo libreria; un solo comando `posts workflow` | Ogni scrittura ha il suo comando (ADR 0001); scopribile e documentabile |
| `posts delete` e `posts mark-erasable` distinti, prompt dal dettaglio del post | `posts delete --erasable`; solo `delete` in CLI | Due endpoint con effetti diversi, due comandi chiari; schema di conferma della spec 02 |
| `add_comment` con kwargs completi e `posts comment --text` | Solo testo e parent | Un kwarg per campo; il comando copre l'uso comune |
| `edit_watchers` ed `edit_attachments` in libreria, solo i watcher in CLI | Entrambi in CLI; solo libreria | Gli allegati in CLI hanno senso solo con l'upload (RF-024); i watcher sono subito utili |
| `PostCapabilities` estesa con copia, allegati e operazioni di workflow | Lasciare i flag in `.raw` | Un agente deve poter scoprire gli `operation_id` senza leggere il DTO grezzo |
| Integration test con ciclo completo su una community di prova, workflow in sola lettura | Solo create → edit → delete; nessuna prova | Fissa contro il server reale copia, commenti e watcher; le transizioni cambiano stato e non si possono annullare |
| Riga `0.11.0` in ROADMAP | – | I `feat` producono un minor (politica pre-1.0) |

## Verifica manuale

- La semantica dei campi omessi in `edit-post`, `edit-post-custom-data` e `copy-post` (invariati o
  azzerati), il formato della descrizione accettato in modifica (lo swagger dice "markdown" per
  `descriptionFormat: 2`, "plain text" in creazione), l'effetto di `mark-post-as-erasable` rispetto
  a `delete-post` e il corpo accettato da `execute-post-workflow-operation` per una transizione
  senza screen (`{}` o `{"screenData": null}`) non sono documentati dallo swagger: si stabiliscono
  eseguendo 03-C31 e prove a mano sulla community di prova, in un task dedicato. L'esito si registra
  in `docs/api/posts.md` e in `verifica.md`; se il server non azzera i campi omessi, la base delle
  patch in CLI si riduce ai soli campi passati con una revisione della spec (03-C19…03-C22). Fino a
  quell'esecuzione 03-C31 vale come saltato.

## Domande aperte

Nessuna.
