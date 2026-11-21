# PRD – pynteracta

Origine: ricostruito dal codice il 2026-10-08 da `/sddpa:init`
Stato: confermato (tutte le sezioni confermate dal maintainer; l'ultima il 2026-11-21)

Ogni sezione porta la data della conferma del maintainer; `/sddpa:specifica` chiede di
riconfermare le sezioni che la spec tocca. Le funzioni sono descritte per quello che il codice fa
davvero alla versione 0.14.0. Le spec per versione precedenti all'adozione del metodo stanno in
[`legacy/`](legacy/), congelate; la storia del progetto è in [`../PROGRESS.md`](../PROGRESS.md).

## 1. Scopo

Confermato dal maintainer il 2026-10-08.

`pynteracta` è una libreria Python 3.12+ e un client a riga di comando, non ufficiali, per l'API
REST `external_v2` della piattaforma Interacta™ (Dinova S.r.l. / Maggioli S.p.A.). Serve a chi
scrive automazioni e integrazioni interne: legge utenti, post, community, cataloghi, allegati,
task, gruppi e hashtag di un tenant con tipi espliciti, paginazione pigra ed esportazione su file.
Ha inoltre due usi voluti: essere la libreria che gli strumenti di *vibe coding* (agenti di
programmazione assistita) usano per lavorare con Interacta, quindi con un'API tipizzata, uniforme e
documentata che un agente possa scoprire e comporre; ed essere la base di un **server MCP non
ufficiale per Interacta**. Con [ADR 0002](adr/0002-server-mcp-locale-e-login-google-integrato.md)
il server entra nel pacchetto: locale, su stdio, avviato da `pynteracta mcp serve` e distribuito
come extra opzionale (`pynteracta[mcp]`), con letture curate e la scrittura dei task dietro un
flag esplicito (RF-027); lo stesso ADR porta nella libreria il login Google dal browser, con
rinnovo automatico della sessione (RF-026). Il login Google è realizzato dalla
[spec 10](10-google-login/spec.md); il server MCP è deciso e da realizzare.
La superficie è sincrona. Fino alla versione 0.9.4 era di sola lettura; con
[ADR 0001](adr/0001-apertura-della-superficie-di-scrittura.md) le scritture (post, post evento e
commenti, task, anagrafiche admin, upload di allegati) sono entrate nell'ambito e le spec dalla 02
alla 08 le hanno realizzate tutte: la superficie di scrittura dell'ADR è completa. Dalla
[spec 09](09-swagger-align/spec.md) la libreria espone tutti i 76 endpoint dello swagger
`external_v2` pinnato.

## 2. Attori e ruoli

Confermato dal maintainer il 2026-10-08 (riga "Utente Google" riconfermata il 2026-11-21,
spec 10).

| Attore | Ruolo o gruppo | Cosa può fare |
|---|---|---|
| Sviluppatore di integrazioni | usa la libreria da Python | istanzia `InteractaClient`, chiama le risorse `client.<risorsa>.*`, registra hook, legge gli errori tipizzati |
| Operatore | usa la CLI `pynteracta` | configura profili, si autentica, interroga ed esporta dati di lettura |
| Service account Interacta | identità tecnica del tenant | firma l'asserzione JWT (RS512) con cui la libreria ottiene l'access token; vede ciò che il tenant gli concede |
| Utente Google | identità personale già collegata a un utente Interacta | fornisce un access token Google, oppure (ADR 0002, RF-026) fa il login Google dal browser una volta e la libreria ne conserva e rinnova la sessione; in entrambi i casi la libreria scambia il token Google con un access token Interacta |
| Client MCP o agente LLM | agisce per conto della persona che lo avvia, con l'identità del profilo | chiama gli strumenti del server MCP locale (ADR 0002, RF-027): letture curate e, solo con `--enable-task-writes`, scrittura dei task; mai l'area admin |
| Tenant Interacta | sistema esterno | espone l'API `external_v2`; decide visibilità e permessi, che la libreria non aggira |

## 3. Requisiti funzionali

Confermato dal maintainer il 2026-10-13 (i singoli requisiti portano la data della conferma
data dalla spec che li ha toccati). Uno per funzione; il dettaglio arriva con le spec che li
toccano.

- RF-001. Autenticazione con service account: da un file chiave JSON (`ServiceAccountKey`) la
  libreria costruisce un'asserzione JWT firmata RS512 e ottiene un access token dal tenant.
- RF-002. Autenticazione Google OAuth2: un access token Google (scope minimo `email`), fornito
  dall'utente o ottenuto con il login integrato (RF-026), viene scambiato con un access token
  Interacta. Verificato sul tenant il 2026-11-20: con il solo scope `profile` lo scambio
  risponde `401` `BAD_CREDENTIALS`. *(Precisato da ADR 0002, 2026-11-20.)*
- RF-003. Ciclo di vita del token: cache su file (`FileTokenCache`) o in memoria
  (`MemoryTokenCache`), refresh anticipato di 60 s rispetto alla scadenza, invalidazione quando il
  server rifiuta il token, chiave di cache distinta per tenant. Il token Interacta ottenuto
  dallo scambio Google dura un'ora (verificato sul tenant il 2026-11-20); con il login
  integrato la libreria rinnova da sola l'access token Google e ripete lo scambio (RF-026).
  *(Precisato da ADR 0002, 2026-11-20.)*
- RF-004. Identità corrente: dati dell'utente autenticato (`auth whoami`, `users me`,
  `users profile`).
- RF-005. Utenti: elenco paginato con filtri (stato, provider di login, manager, lingua, prefissi
  di nome ed email…) e ordinamento, iterazione su tutte le pagine, form di modifica
  (`get_for_edit`, che espone `occ_token`: RF-023a). *(Confermato dal maintainer il 2026-10-10,
  spec 05.)*
