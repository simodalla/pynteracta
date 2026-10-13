# 08 – Scrittura dei post evento

Stato: approvata
Branch: `m34_event_post_write`
Requisiti del PRD: RF-021, RF-021a, RF-021b, RF-021c, RF-021d, RF-025, RF-025a, RF-015,
RF-015a, RF-024, RF-024a, RNF-009, RNF-010; toccati RF-019, §1 (scopo), §6 "Dati scritti sul
tenant"
Dipende da: spec 02 (chiusa): `_put` del client base, `build_write_body`, `zoned_datetime_input`,
`load_json_body`, `EXIT_CONFLICT`; spec 03 (chiusa): `PostWriteResult`, unione di `--json` e
flag, patch della CLI con i riferimenti tradotti in id, `_token_or_exit`; spec 04 (chiusa):
`attachments.upload`, `--attach`, exit code `11`

Sesta e ultima spec della superficie di scrittura aperta da
[ADR 0001](../adr/0001-apertura-della-superficie-di-scrittura.md): i post **evento** (tipo 2),
cioè i 7 endpoint del gruppo "post e commenti" che la [spec 03](../03-post-write/spec.md) aveva
rimandato. Con questa spec il gruppo post (15 endpoint) e l'intera superficie di scrittura
dell'ADR (34 endpoint) sono completi. Minor **0.14.0**, milestone **M34**.

## Scopo

Chi scrive automazioni con la libreria, e chi usa la CLI, può creare un post evento in una
community (date, fuso, luogo, invitati, copertina), modificarlo, copiarlo e rispondere all'invito
(sì, forse, no), con la stessa forma dei post custom: metodi tipizzati con kwargs espliciti e
varianti `*_raw`, façade con `.raw`, comandi `posts …-event` che compongono con `--output`,
`--full`, `--fields`, `--export`. Le date si passano come `datetime` con fuso; la concorrenza
ottimistica resta visibile al chiamante; nessuna scrittura viene ripetuta da sola.

## Comportamento attuale

Sui post evento non esiste nulla: `docs/api/posts.md` li dichiara "read-only for now", home del
sito e README dicono "Event posts follow". Il dettaglio del post (`posts get`) nel swagger pinnato
non ha il blocco `event`: i dati di un evento (date, luogo, invitati, partecipanti) non sono
leggibili da nessuna façade; il filtro `eventPostFilter` dell'elenco in community è raggiungibile
solo con `list_in_community_raw`. I post custom hanno tutto il ciclo di scrittura (spec 03),
l'upload degli allegati e `--attach` (spec 04), `--cover` con upload per il workspace (spec 06).
I DTO di richiesta e risposta dei sette endpoint sono già nei modelli generati dal swagger pinnato
(`CreateEventPostRequestDTO`, `EditEventPostRequestDTO`, `CopyEventPostRequestDTO`,
`EditPostEventPartecipateRequestDTO`, `GetEventPostForCreate|Edit|CopyResponseDTO`, con le
varianti tipizzate `EventPostEditableContentDataDTOModel`, `EventPostDataDTOModel`,
`EventDatetimeDTO`, `InvitationUserDTO1`, `InvitationGroupDTO1`): nessuna rigenerazione. Le
risposte di `create-event-post`, `edit-event-post` e `copy-event-post` sono gli stessi DTO dei
post custom (`CreatePostResponseDTO`, `EditPostResponseDTO`, `CopyPostResponseDTO`), già letti da
`PostWriteResult`.

Differenze dai post custom che il swagger mostra: i DTO evento hanno il blocco `event`
(`startAt`/`endAt` come `{localDatetime}` più un `timezone` a livello di evento, `allDay`,
`location`, `invitations` con utenti e gruppi, ciascuno con `typeId` 0 = guest, 2 = collaborator,
e `sendEditPostNotifications`) e in più `coverImageContentRef`, `watcherGroupIds` (con le coppie
add/remove in modifica), `pinned` ("null per lasciare invariato") e `linkPreview`, che i DTO custom
non hanno; non hanno `customData`, `deltaAreaFormat` né `workflowInitStateId`. `announcement` non è
obbligatorio (nel DTO custom lo era). La partecipazione è `{typeId, notes}` con `typeId` 1 = sì,
2 = forse, 3 = no, risposta `200` senza corpo, `404` "Post evento non esistente".

## Comportamento

### Libreria

Tutti i metodi stanno su `client.posts`, accanto a quelli dei post custom, con il suffisso
`_event`. Ogni scrittura invia **una sola richiesta** con **solo i campi passati**, in camelCase
(un kwarg per campo del DTO; il blocco `event` lo compone la libreria dai kwargs dell'evento, con le
sole chiavi passate); un errore del server o di rete risale al chiamante, mai un nuovo tentativo.
Ogni metodo ha la variante `*_raw(…, req: DTO)` con gli stessi argomenti di percorso. Gli errori
sono quelli della spec 03 (`400 → ValidationError`, `403 → PermissionError`, `404 →
NotFoundError`, `409 → ConcurrencyError`, timeout e rete → `TransportError`).

- **Letture propedeutiche** (RF-021a): `get_event_for_create(community_id)` →
  `EventPostForCreate` (`content_data`, `event`, `cover_image`, `.raw`);
  `get_event_for_edit(post_id, *, load_attachments=None)` → `EventPostForEdit` con `occ_token`,
  `community_id`, `custom_id`, `content_data` (titolo, descrizione delta e testo, copertina,
  visibilità, annuncio, allegati, watcher utenti e gruppi, hashtag, `pinned`, bozza,
  pubblicazione programmata), `event`, `cover_image`, `.raw`; `get_event_for_copy(post_id, *,
  load_attachments=None)` → `EventPostForCopy` con `occ_token`, `content_data`, `event`, `.raw`.
  `load_attachments` va in query solo se passato.
