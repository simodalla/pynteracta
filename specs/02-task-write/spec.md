# 02 – Scrittura dei task: creazione, modifica, eliminazione

Stato: chiusa
Branch: `m28_task_write`
Requisiti del PRD: RF-022, RF-025, RNF-009; toccati RF-010, RF-015, RF-019
Dipende da: nessuna (spec 01 chiusa)

Prima spec della superficie di scrittura aperta da
[ADR 0001](../adr/0001-apertura-della-superficie-di-scrittura.md): il gruppo più piccolo (3
endpoint), banco di prova per `occToken`, `ConcurrencyError` e la conferma delle operazioni
distruttive in CLI.

## Scopo

Chi scrive automazioni con la libreria, e chi usa la CLI, può creare un task su un post, modificarne
i dati ed eliminarlo, con la stessa forma delle letture: metodi tipizzati con kwargs espliciti e
varianti `*_raw`, façade con `.raw`, comandi `tasks create|edit|delete` che compongono con
`--output`, `--full`, `--fields`, `--export`. La concorrenza ottimistica resta visibile al
chiamante; nessuna scrittura viene ripetuta da sola.

## Comportamento attuale

Sui task esiste solo la lettura: `client.tasks.get(task_id)` restituisce la façade `Task`
(`id`, `post_id`, `title`, `description_plain_text`, `expiration`, `priority`, `state`, assegnatari,
watcher, `capabilities`, `sub_tasks`, `reminders`, `.raw`) e la CLI ha `tasks get`. La façade non
espone `occToken`, che il server restituisce. Il client base sa fare solo `GET` e `POST`. Il `409`
è già mappato su `ConcurrencyError`, ma nella CLI finisce nell'exit code generico `1`. Nessun
comando chiede conferme. I DTO di richiesta e risposta delle tre scritture sono già nei modelli
generati dal swagger pinnato: nessuna rigenerazione.

## Comportamento

### Libreria

- **Creare**: `client.tasks.create(post_id, *, title=None, description_delta=None,
  description_plain_text=None, expiration=None, priority=None, sub_tasks=None,
  assignee_user_id=None, assignee_group_id=None, attachments=None, watcher_user_ids=None,
  watcher_group_ids=None, client_uid=None)` invia la richiesta di creazione al post indicato con
  **solo i campi passati**, in camelCase, e restituisce un `TaskWriteResult` con `task_id`,
  `next_occ_token`, `task` (i dati del task appena creato), `capabilities` e `.raw`. `create_raw(post_id,
  req: CreateTaskRequestDTO)` fa lo stesso da un DTO già costruito.
- **Modificare**: `client.tasks.edit(task_id, occ_token, *, title=None, description_delta=None,
  description_plain_text=None, expiration=None, priority=None, sub_tasks=None,
  assignee_user_id=None, assignee_group_id=None, add_attachments=None, remove_attachment_ids=None,
  add_watcher_user_ids=None, remove_watcher_user_ids=None, add_watcher_group_ids=None,
  remove_watcher_group_ids=None)` invia la modifica con il token di concorrenza nel percorso e **solo
  i campi passati** nel corpo; restituisce un `TaskWriteResult` con il `next_occ_token` da usare
  per la modifica successiva. `edit_raw(task_id, occ_token, req: EditTaskRequestDTO)` idem.
  `occ_token` lo fornisce il chiamante: lo legge da `Task.occ_token`, che la lettura ora espone.
- **Eliminare**: `client.tasks.delete(task_id)` elimina il task e restituisce il `post_id` del post
  che lo conteneva.
- **Scadenza**: `expiration` è un `datetime` **con fuso orario**; la libreria lo traduce nella
  coppia `{datetime, timezone}` attesa dal server (data e ora locali del fuso e nome IANA del fuso).
  Un `datetime` senza fuso è rifiutato con `ValueError` prima di qualunque chiamata.