- RF-006. Post: dettaglio per id e per client uid, capabilities, storia degli eventi, stream
  globale, elenco in community con filtri su campi standard, custom e di workflow (validazione
  opzionale contro la definizione dei post della community) e ordinamento, controllo di visibilità
  con e senza commenti, elenco dei commenti. *(Confermato dal maintainer il 2026-10-10, spec
  03.)*
  - RF-006a. `PostCapabilities` espone `can_copy`, `can_edit_attachments`,
    `can_edit_workflow_screen_data` e le operazioni di workflow permesse, con cui il chiamante
    scopre l'`operation_id` delle transizioni. *(Spec 03, 2026-10-10.)*
  - RF-006b. Il dettaglio del post (`Post`) espone `draft` (bozza o pubblicato) e
    `publication_timestamp` (epoch in millisecondi, UTC), `None` se il tenant non li manda;
    `posts get` li mostra come `draft` e `publication_ts`. Il tenant di prova li manda.
    *(Spec 09, 2026-10-13.)*
- RF-007. Community: elenco, dettagli singoli e in blocco, definizione dei post (singola e
  multipla).
  - RF-007a. Community per capability di visualizzazione dei post:
    `communities.list_by_view_post_capability(level=None)` con `ViewPostCapabilityLevel`
    (`PRIVATE`, `PUBLIC`, `ALL`) o il suo nome come stringa senza distinzione di maiuscole, un
    valore diverso rifiutato prima della richiesta; senza livello il parametro non è inviato e
    decide il server (sul tenant di prova, con il service account, come `ALL`: le tre scelte e
    nessuna danno le stesse 15 community, contro le 9 di `list()`). In CLI
    `communities list-by-view-post [--level private|public|all]`. *(Spec 09, 2026-10-13.)*
- RF-008. Cataloghi: elenco dei cataloghi e delle voci, con iterazione; le scritture di
  cataloghi e voci stanno su `client.catalogs` (RF-023, RF-023e). *(Confermato dal maintainer il 2026-10-12, spec 06.)*
- RF-009. Allegati: elenco per post, dettaglio per id, controllo di visibilità.
- RF-010. Task: dettaglio per id.
  - RF-022a. La lettura di un task espone `occ_token`, il token di concorrenza da passare alla
    modifica. *(Spec 02, 2026-10-08.)*
- RF-011. Gruppi: elenco, membri di un gruppo, form di modifica (`get_for_edit`, che espone
  `occ_token`: RF-023a). *(Confermato dal maintainer il 2026-10-10, spec 05.)*
- RF-012. Hashtag di una community.
- RF-013. Form di modifica dell'area admin (sola lettura): workspace, catalogo, voce di catalogo,
  credenziali utente (`UserCredentialsForEdit` espone `occ_token`, e `users.get_credentials_for_edit`
  è l'alias di `admin_manage.user_credentials_for_edit`: RF-023a). *(Confermato dal maintainer il
  2026-10-10, spec 05.)* Tutte le façade dei form espongono `occ_token`, `CatalogForEdit` anche
  `parent_catalog_id` (RF-023e). *(Confermato dal maintainer il 2026-10-12, spec 06.)*
- RF-014. Paginazione pigra: `PageIterator` e i metodi `iterate*()` seguono `nextPageToken` fino
  all'esaurimento; nella CLI `--all`, `--page-token`, `--count`.
- RF-015. Output CLI componibile: `table` (default), `json`, `yaml`; `--full` e `--fields` per la
  selezione dei campi; `--web-url` per i deep link; `--export` su csv/json/yaml/parquet, formato
  dedotto dall'estensione (`yaml` e `parquet` sono extra opzionali).
  - RF-015a. La CLI termina con exit code `9` quando una scrittura fallisce per conflitto di
    concorrenza (`409`), distinto dagli altri errori. *(Spec 02, 2026-10-08.)*
- RF-016. Configurazione: profili in `config.toml` (`platformdirs`, override con
  `PYNTERACTA_CONFIG_FILE`), variabili `PYNTERACTA_*`, flag globali della CLI; precedenza flag >
  env > file > default; comandi `config profile|add-profile|set|use-profile|remove-profile` che
  conservano commenti e formattazione del file (`tomlkit`).
  - RF-016a. Campo di profilo `google_client_id` (`PYNTERACTA_GOOGLE_CLIENT_ID`), l'id del
    client OAuth del login integrato. *(Spec 10, 2026-11-21.)*
  - RF-016b. Senza `--profile`, `auth login` (integrato, con token statico e con service
    account) lavora sul profilo corrente di `config.toml`; un `InteractaClient` che risolve da
    sé il profilo usa il nome del profilo corrente per la sessione Google e per la chiave della
    cache del token. *(Spec 10, 2026-11-21.)*
- RF-017. Audit log opzionale delle chiamate API (`audit_log`), su console o su file JSON lines
  rotante (`audit_log_file`, `audit_log_max_bytes`, `audit_log_backups`); i body sono registrati
  solo con `audit_log_bodies`; `audit_log_raw` disattiva la redazione sul solo canale di logging,
  con avviso. *(Confermato dal maintainer il 2026-10-08, spec 01.)*
- RF-018. Hook di richiesta e risposta (`ClientHooks`) che ricevono `RequestInfo` e
  `ResponseInfo`, senza tipi `httpx`. *(Confermato dal maintainer il 2026-10-08, spec 01.)*
- RF-019. Errori tipizzati: ogni stato HTTP è mappato su una sottoclasse di `InteractaError`
  (autenticazione, permessi, non trovato, validazione, concorrenza, server, trasporto), con
  stato, metodo, URL, body e `request_id`. Vale anche per le scritture di cataloghi, voci e
  workspace (`409` → `ConcurrencyError`, nessun nuovo tentativo). *(Confermato dal maintainer il 2026-10-12, spec 06.)*
  - RF-023d. Una `GET` che riceve `204` senza corpo solleva `NotFoundError` (`status_code == 204`):
    è la risposta del tenant al form di modifica di un utente inesistente. *(Spec 05,
    2026-10-10.)*
- RF-020. Deep link web (`WebUrls`) a post, utenti e community a partire da `base_url` e
  `base_path`.

