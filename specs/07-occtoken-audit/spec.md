# 07 – I token di concorrenza ottimistica passano in chiaro nei body redatti

Stato: approvata
Branch: `m33_occtoken_audit`
Requisiti del PRD: RNF-001, RF-017, RF-018, RF-025
Dipende da: 01 (redazione per nome di header e cookie), 04 (chiavi `signature` e `policy`, query firmate)

Chiude il follow-up aperto dalla verifica della [spec 05](../05-admin-users-groups/verifica.md) e
ripetuto in `PROGRESS.md` (M31): "`occToken` è redatto nei body dell'audit log (la chiave contiene
`token`): innocuo, ma rende meno leggibile l'audit delle scritture".

## Scopo

Chi attiva l'audit log con i body, o registra un hook, deve poter ricostruire quale token di
concorrenza ottimistica ha letto e quale ha inviato in una scrittura: oggi vede
`"occToken": "***REDACTED***"` e non distingue una modifica andata a buon fine da una partita con un
token vecchio. L'`occToken` è un contatore di versione dell'entità, non un segreto; con questa spec
lui e le sue varianti passano in chiaro nei body, mentre tutto il resto della redazione resta com'è.

## Comportamento attuale

La redazione dei body sostituisce con `***REDACTED***` il valore di ogni chiave il cui nome
contiene, maiuscole indifferenti, `token`, `password`, `secret`, `privatekey`, `assertion`, `jwt`,
`signature` o `policy`, a qualunque profondità di dict e liste; nei valori stringa sostituisce i
JWT e i parametri di query sensibili. Si applica dentro il transport ai body di richiesta e di
risposta prima che raggiungano gli eventi `audit.request` / `audit.response` (console e file, solo
con `audit_log_bodies`) e i hook (`RequestInfo.body`, `ResponseInfo.body`), e a ogni evento di log
con chiave `body` tramite il processore structlog.

Per effetto della parola `token`, sono redatte anche le chiavi `occToken` (nei body di
`users.edit`, `groups.edit`, `catalogs.edit`, `edit_entry`, `edit_credentials`, in ogni elemento
di `edit_members` e nelle risposte dei form `get_for_edit`), `nextOccToken` (nelle risposte degli
`edit`), `screenOccToken` e `nextScreenOccToken` (nei form admin). L'`occToken` passato nel path
(`edit-post/{postId}/{occToken}`, `workspaces/{workspaceId}/{occToken}`) non è toccato, perché la
redazione degli URL agisce solo sui parametri di query. `--audit-raw` toglie la redazione sul solo
canale di logging.

## Comportamento

Quando un body di richiesta o di risposta arriva a chi lo osserva (hook, audit log su console o
file, qualunque evento di log con `body`), i campi di concorrenza ottimistica sono in chiaro:

- **Chiavi escluse dalla redazione**: `occToken`, `nextOccToken`, `screenOccToken`,
  `nextScreenOccToken` e le grafie snake_case `occ_token`, `next_occ_token`, `screen_occ_token`,
  `next_screen_occ_token`. Il confronto è sul **nome esatto**, maiuscole indifferenti
  (`OCCTOKEN`, `OccToken`…), a qualunque profondità e dentro le liste. Il valore resta quello che è
  (numero o stringa).
- **In dubbio si redige**: una chiave che contiene `token` ma non è nell'elenco (`userOccToken`,
  `myToken`, `accessToken`, `nextPageToken`…) resta `***REDACTED***` come oggi.
- **Tutto il resto resta com'è**: le altre chiavi sensibili (`password`, `secret`, `privateKey`,
  `assertion`, `jwt`, `signature`, `policy`), i JWT nei valori stringa, i parametri di query
  firmati, gli header e i cookie. La redazione avviene ancora nel transport, prima di hook e
  logging, quindi vale senza configurazione e in modo identico sui tre canali; `--audit-raw` continua
  a togliere la redazione sul solo canale di logging.