- **Errori**: come per le letture (`400 → ValidationError`, `403 → PermissionError`,
  `404 → NotFoundError`, `409 → ConcurrencyError`, timeout e rete → `TransportError`). Una scrittura
  che fallisce in modo incerto non si ripete: una sola richiesta per chiamata, sempre.
- **Campi omessi in `edit`**: non vengono inviati. Il server tratta la modifica come una
  **sostituzione** (verificato sul tenant di prova, T11, 2026-10-08): `title`, descrizione,
  `priority`, `expiration`, assegnatario e `subTasks` omessi vengono **azzerati**; i watcher e gli
  allegati, che hanno coppie add/remove, restano. Lo stesso tenant esige sempre un assegnatario
  (`assigneeUserId` o `assigneeGroupId`: senza, `400` sul campo `assignee`) e una `expiration`
  (senza, `500`), in creazione e in modifica, e per ogni sub-task uno `state` diverso da `0`,
  anche se lo swagger non marca nulla come obbligatorio. La libreria non aggiunge nulla da sola:
  `docs/api/tasks.md` lo dice come avviso, con l'elenco dei campi da ripassare.

### CLI

- `pynteracta tasks create POST_ID [--title T] [--description TEXT] [--expiration ISO8601]
  [--timezone IANA] [--priority N] [--assignee-user ID] [--assignee-group ID] [--watcher-user ID]…
  [--watcher-group ID]… [--client-uid UID] [--json FILE|-]` crea il task e mostra il risultato
  con `render_output` (tabella curata: id, post_id, title, state, priority, expiration, assignee;
  `--output json`, `--full`, `--fields`, `--export` come per `tasks get`). `--json` prende il
  DTO completo da file o da stdin (`-`): serve per sub-task e allegati; se compaiono anche i flag,
  i flag prevalgono campo per campo. `--description` riempie `descriptionPlainText`.
  `--expiration` è una data-ora ISO 8601 senza fuso, interpretata nel fuso di `--timezone`
  (predefinito `Europe/Rome`); con un offset esplicito nel valore, `--timezone` è ignorato.
- `pynteracta tasks edit TASK_ID [stessi flag] [--remove-watcher-user ID]… [--remove-watcher-group
  ID]… [--occ-token N]` è una **patch**: legge il task, costruisce il corpo dai valori letti
  (`title`, `descriptionDelta`, `expiration` come `{datetime: localDatetime, timezone}`,
  `priority`, `assigneeUserId` o `assigneeGroupId`, `subTasks` con `id`, `description`, `state`),
  vi sovrappone il corpo di `--json` e poi i flag, e invia la modifica con l'`occToken` letto. Un
  campo assente nel task letto non viene inventato. `--description` (o `descriptionPlainText` in
  `--json`) sostituisce la descrizione: il `descriptionDelta` letto non viene inviato. I watcher
  non compaiono nel corpo se non con `--watcher-*`/`--remove-watcher-*`. `--occ-token N` impone
  il token da usare nella `PUT`; la lettura avviene comunque, perché serve per il corpo. Su `409`
  esce con il nuovo exit code **9** e il messaggio `Task TASK_ID changed since it was read: fetch
  it again and retry`. Mai un secondo tentativo.
- `pynteracta tasks delete TASK_ID [--yes|-y]` legge il task, mostra `Delete task TASK_ID
  "<title>"? [y/N]` e procede solo con `y`; con `--yes` non chiede; senza terminale interattivo e
  senza `--yes` rifiuta con un messaggio (`--yes is required when not running interactively`) e
  nessuna richiesta di eliminazione parte. In caso di successo stampa `Task TASK_ID deleted (post
  POST_ID)` e, con `--output json`, `{"task_id": …, "post_id": …}`.
- I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI e del sito.
- Exit code: `9` per `ConcurrencyError`, documentato in `docs/cli.md` accanto agli altri.

### Documentazione e test