Scritture, decise con [ADR 0001](adr/0001-apertura-della-superficie-di-scrittura.md): ogni spec
che le realizza ne precisa i dettagli (RF-022 dalla [spec 02](02-task-write/spec.md), 0.10.0;
RF-021 per i post custom, i commenti e il workflow dalla [spec 03](03-post-write/spec.md) e per i
post evento dalla [spec 08](08-event-post-write/spec.md); RF-024 dalla
[spec 04](04-attachment-upload/spec.md); RF-023 dalle [spec 05](05-admin-users-groups/spec.md) e
[06](06-admin-catalogs-workspace/spec.md)). Stessa forma
delle letture (façade con `.raw`, kwargs espliciti
più `*_raw`, comando CLI, test unit e contract).

- RF-021. Post e commenti: creazione e modifica di post e post-evento (dati, campi custom,
  allegati, watcher, dati di screen del workflow), transizione di workflow, copia, eliminazione e
  marcatura per cancellazione, risposta di partecipazione a un evento, creazione di commenti; con
  gli helper di lettura propedeutici (`post-data-for-create|edit|copy`, `event-post-data-for-*`,
  `post-workflow-screen-data-for-edit`). La spec 03 realizza i post custom, i commenti e il
  workflow; la spec 08 i post evento. *(Confermato dal maintainer il 2026-10-10, spec 03, e il
  2026-10-13, spec 08.)*
  - RF-021a. Le letture propedeutiche `get_for_create`, `get_for_edit`, `get_for_copy` sono
    esposte come letture e restituiscono `occ_token` (dove il server lo dà) e i dati editabili;
    `edit`, `edit_custom_data` e `copy` ricevono l'`occ_token` dal chiamante. *(Spec 03.)*
  - RF-021b. `posts edit`, `posts edit-custom-data` e `posts copy` in CLI sono patch: rileggono i
    dati propedeutici e rimandano i campi non indicati; `--custom-data` e `--screen-data`
    sovrascrivono chiave per chiave; `--occ-token` e `--screen-occ-token` impongono solo il token.
    *(Spec 03.)*
  - RF-021c. `edit_attachments` e gli `attachments` di `create`, `edit`, `copy`, `add_comment`
    accettano riferimenti già noti al server e, dalla spec 04, i file appena caricati
    (`UploadedAttachment`, RF-024); `posts edit-attachments` in CLI è arrivato con la spec 04
    (RF-024a). Dalla spec 09 un `UploadedAttachment` con `downloadable` porta il flag nella voce
    degli allegati (RF-024b), che il server accetta solo sui post. *(Spec 03, aggiornato dalle
    spec 04 e 09.)*
  - RF-021d. In scrittura i riferimenti a voci di catalogo, utenti e gruppi nei campi custom e nei
    dati di screen si inviano come id, anche se le letture li restituiscono come oggetti; le patch
    della CLI traducono i valori letti che rimandano. `edit-post` e `copy-post` sostituiscono il
    post: la descrizione omessa conta come vuota. *(Spec 03, verificato sul tenant il
    2026-10-09.)*
  - RF-021e. Post evento: `create_event`, `edit_event`, `copy_event`, `participate` e le letture
    `get_event_for_create|edit|copy` stanno su `client.posts` con un kwarg per campo del DTO; il
    blocco `event` lo compone la libreria; `start_at` ed `end_at` sono `datetime` con fuso,
    inviati come data-ora locale più il nome IANA del fuso di `start_at` (RNF-010), o sole date
    senza fuso per gli eventi `all_day`; in lettura (`EventData`) sono nel fuso dell'evento, e
    `date` per gli eventi tutto il giorno; gli invitati si passano per id con un tipo unico
    facoltativo; la risposta di partecipazione è `ParticipationAnswer` (sì 1, forse 2, no 3), con
    le note in testo inviate come delta, e vale per l'identità autenticata (anche il service
    account, anche se non invitato). Il server sostituisce il post in modifica e copia: titolo,
    visibilità, fine, luogo e invitati sono obbligatori, la descrizione omessa conta come vuota,
    il fuso omesso diventa quello del server; gli invitati sono obbligatori con almeno un ospite
    (`typeId` 0 o omesso) e la lettura propedeutica non li restituisce. La libreria non aggiunge
    nulla da sola: lo dice la documentazione. *(Spec 08, verificato sul tenant il 2026-10-13.)*
  - RF-021f. In CLI: `posts create-event|edit-event|copy-event|participate|
    get-event-for-create|get-event-for-edit|get-event-for-copy`. `edit-event` e `copy-event`
    sono patch che rileggono il form evento e rimandano titolo, descrizione, visibilità,
    copertina e il blocco `event` ripulito dai campi di sola lettura, con gli invitati tradotti
    in `{id, typeId}`; gli invitati, che la lettura non restituisce, si ripassano con
    `--invite-user`/`--invite-group`; `--start`/`--end` accettano data-ora o sola data nel fuso
    di `--timezone` (in `edit-event`, per default quello dell'evento letto), e con `allDay` nel
    blocco unito diventano sole date senza fuso; `--cover` carica la copertina (RF-024a). *(Spec
    08.)*
- RF-022. Task: creazione, modifica, eliminazione. La libreria invia solo i campi passati, in una
  sola richiesta; `edit` riceve l'`occToken` dal chiamante. Il server tratta la modifica come una
  sostituzione (i campi omessi sono azzerati, tranne watcher e allegati, che hanno coppie
  add/remove) ed esige assegnatario e scadenza: lo dice la documentazione, la libreria non aggiunge
  nulla da sola. *(Confermato dal maintainer il 2026-10-08, spec 02.)*
- RF-023. Anagrafiche admin: creazione, modifica, eliminazione e credenziali degli utenti;
  creazione, modifica, eliminazione e membri dei gruppi (spec 05, 0.12.0); creazione, modifica e
  flag `deleted` (cancellazione logica, reversibile: l'API non elimina) di cataloghi e voci;
  modifica del workspace: nome, traduzioni, descrizione, membri, ruoli, copertina e logo
  (spec 06, 0.13.0). La libreria invia solo i campi passati, in una sola richiesta; `edit`,
  `edit_entry`, `edit_credentials`, `edit_members` ed `edit_workspace` ricevono l'`occToken` dal
  chiamante (per il workspace nel path). Semantica del server verificata sul tenant
  (spec 05): `users.edit` esige `firstname` e `lastname` e azzera `contactEmail`, `privateEmail`
  ed `externalId` omessi, mentre mantiene preferenze, info e impostazioni omesse; `groups.edit`
  esige `name` e azzera `email`, `externalId` e `visible` omessi, mentre mantiene i membri; in
  `edit_credentials` i blocchi omessi sono mantenuti, un blocco con `active`/`enabled` falso e
  senza account id lo rimuove, con account id è rifiutato (`INVALID_VALUE`), e username e account
  id devono stare nel dominio del tenant; dopo `delete` utente e gruppo spariscono (il form utente
  risponde `204` vuoto: RF-023d); la password generata alla creazione arriva come stringa, che la
  façade espone in lista (`generated_password`), ed è redatta in log, audit log, hook e messaggi
  di eccezione; l'`occToken` restituito da `edit_members` vale per la chiamata successiva. Lo dice
  la documentazione, la libreria non aggiunge nulla da sola. *(Confermato dal maintainer il
  2026-10-10, spec 05.)* Semantica verificata sul tenant (spec 06): `catalogs.edit` ed
  `edit_entry` sostituiscono per intero la mappa del nome o della label (le lingue omesse perdono
  il testo e `it` riceve quello passato) ed `edit_entry` azzera `externalId` e parent omessi;
  `…/entries/{id}/deleted` risponde con `entryId`; un catalogo disabilitato non compare più e
  `catalogs.list([id])` risponde `400` `NOT_EXISTS`; la `GET` del form di una voce risponde con
  qualunque `catalogId` nel path; `edit_workspace` esige `name` (`400` `REQUIRED_FIELD`) e la sua
  risposta ha l'`occ_token` successivo ma i conteggi di utenti e gruppi a `0`; il tenant può
  rispondere mappe per lingua con valori `null`. *(Confermato dal maintainer il 2026-10-12, spec 06.)*
  - RF-023a. Le letture per la modifica (`UserForEdit`, `GroupForEdit`,
    `UserCredentialsForEdit`) espongono `occ_token`, il token di concorrenza da passare alla
    scrittura; `users.get_credentials_for_edit` è l'alias di
    `admin_manage.user_credentials_for_edit`. *(Spec 05, 2026-10-10.)*
  - RF-023b. In CLI: `users create|edit|edit-credentials|delete` e
    `groups create|edit|edit-members|delete`. `users edit` e `groups edit` sono patch che
    rileggono il form e rimandano i campi non indicati; `groups edit` non tocca i membri, che si
    cambiano con `groups edit-members` (`--add`/`--remove`, o `--json` per più gruppi con exit `9`
    se un gruppo è in conflitto); `users edit-credentials` invia solo i blocchi indicati e
    `--no-google`, `--no-microsoft`, `--no-custom` rimuovono un blocco con conferma, perché il
    server mantiene i blocchi omessi e non ha credenziali disattivate. La password custom arriva
    solo da stdin o da prompt nascosto (`--password-stdin`) o è generata dal server
    (`--generate-password`), mai da un argomento; la password generata compare nell'output di
    `users create` (anche in `--export`, con avviso nei docs). *(Spec 05, 2026-10-10.)*
  - RF-023c. `groups.edit_members` su un singolo gruppo solleva `ConcurrencyError` quando il
    server lo mette in `concurrencyErrorGroups`, anche se lo stato è `200`; `edit_members_bulk`
    restituisce le due liste senza sollevare. *(Spec 05, 2026-10-10.)*
  - RF-023e. Le letture per la modifica di catalogo, voce e workspace (`CatalogForEdit`,
    `CatalogEntryForEdit`, `WorkspaceForEdit`) espongono `occ_token`; `CatalogForEdit` espone
    `parent_catalog_id` e `WorkspaceForEdit` `translations`; le lingue con valore `null` sono
    scartate dalle mappe; `catalogs.get_for_edit` e `catalogs.get_entry_for_edit` sono alias di
    `admin_manage.catalog_for_edit` e `catalog_entry_for_edit`. *(Spec 06, 2026-10-12.)*
  - RF-023f. In CLI: `catalogs create|edit|delete|restore`,
    `catalogs create-entry|edit-entry|delete-entry|restore-entry` e `admin-manage edit-workspace`.
    Le mappe per lingua si passano con `--name|--label|--description LANG=TESTO` ripetibili e si
    uniscono per lingua alla mappa letta o di `--json`. `catalogs edit`, `edit-entry` ed
    `edit-workspace` sono patch che rileggono il form (anche con `--occ-token`) e rimandano nome o
    label, parent ed external id, o nome, traduzioni e descrizione; `edit-workspace` rilegge il
    form dopo la modifica per mostrare i conteggi e, se la rilettura fallisce, avvisa ed esce `0`;
    `--cover` e `--logo` caricano i file (RF-024a) e al primo upload fallito escono `11` senza
    modifica. `delete` e `delete-entry` sono cancellazioni logiche con conferma (RF-025a),
    reversibili con `restore` e `restore-entry`, che non chiedono conferma; il flag `deleted` non
    passa da `edit`. *(Spec 06, 2026-10-12.)*
- RF-024. Upload di allegati in due passi: `POST core/storage/upload-new-attachment` senza corpo
  restituisce il riferimento (`contentRef`), l'URL dello storage temporaneo e i campi di una
  policy firmata; il file si carica con un form multipart `POST` a quell'URL, con i campi della
  policy prima del file (verificato sul tenant il 2026-10-10: il `PUT` è rifiutato).
  `client.attachments.upload(file, *, name, mime_type)` esegue entrambi i passi e restituisce
  `UploadedAttachment`, accettato dagli allegati delle scritture di post, commenti e task (nuova
  versione con `as_version_of`); `request_upload_url()` espone il primo passo. Una risposta non
  2xx dello storage è `UploadError`, timeout e rete `TransportError`; nessun nuovo tentativo.
  *(Confermato dal maintainer il 2026-10-10, spec 04.)*
  - RF-024a. In CLI: `attachments upload PATH`; `--attach PATH` ripetibile su
    `posts create|comment|edit|copy` e `tasks create|edit`, accodato agli allegati di `--json`;
    `posts edit-attachments` con `--add PATH`, `--remove ID`, `--update ID=PATH` (il server
    mantiene l'id, incrementa la versione e applica il nome nuovo). `UploadError` esce con exit
    code `11`; al primo upload fallito nessuna scrittura parte verso Interacta. *(Spec 04.)*
  - RF-024b. `attachments.upload(..., downloadable=None)`: il flag non va allo storage;
    `UploadedAttachment.downloadable` lo conserva e `as_write_input()` e `as_version_of()` lo
    aggiungono come `"downloadable"` solo se indicato (omesso, il default del server è
    scaricabile). Sul tenant di prova è applicato agli allegati dei post custom ed evento,
    mentre su commenti e task il server rifiuta la scrittura con `400` ("Unrecognized field"):
    la libreria lo invia così come lo riceve e lo dice la documentazione. In CLI passa solo
    negli allegati di `--json`. *(Spec 09, 2026-10-13.)*
- RF-025. Concorrenza ottimistica: dove l'API richiede un `occToken`, la libreria lo espone al
  chiamante e mappa il `409` su `ConcurrencyError`; non rilegge e non riprova da sola. Le
  operazioni distruttive nella CLI chiedono conferma esplicita. *(Confermato dal maintainer il
  2026-10-08, spec 02.)*
  - RF-025a. `tasks delete` (e i comandi distruttivi futuri) chiede conferma mostrando id e titolo;
    `--yes` la salta; senza terminale interattivo e senza `--yes` il comando rifiuta con exit code
    `2` e non invia nulla. *(Spec 02, 2026-10-08.)*
  - RF-025b. `tasks edit` modifica solo i campi indicati: rilegge il task e rimanda gli altri,
    perché il server sostituisce il task intero; `--occ-token` impone solo il token. *(Spec 02,
    2026-10-08, dopo la prova sul tenant.)*

Login Google integrato e server MCP, decisi con
[ADR 0002](adr/0002-server-mcp-locale-e-login-google-integrato.md): il login è realizzato
dalla [spec 10](10-google-login/spec.md), il server MCP è da realizzare; ogni spec che li
realizza ne precisa i dettagli e aggiunge i sottorequisiti.

- RF-026. Login Google integrato: `pynteracta auth login --google` esegue il flusso OAuth2 per
  applicazioni installate (authorization code con PKCE e redirect su loopback) con un client
  OAuth dell'organizzazione, il cui id sta nel profilo, e con lo scope minimo dello scambio
  (`email`, RF-002). La libreria conserva il refresh token (RNF-012) e rinnova da sola l'access
  token Google quando deve ripetere lo scambio con Interacta; la sessione si può eliminare
  (logout). Il token statico (`--google-token`, `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`,
  `google_token`, `google_token_provider`) resta valido. Il client "Desktop" di Google richiede
  il client secret allo scambio del codice (verificato il 2026-11-20): la persona lo fornisce
  una volta, mai come argomento di riga di comando. *(ADR 0002, 2026-11-20; realizzato dalla
  spec 10, 2026-11-21.)*
  - RF-026a. Il login integrato si avvia con `auth login --google` senza token statico; flag
    `--google-client-id`, `--google-client-file` (id e secret dal JSON del client "Desktop"
    scaricato dalla console Google, letto una volta e mai salvato), `--client-secret-stdin`,
    `--replace-client-secret`, `--no-browser`, `--login-timeout` (predefinito 300 s); profilo
    e portachiavi sono scritti solo dopo lo scambio riuscito con Interacta; i flag del login
    integrato insieme a un token statico sono un errore d'uso (exit `2`). *(Spec 10, 2026-11-21.)*
  - RF-026b. La sessione è distinta per profilo e tenant; il client secret è legato all'id del
    client. Precedenza: token o provider esplicito > variabile d'ambiente > sessione salvata.
    Un client costruito senza profilo non usa la sessione. *(Spec 10, 2026-11-21.)*
  - RF-026c. Rinnovo senza browser. `invalid_grant` e sessione assente → `AuthenticationError`
    con l'invito al login; `invalid_client` → `AuthenticationError` con l'indicazione di
    sostituire il secret; rete e timeout → `TransportError` senza nuovo tentativo. Una sessione
    rifiutata resta nel portachiavi finché non è sostituita o eliminata. *(Spec 10, 2026-11-21.)*
  - RF-026d. `auth status`: stato del profilo e della sessione senza rete e senza segreti, exit
    `0`; `--check` prova l'autenticazione ed esce `3` se fallisce. *(Spec 10, 2026-11-21.)*
  - RF-026e. `auth logout` elimina la sessione Google del profilo senza rete;
    `--forget-client-secret` elimina il secret; `--revoke` revoca presso Google ed elimina
    comunque in locale; quando non c'è nulla da revocare o da eliminare lo dice in una nota,
    con exit `0`. *(Spec 10, 2026-11-21.)*
  - RF-026f. Funzioni pubbliche di libreria per login, logout e stato su un profilo
    (`pynteracta.google_login`). *(Spec 10, 2026-11-21.)*
  - RF-026g. Extra `pynteracta[google]` (porta `keyring`); senza, il login integrato fallisce
    nominando l'extra. *(Spec 10, 2026-11-21.)*
- RF-027. Server MCP locale: `pynteracta mcp serve` avvia un server MCP sul solo trasporto
  stdio, distribuito come extra opzionale (`pynteracta[mcp]`). Agisce con l'identità del
  profilo: quella prevista è Google OAuth2 personale; un profilo con service account è
  accettato con un avviso, sullo standard error e nello strumento dell'identità corrente.
  Espone letture curate per intento (identità corrente, community, post, storia, commenti,
  allegati, cataloghi, hashtag, dettaglio di un task), con output ridotto e paginazione
  limitata; mai gli endpoint `admin/*` né gli elenchi di utenti e gruppi. Creazione, modifica
  ed eliminazione dei task sono registrate come strumenti solo con `--enable-task-writes`;
  nessun'altra scrittura è esposta. Le regole sulle scritture valgono anche qui (RF-025,
  RNF-009): un esito incerto torna al modello come "esito sconosciuto, non ripetere", un `409`
  come conflitto, e l'eliminazione è dichiarata distruttiva nelle annotazioni MCP perché sia il
  client a chiedere conferma. Il server non apre mai il browser: se la sessione Google manca o
  è revocata, gli strumenti rispondono con un errore che indica di rieseguire il login.
  *(ADR 0002, 2026-11-20.)*

## 4. Requisiti non funzionali

Confermato dal maintainer il 2026-10-13. Solo ciò che il codice o la configurazione mostrano.

- RNF-001. Redazione prima di log, audit log e hook, dentro il transport: gli header
  `Authorization`, `Proxy-Authorization` e quelli il cui nome contiene `token`, `secret`,
  `password` o `api-key` perdono l'intero valore; in `Cookie` e `Set-Cookie` ogni cookie perde il
  valore e conserva nome e attributi (un header cookie non analizzabile con certezza è redatto per
  intero); i JWT sono sostituiti ovunque; i campi `token|password|secret|privatekey|assertion|jwt`
  dei body sono sostituiti da `***REDACTED***`. *(Confermato dal maintainer il 2026-10-08;
  precisato dalla spec 01, che chiude P-01.)* Dalla spec 04 le chiavi sensibili dei body
  comprendono anche `signature` e `policy`, e negli URL i parametri di query il cui nome
  contiene `signature`, `token`, `secret`, `password` o `key` perdono il valore (nome e altri
  parametri restano), ovunque si applica la redazione. Dalla spec 07 i campi di concorrenza
  ottimistica `occToken`, `nextOccToken`, `screenOccToken`, `nextScreenOccToken` (e le grafie
  snake_case) non sono segreti e passano in chiaro nei body redatti, per nome esatto e senza
  distinzione di maiuscole; ogni altra chiave che contiene `token` resta redatta (RNF-001b).
  Con ADR 0002 la redazione copre anche i segreti del login Google, sulle chiamate agli
  endpoint di Google come su quelle a Interacta: refresh token, authorization code,
  verificatore PKCE, id token e client secret non compaiono in log, audit log, hook né
  messaggi di eccezione (realizzato dalla spec 10).
  - RNF-001c. Le chiamate agli endpoint di Google (token, userinfo, revoca) sono registrate in
    log, audit log e hook con metodo, URL e stato, mai con i corpi, neppure con
    `audit_log_bodies` e `audit_log_raw`. *(Spec 10, 2026-11-21.)*
- RNF-002. Cache del token su file con permessi POSIX stretti (`0o600` file, `0o700` cartella),
  lettura rifiutata se più larghi; su Windows avviso una tantum e raccomandazione di
  `token_cache = "memory"`.
- RNF-003. Tipizzazione completa: `py.typed`, `mypy --strict`, modelli pydantic v2 generati dal
  swagger pinnato (`datamodel-code-generator`) e façade a mano con `extra="ignore"` e `.raw` per
  la compatibilità in avanti.
- RNF-004. Python ≥ 3.12, client sincrono (`httpx.Client`); nessun client asincrono.
- RNF-005. La libreria non configura il logging a import: `structlog.configure()` solo dentro
  `setup_default_logging()`, chiamata solo dalla CLI.
- RNF-006. Qualità misurata in CI: ruff (lint e formato), mypy strict, unit test su Python 3.12 e
  3.13 con copertura ≥ 85 %, contract test contro il swagger, build della distribuzione e del sito.
- RNF-007. Licenza Apache-2.0 con intestazione SPDX su ogni sorgente; distribuzione su PyPI via
  trusted publishing (OIDC), senza token nel repository.
- RNF-008. Timeout configurabile (`timeout_seconds`, default 30 s); nessun retry automatico.
- RNF-009. Nessuna operazione ripetuta in automatico verso Interacta (ADR 0001, regola non
  negoziabile): una scrittura che fallisce in modo incerto (timeout, errore di rete) non si ritenta
  da sola, l'errore risale al chiamante con esito sconosciuto; un futuro retry/backoff vale solo
  per le letture. *(Confermato dal maintainer il 2026-10-08, spec 02.)*
- RNF-010. Le date-ora di scrittura (`expiration`, `scheduled_publication`, inizio e fine degli
  eventi) accettano solo `datetime` con fuso orario e arrivano al server come data-ora locale più
  nome IANA del fuso (offset fisso → UTC); la CLI interpreta i valori senza offset nel fuso
  `--timezone` (predefinito `Europe/Rome`). Eccezione: gli eventi tutto il giorno viaggiano come
  sole date senza fuso, l'unica forma che il server accetta. *(Spec 02, 2026-10-08; confermato
  dal maintainer per gli eventi il 2026-10-13, spec 08.)*
- RNF-011. Il contenuto dei file caricati non compare mai in log, audit log né hook, neppure con
  `audit_log_bodies`: la richiesta allo storage è registrata con URL e stato, senza corpo, e non
  porta il token Interacta. *(Spec 04, 2026-10-10.)*
- RNF-012. Segreti di lunga durata nel portachiavi di sistema (ADR 0002, regola non
  negoziabile; affianca RNF-002): il refresh token Google e il client secret OAuth stanno nel
  Portachiavi di macOS o nella Gestione credenziali di Windows, mai in `config.toml`, mai in
  un file in chiaro, mai nei log. Se il portachiavi non è disponibile (per esempio Linux senza
  sessione grafica) il login integrato fallisce con un messaggio chiaro, senza ripiegare su un
  file. Nessun id o segreto di client OAuth è distribuito con il codice. *(ADR 0002,
  2026-11-20; realizzato dalla spec 10, 2026-11-21.)*
  - RNF-012a. Sono accettati i portachiavi di sistema (macOS, Windows e, senza supporto
    dichiarato, Secret Service e KWallet su Linux); sono rifiutati quelli assenti o che
    conservano in chiaro su file. La voce della sessione contiene refresh token, email
    dell'account Google e data del login. *(Spec 10, 2026-11-21.)*
- RNF-013. Canale stdio riservato al protocollo (ADR 0002, regola non negoziabile): in modalità
  server MCP lo standard output porta solo messaggi MCP; log e diagnostica vanno sullo standard
  error. *(ADR 0002, 2026-11-20; da realizzare con RF-027.)*

## 5. Integrazioni esterne

Confermato dal maintainer il 2026-10-10 (spec 03), per la parte dell'API `external_v2`; righe
"Google OAuth2" e "Portachiavi di sistema" riconfermate il 2026-11-21 (spec 10).

| Sistema | Uso | Come si collega |
|---|---|---|
| Interacta REST API `external_v2` | letture e scritture | HTTPS verso `{base_url}{base_path}/api/external/v{api_version}/`, header `Authorization: Bearer <token>` e `User-Agent: pynteracta/<versione>` |
| Interacta auth (`core/auth`) | ottenere l'access token | `create-access-token-by-service-account` con asserzione JWT RS512; `create-access-token-by-google-oauth2-access-token-credentials` con token Google |
| Google OAuth2 | identità personale | con il token statico lo procura l'utente fuori dalla libreria, che lo inoltra una sola volta per lo scambio; con il login integrato (ADR 0002, RF-026) la libreria chiama direttamente gli endpoint di autorizzazione (nel browser della persona, redirect su loopback), di token, userinfo (email dell'account) e revoca di Google, con il client OAuth "Desktop" dell'ente in un'app "Internal" del Workspace |
| Portachiavi di sistema | custodia del refresh token Google e del client secret (RNF-012) | Portachiavi di macOS e Gestione credenziali di Windows, tramite `keyring` (extra `pynteracta[google]`); su Linux Secret Service e KWallet, senza supporto dichiarato; rifiutati i backend assenti o in chiaro su file |
| Client MCP | usa Interacta per conto della persona (ADR 0002, RF-027) | avvia `pynteracta mcp serve` in locale e parla MCP su stdio; nessun trasporto di rete |
| PyPI, GitHub Releases, GitHub Pages | distribuzione e documentazione | solo in CI, su tag `v*` e push su `main`; nessun uso a runtime |