Nel sito, la pagina "Audit Logging" ("Redaction guarantees") dice che i token di concorrenza
ottimistica passano in chiaro e perché.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 07-C01 | Quando un body è `{"occToken": 7, "password": "x"}`, la redazione restituisce `occToken` pari a `7` e `password` pari a `***REDACTED***`. | RNF-001, RF-025 |
| 07-C02 | Quando la chiave è una tra `occToken`, `nextOccToken`, `screenOccToken`, `nextScreenOccToken`, `occ_token`, `next_occ_token`, `screen_occ_token`, `next_screen_occ_token`, `OCCTOKEN`, `OccToken`, il valore resta invariato, sia numero sia stringa. | RNF-001, RF-025 |
| 07-C03 | Quando la chiave è una tra `userOccToken`, `myToken`, `accessToken`, `nextPageToken`, `token`, `TOKEN`, il valore è `***REDACTED***`: la regola generale sul nome che contiene `token` non cambia. | RNF-001 |
| 07-C04 | Quando il body ha la forma di `edit_members` (`[{"id": 1, "occToken": 3, "addUserIds": [5]}, {"id": 2, "occToken": 4, "deleteUserIds": [6]}]`) o di un form admin (`{"data": {"occToken": 3, "screenOccToken": 2, "password": "x"}}`), gli `occToken` restano a ogni livello e `password` è `***REDACTED***`. | RNF-001, RF-025 |
| 07-C05 | Quando sono attivi audit su console, audit su file, `audit_log_bodies` e un hook, una richiesta con body `{"occToken": 3, "password": "s3cret"}` e la sua risposta con body `{"nextOccToken": 4, "accessToken": "a"}` producono: `"occToken": 3` nell'evento `audit.request` su console e su file e in `RequestInfo.body`; `"nextOccToken": 4` nell'evento `audit.response` su console e su file e in `ResponseInfo.body`; la stringa `s3cret` e il valore di `accessToken` in nessuno dei tre canali. | RNF-001, RF-017, RF-018, RF-025 |
| 07-C06 | Quando un evento di log passa dal processore structlog con `body={"occToken": 3, "token": "x"}`, l'evento emesso contiene `"occToken": 3` e `"token": "***REDACTED***"`; lo stesso evento scritto dall'handler di file dell'audit ha lo stesso contenuto. | RNF-001, RF-017 |
| 07-C07 | Quando `audit_log_raw` è attivo, l'`occToken` resta in chiaro e l'avviso `audit.redaction_disabled` è emesso come prima: nulla cambia su quel canale. | RF-017 |
| 07-C08 | La pagina `docs/logging.md` elenca i token di concorrenza ottimistica come eccezione alle chiavi redatte nei body; `uv run mkdocs build --strict` e `tests/unit/test_docs_snippets.py` sono verdi. | RF-017 |

## Casi limite

- `occToken` dentro gli elementi di una lista (`edit_members`) o dentro `data` di un form → in
  chiaro a ogni livello (07-C04).
- Valore stringa invece che numero (`"occToken": "12"`) → invariato; la redazione dei JWT nei
  valori stringa continua ad applicarsi, ma un contatore non ha mai la forma `eyJ…` (07-C02).
- Chiave che finisce in `occToken` ma non è nell'elenco (`userOccToken`) → redatta (07-C03).
- `nextPageToken` e gli altri cursori di paginazione → redatti come oggi (07-C03, fuori ambito).
- `accessToken` e `portal_api_jwt_token*` delle risposte di autenticazione → redatti (07-C03).
- Stessa chiave con maiuscole diverse (`OCCTOKEN`) → in chiaro: il confronto ignora le maiuscole
  (07-C02).
- `audit_log_raw` attivo → nessuna differenza rispetto a oggi su quel canale (07-C07).

## Dati personali e segreti

Passano: i token di concorrenza ottimistica, numeri interi (o stringhe) che il tenant assegna a
ogni versione di utente, gruppo, catalogo, voce, workspace, post e task. Non sono credenziali: non
autenticano nessuno e non danno accesso a nulla; chi li conosce può al più provocare un `409` su
una scrittura che il tenant gli permette già. Non si salva nulla di nuovo: l'audit log, solo con
`audit_log_bodies`, continua a contenere i body già elencati nella sezione 6 del PRD, ora con gli
`occToken` in chiaro. Non devono mai comparire, in nessun canale: password, segreti, JWT, chiavi
private, `accessToken`, firme e policy dello storage, valori dei cookie e degli header redatti per
nome. Nessun dato personale nuovo.

## Requisiti nuovi

- RNF-001b (precisazione di RNF-001): i campi di concorrenza ottimistica `occToken`,
  `nextOccToken`, `screenOccToken`, `nextScreenOccToken` (e le grafie snake_case) non sono
  segreti e passano in chiaro nei body redatti, per nome esatto; ogni altra chiave che contiene
  `token` resta redatta. Entra nel PRD con il task di chiusura, insieme alla conferma della sezione
  6 ("Dati personali trattati", parte sull'audit log) data dal maintainer il 2026-10-12.

## Fuori ambito

- I cursori di paginazione (`pageToken`, `nextPageToken`, `nextSyncToken`): restano redatti; spec
  a parte se si vorrà renderli leggibili.
- Il `response_body` delle eccezioni e i messaggi di errore: non passano dalla redazione dei body
  e non portano `occToken`.
- `--audit-raw`: resta un bypass del solo canale di logging.
- Header, cookie, query firmate e JWT: nessun cambiamento.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Eccezione per nome esatto, maiuscole indifferenti, limitata alla famiglia occ del swagger (`occToken`, `nextOccToken`, `screenOccToken`, `nextScreenOccToken`) | Solo `occToken`; ogni chiave che finisce in `occToken` | Le quattro chiavi hanno la stessa natura; un suffisso allenterebbe "in dubbio si redige" (spec 01) |
| Grafie snake_case incluse | Solo camelCase del swagger | I body verso Interacta sono camelCase, ma il processore structlog riceve qualunque dict e le façade usano `occ_token` |
| Cursori di paginazione fuori ambito | Escluderli insieme agli occ | Il follow-up riguarda le scritture; i cursori sono una scelta a parte |
| Commit `fix(audit)` e patch 0.13.1 subito dopo il merge, riga `0.13.1 ⏳ M33` in ROADMAP | Uscire con la prossima minor | Correzione piccola e autonoma; l'audit delle scritture già rilasciate ne beneficia subito |

## Verifica manuale

Nessuna.

## Domande aperte

Nessuna.