`docs/api/tasks.md` (metodi, `TaskWriteResult`, `occ_token`, formato della scadenza, semantica dei
campi omessi), `docs/cli.md` (tre comandi, `--json`, exit code 9), `docs/testing.md` e
`tests/integration/.env.example` (variabile `PYNTERACTA_TEST_WRITE_POST_ID`). Fixture JSON e
contract test per i DTO delle tre scritture. Integration test opt-in che esegue il ciclo
`create → edit → delete` su un post di prova, con pulizia garantita.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 02-C01 | Quando si chiama `client.tasks.create(42, title="T", priority=2, watcher_user_ids=[7])`, parte una sola `POST …/communication/tasks/manage/create-task/42` con corpo `{"title": "T", "priority": 2, "watcherUserIds": [7]}` (nessun'altra chiave) e, con una risposta `CreateTaskResponseDTO`, il risultato ha `task_id`, `next_occ_token`, `task.title`, `capabilities.can_modify` e `.raw` valorizzati dalla risposta. | RF-022 |
| 02-C02 | Quando si chiama `create_raw(42, CreateTaskRequestDTO(title="T"))`, la richiesta e il risultato sono gli stessi di 02-C01 con quel corpo. | RF-022 |
| 02-C03 | Quando `expiration` è `datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome"))`, il corpo contiene `"expiration": {"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"}`; quando è senza fuso, `create` ed `edit` sollevano `ValueError` e nessuna richiesta parte. | RF-022, RNF-010 |
| 02-C04 | Quando si chiama `client.tasks.edit(7001, 3, title="T2", remove_watcher_user_ids=[7])`, parte una sola `PUT …/communication/tasks/manage/edit-task/7001/3` con corpo `{"title": "T2", "removeWatcherUserIds": [7]}` e il risultato ha `next_occ_token` e `task` dalla risposta `EditTaskResponseDTO`; `edit_raw` con il DTO equivalente produce la stessa richiesta. | RF-022, RF-025 |
| 02-C05 | Quando il server risponde `409` a `edit`, viene sollevata `ConcurrencyError` con `status_code == 409` e il server ha ricevuto **esattamente una** richiesta. | RF-025, RNF-009 |
| 02-C06 | Quando si chiama `client.tasks.delete(7001)`, parte una sola `DELETE …/communication/tasks/manage/delete-task/7001` e il valore restituito è il `postId` della risposta. | RF-022 |
| 02-C07 | Quando `tasks.get(7001)` riceve un `GetTaskDetailResponseDTO` con `occToken: 5`, `Task.occ_token == 5`. | RF-010, RF-022a |
| 02-C08 | Quando si esegue `tasks create 42 --title T --priority 2 --watcher-user 7 --watcher-user 8 --json body.json` dove `body.json` contiene `{"title": "X", "assigneeUserId": 9}`, il corpo inviato è `{"title": "T", "priority": 2, "watcherUserIds": [7, 8], "assigneeUserId": 9}` (i flag prevalgono) e l'output tabella mostra id, title, state, priority del task creato; `--output json` restituisce la risposta serializzata. | RF-022, RF-015 |
| 02-C09 | *Sostituito da 02-C17 il 2026-10-08 (T11: il server azzera i campi omessi).* ~~Quando si esegue `tasks edit 7001 --title T2`, la CLI fa prima `GET …/task-detail-by-id/7001` e poi `PUT …/edit-task/7001/<occToken letto>`; con `--occ-token 3` non fa la `GET` e usa `3`.~~ | RF-022, RF-025 |
| 02-C10 | Quando la `PUT` di `tasks edit` risponde `409`, il comando termina con exit code `9`, stampa `Task 7001 changed since it was read: fetch it again and retry` e il server ha ricevuto una sola `PUT`. | RF-025, RF-015a, RNF-009 |
| 02-C11 | Quando si esegue `tasks delete 7001` in un terminale interattivo, il prompt riporta id e titolo; con risposta `y` parte la `DELETE` e il comando stampa `Task 7001 deleted (post 42)`; con risposta `n` nessuna `DELETE` parte e l'exit code è `0`. | RF-025, RF-025a |
| 02-C12 | Quando si esegue `tasks delete 7001 --yes`, nessun prompt compare e la `DELETE` parte; senza terminale interattivo e senza `--yes`, nessuna `DELETE` parte, l'exit code è `2` (errore d'uso, come gli altri della CLI) e il messaggio dice che serve `--yes`. | RF-025a |
| 02-C13 | Quando `create` va in timeout o errore di rete, viene sollevata `TransportError` e il server ha ricevuto al più una richiesta. | RNF-009 |
| 02-C14 | I contract test dimostrano che i modelli generati `CreateTaskRequestDTO`, `CreateTaskResponseDTO`, `EditTaskRequestDTO`, `EditTaskResponseDTO`, `DeleteTaskResponseDTO` coprono tutte le proprietà del swagger pinnato, e le fixture JSON di risposta si leggono nelle façade. | RF-022, RNF-003 |
| 02-C15 | `docs/cli.md` documenta `tasks create`, `tasks edit`, `tasks delete` e l'exit code `9`; `docs/api/tasks.md` documenta `create`, `edit`, `delete`, `TaskWriteResult`, `occ_token` e il formato della scadenza; `uv run mkdocs build --strict` e `test_docs_snippets` sono verdi. | RF-015 |
| 02-C16 | Quando `PYNTERACTA_TEST_WRITE_POST_ID` e `PYNTERACTA_TEST_USER_ID` sono impostate (integration, opt-in), il ciclo `create` (con `client_uid` riconoscibile, `expiration` e assegnatario) → `get` (occ_token) → `edit` → `delete` termina senza errori sul tenant e il task non esiste più al termine; senza una delle variabili il test è saltato. | RF-022, RF-025 |
| 02-C17 | Quando si esegue `tasks edit 7001 --title T2` e la `GET …/task-detail-by-id/7001` restituisce un task con `descriptionDelta`, `expiration` (`localDatetime`, `timezone`), `priority`, `assigneeUser.id` e `subTasks`, la `PUT …/edit-task/7001/<occToken letto>` ha corpo `{"title": "T2", "descriptionDelta": <letto>, "expiration": {"datetime": <localDatetime letto>, "timezone": <timezone letto>}, "priority": <letta>, "assigneeUserId": <id letto>, "subTasks": [{"id", "description", "state"} letti]}` e nessun'altra chiave; con `--occ-token 3` la `GET` avviene lo stesso e la `PUT` usa `3`. | RF-022, RF-025, RF-025b |
| 02-C18 | Quando si esegue `tasks edit 7001 --description X --priority 3 --json body.json` con `body.json` = `{"priority": 2, "assigneeGroupId": 9}` sul task di 02-C17, il corpo contiene `descriptionPlainText: "X"` e non `descriptionDelta`, `priority: 3` (flag > json > letto), `assigneeGroupId: 9` **e** `assigneeUserId` letto (la CLI non decide tra i due); quando il task letto non ha scadenza, assegnatario o sub-task, le chiavi corrispondenti mancano dal corpo. | RF-022, RF-025b |