## 6. Dati personali trattati

Confermato dal maintainer il 2026-10-13 (le voci sulle scritture erano già confermate spec per
spec); riconfermato il 2026-11-21 per il login Google integrato (spec 10).

- **Dati letti dal tenant**: anagrafiche degli utenti Interacta (nome, cognome, email, id, stato,
  provider di login), contenuti di post, commenti, allegati e task, membri dei gruppi. La libreria
  li restituisce al chiamante e, nella CLI, li stampa o li esporta su file **scelti
  dall'operatore**; non li conserva.
- **Dati scritti su disco dalla libreria**: il token di accesso (cache su file, permessi stretti,
  cartella utente); il file di configurazione (URL del tenant, percorso della chiave, profili);
  l'audit log, solo se abilitato, che contiene URL, header redatti e, con `audit_log_bodies`, i
  body delle risposte e quindi i dati personali sopra elencati (eccezione documentata nelle
  Regole non negoziabili del `CLAUDE.md`); i token di concorrenza ottimistica vi compaiono in
  chiaro (RNF-001b). *(Confermato dal maintainer il 2026-10-12, spec 07, per la parte
  sull'audit log.)* Con il login Google integrato (ADR 0002, RF-026): il refresh token Google e
  il client secret, solo nel portachiavi di sistema (RNF-012), insieme all'email dell'account
  Google e alla data del login, che `auth status` mostra e che non compaiono mai nei log
  applicativi; l'id del client OAuth nel profilo. Il file JSON del client scaricato dalla
  console (`--google-client-file`) è letto una volta e non è copiato né modificato.
- **Dati passati al client MCP** (ADR 0002, RF-027): ciò che gli strumenti del server leggono
  dal tenant (contenuti di post, commenti e task, nomi, metadati degli allegati) passa al
  client MCP e da lì al fornitore del modello. È un trattamento che la libreria non controlla,
  a carico di chi abilita il server; la guida al server lo dichiara.
- **Dati scritti sul tenant** (dalle spec di scrittura, ADR 0001): anagrafiche di utenti
  (compresi i dati di credenziale), appartenenze ai gruppi, contenuti di post, commenti, task e
  allegati forniti dal chiamante. La libreria li inoltra al tenant così come li riceve; non li
  conserva e non li logga (eccezione: audit log con `audit_log_bodies`, come sopra). *(Confermato
  dal maintainer il 2026-10-08, spec 02: titolo e descrizione dei task, id di assegnatari e
  watcher.)* Gli allegati caricati (spec 04) passano dalla libreria allo storage temporaneo del
  tenant così come il chiamante li fornisce, con nome e MIME; la libreria non li conserva né li
  logga, e i file temporanei scadono con la policy del tenant. *(Confermato dal maintainer il
  2026-10-10, spec 04.)* Il flag `downloadable` degli allegati dei post (spec 09) non è un dato
  personale. Le anagrafiche admin (spec 05): nome, cognome, email di contatto e
  privata, riferimento esterno, preferenze, info e impostazioni degli utenti; le credenziali
  (account Google e Microsoft, username custom, password impostata o generata, che la libreria
  redige in log, audit log, hook e messaggi di eccezione e mostra solo nell'output di
  `users create`); nome, email e membri dei gruppi. *(Confermato dal maintainer il 2026-10-10,
  spec 05.)* Cataloghi e voci (spec 06): nomi e label per lingua, external id e
  parent, dati non personali; il workspace: nome, traduzioni, descrizione, id di utenti, gruppi
  e ruoli aggiunti o tolti, e i file di copertina e logo, che passano dallo storage temporaneo
  come gli allegati. *(Confermato dal maintainer il 2026-10-12, spec 06.)* Post evento (spec 08): oltre ai
  contenuti dei post, date, fuso e luogo dell'evento, id di utenti e gruppi invitati, risposta
  di partecipazione e note dell'identità autenticata. *(Confermato dal maintainer il 2026-10-13,
  spec 08.)*