- **Dati dell'evento letti**: `event` è una façade `EventData` con `start_at` ed `end_at` come
  `datetime` **con fuso** (dall'istante con offset che il server restituisce), `timezone`
  (nome IANA), `all_day`, `location`, `participants_count`, `my_answer`
  (`ParticipationAnswer` o `None` se l'utente non ha ancora risposto), `invited_users` e
  `invited_groups` (liste tipizzate con `id`, nome e `type_id` dell'invito),
  `send_edit_post_notifications`, `.raw` (`EventPostDataDTOModel`). `event` è `None` quando il
  server non lo restituisce.
- **Creare**: `create_event(community_id, *, start_at, end_at=None, all_day=None,
  location=None, invited_user_ids=None, invited_group_ids=None, invitation_type_id=None,
  send_edit_post_notifications=None, title=None, description=None, description_format=None,
  cover_image_content_ref=None, attachments=None, watcher_user_ids=None,
  watcher_group_ids=None, visibility=None, announcement=None, client_uid=None,
  link_preview=None, pinned=None, draft=None, scheduled_publication=None)` → `PostWriteResult`
  (`post_id`, `next_occ_token`, `post`, `.raw`). `start_at` è l'unico kwarg obbligatorio (il
  swagger lo dice obbligatorio). `announcement` è inviato solo se passato. `attachments` accetta
  `UploadedAttachment` e riferimenti già noti al server (RF-021c). `link_preview` è un dict o
  modello nella forma di `LinkPreviewDTO`, inviato com'è.
- **Date dell'evento** (RNF-010): `start_at` ed `end_at` sono `datetime` **con fuso**; senza
  fuso → `ValueError` prima di qualunque chiamata. La libreria invia
  `event.startAt.localDatetime` ed `event.endAt.localDatetime` come data-ora locale senza
  offset (`YYYY-MM-DDTHH:MM:SS`) ed `event.timezone` con il nome IANA del fuso di `start_at`;
  `end_at` è convertito nel fuso di `start_at`. Con un offset fisso (nessun nome IANA) si converte
  in UTC e si invia `"UTC"`. In `edit_event` e `copy_event`, dove `start_at` è facoltativo, il
  fuso viene da `start_at` se passato, altrimenti da `end_at`.
- **Invitati**: `invited_user_ids` e `invited_group_ids` diventano `event.invitations.users` e
  `event.invitations.groups` come liste di `{"id": N}`; con `invitation_type_id` ogni elemento ha
  anche `"typeId"` (0 guest, 2 collaborator), uguale per tutti; senza, decide il server.
  `send_edit_post_notifications` va in `event.invitations.sendEditPostNotifications`. Tipi diversi
  per singolo invitato si passano con `*_raw`.
- **Modificare**: `edit_event(post_id, occ_token, *, start_at=None, end_at=None, all_day=None,
  location=None, invited_user_ids=None, invited_group_ids=None, invitation_type_id=None,
  send_edit_post_notifications=None, title=None, description=None, description_format=None,
  cover_image_content_ref=None, add_attachments=None, update_attachments=None,
  remove_attachment_ids=None, add_watcher_user_ids=None, remove_watcher_user_ids=None,
  add_watcher_group_ids=None, remove_watcher_group_ids=None, visibility=None,
  link_preview=None, pinned=None, draft=None, scheduled_publication=None)` → `PostWriteResult`
  con il `next_occ_token`. Il blocco `event` compare solo se almeno un kwarg dell'evento è
  passato, con le sole chiavi passate. `occ_token` viene da `EventPostForEdit.occ_token`.
- **Copiare**: `copy_event(post_id, occ_token, *, …gli stessi kwargs di edit_event più
  announcement=None e client_uid=None…)` → `PostWriteResult` con il `post_id` del post nuovo.
  `occ_token` viene da `EventPostForCopy`.
- **Partecipare**: `participate(post_id, answer, *, notes=None)` → `None` (il server risponde
  senza corpo). `answer` è un `ParticipationAnswer` (`YES = 1`, `MAYBE = 2`, `NO = 3`, enum
  intero: accetta anche `1`, `2`, `3`). Risponde l'identità autenticata: con il service account
  l'identità tecnica, con Google OAuth2 l'utente collegato. `participate_raw(post_id, req:
  EditPostEventPartecipateRequestDTO)`.
- Watcher, allegati, eliminazione, marcatura per cancellazione e commenti dei post evento usano i
  metodi della spec 03 (`edit_watchers`, `edit_attachments`, `delete`, `mark_as_erasable`,
  `add_comment`): gli endpoint sono gli stessi per ogni tipo di post.

### CLI

Tutti i comandi stanno sotto `posts`, con i testi in inglese e `render_output` (`--output`,
`--full`, `--fields`, `--export`; `--web-url` dove c'è un post da linkare). `--json FILE|-`
prende il DTO completo e vale per i campi senza flag (`linkPreview`, inviti con tipi diversi,
allegati già noti); i flag prevalgono campo per campo e, dentro `event`, chiave per chiave;
`--invite-user` e `--invite-group` sostituiscono per intero `invitations.users` e
`invitations.groups`. `--description` invia testo semplice (formato `2`). Su `409` il comando
esce con exit code `9` e il messaggio `Post POST_ID changed since it was read: fetch it again and
retry`; mai un secondo tentativo.

- **Date in CLI**: `--start` ed `--end` sono date-ora ISO 8601 (`2026-11-05T10:00:00`) oppure
  sole date (`2026-11-05`, che vale mezzanotte locale), interpretate nel fuso di `--timezone`
  (IANA; predefinito `Europe/Rome` in `create-event`); con un offset esplicito `--timezone` è
  ignorato e si invia in UTC (RNF-010). `--all-day` invia `allDay: true` e lascia le date come
  date; l'effetto sul tenant si verifica a mano e si documenta.
- `posts create-event COMMUNITY_ID --start ISO [--end ISO] [--timezone IANA] [--all-day]
  [--location TEXT] [--invite-user ID]… [--invite-group ID]… [--invite-type N]
  [--notify-on-edit] [--title T] [--description TEXT] [--cover PATH] [--attach PATH]…
  [--watcher-user ID]… [--watcher-group ID]… [--visibility N] [--announcement] [--pinned]
  [--draft] [--scheduled-publication ISO] [--client-uid UID] [--json FILE|-]`: crea il post
  evento; tabella con id, community_id, title, start_at, end_at, timezone, location, visibility e
  next_occ_token. Senza `--start` e senza `event.startAt` in `--json` esce con exit `2` e nessuna
  richiesta parte. `--cover PATH` carica il file con l'upload della spec 04 e mette il
  `contentRef` in `coverImageContentRef`; `--attach` accoda gli allegati; al primo upload fallito
  esce `11` senza scrittura. `--announcement` e `--pinned` inviano `true`; altrimenti le chiavi
  mancano.
- `posts edit-event POST_ID [--occ-token N] [stessi flag di create-event tranne --announcement e
  --client-uid] [--remove-watcher-user ID]… [--remove-watcher-group ID]…` è una **patch**
  (RF-021b): legge `event-post-data-for-edit`, costruisce il corpo dai dati letti (`title`,
  `description` dal delta letto con `descriptionFormat: 1`, `visibility`,
  `coverImageContentRef`, e il blocco `event` letto **ripulito**: `startAt` ed `endAt` con il solo
  `localDatetime`, `timezone`, `allDay`, `location`, `invitations` con utenti e gruppi tradotti in
  `{id, typeId}` (RF-021d) e `sendEditPostNotifications`; i campi di sola lettura
  `zonedDatetime`, `utcDatetime`, `participantsCount`, `participate`, `participateTypeId` non si
  rimandano; le chiavi lette come `null` mancano), vi sovrappone `--json` e poi i flag, e invia con
  l'`occToken` letto. Senza `--timezone`, `--start` ed `--end` sono interpretati nel fuso
  dell'evento letto (se c'è), altrimenti in `Europe/Rome`; con `--timezone` il fuso dell'evento
  cambia. `pinned`, bozza, pubblicazione programmata, watcher e allegati non compaiono nel corpo
  se non con i flag o `--json`. `--occ-token N` impone solo il token; la lettura avviene comunque.
- `posts copy-event POST_ID [stessi flag di create-event] [--occ-token N]`: patch come
  `edit-event` con base da `event-post-data-for-copy` (gli stessi campi più `announcement` letto)
  e invio di `copy-event-post` con il token letto. Mostra il post nuovo.
- `posts participate POST_ID yes|maybe|no [--notes TEXT]`: una `PUT`; stampa `Participation to
  post POST_ID recorded: yes` e, con `--output json`, `{"post_id", "answer", "type_id"}`. Una
  risposta diversa dalle tre → exit `2`, nessuna richiesta.
- `posts get-event-for-create COMMUNITY_ID`, `posts get-event-for-edit POST_ID
  [--no-attachments]`, `posts get-event-for-copy POST_ID [--no-attachments]`: mostrano i dati
  propedeutici; la tabella di `get-event-for-edit` e `get-event-for-copy` ha in testa `occ_token`,
  poi title, start_at, end_at, timezone, all_day, location, participants_count, visibility (e
  community_id per `edit`).

### Documentazione e test

`docs/api/posts.md` (sezione "Event posts": metodi, façade `EventData`, `ParticipationAnswer`,
formato delle date, inviti, semantica dei campi omessi come verificata sul tenant; via "Event posts
(type 2) are read-only for now"), `docs/cli.md` (i sette comandi), `docs/testing.md` e
`tests/integration/.env.example` (`PYNTERACTA_TEST_EVENT_COMMUNITY_ID`), `docs/index.md` e
`README.md` (la superficie di scrittura copre post custom ed evento, commenti, workflow, task,
anagrafiche admin e allegati; via "Event posts follow"; senza numeri di versione). Fixture JSON e
contract test per i DTO evento. Snapshot `syrupy` dei comandi. Integration test opt-in con il
ciclo completo su una community di prova che ammette post evento, con pulizia garantita.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 08-C01 | Quando si chiama `client.posts.create_event(79, start_at=datetime(2026, 11, 5, 10, 0, tzinfo=ZoneInfo("Europe/Rome")), end_at=datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo("Europe/Rome")), location="Sala A", invited_user_ids=[7], invited_group_ids=[3], invitation_type_id=2, send_edit_post_notifications=True, title="T", description="D", description_format=2, cover_image_content_ref="ref-1", watcher_user_ids=[8], watcher_group_ids=[4], pinned=True, announcement=False, client_uid="uid-1")`, parte una sola `POST …/communication/posts/manage/create-event-post/79` con corpo `{"title": "T", "description": "D", "descriptionFormat": 2, "coverImageContentRef": "ref-1", "watcherUserIds": [8], "watcherGroupIds": [4], "announcement": false, "clientUid": "uid-1", "pinned": true, "event": {"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "endAt": {"localDatetime": "2026-11-05T12:00:00"}, "timezone": "Europe/Rome", "location": "Sala A", "invitations": {"users": [{"id": 7, "typeId": 2}], "groups": [{"id": 3, "typeId": 2}], "sendEditPostNotifications": true}}}` (nessun'altra chiave) e, con una risposta `CreatePostResponseDTO`, il risultato ha `post_id`, `next_occ_token`, `post.title` e `.raw` dalla risposta. | RF-021, RNF-010 |
| 08-C02 | Quando si chiama `create_event(79, start_at=<10:00 Europe/Rome>)` senza altri kwargs, il corpo è `{"event": {"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "timezone": "Europe/Rome"}}` (niente `announcement`); con `invited_user_ids=[7]` senza `invitation_type_id` gli invitati sono `[{"id": 7}]`; con `end_at` nel fuso `UTC` (`11:00+00:00`) e `start_at` in `Europe/Rome`, `endAt.localDatetime` è `2026-11-05T12:00:00` e `timezone` resta `Europe/Rome`; con `start_at` a offset fisso `+02:00` (`10:00`) si invia `localDatetime: "2026-11-05T08:00:00"` e `timezone: "UTC"`. | RF-021, RNF-010 |
| 08-C03 | Quando `start_at` o `end_at` è un `datetime` senza fuso, `create_event`, `edit_event` e `copy_event` sollevano `ValueError` e nessuna richiesta parte. | RNF-010 |
| 08-C04 | Quando si chiama `create_event_raw(79, CreateEventPostRequestDTO(title="T", event={"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "timezone": "Europe/Rome"}))`, la richiesta e il risultato sono gli stessi di 08-C01 con quel corpo; lo stesso vale per `edit_event_raw`, `copy_event_raw`, `participate_raw` con il DTO equivalente. | RF-021 |
| 08-C05 | Quando si chiama `client.posts.edit_event(21269, 5, location="Sala B", add_watcher_group_ids=[4], remove_watcher_user_ids=[8], pinned=False, cover_image_content_ref="ref-2")`, parte una sola `PUT …/communication/posts/manage/edit-event-post/21269/5` con corpo `{"coverImageContentRef": "ref-2", "addWatcherGroupIds": [4], "removeWatcherUserIds": [8], "pinned": false, "event": {"location": "Sala B"}}` e il risultato ha `next_occ_token` e `post` dalla risposta `EditPostResponseDTO`; con il solo `end_at=<12:00 Europe/Rome>` il corpo è `{"event": {"endAt": {"localDatetime": "2026-11-05T12:00:00"}, "timezone": "Europe/Rome"}}`; con tutti i kwargs a `None` il corpo è `{}` (nessuna chiave `event`). | RF-021, RF-025 |
| 08-C06 | Quando si chiama `client.posts.copy_event(21269, 5, title="Copia", announcement=True, client_uid="uid-2", start_at=<10:00 Europe/Rome>)`, parte una sola `PUT …/copy-event-post/21269/5` con corpo `{"title": "Copia", "announcement": true, "clientUid": "uid-2", "event": {"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "timezone": "Europe/Rome"}}` e il risultato ha `post_id` (del post nuovo) e `next_occ_token` dalla risposta `CopyPostResponseDTO`. | RF-021, RF-025 |
| 08-C07 | *Sostituito da 08-C29 il 2026-10-13 (T16: le note vanno in formato delta).* ~~Quando si chiama `client.posts.participate(21269, ParticipationAnswer.YES, notes="Arrivo tardi")`, parte una sola `PUT …/post-event/21269/partecipate` con corpo `{"typeId": 1, "notes": "Arrivo tardi"}` e il metodo restituisce `None` su risposta `200` senza corpo; `participate(21269, 3)` invia `{"typeId": 3}`; `ParticipationAnswer(2) is ParticipationAnswer.MAYBE`; un valore diverso da 1, 2, 3 → `ValueError` senza richiesta.~~ | RF-021 |
| 08-C08 | Quando il server risponde `409` a `edit_event` o `copy_event`, viene sollevata `ConcurrencyError` con `status_code == 409` e il server ha ricevuto **esattamente una** richiesta. | RF-025, RNF-009 |
| 08-C09 | Quando il server risponde `404` a `participate`, viene sollevata `NotFoundError`; `403` → `PermissionError`; quando risponde `400` con un `CustomFieldValidationErrorResponseDTO` a `create_event`, viene sollevata `ValidationError` con `response_body` che contiene `validationErrors`; in ogni caso una sola richiesta; in CLI gli exit code sono `5`, `4` e `6`. | RF-019, RF-021 |
| 08-C10 | Quando `create_event` o `participate` va in timeout o errore di rete, viene sollevata `TransportError` e il server ha ricevuto al più una richiesta. | RNF-009 |
| 08-C11 | Quando si chiama `get_event_for_create(79)`, parte una `GET …/event-post-data-for-create/79` e il risultato ha `content_data`; quando si chiama `get_event_for_edit(21269)`, parte una `GET …/event-post-data-for-edit/21269` senza query (con `load_attachments=False` la query è `loadAttachments=false`) e il risultato ha `occ_token`, `community_id`, `content_data.title`, `content_data.coverImageContentRef` e `event` con `start_at == datetime(2026, 11, 5, 10, 0, tzinfo=ZoneInfo("Europe/Rome"))`, `end_at`, `timezone == "Europe/Rome"`, `all_day`, `location`, `participants_count`, `my_answer == ParticipationAnswer.YES` (dalla fixture con `participateTypeId: 1`; `None` quando manca), `invited_users[0].id == 7`, `invited_users[0].type_id == 2`, `invited_groups[0].id == 3`, `send_edit_post_notifications`; quando si chiama `get_event_for_copy(21269)`, parte una `GET …/event-post-data-for-copy/21269` e il risultato ha `occ_token`, `content_data` ed `event`. Quando la risposta non ha `event`, `event` è `None`. | RF-021, RF-021a |
| 08-C12 | *Sostituito da 08-C31 il 2026-10-13 (T16: le risposte di scrittura non hanno `event`).* ~~Quando si esegue `posts create-event 79 --start 2026-11-05T10:00:00 --end 2026-11-05T12:00:00 --location "Sala A" --invite-user 7 --invite-group 3 --invite-type 2 --notify-on-edit --title T --description D --watcher-user 8 --watcher-group 4 --announcement --pinned --json body.json` con `body.json` = `{"title": "X", "visibility": 1, "linkPreview": {"url": "https://example.org"}, "event": {"allDay": false, "invitations": {"users": [{"id": 99}]}}}`, il corpo inviato è `{"title": "T", "description": "D", "descriptionFormat": 2, "visibility": 1, "linkPreview": {"url": "https://example.org"}, "watcherUserIds": [8], "watcherGroupIds": [4], "announcement": true, "pinned": true, "event": {"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "endAt": {"localDatetime": "2026-11-05T12:00:00"}, "timezone": "Europe/Rome", "allDay": false, "location": "Sala A", "invitations": {"users": [{"id": 7, "typeId": 2}], "groups": [{"id": 3, "typeId": 2}], "sendEditPostNotifications": true}}}` (i flag prevalgono; `event` unito chiave per chiave; `--invite-user` sostituisce `users`) e la tabella mostra id, community_id, title, start_at, end_at, timezone, location, visibility e next_occ_token; `--output json` restituisce la risposta serializzata. Senza `--announcement` e `--pinned` le due chiavi mancano.~~ | RF-021, RF-015 |
| 08-C13 | *Sostituito da 08-C25 il 2026-10-13 (T16: un evento `allDay` vuole date senza ora e nessun fuso).* ~~Quando si esegue `posts create-event 79 --start 2026-11-05 --all-day`, il corpo ha `startAt.localDatetime == "2026-11-05T00:00:00"`, `timezone == "Europe/Rome"` e `allDay: true`; con `--start 2026-11-05T10:00:00+02:00` il corpo ha `localDatetime == "2026-11-05T08:00:00"` e `timezone == "UTC"`; con `--timezone America/New_York` il fuso inviato è quello; con `--timezone Nowhere/Town` o `--start` non ISO esce con exit `2`; senza `--start` e senza `event.startAt` in `--json` esce con exit `2`; in tutti i casi di errore nessuna richiesta parte.~~ | RF-021, RF-015, RNF-010 |
| 08-C14 | Quando si esegue `posts edit-event 21269 --title T2 --location "Sala B"` e la `GET …/event-post-data-for-edit/21269` restituisce `occToken: 5` e `contentData` con `descriptionDelta`, `visibility: 2`, `coverImageContentRef: "ref-1"` ed `event` `{"startAt": {"zonedDatetime": "2026-11-05T10:00:00+01:00", "localDatetime": "2026-11-05T10:00:00", "utcDatetime": "…"}, "endAt": {…"localDatetime": "2026-11-05T12:00:00"…}, "timezone": "Europe/Rome", "allDay": false, "location": "Sala A", "participantsCount": 3, "participate": true, "participateTypeId": 1, "invitations": {"users": [{"id": 7, "firstName": "Alice", "typeId": 2}], "groups": [{"id": 3, "name": "G", "typeId": 0}], "sendEditPostNotifications": false}}`, la `PUT …/edit-event-post/21269/5` ha corpo `{"title": "T2", "description": <delta letto>, "descriptionFormat": 1, "visibility": 2, "coverImageContentRef": "ref-1", "event": {"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "endAt": {"localDatetime": "2026-11-05T12:00:00"}, "timezone": "Europe/Rome", "allDay": false, "location": "Sala B", "invitations": {"users": [{"id": 7, "typeId": 2}], "groups": [{"id": 3, "typeId": 0}], "sendEditPostNotifications": false}}}` e nessun'altra chiave; con `--occ-token 3` la `GET` avviene lo stesso e la `PUT` usa `3`; quando il post letto non ha descrizione, copertina o `endAt`, le chiavi corrispondenti mancano. | RF-021, RF-021b, RF-021d, RF-025 |
| 08-C15 | Sul post di 08-C14, `posts edit-event 21269 --start 2026-11-06T09:00:00` senza `--timezone` invia `startAt.localDatetime == "2026-11-06T09:00:00"` e `timezone == "Europe/Rome"` (il fuso letto) lasciando `endAt` letto; con `--timezone America/New_York` invia `timezone == "America/New_York"`; `--invite-user 9` sostituisce `invitations.users` con `[{"id": 9}]` e lascia `groups` letti; `--json body.json` con `{"event": {"location": "Sala C"}, "pinned": true}` dà `location: "Sala C"` (json > letto) e `pinned: true`, mentre un flag `--location "Sala D"` vince sul json. | RF-021, RF-021b |
| 08-C16 | Quando si esegue `posts copy-event 21269 --title Copia` e la `GET …/event-post-data-for-copy/21269` restituisce `occToken: 5` e `contentData` con `title`, `descriptionDelta`, `visibility`, `announcement: true` ed `event` come in 08-C14, la `PUT …/copy-event-post/21269/5` ha corpo `{"title": "Copia", "description": <delta letto>, "descriptionFormat": 1, "visibility": <letta>, "announcement": true, "event": <blocco ripulito di 08-C14 con location "Sala A">}` e la tabella mostra il post nuovo con il suo id. | RF-021, RF-021b, RF-021d |
| 08-C17 | *Sostituito da 08-C30 il 2026-10-13 (T16: le note vanno in formato delta).* ~~Quando si esegue `posts participate 21269 yes --notes "Arrivo tardi"`, parte una sola `PUT …/post-event/21269/partecipate` con corpo `{"typeId": 1, "notes": "Arrivo tardi"}` e il comando stampa `Participation to post 21269 recorded: yes`; `maybe` e `no` inviano `2` e `3`; con `--output json` stampa `{"post_id": 21269, "answer": "yes", "type_id": 1}`; con `perhaps` esce con exit `2` e nessuna richiesta parte.~~ | RF-021, RF-015 |
| 08-C18 | Quando si esegue `posts create-event 79 --start 2026-11-05T10:00:00 --cover cover.png --attach doc.pdf`, i due file sono caricati nell'ordine con il meccanismo della spec 04, il corpo ha `coverImageContentRef` con il `contentRef` della copertina e `attachments: [{"name": "doc.pdf", "contentRef": …}]`; quando l'upload della copertina fallisce (`UploadError`), il comando esce `11`, l'allegato non viene caricato e nessuna `POST` parte. Lo stesso vale per `--cover` di `edit-event` (in `coverImageContentRef`, che vince sul valore letto) e `copy-event`. | RF-024, RF-024a, RF-021c |
| 08-C19 | Quando la `PUT` di `posts edit-event` o `posts copy-event` risponde `409`, il comando termina con exit code `9`, stampa `Post 21269 changed since it was read: fetch it again and retry` e il server ha ricevuto una sola richiesta di scrittura. | RF-025, RF-015a, RNF-009 |
| 08-C20 | Quando si esegue `posts get-event-for-edit 21269`, la tabella ha in testa `occ_token` seguito da community_id, title, start_at, end_at, timezone, all_day, location, participants_count, visibility; `posts get-event-for-copy 21269` mostra `occ_token`, title e i campi dell'evento; `posts get-event-for-create 79` mostra i dati di `content_data`; `--no-attachments` manda `loadAttachments=false`; `--output json` e `--full` restituiscono il DTO intero. | RF-021a, RF-015 |
| 08-C21 | La funzione che ricava il blocco `event` da scrivere da un evento letto restituisce, per l'`event` di 08-C14, il blocco ripulito di 08-C14; per `{"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "timezone": "Europe/Rome"}` → lo stesso; per `{"invitations": {"users": [{"id": 7}]}}` → `{"invitations": {"users": [{"id": 7}]}}` (senza `typeId` se non letto); per `None` → `{}`. | RF-021d |
| 08-C22 | I contract test dimostrano che i modelli generati `CreateEventPostRequestDTO`, `EditEventPostRequestDTO`, `CopyEventPostRequestDTO`, `EditPostEventPartecipateRequestDTO`, `GetEventPostForCreateResponseDTO`, `GetEventPostForEditResponseDTO`, `GetEventPostForCopyResponseDTO`, `EventPostEditableContentDataDTOModel`, `EventPostDataDTOModel`, `EventDatetimeDTO`, `EventPostInvitationsDataDTO1`, `InvitationUserDTO1`, `InvitationGroupDTO1` coprono tutte le proprietà del swagger pinnato, e le fixture JSON di risposta si leggono nelle façade. | RF-021, RNF-003 |
| 08-C23 | `docs/cli.md` documenta i sette comandi di questa spec; `docs/api/posts.md` ha la sezione "Event posts" (metodi, `EventData`, `ParticipationAnswer`, date, inviti, semantica dei campi omessi) e non dice più che i post evento sono di sola lettura; `docs/index.md` e `README.md` dicono che la scrittura copre tutti i gruppi dell'ADR 0001, senza "Event posts follow" e senza numeri di versione; `docs/testing.md` e `.env.example` hanno `PYNTERACTA_TEST_EVENT_COMMUNITY_ID`; `uv run mkdocs build --strict` e `test_docs_snippets` sono verdi. | RF-015 |
| 08-C24 | Quando `PYNTERACTA_TEST_EVENT_COMMUNITY_ID` e `PYNTERACTA_TEST_USER_ID` sono impostate (integration, opt-in), il ciclo `create_event` (con `client_uid` riconoscibile, `start_at`/`end_at` nel futuro, l'utente di prova invitato) → `get_by_client_uid` → `get_event_for_edit` (occ_token, `event.start_at` uguale all'istante inviato) → `edit_event` (titolo e luogo nuovi, blocco letto rimandato ripulito) → `participate(YES)` → `get_event_for_copy` → `copy_event` → `delete` della copia → `delete` dell'originale termina senza errori sul tenant e i due post rispondono `404` al termine; la pulizia avviene anche se un passo intermedio fallisce; senza una delle variabili il test è saltato. | RF-021, RF-025 |
| 08-C25 | Quando si esegue `posts create-event 79 --start 2026-11-05 --all-day`, il blocco `event` del corpo ha `startAt == {"localDatetime": "2026-11-05"}`, `allDay: true` e nessuna chiave `timezone`; con `--start 2026-11-05T10:00:00 --end 2026-11-06T18:00:00 --all-day` le date sono `"2026-11-05"` e `"2026-11-06"`; senza `--all-day`, `--start 2026-11-05` dà `localDatetime == "2026-11-05T00:00:00"` e `timezone == "Europe/Rome"`; con `--start 2026-11-05T10:00:00+02:00` il corpo ha `localDatetime == "2026-11-05T08:00:00"` e `timezone == "UTC"`; con `--timezone America/New_York` il fuso inviato è quello; con `--timezone Nowhere/Town` o `--start` non ISO esce con exit `2`; senza `--start` e senza `event.startAt` in `--json` esce con exit `2`; in tutti i casi di errore nessuna richiesta parte. | RF-021, RF-015, RNF-010 |
| 08-C26 | Quando si chiama `create_event(79, start_at=date(2026, 11, 5), end_at=date(2026, 11, 6), all_day=True)`, il blocco `event` del corpo è `{"startAt": {"localDatetime": "2026-11-05"}, "endAt": {"localDatetime": "2026-11-06"}, "allDay": true}` (nessun `timezone`); con `all_day=True` e `start_at=datetime(2026, 11, 5, 23, 30, tzinfo=ZoneInfo("Europe/Rome"))` si invia `"2026-11-05"` (la data nel fuso del valore) e un `datetime` senza fuso è accettato; un `date` che non è un `datetime`, senza `all_day=True`, solleva `ValueError` e nessuna richiesta parte; lo stesso vale per `edit_event` e `copy_event`. | RF-021, RNF-010 |
| 08-C27 | Quando `posts edit-event 21269 --start 2026-11-06` legge un evento con `allDay: true`, `startAt.localDatetime == "2026-11-05"`, `endAt.localDatetime == "2026-11-05"` e `timezone: null`, la `PUT` ha `event` con `startAt == {"localDatetime": "2026-11-06"}`, `endAt == {"localDatetime": "2026-11-05"}`, `allDay: true` e nessun `timezone`; lo stesso vale per `posts copy-event` e per `posts create-event` quando `allDay: true` arriva da `--json`: con `allDay: true` nel blocco unito le date perdono l'ora e `timezone` sparisce. | RF-021, RF-021f, RNF-010 |
| 08-C28 | Quando l'evento letto ha `startAt` `{"zonedDatetime": "2026-11-05T10:00:00+01:00", "localDatetime": "2026-11-05T10:00:00"}` e `timezone: "Europe/Rome"`, `EventData.start_at == datetime(2026, 11, 5, 10, 0, tzinfo=ZoneInfo("Europe/Rome"))` con `start_at.tzinfo == ZoneInfo("Europe/Rome")`, e `edit_event(21269, 5, start_at=form.event.start_at)` invia `{"localDatetime": "2026-11-05T10:00:00"}` e `timezone: "Europe/Rome"`; quando l'evento ha `allDay: true`, `startAt` `{"zonedDatetime": "2026-11-05", "localDatetime": "2026-11-05", "utcDatetime": "2026-11-05"}` e `timezone: null`, `start_at == date(2026, 11, 5)` e non è un `datetime`, e `posts get-event-for-edit` mostra `start_at` `2026-11-05`; con il solo `zonedDatetime` vale quello; senza `zonedDatetime` e con un `timezone` sconosciuto, `None`. | RF-021, RF-021a, RNF-010 |
| 08-C29 | Quando si chiama `client.posts.participate(21269, ParticipationAnswer.YES, notes="Arrivo tardi")`, parte una sola `PUT …/post-event/21269/partecipate` con corpo `{"typeId": 1, "notes": "[{\"insert\":\"Arrivo tardi\\n\"}]"}` (le note in testo diventano un delta di una riga) e il metodo restituisce `None` su risposta `200` senza corpo; `participate(21269, 3)` invia `{"typeId": 3}`; `participate_raw` invia `notes` così com'è; `ParticipationAnswer(2) is ParticipationAnswer.MAYBE`; un valore diverso da 1, 2, 3 → `ValueError` senza richiesta. | RF-021 |
| 08-C30 | Quando si esegue `posts participate 21269 yes --notes "Arrivo tardi"`, parte una sola `PUT …/post-event/21269/partecipate` con corpo `{"typeId": 1, "notes": "[{\"insert\":\"Arrivo tardi\\n\"}]"}` e il comando stampa `Participation to post 21269 recorded: yes`; `maybe` e `no` inviano `2` e `3`; con `--output json` stampa `{"post_id": 21269, "answer": "yes", "type_id": 1}`; con `perhaps` esce con exit `2` e nessuna richiesta parte. | RF-021, RF-015 |
| 08-C31 | Quando si esegue `posts create-event 79 --start 2026-11-05T10:00:00 --end 2026-11-05T12:00:00 --location "Sala A" --invite-user 7 --invite-group 3 --invite-type 2 --notify-on-edit --title T --description D --watcher-user 8 --watcher-group 4 --announcement --pinned --json body.json` con `body.json` = `{"title": "X", "visibility": 1, "linkPreview": {"url": "https://example.org"}, "event": {"allDay": false, "invitations": {"users": [{"id": 99}]}}}`, il corpo inviato è `{"title": "T", "description": "D", "descriptionFormat": 2, "visibility": 1, "linkPreview": {"url": "https://example.org"}, "watcherUserIds": [8], "watcherGroupIds": [4], "announcement": true, "pinned": true, "event": {"startAt": {"localDatetime": "2026-11-05T10:00:00"}, "endAt": {"localDatetime": "2026-11-05T12:00:00"}, "timezone": "Europe/Rome", "allDay": false, "location": "Sala A", "invitations": {"users": [{"id": 7, "typeId": 2}], "groups": [{"id": 3, "typeId": 2}], "sendEditPostNotifications": true}}}` (i flag prevalgono; `event` unito chiave per chiave; `--invite-user` sostituisce `users`) e la tabella mostra id, community_id, title, visibility e next_occ_token (nessuna colonna dell'evento: le risposte di scrittura non hanno `event`); `--output json` restituisce la risposta serializzata. Senza `--announcement` e `--pinned` le due chiavi mancano. | RF-021, RF-015 |

## Casi limite

- `create_event` con il solo `start_at` → corpo con il solo blocco `event`; decide il server
  (08-C02).
- `end_at` prima di `start_at` → decide il server (`400`), una sola richiesta; la libreria non
  confronta le date.
- `start_at` o `end_at` senza fuso → `ValueError`, nessuna richiesta (08-C03).
- `end_at` in un fuso diverso da `start_at` → convertito nel fuso di `start_at` (08-C02).
- `edit_event` con solo kwargs dell'evento → corpo con il solo `event` parziale; l'effetto sulle
  chiavi dell'evento omesse lo decide il server (08-C05) e si verifica a mano.
- `edit_event` con tutti i kwargs a `None` → `PUT` con corpo `{}` (08-C05).
- `occ_token` sbagliato → `409 → ConcurrencyError`, una sola richiesta (08-C08); in CLI exit `9`
  (08-C19).
- `participate` su un post inesistente o non evento → `404 → NotFoundError`, exit `5` (08-C09);
  `answer` fuori da 1, 2, 3 → `ValueError` prima della chiamata (08-C07).
- `participate` con il service account → risponde l'identità tecnica, se il tenant lo ammette;
  lo si verifica a mano (08-C24) e si documenta.
- `posts edit-event`, `posts copy-event` su un post che la lettura propedeutica non trova → exit
  `5`, nessuna scrittura, anche con `--occ-token`; su un post custom la lettura risponde `404` o
  `400`: decide il server, nessuna scrittura.
- `posts edit-event` con `--json` che contiene `event` → unione chiave per chiave con il blocco
  letto, poi i flag (08-C15); `invitations` dentro `--json` sostituisce per intero quelle lette.
- `posts edit-event` con `--start` e senza `--timezone` → fuso dell'evento letto (08-C15); se
  l'evento letto non ha `timezone`, `Europe/Rome`.
- `--start 2026-11-05` (sola data) → mezzanotte locale (08-C25); `--all-day` con date-ora →
  inviate come sole date, senza fuso (08-C25, 08-C27).
- `--invite-type` senza `--invite-user` né `--invite-group` → ignorato, nessun errore.
- `--invite-user` senza `--invite-type` → `[{"id": N}]` (08-C02): il server lo tratta come
  ospite (T16).
- Invitati obbligatori e almeno un ospite (T16): senza, o con soli collaboratori, il server
  risponde `400 REQUIRED_FIELD event.inivations`; la lettura propedeutica restituisce gli
  invitati vuoti, quindi `posts edit-event` e `posts copy-event` vanno usati con `--invite-user`
  o `--invite-group` (o `invitations` in `--json`). La libreria non controlla: decide il server.
- `--cover` fallito → exit `11`, nessuna scrittura; upload riuscito ma `PUT` in `409` → exit `9`,
  il file resta nello storage temporaneo fino alla scadenza della policy del tenant (08-C18).
- `--json -` con stdin vuoto o JSON non valido, o chiavi sconosciute al DTO → exit `2`, nessuna
  richiesta (`load_json_body` esistente).
- Timeout **dopo** l'invio di `create_event` → il post potrebbe esistere; `TransportError`, nessun
  nuovo tentativo (08-C10); il chiamante può cercarlo con `get_by_client_uid`.
- `posts delete`, `posts mark-erasable`, `posts comment`, `posts edit-watchers`,
  `posts edit-attachments` su un post evento → comandi della spec 03, invariati.

## Dati personali e segreti

Passano al tenant: titolo, descrizione, luogo dell'evento, id di invitati (utenti e gruppi) e di
watcher, note di partecipazione, riferimenti ad allegati e copertina, `client_uid`. La libreria li
inoltra e non li conserva; l'audit log opzionale li registra solo con `audit_log_bodies`
(eccezione documentata). Nei log applicativi compaiono solo metodo, URL redatto e stato. L'output
dei comandi mostra nomi di invitati e watcher letti dal form, come già `posts get`: è output per
l'operatore, non log. La copertina passa dallo storage temporaneo come gli allegati (RNF-011).
Nessun segreto nuovo. Gli integration test usano una community di prova dedicata
(`PYNTERACTA_TEST_EVENT_COMMUNITY_ID`), un `client_uid` riconoscibile
(`pynteracta-it-event-<timestamp>`) e invitano il solo utente di prova (`PYNTERACTA_TEST_USER_ID`),
già usato come watcher dalla spec 03; la risposta di partecipazione è quella del service account
di prova.

## Requisiti nuovi

- RF-021e (precisa RF-021). Post evento: `create_event`, `edit_event`, `copy_event`,
  `participate` e le letture `get_event_for_create|edit|copy` stanno su `client.posts` con un
  kwarg per campo del DTO; il blocco `event` lo compone la libreria; `start_at` ed `end_at` sono
  `datetime` con fuso, inviati come data-ora locale più il nome IANA del fuso di `start_at`
  (RNF-010), o sole date senza fuso per gli eventi `all_day`; in lettura sono nel fuso
  dell'evento, `date` per gli eventi tutto il giorno; gli invitati si passano per id con un tipo unico facoltativo; la risposta di
  partecipazione è `ParticipationAnswer` (sì 1, forse 2, no 3), con note in testo inviate come
  delta, e vale per l'identità autenticata.
  Le letture propedeutiche espongono `occ_token` e i dati dell'evento tipizzati (`EventData`).
- RF-021f (precisa RF-021b, RF-021d). In CLI: `posts create-event|edit-event|copy-event|
  participate|get-event-for-create|get-event-for-edit|get-event-for-copy`. `edit-event` e
  `copy-event` sono patch che rileggono il form evento e rimandano titolo, descrizione,
  visibilità, copertina e il blocco `event` ripulito dai campi di sola lettura, con gli invitati
  tradotti in `{id, typeId}`; `--start`/`--end` accettano data-ora o sola data nel fuso di
  `--timezone` (in `edit-event`, per default quello dell'evento letto); `--cover` carica la
  copertina (RF-024a).
- Aggiornamento di RF-021 ("i post evento restano da fare" → realizzati dalla spec 08) e di §1
  del PRD (la superficie di scrittura dell'ADR 0001 è completa).

## Fuori ambito

- Filtro eventi dell'elenco in community (`eventPostFilter`: luogo, intervalli di inizio e fine)
  come kwargs e flag: spec di lettura a parte (RF-006); oggi via `list_in_community_raw`.
- Blocco `event` nel dettaglio del post (`posts get`): il swagger pinnato non lo prevede; se il
  tenant lo restituisce resta in `.raw`.
- Flag CLI per `linkPreview` (solo `--json`) e tipi di invito diversi per singolo invitato (solo
  `--json` o `*_raw`).
- Post questionario (tipo 3): nessun endpoint di scrittura nel swagger.
- Lettura dell'elenco dei partecipanti e delle risposte degli altri invitati: nessun endpoint.
- Retry automatico e risoluzione automatica del `409` (RNF-009, ADR 0001).
- Traduzione in italiano della CLI esistente.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Kwargs piatti per l'evento (`start_at`, `end_at`, `all_day`, `location`, inviti…); il blocco `event` lo compone la libreria | Blocco `event=` passante come `custom_data`; entrambi | Un kwarg per campo (spec 02 e 03), scopribile da un agente; le date restano `datetime` con fuso |
| Metodi su `client.posts` con suffisso `_event` | Sotto-risorsa `client.posts.events`; risorsa `client.event_posts` | Stesso posto dei post custom, nomi che ricalcano gli endpoint; nessun livello in più |
| Comandi piatti `posts create-event`, `edit-event`, `copy-event`, `participate`, `get-event-for-*` | Sottogruppo `posts events …`; solo libreria | Come i quattordici comandi della spec 03; ogni scrittura ha il suo comando (ADR 0001) |
| Tutti i campi extra dei DTO evento come kwargs; in CLI `--cover PATH`, `--watcher-group`, `--pinned`; `linkPreview` solo via `--json` | Solo via `--json`; solo copertina e gruppi | Un kwarg per campo; `--cover` riusa l'upload della spec 04 come `edit-workspace` |
| Date come `datetime` con fuso; `timezone` ricavato da `start_at` (da `end_at` se `start_at` manca); `end_at` convertito; offset fisso → UTC | Datetime naive più kwarg `timezone`; stringhe passanti | Stessa regola di `expiration` e `scheduled_publication` (RNF-010); nessuna validazione a carico del chiamante |
| Inviti per id (`invited_user_ids`, `invited_group_ids`) con `invitation_type_id` unico e `send_edit_post_notifications` | Blocco `invitations=` passante; coppie `ID=TIPO` | Forma semplice per l'uso comune; i tipi per singolo invitato restano in `*_raw` e `--json` |
| `participate(post_id, answer, *, notes=None)` con enum `ParticipationAnswer`; CLI `posts participate POST_ID yes\|maybe\|no` | Solo intero; tre metodi accept/maybe/decline | Un endpoint, un metodo; leggibile senza conoscere i codici |
| `announcement` inviato solo se passato | Sempre inviato come nella spec 03 | Nel DTO evento non è obbligatorio: vale la regola "solo i campi passati" |
| `posts edit-event` e `posts copy-event` come patch sul form evento, con il blocco `event` ripulito dai campi di sola lettura e gli invitati tradotti in `{id, typeId}` | Solo i campi passati; decidere dopo la prova | Sui post custom il server sostituisce (spec 03, T16); i campi di sola lettura e gli oggetti completi sarebbero rifiutati (RF-021d). Se il server non azzera, si riduce la base con una revisione |
| In `edit-event` le date senza `--timezone` sono nel fuso dell'evento letto | Sempre `Europe/Rome` | Evita di spostare un evento cambiando fuso per sbaglio |
| `--start`/`--end` accettano anche la sola data (mezzanotte locale); `--all-day` è un flag | Solo data-ora; forme esclusive | Stessa forma di `--scheduled-publication`, un caso in più per gli eventi tutto il giorno |
| Integration test con variabile nuova `PYNTERACTA_TEST_EVENT_COMMUNITY_ID` e ciclo completo, partecipazione compresa | Riusare la community dei post custom; nessun test | La community di prova potrebbe non ammettere eventi: con la variabile il test salta invece di fallire; la partecipazione del service account è da verificare |
| Letture (filtro eventi, blocco `event` nel dettaglio) fuori ambito | Includere il filtro; includere il dettaglio | La spec resta sulle scritture; il dettaglio non ha `event` nel swagger pinnato |
| README, home del sito e PRD §1 dichiarano completa la superficie di scrittura dell'ADR 0001 | Solo `docs/api/posts.md` e `docs/cli.md` | "Event posts follow" sarebbe falso dopo il merge; l'ADR non si modifica |
| Riga `0.14.0` in ROADMAP (minor) | – | I `feat` producono un minor (politica pre-1.0) |
| Eventi `all_day`: date senza ora e nessun `timezone`, nella libreria (`date` o `datetime`) e in CLI (anche sul blocco unito) (revisione del 2026-10-13) | Lasciare decidere il server; kwarg separati `start_date`/`end_date` | Il server rifiuta ora e fuso sugli eventi tutto il giorno (T16); stessi kwarg, un solo modo di passare le date |
| `EventData.start_at`/`end_at` da `localDatetime` più `timezone` IANA, `date` per gli eventi tutto il giorno (revisione del 2026-10-13) | `zonedDatetime` a offset fisso | Rileggere e riscrivere una data non deve spostare l'evento in UTC (T16) |
| Note di partecipazione in testo convertite in un delta di una riga; `participate_raw` le passa com'è (revisione del 2026-10-13) | Solo documentare il formato delta; kwarg `notes_format` | Il server rifiuta il testo semplice (T16); il chiamante comune scrive testo, chi ha un delta usa `*_raw` |
| Tabella delle scritture senza colonne dell'evento (revisione del 2026-10-13) | Colonne sempre vuote documentate | Il server non restituisce `event` in `postData` (T16) |

## Verifica manuale

- La semantica dei campi omessi in `edit-event-post` e `copy-event-post` (invariati o azzerati,
  per il post e per le chiavi del blocco `event`), se il server esige `typeId` negli invitati e
  quale sia il default, l'effetto di `allDay` sulle date, l'accettazione della partecipazione da
  parte del service account e il formato della descrizione in modifica non sono documentati dallo
  swagger: si stabiliscono eseguendo 08-C24 e prove a mano sulla community di prova, in un task
  dedicato. L'esito si registra in `docs/api/posts.md` e in `verifica.md`; se il server non azzera
  i campi omessi, la base delle patch in CLI si riduce con una revisione della spec (08-C14,
  08-C15, 08-C16); se esige `typeId`, `invitation_type_id` prende un default documentato. Fino a
  quell'esecuzione 08-C24 vale come saltato.

## Revisioni

- 2026-10-13, dopo T16: gli eventi `allDay` vogliono date senza ora e nessun fuso; le date lette
  a offset fisso spostavano in UTC un evento riscritto; le note di partecipazione vanno in delta;
  le risposte di scrittura non hanno `event`. 08-C07, 08-C12, 08-C13, 08-C17 sostituiti da
  08-C29, 08-C31, 08-C25, 08-C30; nuovi 08-C26, 08-C27, 08-C28; task T18 (libreria) e T19 (CLI).
  Invitati obbligatori (almeno un ospite) e campi obbligatori in modifica e copia restano al
  server e si documentano in T17.

## Domande aperte

Nessuna.