## Casi limite

- `create` senza alcun campo → corpo `{}` inviato così com'è; decide il server (02-C01: nessuna
  chiave in più oltre a quelle passate).
- `expiration` con fuso UTC → `{"datetime": "…", "timezone": "UTC"}` (02-C03); `datetime` naive →
  `ValueError` (02-C03).
- `edit` con tutti i kwargs a `None` → `PUT` con corpo `{}` (02-C04: solo i campi passati).
- `occ_token` sbagliato → `409 → ConcurrencyError`, una sola richiesta (02-C05).
- `delete` di un task inesistente → `404 → NotFoundError`, exit `5` in CLI (comportamento esistente
  degli errori).
- `tasks edit` su un task che il `GET` non trova → exit `5`, nessuna `PUT`, anche con
  `--occ-token` (02-C17 implica la sequenza; il caso è coperto dal mapping errori esistente).
- `tasks edit` con `--json` che contiene `descriptionDelta` → quello vince sul delta letto e
  `descriptionPlainText` non viene aggiunto (02-C18: il delta si toglie solo quando arriva un
  testo semplice).
- `tasks edit` che rimanda i `subTasks` letti: il server li ricrea con id nuovi (osservato in T11);
  la CLI non può evitarlo, `docs/cli.md` lo dice.