- **Chiave del service account**: letta dal percorso configurato, mai copiata altrove; la chiave
  privata non compare nei log.
- **Conservazione**: nessuna, oltre a cache del token (fino alla scadenza) e audit log (rotazione a
  `audit_log_max_bytes` × `audit_log_backups`), entrambi a carico di chi li abilita, e alla
  sessione Google nel portachiavi (refresh token, email dell'account e data del login fino al
  logout o alla revoca; client secret fino a `--forget-client-secret`; ADR 0002, spec 10).

## 7. Fuori ambito

Confermato dal maintainer il 2026-10-10 (spec 03), per la parte dei post; riconfermato il
2026-11-21 (spec 10).

- Client asincrono.
- Autenticazione Microsoft OAuth2 e username/password.
- Retry automatico con backoff sulle scritture (vedi RNF-009); sulle letture è solo rimandato.
- Risoluzione automatica dei conflitti di concorrenza (`occToken`): spetta al chiamante.
- Server MCP remoto (HTTP) con autenticazione per utente (ADR 0002): il server è solo locale,
  su stdio.
- Scritture via MCP oltre i task: allargarle richiede una spec che citi ADR 0002. Area admin ed
  elenchi di utenti e gruppi via MCP: richiedono un nuovo ADR.
- Un client OAuth (id o segreto) distribuito con il pacchetto: lo fornisce l'organizzazione.
- Versione 1.0 con semver stretto, finché la superficie di lettura non è completa e stabile.

