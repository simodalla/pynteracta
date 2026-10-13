# Piano 08 – Scrittura dei post evento

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Si ripete la catena della spec 03 in tre moduli nuovi, senza toccare il transport né il client
base. Le scritture dei post evento stanno in un secondo mixin, `PostsEventAPI` in
`api/posts_event.py`, che `PostsAPI` eredita accanto a `PostsWriteAPI`: `client.posts.*` resta
unico. Ogni metodo costruisce il corpo dai kwargs con `build_write_body` (camelCase, solo i campi
passati); il blocco `event` lo compone una funzione pura, `build_event_block`, che riceve i kwargs
dell'evento e restituisce il dict con le sole chiavi passate, con le date tradotte da
`event_datetime_block` in `api/_utils.py` (stessa regola di `zoned_datetime_input`: fuso IANA o
UTC, `ValueError` senza fuso). Le risposte di creazione, modifica e copia si leggono con il
`PostWriteResult` esistente; le tre letture propedeutiche hanno façade nuove in
`models/facade/posts_event.py`, con `EventData` che rivalida gli stub `RootModel` nelle varianti
tipizzate (`EventPostEditableContentDataDTOModel`, `EventPostDataDTOModel`, `EventDatetimeDTO`,
`InvitationUserDTO1`, `InvitationGroupDTO1`) e `ParticipationAnswer` (`IntEnum`). I due helper di
rivalidazione `_typed`/`_typed_list` di `facade/posts_write.py` si spostano in
`facade/_stubs.py`, condivisi.