- `--json -` con stdin vuoto o JSON non valido → exit `2`, nessuna richiesta.
- `--json` con chiavi sconosciute → rifiutato con exit `2` (i DTO generati non le accettano in
  modo silenzioso: la CLI valida con il DTO prima di inviare).
- `--expiration` con offset esplicito (`2026-12-31T18:00+01:00`) → fuso dell'offset, `--timezone`
  ignorato; `--timezone` non IANA → exit `2`.
- `tasks delete` con risposta al prompt diversa da `y`/`Y` → nessuna richiesta, exit `0` (02-C11).
- Timeout **dopo** l'invio di `create`: il task potrebbe esistere; la libreria solleva
  `TransportError` e non riprova (02-C13); il chiamante può cercarlo con il `client_uid`, se lo
  ha passato, tramite le letture del post.

## Dati personali e segreti

Passano al tenant: titolo e descrizione del task, id di assegnatari e watcher (utenti e gruppi),
riferimenti ad allegati. La libreria li inoltra e non li conserva; l'audit log opzionale li
registra solo con `audit_log_bodies` (eccezione documentata). Nei log applicativi compaiono solo
metodo, URL redatto e stato. Nessun segreto nuovo. Gli integration test usano un post di prova
dedicato (`PYNTERACTA_TEST_WRITE_POST_ID`), mai il post di produzione dei test di lettura, e un
`client_uid` riconoscibile (`pynteracta-it-<timestamp>`).

## Requisiti nuovi

- RF-022a. La lettura di un task espone `occ_token`, il token di concorrenza da passare alla
  modifica.
- RF-015a. La CLI termina con exit code `9` quando una scrittura fallisce per conflitto di
  concorrenza (`409`).
- RF-025a (precisa RF-025). `tasks delete` chiede conferma mostrando id e titolo; `--yes` la salta;
  senza terminale interattivo e senza `--yes` il comando rifiuta.
- RNF-010. Le date-ora di scrittura (`expiration`) accettano solo `datetime` con fuso; la CLI
  interpreta i valori senza offset nel fuso `--timezone` (predefinito `Europe/Rome`).
- RF-025b (precisa RF-025). `tasks edit` modifica solo i campi indicati: rilegge il task e
  rimanda gli altri, perché il server sostituisce il task intero e azzera ciò che manca.

## Fuori ambito

- Upload di nuovi allegati (RF-024): `attachments` e `add_attachments` accettano solo riferimenti
  già noti al server (`attachmentId` o `name`+`contentRef`).