## Storia del documento

- 2026-10-08: prima versione, ricostruita dal codice (v0.9.4, commit `f0398bc`).
- 2026-10-08: apertura della superficie di scrittura (§1, RF-021…RF-025, RNF-009, §6, §7), vedi
  [ADR 0001](adr/0001-apertura-della-superficie-di-scrittura.md).
- 2026-10-08: §1 e §2 confermati dal maintainer; §1 aggiunge gli usi da strumenti di vibe coding e
  come base di un server MCP non ufficiale.
- 2026-10-08: RNF-001 precisato dalla [spec 01](01-redazione-cookie-header/spec.md) (cookie e
  header redatti per nome); RF-017, RF-018 e RNF-001 confermati dal maintainer.
- 2026-10-08: [spec 02](02-task-write/spec.md) (scrittura dei task, 0.10.0): RF-022 precisato con
  la semantica del server; nuovi RF-022a, RF-015a, RF-025a, RF-025b, RNF-010; RF-022, RF-025,
  RNF-009 e la voce "Dati scritti sul tenant" di §6 confermati dal maintainer.
- 2026-10-10: [spec 03](03-post-write/spec.md) (scrittura dei post custom, commenti e workflow,
  0.11.0): nuovi RF-006a, RF-021a, RF-021b, RF-021c, RF-021d; RF-021, RF-006, §5 (con "letture e
  scritture") e §7 confermati dal maintainer.
- 2026-10-10: [spec 04](04-attachment-upload/spec.md) (upload degli allegati, 0.12.0): RF-024
  precisato con il meccanismo verificato sul tenant (form multipart firmato); nuovi RF-024a e
  RNF-011; RNF-001 precisato (firme e query sensibili); RF-021c aggiornato; RF-024 e la voce
  "Dati scritti sul tenant" di §6 confermati dal maintainer.
- 2026-10-10: [spec 05](05-admin-users-groups/spec.md) (anagrafiche admin, prima metà: utenti e
  gruppi, 0.13.0): RF-023 precisato con la semantica verificata sul tenant; nuovi RF-023a,
  RF-023b, RF-023c, RF-023d; RF-023, RF-005, RF-011, RF-013 e la voce "Dati scritti sul tenant"
  di §6 confermati dal maintainer.
- 2026-10-12: [spec 06](06-admin-catalogs-workspace/spec.md) (anagrafiche admin, seconda metà:
  cataloghi, voci e workspace, 0.13.0): RF-023 precisato con la semantica verificata sul tenant
  e con la versione della spec 05 corretta in 0.12.0; nuovi RF-023e e RF-023f; RF-023, RF-008,
  RF-013, RF-019 e la voce "Dati scritti sul tenant" di §6 confermati dal maintainer.
- 2026-10-13: [spec 08](08-event-post-write/spec.md) (scrittura dei post evento, 0.14.0): nuovi
  RF-021e e RF-021f con la semantica verificata sul tenant; RF-021 aggiornato (post evento
  realizzati); §1 con la superficie di scrittura dell'ADR 0001 completa; RNF-010 esteso alle date
  degli eventi; RF-021, RNF-010 e la voce "Dati scritti sul tenant" di §6 confermati dal
  maintainer per la parte degli eventi.
- 2026-10-13: §3, §4 e §6 confermati per intero dal maintainer a scritture completate; lo stato del
  documento passa da bozza a confermato e la versione di riferimento da 0.9.4 a 0.14.0 (branch
  `bugfix_docs_allineamento`, allineamento dei documenti di governo).
- 2026-10-13: [spec 09](09-swagger-align/spec.md) (allineamento allo swagger live, 0.15.0):
  swagger ripinnato e modelli rigenerati con ordine stabile delle definizioni; nuovi RF-006b,
  RF-007a e RF-024b con la semantica verificata sul tenant; RF-021c e §6 aggiornati per
  `downloadable`; §1 dice che tutti i 76 endpoint dello swagger pinnato sono esposti.
- 2026-11-20: server MCP locale e login Google integrato, vedi
  [ADR 0002](adr/0002-server-mcp-locale-e-login-google-integrato.md): §1, §2 (nuovo attore, riga
  "Utente Google"), RF-002 (scope minimo `email`) e RF-003 precisati, nuovi RF-026 e RF-027,
  RNF-001 esteso, nuovi RNF-012 e RNF-013, §5, §6 e §7 (esce "ottenere un token Google per conto
  dell'utente"). RF-026, RF-027, RNF-012 e RNF-013 sono decisi e da realizzare.
- 2026-11-21: [spec 10](10-google-login/spec.md) (login Google integrato con rinnovo
  automatico): RF-026, RNF-012 e l'estensione di RNF-001 realizzati; nuovi RF-026a…RF-026g,
  RF-016a, RF-016b, RNF-012a e RNF-001c; §1 e §3 non dicono più il login "da realizzare"; §5
  con gli endpoint userinfo e revoca e i portachiavi accettati; §6 con l'email dell'account
  nel portachiavi e il file JSON del client; §2 (riga "Utente Google"), §5, §6 e §7
  riconfermati dal maintainer.