Nella CLI i sette comandi stanno in `cli/posts_event.py`, registrati sullo stesso `Typer` di
`cli/posts.py`; riusano `load_json_body`, `merge_body`, `validate_body`, `upload_all`,
`append_attachments`, `handle_error(resource=…)` e le opzioni condivise di `posts_write.py`. Le
patch (`edit-event`, `copy-event`) usano funzioni pure testabili da sole: `event_write_block`
(il blocco `event` letto ripulito e con gli invitati tradotti, 08-C21), `event_edit_base`,
`event_copy_base`, `merge_event`. Le date della CLI passano da `parse_event_datetime` in
`cli/_write.py` (data-ora o sola data, fuso di `--timezone`) e poi dalla stessa
`event_datetime_block` della libreria, così la conversione è una sola. Fixture JSON e contract
test per i DTO; integration test opt-in nel file dei post; pagine `docs/`. Test prima del codice.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `src/pynteracta/api/_utils.py` | modificato | `event_datetime_block(start_at: datetime \| None, end_at: datetime \| None) -> dict[str, Any]`: `{"startAt": {"localDatetime": …}, "endAt": {…}, "timezone": …}` con le sole chiavi dei valori passati; fuso dal primo non `None` tra `start_at` ed `end_at` (`ZoneInfo.key`, altrimenti conversione in UTC e `"UTC"`); l'altra data convertita in quel fuso; data senza fuso → `ValueError` (`"start_at must be a timezone-aware datetime"` / `end_at`); entrambi `None` → `{}`. `isoformat(timespec="seconds")` senza offset, come `zoned_datetime_input` |
| `src/pynteracta/api/posts_event.py` | nuovo | `PostsEventAPI(ResourceClient)`: costanti dei 7 percorsi `communication/posts/manage/…`; `build_event_block(*, start_at, end_at, all_day, location, invited_user_ids, invited_group_ids, invitation_type_id, send_edit_post_notifications) -> dict` (funzione pura di modulo: `event_datetime_block` + `allDay` + `location` + `invitations` con `users`/`groups` come `[{"id": N}]` o `[{"id": N, "typeId": T}]` e `sendEditPostNotifications`; chiavi solo se passate; `{}` se nulla); `get_event_for_create`, `get_event_for_edit`, `get_event_for_copy` (query `loadAttachments` solo se passata, via `build_query_params`); `create_event`/`create_event_raw` (`start_at` keyword obbligatorio; `event` nel corpo solo se il blocco non è vuoto; `announcement` solo se passato); `edit_event`/`edit_event_raw`; `copy_event`/`copy_event_raw`; `participate`/`participate_raw` (`ParticipationAnswer(answer)` valida l'intero prima della chiamata; `_put(path, json=body)` → `None`); `_dump` e `_zoned` come in `posts_write.py` (importati da lì o duplicati in due righe); docstring Google in italiano con tutti i kwargs |
| `src/pynteracta/api/posts.py` | modificato (una riga) | `class PostsAPI(PostsWriteAPI, PostsEventAPI)`; docstring cita i post evento |
| `src/pynteracta/models/facade/_stubs.py` | nuovo | `typed(stub, model)` e `typed_list(stubs, model)`: gli attuali `_typed`/`_typed_list` di `posts_write.py`, invariati |
| `src/pynteracta/models/facade/posts_write.py` | modificato | importa `typed`/`typed_list` da `_stubs.py` al posto delle copie locali; nessun cambio di comportamento |
| `src/pynteracta/models/facade/posts_event.py` | nuovo | `ParticipationAnswer(IntEnum)`: `YES = 1`, `MAYBE = 2`, `NO = 3`; `EventInvitee(raw: InvitationUserDTO1 \| InvitationGroupDTO1)` con `id`, `name` (`firstName lastName` o `name`), `type_id` (`typeId`), `.raw`; `EventData(raw: EventPostDataDTOModel)` con `start_at`/`end_at` (`datetime` con fuso: `datetime.fromisoformat(zonedDatetime)` se c'è, altrimenti `localDatetime` + `ZoneInfo(timezone)` se entrambi ci sono, altrimenti `None`), `timezone`, `all_day`, `location`, `participants_count`, `my_answer` (`ParticipationAnswer(participateTypeId)` o `None`), `invited_users`, `invited_groups` (liste di `EventInvitee` dalle rivalidazioni di `invitations.users/groups`), `send_edit_post_notifications`, `.raw`; `EventPostForCreate(raw: GetEventPostForCreateResponseDTO)` con `content_data: EventPostEditableContentDataDTOModel \| None`, `event: EventData \| None` (da `content_data.event`), `cover_image: PostCoverImageDTO1 \| None`, `from_dict`; `EventPostForEdit(raw: GetEventPostForEditResponseDTO)` con `occ_token`, `community_id`, `custom_id`, `content_data`, `event`, `cover_image`, `from_dict`; `EventPostForCopy` con `occ_token`, `content_data`, `event`, `from_dict` |
| `src/pynteracta/models/facade/__init__.py` | modificato | esporta `EventData`, `EventInvitee`, `EventPostForCreate`, `EventPostForEdit`, `EventPostForCopy`, `ParticipationAnswer` |
| `src/pynteracta/cli/_write.py` | modificato | `parse_event_datetime(value: str \| None, timezone: str, *, option: str) -> datetime \| None`: `YYYY-MM-DD` → `datetime` a mezzanotte, altrimenti `datetime.fromisoformat`; se senza fuso, `ZoneInfo(timezone)` (fuso sconosciuto → messaggio `--timezone: unknown IANA time zone` ed `EXIT_CONFIG`; valore non ISO → messaggio con `option` ed `EXIT_CONFIG`); restituisce il `datetime` con fuso, **non** il dict (la traduzione la fa `event_datetime_block`). `parse_zoned_datetime` resta com'è |
| `src/pynteracta/cli/posts_event.py` | nuovo | importa `app` da `cli/posts.py` e registra `create-event`, `edit-event`, `copy-event`, `participate`, `get-event-for-create`, `get-event-for-edit`, `get-event-for-copy`; opzioni nuove `--start`, `--end`, `--all-day`, `--location`, `--invite-user`, `--invite-group`, `--invite-type`, `--notify-on-edit`, `--cover` (`exists=True, dir_okay=False`), `--watcher-group`, `--remove-watcher-group`, `--pinned`, `--notes`; riusa da `posts_write.py` `TitleOption`, `DescriptionOption`, `WatcherUserOption`, `RemoveWatcherUserOption`, `VisibilityOption`, `AnnouncementOption`, `DraftOption`, `ScheduledPublicationOption`, `TimezoneOption`, `ClientUidOption`, `JsonBodyOption`, `OccTokenOption`, `NoAttachmentsOption`, `_PLAIN_TEXT`, `_DELTA`, `_token_or_exit`, `_render_single`, `_root`; `ParticipationChoice(str, Enum)` `yes/maybe/no` come argomento typer (scelta non valida → usage error, exit `2`). Funzioni pure: `event_write_block(event: dict \| None) -> dict` (08-C21: `startAt`/`endAt` ridotti a `{"localDatetime"}` se presente, `timezone`, `allDay`, `location`, `invitations` con `users`/`groups` ridotti a `{"id"[, "typeId"]}` e `sendEditPostNotifications`; via le chiavi di sola lettura e quelle `None`); `event_edit_base(form: EventPostForEdit) -> dict` (`title`, `description` = `descriptionDelta` con `descriptionFormat: 1`, `visibility`, `coverImageContentRef`, `event` = `event_write_block(root del contentData.event)`; chiavi `None` omesse; `event` omesso se `{}`); `event_copy_base(form: EventPostForCopy) -> dict` (idem più `announcement`); `event_flags_block(start, end, timezone, all_day, location, invite_user, invite_group, invite_type, notify_on_edit) -> dict` (le date via `parse_event_datetime` + `event_datetime_block`; `invitations` solo con i flag passati); `merge_event(base_event, json_event, flags_event) -> dict` (`{**base, **json}` shallow, poi i flag chiave per chiave; `invitations` dei flag unita chiave per chiave con quella corrente: `users`/`groups`/`sendEditPostNotifications` sostituiti singolarmente); `read_timezone(form) -> str` (fuso dell'evento letto o `DEFAULT_TIMEZONE`); righe curate `event_write_result_row` (id, community_id, title, start_at, end_at, timezone, location, visibility, next_occ_token: i campi evento da `_root(result.raw.postData).get("event")` se dict, altrimenti `None`), `event_for_edit_row` (occ_token, community_id, custom_id, title, start_at, end_at, timezone, all_day, location, participants_count, visibility), `event_for_copy_row` (occ_token, title, …evento…, visibility, announcement), `event_for_create_row` (title, visibility, announcement, draft, …evento se c'è…); `_cover_ref(client, cover) -> str \| None` (`upload_all(client, [cover])[0]["contentRef"]`, prima di `--attach`) |
| `src/pynteracta/cli/__init__.py` | modificato | `from pynteracta.cli import posts_event as _posts_event_cli  # noqa: F401` dopo `posts_write` |
| `tests/unit/test_api_utils.py` | modificato | 08-C02, 08-C03: `event_datetime_block` da solo (fuso da `start_at`, `end_at` convertito, offset fisso → UTC, fuso da `end_at` se `start_at` manca, naive → `ValueError`, entrambi `None` → `{}`) |
| `tests/unit/test_api_posts_event.py` | nuovo | 08-C01…C11 (classi `TestEventPrep`, `TestEventCreate`, `TestEventEdit`, `TestEventCopy`, `TestParticipate`, `TestEventErrors`; `build_event_block` da solo; `_api()`, `_sent(route)` come in `test_api_posts_write.py`) |
| `tests/unit/test_facade_posts_event.py` | nuovo | le façade sulle fixture: `EventData` (date con fuso, `my_answer`, invitati, `None` se manca `event`), `EventInvitee`, `EventPostForCreate/Edit/Copy`, `ParticipationAnswer(2) is MAYBE`, `ParticipationAnswer(4)` → `ValueError` (08-C07, 08-C11) |
| `tests/unit/test_facade_posts_write.py` | invariato | fissa già le otto façade: resta verde dopo lo spostamento di `_typed`/`_typed_list` in `_stubs.py` |
| `tests/unit/test_cli_write.py` | modificato | `parse_event_datetime`: sola data → mezzanotte, data-ora senza offset nel fuso dato, offset esplicito conservato, fuso sconosciuto → exit 2, valore non ISO → exit 2, `None` → `None` (08-C13) |
| `tests/unit/test_cli_posts_event.py` | nuovo | 08-C09 (exit code), 08-C12…C21 (snapshot syrupy per le tabelle di `create-event`, `get-event-for-edit`, `get-event-for-copy`, `get-event-for-create` e per l'output di `participate`; corpi letti con `_sent_body`; `posts --help` elenca i sette comandi; `event_write_block`, `event_edit_base`, `event_copy_base`, `merge_event` da soli) |
| `tests/fixtures/payloads/create_event_post_response.json`, `edit_event_post_response.json`, `copy_event_post_response.json`, `event_post_for_create_response.json`, `event_post_for_edit_response.json`, `event_post_for_copy_response.json` | nuovi | risposte sagomate sul swagger: `postData`/`contentData` con `event` completo (`startAt` con `zonedDatetime: "2026-11-05T10:00:00+01:00"`, `localDatetime`, `utcDatetime`; `endAt` 12:00; `timezone: "Europe/Rome"`; `allDay: false`; `location: "Sala A"`; `participantsCount: 3`; `participate: true`; `participateTypeId: 1`; `invitations` con l'utente 7 `Alice Rossi` `typeId: 2` e il gruppo 3 `G` `typeId: 0`, `sendEditPostNotifications: false`), `coverImageContentRef: "ref-1"`, `occToken: 5`, `visibility: 2`, `descriptionDelta` finto; `event_post_for_copy_response.json` con `announcement: true`; dati finti |
| `tests/contract/test_models.py` | modificato | 08-C22: `TestEventPostDTOs` con `assert_superset` sui 13 modelli della spec e smoke delle façade sulle sei fixture |
| `tests/integration/test_posts_integration.py` | modificato | 08-C24: `TestEventPostsWriteIntegration::test_full_cycle` (skip senza `PYNTERACTA_TEST_EVENT_COMMUNITY_ID` o `PYNTERACTA_TEST_USER_ID`; `client_uid = f"pynteracta-it-event-{int(time.time())}"`; date domani 10:00–12:00 `Europe/Rome`; `delete` dei post creati in `finally` con `contextlib.suppress(NotFoundError)`; stampe `[T-manuale]` dei dati osservati: `event` dopo la modifica, invitati come li restituisce il server, risposta di `participate`) |
| `tests/integration/.env.example`, `docs/testing.md` | modificati | `PYNTERACTA_TEST_EVENT_COMMUNITY_ID` (community di prova che ammette post evento, mai di produzione) |
| `docs/api/posts.md` | modificato | 08-C23: sezione "Event posts" (metodi, `EventData`, `ParticipationAnswer`, date e fuso, inviti, copertina, semantica dei campi omessi come verificata, colonne vuote se il tenant non restituisce `event` in `postData`); via "Event posts (type 2) are read-only for now"; `::: pynteracta.api.posts_event.PostsEventAPI` e `::: pynteracta.models.facade.posts_event` nei reference |
| `docs/cli.md` | modificato | 08-C23: i sette comandi dopo `posts get-for-*`; exit `11` cita anche `--cover` dei post evento |
| `docs/index.md`, `README.md` | modificati | 08-C23: la scrittura copre post custom ed evento, commenti, workflow, task, anagrafiche admin e allegati; via "Event posts follow"; nessun numero di versione |
| `tests/unit/test_docs_snippets.py` | modificato | `test_event_posts_pages_document_write_commands` con marker 08-C23 (sette nomi di comando in `cli.md`; `create_event(`, `participate(`, `EventData`, `ParticipationAnswer`, `get_event_for_edit` in `api/posts.md`; assenza di "read-only for now" e "Event posts follow"; `PYNTERACTA_TEST_EVENT_COMMUNITY_ID` in `testing.md`) |
| `ROADMAP.md`, `PROGRESS.md` | modificati | riga `0.14.0 ⏳ M34` all'apertura (primo task); sezione M34 alla verifica |
| `specs/prd.md` | modificato (chiusura) | RF-021e, RF-021f; RF-021 aggiornato; §1 (scrittura completa); conferma di RF-021, RNF-010 e §6 nella parte degli eventi |

Non si toccano: `transport.py`, `hooks.py`, `client.py`, `api/_base.py`, `api/posts_write.py`,
`cli/posts_write.py` (si importano solo le sue opzioni e i suoi helper), `cli/_common.py`,
`models/generated/` (nessuna rigenerazione: i DTO ci sono già).

## Modello dati e migrazioni

Nessuna modifica di schema. Nei DTO di richiesta `event` è lo stub `EventPostDataDTO`
(`RootModel[Any]`), che accetta il dict composto dalla libreria; nelle risposte `contentData` è
lo stub `EventPostEditableContentDataDTO`, rivalidato in `EventPostEditableContentDataDTOModel`,
il cui `event` è a sua volta lo stub `EventPostDataDTO`, rivalidato in `EventPostDataDTOModel`;
dentro, `startAt`/`endAt` sono `EventDatetimeDTOModel` (stub) → `EventDatetimeDTO`, e gli
invitati `InvitationUserDTO`/`InvitationGroupDTO` (stub) → `…1`. `postData` delle risposte di
scrittura resta `PostDetailDTO` (stub): `PostWriteResult.post` lo tipizza in `PostDetailDTO1`,
che non ha `event`; il dict grezzo in `.root` sì, se il server lo manda, ed è da lì che la CLI
legge le colonne dell'evento.

## Flussi

```
Libreria (api/posts_event.py)
get_event_for_edit(post_id, load_attachments=None)
    → _get("…/manage/event-post-data-for-edit/{post_id}", params=build_query_params(load_attachments=…) or None)
    → EventPostForEdit.from_dict(resp)                 (occ_token = resp["occToken"]; event = EventData(…) o None)
create_event(community_id, *, start_at, **kw)
    → event = build_event_block(start_at=…, end_at=…, all_day=…, location=…, invited_user_ids=…, …)
         (event_datetime_block → ValueError se una data è senza fuso, prima di qualunque richiesta)
    → body = build_write_body(title=…, …, announcement=announcement, event=event or None,
                              scheduled_publication=zoned_datetime_input(dt) se dt)
    → _post("…/manage/create-event-post/{community_id}", json=body) → PostWriteResult.from_create(resp)
edit_event(post_id, occ_token, **kw)
    → event = build_event_block(…) ; body = build_write_body(…, event=event or None)
    → _put("…/manage/edit-event-post/{post_id}/{occ_token}", json=body) → PostWriteResult.from_edit(resp)
copy_event(post_id, occ_token, **kw)   → idem su "…/manage/copy-event-post/{post_id}/{occ_token}" → from_copy
participate(post_id, answer, *, notes=None)
    → type_id = int(ParticipationAnswer(answer))        (ValueError se fuori da 1, 2, 3)
    → _put("…/manage/post-event/{post_id}/partecipate", json=build_write_body(type_id=type_id, notes=notes)) → None
Errori: nessun try/except nei metodi; il transport solleva le InteractaError; una richiesta per chiamata.

CLI (cli/posts_event.py)
posts create-event COMMUNITY_ID
    → json_part = load_json_body(--json, CreateEventPostRequestDTO)
    → senza --start e senza json_part["event"]["startAt"] → messaggio ed Exit(EXIT_CONFIG)
    → flags_event = event_flags_block(--start, --end, --timezone (default Europe/Rome), --all-day, --location,
                                      --invite-user, --invite-group, --invite-type, --notify-on-edit)
    → merged = merge_body(json_part, title=…, description=…, description_format=2 se --description,
                          watcher_user_ids=…, watcher_group_ids=…, visibility=…, announcement=True se flag,
                          pinned=True se flag, draft=True se flag, scheduled_publication=parse_zoned_datetime(…),
                          client_uid=…)
    → merged["event"] = merge_event({}, json_part.get("event", {}), flags_event)
    → validate_body(merged, CreateEventPostRequestDTO)
    → with client: merged["coverImageContentRef"] = _cover_ref(client, --cover) se --cover;
                   append_attachments(merged, "attachments", upload_all(client, --attach))
    → req = validate_body(…) → client.posts.create_event_raw(COMMUNITY_ID, req) → render_output(event_write_result_row)
posts edit-event POST_ID
    → form = client.posts.get_event_for_edit(POST_ID)             (sempre)
    → token = --occ-token oppure form.occ_token (None → _token_or_exit → exit 1)
    → tz = --timezone oppure read_timezone(form)
    → base = event_edit_base(form); flags_event = event_flags_block(…, tz, …)
    → merged = merge_body({**base, **json_part}, title=…, description=…, description_format=2 se --description,
                          add_watcher_user_ids=…, remove_watcher_user_ids=…, add_watcher_group_ids=…,
                          remove_watcher_group_ids=…, visibility=…, pinned=True se flag, draft=…, scheduled_publication=…)
    → merged["event"] = merge_event(base.get("event", {}), json_part.get("event", {}), flags_event)  (omesso se {})
    → validate_body(merged, EditEventPostRequestDTO) → --cover → coverImageContentRef (vince sul letto) → --attach
    → client.posts.edit_event_raw(POST_ID, token, req) → render_output
    → ConcurrencyError → handle_error(exc, console=…, resource=f"Post {POST_ID}") → exit 9
posts copy-event POST_ID  → form = get_event_for_copy(POST_ID); base = event_copy_base(form); DTO CopyEventPostRequestDTO;
                            --announcement e --client-uid ammessi; PUT copy-event-post con il token letto
posts participate POST_ID yes|maybe|no [--notes]
    → answer = ParticipationAnswer[CHOICE.upper()] → client.posts.participate(POST_ID, answer, notes=…)
    → "Participation to post {id} recorded: {choice}" | {"post_id", "answer", "type_id"}
posts get-event-for-create|edit|copy → letture, render_output con la riga curata (occ_token in testa)
```

## Interfaccia

Comandi, opzioni e messaggi come nella sezione "CLI" della spec; testi in inglese. Help breve con
il formato atteso (`--start`: `ISO 8601 date-time or date, e.g. 2026-11-05T10:00 or 2026-11-05;
read in the --timezone zone unless it has an offset`; `--invite-type`: `0 = guest, 2 =
collaborator, applied to every --invite-user/--invite-group`). `--all-day`, `--pinned`,
`--notify-on-edit`, `--announcement`, `--draft` sono flag booleani che inviano `true` solo se
presenti. `--timezone` ha default `Europe/Rome` in `create-event` e `copy-event`, nessun default
in `edit-event` (fuso dell'evento letto). L'argomento di `participate` è un `Enum` typer con le
tre scelte: typer rifiuta le altre con un usage error (exit `2`). Nessuna pagina web.

## Configurazione

Nessuna variabile di runtime. Solo per gli integration test: `PYNTERACTA_TEST_EVENT_COMMUNITY_ID`
(community di prova che ammette post evento, mai di produzione: il test vi crea e cancella post),
in `tests/integration/.env.example` e `docs/testing.md`; riusa `PYNTERACTA_TEST_USER_ID` come
invitato.

## Sicurezza e dati personali

- **Nessuna operazione ripetuta in automatico**: ogni metodo fa una richiesta e lascia salire le
  eccezioni del transport; la CLI non riprova su `409` (08-C08, 08-C10, 08-C19). La lettura
  propedeutica delle patch è una lettura, non una ripetizione.
- **Token e segreti mai nei log**: nessun log nuovo; i corpi passano dall'audit log solo con
  `audit_log_bodies`, già redatti dal transport; la copertina passa dallo storage come gli
  allegati (RNF-011, meccanismo della spec 04).
- **Dati personali**: i corpi contengono titolo, descrizione, luogo, id di invitati e watcher,
  note di partecipazione; non si salvano. Le fixture usano valori finti (`Alice Rossi`, id
  piccoli). L'integration test usa `PYNTERACTA_TEST_EVENT_COMMUNITY_ID`, mai
  `PYNTERACTA_TEST_COMMUNITY_ID`, invita il solo utente di prova e cancella i post in `finally`.
- **Soglie che non scendono**: i file nuovi e toccati hanno test per ogni ramo; copertura ≥ 85 %
  per file e totale ≥ 95,18 %.

## Test di caratterizzazione

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `facade/posts_write.py::_typed`, `_typed_list` | rivalidazione degli stub, `None` se vuoto, elementi non oggetto scartati | già fissati da `test_facade_posts_write.py` (otto façade sulle fixture); restano verdi dopo lo spostamento in `_stubs.py`, che cambia solo l'import |
| `api/posts.py::PostsAPI` | tutti i metodi di lettura e di scrittura dei post custom | già fissati da `test_api_posts.py` e `test_api_posts_write.py`; la riga di ereditarietà aggiunge un mixin senza nomi in conflitto (verificato: nessun metodo di `PostsEventAPI` esiste in `PostsWriteAPI`) |
| `cli/__init__.py`, `cli/posts.py::app` | i comandi `posts` esistenti | `test_cli_posts_write.py::test_posts_help_lists_write_commands` resta verde; il test nuovo verifica i sette nomi in più |
| `cli/_write.py::parse_zoned_datetime` | comportamento attuale | già fissato da `test_cli_write.py`; `parse_event_datetime` è una funzione nuova accanto |
| `api/_utils.py::zoned_datetime_input` | comportamento attuale | già fissato da `test_api_utils.py`; `event_datetime_block` è nuova |

## Strategia di test

Ordine: test prima del codice, rossi per il motivo giusto (modulo, metodo o comando inesistente,
campo mancante), poi il codice. Ogni test porta `# criterio: 08-Cmm`. Le fixture nuove si
scrivono con il test che le usa. `_sent_body(route)`, `mock_json`, `load_payload` come in
`test_cli_posts_write.py`. `_ROME = ZoneInfo("Europe/Rome")`, `_START = datetime(2026, 11, 5,
10, 0, tzinfo=_ROME)`, `_END = … 12, 0 …` come costanti di modulo.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 08-C01 | `test_api_posts_event.py::TestEventCreate::test_create_event_sends_only_given_fields_and_wraps_response`: `respx.post` su `…/create-event-post/79`, corpo == JSON atteso (tutte le chiavi del criterio, nessun'altra), `call_count == 1`, risultato da `create_event_post_response.json` | unitario |
| 08-C02 | `::test_create_event_start_only_sends_event_block_without_announcement`, `::test_invited_user_without_type_sends_id_only`, `::test_end_at_converted_into_start_zone`, `::test_fixed_offset_sends_utc`; `test_api_utils.py::TestEventDatetimeBlock` sugli stessi casi più `end_at` solo (fuso da `end_at`) e `(None, None) → {}` | unitario |
| 08-C03 | `::TestEventErrors::test_naive_datetime_raises_before_request` parametrizzato su `create_event`, `edit_event`, `copy_event` × `start_at`/`end_at` (`call_count == 0`) | unitario |
| 08-C04 | `::TestEventCreate::test_create_event_raw_equivalent` (`CreateEventPostRequestDTO(title="T", event={…})`), `::TestEventEdit::test_raw_equivalent`, `::TestEventCopy::test_raw_equivalent`, `::TestParticipate::test_raw_equivalent` | unitario |
| 08-C05 | `::TestEventEdit::test_edit_event_sends_only_given_fields` (PUT `…/edit-event-post/21269/5`, corpo atteso, `next_occ_token` e `post` da `edit_event_post_response.json`), `::test_edit_event_end_only_sends_end_and_timezone`, `::test_edit_event_without_fields_sends_empty_body` (nessuna chiave `event`); `build_event_block` da solo: `{}` senza kwargs | unitario |
| 08-C06 | `::TestEventCopy::test_copy_event_body_and_result` (`post_id` del post nuovo da `copy_event_post_response.json`) | unitario |
| 08-C07 | `::TestParticipate::test_participate_body_and_none` (risposta `200` vuota, `typeId: 1`, `notes`), `::test_participate_int_answer` (`{"typeId": 3}`), `::test_participate_invalid_answer_raises_before_request` (`ValueError`, `call_count == 0`); `test_facade_posts_event.py::test_participation_answer_values` (`ParticipationAnswer(2) is MAYBE`, `(4)` → `ValueError`) | unitario |
| 08-C08 | `::TestEventErrors::test_409_raises_concurrency_error_once` parametrizzato su `edit_event`, `copy_event` | unitario |
| 08-C09 | `::TestEventErrors::test_participate_404_not_found_once`, `::test_participate_403_permission_once`, `::test_create_400_custom_field_validation_readable` (`response_body["validationErrors"]`); `test_cli_posts_event.py::TestExitCodes::test_participate_not_found_exits_5`, `::test_participate_forbidden_exits_4`, `::test_create_validation_error_exits_6` | unitario |
| 08-C10 | `::TestEventErrors::test_timeout_raises_transport_error_once` parametrizzato su `create_event` e `participate` (`httpx.ReadTimeout`) | unitario |
| 08-C11 | `::TestEventPrep::test_get_event_for_create`, `::test_get_event_for_edit_no_query_occ_token_and_event` (campi del criterio su `event_post_for_edit_response.json`: `start_at == datetime(2026, 11, 5, 10, 0, tzinfo=_ROME)`, `my_answer is YES`, invitati), `::test_get_event_for_edit_load_attachments_false_in_query`, `::test_get_event_for_copy`, `::test_event_none_when_missing` (fixture senza `event`); `test_facade_posts_event.py` per `EventData` da solo (date da `zonedDatetime`, fallback `localDatetime` + `timezone`, `None` senza entrambi; `my_answer None` senza `participateTypeId`; `EventInvitee.name` per utente e gruppo) | unitario |
| 08-C12 | `test_cli_posts_event.py::TestCreateEvent::test_flags_and_json_merge_flags_win` (file in `tmp_path`, corpo == JSON del criterio), `::test_without_announcement_and_pinned_keys_missing`, `::test_table_output` (snapshot), `::test_json_output` (snapshot); `merge_event` da solo (`--invite-user` sostituisce `users`, `allDay` del json resta) | unitario |
| 08-C13 | `::TestCreateEvent::test_date_only_is_local_midnight_and_all_day`, `::test_explicit_offset_sends_utc`, `::test_timezone_flag_applied`, `::test_unknown_timezone_exits_2`, `::test_bad_start_exits_2`, `::test_missing_start_exits_2_without_requests`, `::test_start_from_json_event_is_enough` (nessuna richiesta nei casi di errore: `respx` senza route montate e `call_count == 0`); `test_cli_write.py::TestParseEventDatetime` | unitario |
| 08-C14 | `::TestEditEvent::test_edit_reads_form_then_puts_patched_body` (GET + PUT su `/21269/5`, corpo == base di 08-C14 con `title` e `location` nuovi), `::test_edit_with_occ_token_still_reads_base` (PUT su `/21269/3`), `::test_edit_base_skips_missing_fields` (fixture ridotta senza `descriptionDelta`, `coverImageContentRef`, `endAt`), `::test_edit_without_occ_token_in_response_exits_1`, `::test_edit_post_not_found_exits_5_without_put`; `event_edit_base` ed `event_write_block` da soli sulla fixture | unitario |
| 08-C15 | `::TestEditEvent::test_start_without_timezone_uses_read_zone` (corpo con `startAt` nuovo, `timezone: "Europe/Rome"`, `endAt` letto), `::test_timezone_flag_changes_event_zone`, `::test_invite_user_replaces_users_keeps_groups`, `::test_json_event_over_read_flags_over_json` (`location` "Sala C" dal json, poi "Sala D" dal flag; `pinned: true`) | unitario |
| 08-C16 | `::TestCopyEvent::test_copy_reads_form_then_puts_base_with_title` (corpo == `event_copy_base(fixture)` + `title`, con `announcement: true`), `::test_copy_table_shows_new_post` (snapshot); `event_copy_base` da solo | unitario |
| 08-C17 | `::TestParticipate::test_yes_with_notes_body_and_message`, `::test_maybe_and_no_type_ids` (parametrizzato), `::test_json_output`, `::test_invalid_choice_exits_2_without_requests` | unitario |
| 08-C18 | `::TestCoverAndAttach::test_cover_then_attach_uploaded_in_order` (storage mock come `test_cli_posts_write.py::_mock_storage`; corpo con `coverImageContentRef` e `attachments`), `::test_cover_upload_failure_exits_11_without_write` (`attach` non caricato: `storage.call_count == 1`, nessuna `POST`), `::test_edit_event_cover_wins_over_read`, `::test_copy_event_cover` | unitario |
| 08-C19 | `::TestConflicts::test_conflict_exits_9_without_retry` parametrizzato su `edit-event` e `copy-event` (`exit_code == 9`, messaggio, `write_route.call_count == 1`) | unitario |
| 08-C20 | `::TestPrepCommands::test_get_event_for_edit_table_starts_with_occ_token` (snapshot), `::test_get_event_for_copy_table` (snapshot), `::test_get_event_for_create_table` (snapshot), `::test_no_attachments_sends_query` (edit e copy), `::test_full_json` | unitario |
| 08-C21 | `::TestEventWriteBlock::test_event_write_block` parametrizzato sui quattro casi del criterio | unitario |
| 08-C22 | `tests/contract/test_models.py::TestEventPostDTOs::test_request_dto_superset` (4 DTO), `::test_response_dto_superset` (3 DTO), `::test_typed_stub_superset` (6 varianti tipizzate), `::test_facade_smoke` sulle sei fixture, `::test_facade_raw_accessible` | contract |
| 08-C23 | `test_docs_snippets.py::test_event_posts_pages_document_write_commands`; `uv run mkdocs build --strict` nei controlli di verifica | unitario + verifica |
| 08-C24 | `tests/integration/test_posts_integration.py::TestEventPostsWriteIntegration::test_full_cycle` (skip senza le variabili; `create_event` → `get_by_client_uid` → `get_event_for_edit` (`event.start_at == _START` inviato) → `edit_event` (titolo, luogo, blocco letto rimandato con `event_write_block`) → `participate(YES)` → `get_event_for_copy` → `copy_event` → `delete` × 2 in `finally` → `NotFoundError` × 2) | integrazione (opt-in) + verifica manuale |

Revisione del 2026-10-13 (dopo T16). 08-C07, 08-C12, 08-C13, 08-C17 sono sostituiti: i loro test
cambiano marker e attese. Moduli: `api/_utils.py` (`event_datetime_block` con `all_day`),
`api/posts_event.py` (`build_event_block`, kwargs `date | datetime`, note in delta con
`text_to_delta`), `models/facade/posts_event.py` (`_event_datetime`), `cli/posts_event.py`
(`all_day_block` applicato al blocco unito, tabella di scrittura ridotta).

| Criterio | Test previsto | Tipo |
|---|---|---|
| 08-C25 | `test_cli_posts_event.py::TestCreateEvent::test_date_only_all_day_sends_date_without_timezone`, `::test_datetimes_all_day_send_dates`, più i test di 08-C13 rimarcati | unitario |
| 08-C26 | `test_api_posts_event.py::TestAllDay::test_create_all_day_dates`, `::test_aware_datetime_all_day_uses_local_date`, `::test_naive_datetime_all_day_accepted`, `::test_date_without_all_day_raises` parametrizzato su `create_event`, `edit_event`, `copy_event` | unitario |
| 08-C27 | `test_cli_posts_event.py::TestAllDayMerge::test_edit_all_day_read_event_start_flag`, `::test_copy_all_day`, `::test_create_all_day_from_json`; `::TestAllDayBlock` sulla funzione pura | unitario |
| 08-C28 | `test_facade_posts_event.py::TestEventDates::test_iana_zone_from_local_and_timezone`, `::test_all_day_is_date`, `::test_zoned_only`, `::test_unknown_zone_without_zoned_is_none`; `test_api_posts_event.py::TestAllDay::test_edit_with_read_start_keeps_zone`; snapshot di `get-event-for-edit` su un evento tutto il giorno | unitario + snapshot |
| 08-C29 | `test_api_posts_event.py::TestParticipate::test_participate_body_and_none` (note in delta), `::test_participate_raw_notes_as_is` | unitario |
| 08-C30 | `test_cli_posts_event.py::TestParticipate::test_yes_with_notes_body_and_message` (note in delta) e i test di 08-C17 rimarcati | unitario |
| 08-C31 | `test_cli_posts_event.py::TestCreateEvent::test_flags_and_json_merge_flags_win` (tabella senza colonne dell'evento; snapshot aggiornati) | unitario + snapshot |

Verifica manuale (dalla spec): l'esecuzione di 08-C24 sulla community di prova, più le prove a
mano in un task dedicato (campi omessi in `edit-event-post` e `copy-event-post`, per il post e per
le chiavi del blocco `event`; `typeId` degli invitati obbligatorio o no e suo default; effetto di
`allDay`; partecipazione del service account; formato della descrizione in modifica; presenza di
`event` in `postData` delle risposte di scrittura), stabilisce ciò che lo swagger non documenta.
L'esito si registra in `docs/api/posts.md` e in `verifica.md`. Se il server non azzera i campi
omessi, la base delle patch si riduce con una revisione della spec (08-C14…08-C16); se esige
`typeId`, `invitation_type_id` prende un default documentato con una revisione; mai un
aggiustamento silenzioso.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| Mixin `PostsEventAPI` in `api/posts_event.py`, façade in `facade/posts_event.py`, comandi in `cli/posts_event.py` | estendere i moduli `*_write` | Decisione del maintainer: moduli leggibili, `client.posts.*` unico, stesso schema della spec 03 |
| `ParticipationAnswer` in `facade/posts_event.py`, esportato da `pynteracta.models.facade` | in `api/posts_event.py`; top level | Decisione del maintainer: la façade lo usa per `my_answer`; stesso import delle altre façade |
| Colonne dell'evento nelle tabelle di scrittura dal dict grezzo di `postData.event`, vuote se manca | dai valori inviati | Decisione del maintainer: si mostra ciò che il server ha salvato; nessuna richiesta in più |
| `event_datetime_block` in `api/_utils.py`, usata da libreria e CLI | conversione duplicata nella CLI; `parse_event_datetime` che restituisce il dict | Una sola regola per le date (RNF-010); la CLI produce `datetime` con fuso e lascia la traduzione alla libreria |
| `build_event_block` funzione pura di modulo, non metodo | costruzione inline nei tre metodi | Tre metodi la condividono; testabile da sola (08-C02, 08-C05) |
| `_typed`/`_typed_list` spostati in `facade/_stubs.py` | import del nome privato da `posts_write`; copia nel modulo nuovo | Niente import di privati tra moduli, niente codice doppio; i test esistenti fissano il comportamento |
| `event_write_block` sul dict grezzo (`root` dello stub), non sulla façade | funzione su `EventData` | Lavora sulla forma del server, indipendente dalle proprietà della façade; corrisponde agli esempi di 08-C21 |
| `merge_event`: base e json uniti shallow, flag chiave per chiave, `invitations` dei flag unita per chiave | unione profonda ovunque | Regola della spec (json sostituisce `invitations` letta per intero; `--invite-user` sostituisce solo `users`) |
| `--timezone` senza default in `edit-event`, `read_timezone(form)` | default `Europe/Rome` ovunque | Regola della spec: senza `--timezone` vale il fuso dell'evento letto |
| Argomento `participate` come `Enum` typer (`yes/maybe/no`) | stringa validata a mano | Typer produce l'usage error ed exit `2` da solo, con le scelte nell'help |
| `--cover` caricato prima di `--attach`, dentro il `with build_client` dopo la prima `validate_body` | upload prima della validazione | Come `posts create --attach` (spec 04): un corpo non valido esce `2` senza caricare nulla |
| Integration test nel file `test_posts_integration.py` | file nuovo | Convenzione del progetto: un file per risorsa |
| Riga `0.14.0 ⏳ M34` in ROADMAP nel primo task | alla verifica | Configurazione SDD: la riga ⏳ si aggiunge all'apertura (come 06-T01 e 07-T01) |
| Commit `feat(posts):` per libreria e façade, `feat(cli):` per i comandi, `refactor(facade):` per `_stubs.py`, `test:` e `docs:` per il resto | `feat:` unico | Scope come nella storia del progetto; semantic-release calcola 0.14.0 |

## Rischi

- **Campi omessi azzerati o conservati dal server, anche dentro `event`** → l'integration test e
  il task manuale lo scoprono; la spec si rivede se serve (08-C14…C16), la libreria non cambia.
- **`typeId` degli invitati obbligatorio** → `{"id": 7}` risponderebbe `400`; il task manuale lo
  mostra e `invitation_type_id` prende un default con revisione della spec.
- **`event` assente da `postData` nelle risposte di scrittura** → le colonne restano vuote
  (decisione del maintainer); i docs lo dicono dopo la prova sul tenant.
- **`zonedDatetime` in un formato non `fromisoformat`** (per esempio `Z` o millisecondi) → Python
  3.12 legge `Z` e i decimali; se il formato è altro, `EventData.start_at` ripiega su
  `localDatetime` + `timezone`; il test della façade copre entrambe le vie.
- **Fuso `Europe/Rome` non disponibile sul runner** → `tzdata` è già usato dai test della spec
  02; nessuna dipendenza nuova.
- **Stub `RootModel` annidati su tre livelli** → `typed` li rivalida uno per uno; i contract test
  `test_typed_stub_superset` mostrano se una variante tipizzata è incompleta (08-C22).
- **Nomi in conflitto tra i due mixin** → nessuno oggi; un test di `test_api_posts_event.py`
  verifica che `PostsAPI` esponga i sette metodi nuovi e che `create`, `edit`, `copy` restino
  quelli dei post custom.
- **Registrazione dei comandi** → l'import in `cli/__init__.py` deve precedere `add_typer`; il
  test di `posts --help` lo verifica.
- **Snapshot syrupy** → generati con `--snapshot-update` al primo run, poi riletti a mano.
- **Copertura di `cli/posts_event.py`** → ogni ramo di errore (`--json` non valido, token assente,
  `--start` mancante, fuso non valido, `409`, `404` dalla lettura, upload fallito) ha un test.