- Scritture dei post e dei commenti (RF-021), anagrafiche admin (RF-023).
- Cambio di stato, promemoria e commenti dei task: nessun endpoint in `tasks/manage`.
- Retry automatico e risoluzione automatica del `409` (RNF-009, ADR 0001).
- Nome IANA del fuso di sistema (`tzlocal`): default fisso `Europe/Rome`.
- Traduzione in italiano della CLI esistente.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Kwargs per tutti i campi del DTO, più `*_raw` | Sottoinsieme curato + raw; solo `*_raw` | Scoperta completa per un agente, un solo posto da documentare; forma delle letture (ADR 0001) |
| `edit(task_id, occ_token, …)` con token esplicito; `Task.occ_token` esposto | `edit(task, …)` dalla façade; GET implicita nella libreria | La concorrenza resta visibile al chiamante (RF-025); la libreria non rilegge per conto suo |
| Ritorno = façade sulla risposta (`TaskWriteResult`), `delete` → `post_id` | Rileggere e restituire `Task`; solo gli id | Nessuna chiamata in più, niente perso della risposta (`nextOccToken`, `capabilities`) |
| CLI: flag per i campi semplici + `--json FILE\|-`, flag prevalgono | Solo flag; solo `--json` | Uso interattivo comodo e DTO completo per sub-task e allegati |
| `tasks edit`: GET implicita, `--occ-token` opzionale | `--occ-token` obbligatorio | La CLI è lo strumento dell'operatore; la libreria resta esplicita |
| `tasks edit` è una patch (2026-10-08, dopo T11): corpo = task letto < `--json` < flag; `--occ-token` impone solo il token, la lettura resta | Solo i campi passati anche in CLI, con avviso nei docs; libreria che rilegge da sola | Con "solo i campi passati" `tasks edit --title` fallisce (`500` senza scadenza) o azzera priorità, descrizione, assegnatario e sub-task: una trappola per l'operatore. La libreria resta "una richiesta, campi espliciti" (ADR 0001, RF-025) |
| `tasks delete`: prompt con id e titolo, `--yes`, rifiuto senza TTY | Solo `--yes`; prompt senza GET | Nessuna cancellazione silenziosa negli script; schema riusabile dalle prossime spec |
| `EXIT_CONFLICT = 9` | Restare su `1` | Uno script distingue "rileggi e riprova tu" dagli altri errori |
| `expiration` = `datetime` aware; CLI ISO 8601 + `--timezone` default `Europe/Rome` | Stringhe grezze come il DTO; `tzlocal`; fuso obbligatorio | Tipi Python, errore prima della chiamata; PA italiana, nessuna dipendenza in più |
| Corpo con i soli campi passati; semantica dei campi omessi verificata contro il server e documentata | Inviare sempre l'oggetto completo | Comportamento della libreria definito e testabile senza GET aggiuntiva |
| Integration test opt-in su `PYNTERACTA_TEST_WRITE_POST_ID` | Nessun integration test di scrittura | Fissa formato di `expiration` e campi omessi contro il server reale, con pulizia |
| ROADMAP: riga `0.10.0` al posto di `0.9.5` | Due righe | La 0.9.5 non verrà mai taggata: i `feat` producono un minor |
| Testi della CLI in inglese | Italiano per il codice nuovo | Help e messaggi uniformi con la CLI e il sito esistenti; precisazione di una riga nella sezione Lingua del `CLAUDE.md` nel task di chiusura |

## Verifica manuale

- Il formato esatto di `expiration` accettato dal server (data-ora locale del fuso, come
  specificato in 02-C03) e l'effetto dei campi omessi in `edit` (invariati o azzerati) si
  stabiliscono eseguendo 02-C16 contro il tenant di prova, perché lo swagger non li documenta.
  L'esito si registra in `docs/api/tasks.md` e in `verifica.md`; se il server azzera i campi
  omessi, la documentazione lo dice come avviso. Fino a quell'esecuzione 02-C16 vale come saltato.
  **Esito (2026-10-08, T11)**: formato accettato, restituito come `{zonedDatetime, localDatetime,
  timezone}`; campi omessi azzerati; assegnatario e scadenza obbligatori; `state` dei sub-task
  obbligatorio e `0` rifiutato. Dettaglio in `tasks.md`, T11.

## Revisioni

- 2026-10-08, dopo T11: `tasks edit` diventa una patch (02-C09 sostituito da 02-C17 e 02-C18,
  RF-025b); semantica dei campi omessi e campi obbligatori del tenant scritte in "Libreria";
  02-C16 richiede anche `PYNTERACTA_TEST_USER_ID`.

## Domande aperte

Nessuna.
