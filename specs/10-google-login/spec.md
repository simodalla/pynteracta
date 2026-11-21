# 10 – Login Google integrato con rinnovo automatico

Stato: approvata
Branch: `m36_google_login`
Requisiti del PRD: RF-026, RNF-012, RNF-001 (estensione ai segreti Google); toccati RF-002,
RF-003, RF-004, RF-015, RF-016, RF-017, RF-018, RF-019; §2 (riga "Utente Google"), §5 (righe "Google
OAuth2" e "Portachiavi di sistema"), §6 e §7, riconfermati dal maintainer il 2026-11-21
Dipende da: [ADR 0002](../adr/0002-server-mcp-locale-e-login-google-integrato.md) (decisioni 6
e 7); spec 01 (chiusa): redazione di header e body. Lascia pronto per la spec 11 (server MCP):
la sessione salvata, il rinnovo senza browser e gli errori che invitano a rifare il login

## Scopo

Chi usa `pynteracta` con l'identità personale fa il login Google una volta, dal browser, e da
lì in poi CLI e libreria lavorano senza che debba procurarsi un access token ogni ora: la
sessione sta nel portachiavi di sistema e la libreria la rinnova da sola. È il prerequisito del
server MCP (spec 11), ma vale da solo per la CLI e per chi usa la libreria da Python.

## Comportamento attuale

- La libreria riceve un access token Google già pronto (`--google-token`,
  `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`, `google_token`, `google_token_provider`) e lo scambia con un
  token Interacta. Non esegue alcun flusso di login e non salva il token Google.
- `pynteracta auth login --google` senza token esce con codice `2` ("No Google access token").
  Con un token scrive nel profilo `auth_method = "google_oauth2"` (più l'indirizzo del tenant, se
  il profilo è nuovo) **prima** di validare, poi scambia il token e stampa
  `✓ Authenticated as: <nome>`.
- `InteractaClient` costruito da un profilo `google_oauth2` senza token solleva
  `AuthenticationError` alla costruzione. La variabile d'ambiente confluisce nel profilo; i
  parametri espliciti (`google_token`, `google_token_provider`) vincono su di essa.
- Il token Interacta ottenuto dallo scambio è in cache, con chiave per tenant e nome del
  profilo, e dura un'ora (verificato sul tenant il 2026-11-20). Alla scadenza la libreria ripete
  lo scambio con lo stesso token Google, che nel frattempo è scaduto se era statico.
- `auth logout` cancella solo la cache del token Interacta. Non esiste un comando di stato.
- Su un profilo `google_oauth2`, `auth logout` dice di aver svuotato la cache ma lascia il file
  del token: il client calcola la chiave di cache sull'indirizzo dello scambio Google
  (`…/portal/api`), il logout su quello dell'API (`…/portal/api/external/v2`). Con il service
  account le due chiavi coincidono (verificato il 2026-11-21).
- `auth login` senza `--profile` scrive nel profilo `default`, mentre gli altri comandi usano il
  profilo corrente di `config.toml` (`current_profile`): se i due nomi differiscono, il login
  configura un profilo che i comandi successivi non leggono. Allo stesso modo un
  `InteractaClient` che risolve da sé il profilo, senza `profile_name`, usa `default` come nome
  nella chiave della cache del token.
- Il profilo non ha campi per il client OAuth. Gli extra del pacchetto sono `yaml`, `parquet`
  ed `export`.
- `docs/authentication.md` e la docstring delle credenziali Google dicono che la libreria non
  esegue il login; la docstring cita ancora lo scope minimo `profile`, mentre il tenant vuole
  `email` (RF-002).

## Comportamento

### Login dal browser

`pynteracta auth login --google`, quando non c'è un token statico (né `--google-token` né la
variabile d'ambiente), esegue il login integrato:

1. Controlla, prima di qualunque richiesta di rete, che il profilo abbia l'id del client OAuth
   (campo `google_client_id`, impostabile anche con `PYNTERACTA_GOOGLE_CLIENT_ID`, con
   `config set` o con `--google-client-id` sul comando), che l'extra `pynteracta[google]` sia
   installato e che un portachiavi di sistema sia disponibile. Se manca qualcosa esce con codice
   `2` e dice cosa manca: il nome del campo, il nome dell'extra, oppure che il portachiavi non
   c'è e che resta il token statico.
2. Se nel portachiavi non c'è il client secret di quel client, lo chiede con un prompt nascosto,
   oppure lo legge dalla prima riga dello standard input con `--client-secret-stdin`. Senza
   terminale interattivo e senza quel flag esce con codice `2`. Il secret non si passa mai come
   argomento. `--replace-client-secret` lo chiede di nuovo anche se è già salvato;
   `--client-secret-stdin` usa sempre il valore letto.

   In alternativa `--google-client-file PERCORSO` legge id e secret dal file JSON che la console
   Google fa scaricare per un client "Desktop app" (sezione `installed`). Il file è letto una
   volta, prima di qualunque richiesta di rete: l'id prende il posto di `--google-client-id`, il
   secret quello del prompt, e vale come valore nuovo (come con `--client-secret-stdin`). Il
   percorso non è salvato da nessuna parte e il file non è modificato né eliminato: la
   documentazione consiglia di cancellarlo dopo il login. Un file illeggibile, non JSON, di un
   client diverso da "Desktop" (per esempio la sezione `web`) o senza id o secret fa uscire il
   comando con `2`, con il motivo e senza mai riportare il contenuto del file. Il flag non si
   combina con `--client-secret-stdin`, né con un `--google-client-id` diverso da quello del
   file.
3. Apre il browser sul consenso Google con lo scope `email`, e stampa comunque l'indirizzo se il
   browser non si apre; con `--no-browser` stampa solo l'indirizzo. Attende la risposta su un
   indirizzo di loopback per al più 300 secondi (`--login-timeout SECONDI` per cambiarli).
4. Il browser mostra una pagina di solo testo, in inglese, che dice se il login è riuscito o
   fallito e che la finestra si può chiudere. La pagina non contiene segreti.
5. Scambia subito il token Google con Interacta e stampa l'identità ottenuta, come oggi
   (`✓ Authenticated as: <nome>`).
6. Solo a questo punto salva: nel profilo `auth_method = "google_oauth2"`, i dati di connessione
   mancanti e l'id del client; nel portachiavi la sessione (refresh token, email dell'account
   Google, data del login) e il client secret, se è nuovo o sostituito.

Se un passo fallisce, profilo e portachiavi restano com'erano prima del comando. Se il consenso
riesce ma l'account Google non è collegato a un utente Interacta, il comando lo dice in modo
esplicito (l'account va collegato dall'amministratore del tenant), esce con codice `3` e non
conserva nulla, nemmeno il client secret appena inserito.

Un nuovo login su un profilo che ha già una sessione la sostituisce senza chiedere conferma e
invalida il token Interacta in cache, così non resta in uso l'identità precedente.

Senza `--profile`, `auth login` lavora sul profilo corrente di `config.toml`, lo stesso che
usano gli altri comandi: vale per il login integrato, per quello con token statico e per quello
con service account (oggi scrivono in `default`). Così la sessione e la configurazione finiscono
dove i comandi successivi le cercano. Per la stessa ragione un `InteractaClient` che risolve da
sé il profilo, senza `profile_name`, usa il nome del profilo corrente per la sessione e per la
cache del token.

Con un token statico il comando si comporta per il resto come oggi, compresa la scrittura del
profilo prima della validazione. I flag del login integrato (`--google-client-id`,
`--google-client-file`, `--client-secret-stdin`, `--replace-client-secret`, `--no-browser`,
`--login-timeout`) insieme a un token statico sono un
errore d'uso: codice `2`, con il motivo (per la variabile d'ambiente, l'invito a toglierla).

### Sessione e rinnovo

La sessione è distinta per profilo e per tenant, come la chiave della cache del token: non è mai
usata contro un altro host, nemmeno se l'indirizzo del profilo viene cambiato o sovrascritto da
un flag. Il client secret è invece legato all'id del client: profili con lo stesso client lo
condividono e lo chiedono una volta sola.

Un comando della CLI, o un `InteractaClient` costruito dal profilo, con `auth_method =
"google_oauth2"` e senza token usa la sessione salvata. Quando il token Interacta manca o sta
per scadere, la libreria chiede a Google un access token nuovo con il refresh token e ripete lo
scambio con Interacta, senza aprire il browser e senza chiedere nulla. Se Google restituisce un
refresh token nuovo, la libreria lo salva al posto del precedente.

Precedenza: un token o un provider passato in modo esplicito vince sulla variabile d'ambiente,
che vince sulla sessione salvata. Un client costruito con il solo `base_url`, senza profilo, non
usa mai la sessione.

Quando la sessione non c'è o non vale più, la libreria non riapre mai il browser da sola:

- sessione assente: `AuthenticationError` con l'invito a eseguire `pynteracta auth login
  --google`; se manca l'extra `google` il messaggio cita anche quello, oltre al token statico;
- sessione revocata o scaduta (Google risponde `invalid_grant`): `AuthenticationError` con lo
  stesso invito; la sessione resta nel portachiavi finché un nuovo login non la sostituisce o un
  logout non la elimina;
- client secret non più valido (`invalid_client`): `AuthenticationError` che indica di rifare il
  login con `--replace-client-secret`;
- account non più collegato (Interacta risponde `401` allo scambio): `AuthenticationError`, come
  oggi;
- timeout o errore di rete verso Google: `TransportError`, senza nuovo tentativo e senza toccare
  la sessione.

In CLI gli errori di autenticazione escono con codice `3` e quelli di trasporto con `7`, come
per le chiamate a Interacta.

### Stato

`pynteracta auth status` descrive il profilo attivo senza fare richieste di rete e senza
mostrare segreti: nome del profilo, indirizzo del tenant, metodo di autenticazione, id del
client OAuth, se c'è una sessione Google salvata, per quale account (email) e da quando, se c'è
il client secret. Vale per ogni profilo, anche con service account (le voci Google risultano
assenti). Se l'extra o il portachiavi mancano lo dice al posto delle voci che non può leggere.
L'output passa dai formati comuni (`--output`, `--fields`, `--export`), ed esce sempre con
codice `0`.

`auth status --check` prova inoltre ad autenticarsi (per una sessione Google: rinnovo e
scambio), mostra l'identità ottenuta ed esce con `3` se l'autenticazione non riesce.

### Logout

`pynteracta auth logout`, oltre alla cache del token Interacta, elimina dal portachiavi la
sessione Google del profilo (refresh token, email, data) e non fa richieste di rete. Il client
secret resta.

- `--forget-client-secret` elimina anche il client secret del client del profilo.
- `--revoke` chiede prima a Google di revocare il refresh token. La revoca vale per il consenso
  dato a quel client: fa decadere anche le sessioni dello stesso account su altri profili o
  postazioni, e la documentazione lo dice. Se la revoca fallisce, la sessione locale è eliminata
  comunque; il comando lo segnala ed esce con il codice dell'errore.

Su un profilo senza sessione Google il comando si comporta come oggi, salvo una nota quando
sono chiesti `--revoke` o `--forget-client-secret` e non c'è nulla su cui agire: senza sessione
Google `--revoke` non revoca nulla e lo dice; senza client secret salvato
`--forget-client-secret` non elimina nulla e lo dice. Vale anche per i profili con service
account, dove l'utente può aver dimenticato `--profile`. L'uscita resta `0`.

### Da Python

Chi non usa la CLI ha funzioni pubbliche e documentate che lavorano su un profilo (per nome, o
un `Profile` con il suo nome): una avvia il login, con il client secret come parametro
facoltativo (se manca, usa quello nel portachiavi) o in alternativa il percorso del file JSON
del client, e la possibilità di non aprire il browser;
le altre eliminano la sessione e ne leggono lo stato. `InteractaClient(profile_name=...)` usa da
solo la sessione salvata. Nessuna di queste funzioni scrive sullo standard output.

### Pacchetto e documentazione

`keyring` arriva con l'extra `pynteracta[google]`; l'installazione base non cambia. La spec 11
farà sì che `pynteracta[mcp]` lo includa. Il supporto dichiarato è per macOS (Portachiavi) e
Windows (Gestione credenziali); su Linux il login funziona dove c'è un portachiavi di sistema
(Secret Service, KWallet) ed è rifiutato dove non c'è o dove l'unico disponibile conserva i
dati in chiaro su file.

`docs/authentication.md` (sezione Google riscritta, con la creazione del client OAuth
dell'ente), `docs/configuration.md`, `docs/cli.md`, `docs/index.md` e `README.md` descrivono il
nuovo comportamento, senza numeri di versione e con valori di esempio finti e riconoscibili.
Nel `CLAUDE.md` si aggiornano la mappa dei moduli e lo "Stack".

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 10-C01 | Con `google_client_id` nel profilo e client secret nel portachiavi, `auth login --google` senza token statico apre un indirizzo di consenso Google che contiene l'id del client, lo scope `email` e nessun altro, una challenge PKCE `S256`, un parametro `state` e un redirect su `127.0.0.1`. | RF-026, RF-002 |
| 10-C02 | Quando il browser non si apre, o con `--no-browser`, l'indirizzo di consenso compare a terminale; con `--no-browser` il browser non viene invocato. | RF-026 |
| 10-C03 | Quando Google restituisce codice e token e Interacta accetta lo scambio, il comando stampa `✓ Authenticated as: <nome>` ed esce `0`; dopo, il profilo contiene `auth_method = "google_oauth2"`, `base_url` e `google_client_id`, e il portachiavi contiene refresh token, email dell'account e data del login per quel profilo e tenant. | RF-026, RF-016, RNF-012 |
| 10-C04 | Senza `google_client_id` (profilo, ambiente, flag), il comando esce `2` nominando il campo, senza richieste di rete e senza aprire il browser. | RF-026, RF-016 |
| 10-C05 | Senza `keyring` installato, il comando esce `2` con un messaggio che contiene `pynteracta[google]`. | RF-026 |
| 10-C06 | Con un portachiavi assente o che conserva in chiaro su file, il comando esce `2` con un messaggio che rimanda al token statico, e non scrive alcun file. | RNF-012 |
| 10-C07 | Senza client secret nel portachiavi: da terminale interattivo il secret è chiesto con un prompt nascosto; con `--client-secret-stdin` è letto dalla prima riga dello standard input; senza terminale e senza flag il comando esce `2` prima di aprire il browser. Il comando non ha un'opzione che accetti il secret come valore. | RF-026, RNF-012 |
| 10-C08 | Una risposta al redirect con `state` diverso da quello inviato fa uscire il comando con `3`, senza chiamare il token endpoint e senza salvare nulla. | RF-026 |
| 10-C09 | Consenso negato (`error=access_denied`), nessuna risposta entro il timeout, o risposta di Google senza refresh token: il comando esce `3` con il motivo, e profilo e portachiavi sono identici a prima. | RF-026 |
| 10-C10 | Il listener del redirect è in ascolto solo su un indirizzo di loopback, smette di accettare connessioni dopo la prima risposta al redirect e si chiude allo scadere di `--login-timeout` (predefinito 300 secondi). | RF-026 |
| 10-C11 | Quando lo scambio con Interacta risponde `401` dopo un consenso riuscito, il comando esce `3` con un messaggio che dice che l'account Google non è collegato a un utente Interacta; profilo e portachiavi sono identici a prima, compreso il client secret appena inserito, che non viene salvato. | RF-026, RF-002 |
| 10-C12 | Con `--google-token` o `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`, `auth login --google` non apre il browser, non legge né scrive il portachiavi e produce lo stesso output e le stesse scritture nel profilo di oggi. | RF-026, RF-002 |
| 10-C13 | Un flag del login integrato insieme a un token statico (flag o variabile d'ambiente) fa uscire il comando con `2`, con un messaggio che nomina il conflitto, prima di qualunque richiesta. | RF-026 |
| 10-C14 | Con una sessione salvata e nessun token in ambiente, un comando della CLI e `InteractaClient(profile_name=...)` ottengono il token Interacta chiamando il token endpoint di Google con il refresh token e poi lo scambio, senza invocare il browser. | RF-026, RF-003 |
| 10-C15 | Quando il token Interacta in cache è a meno di 60 secondi dalla scadenza, la chiamata successiva rinnova l'access token Google e ripete lo scambio, e la richiesta all'API parte con il token nuovo. | RF-003, RF-026 |
| 10-C16 | Con una sessione salvata: `google_token` o `google_token_provider` espliciti sono usati al posto della variabile d'ambiente e della sessione; la variabile d'ambiente al posto della sessione. In entrambi i casi il token endpoint di Google non è chiamato. | RF-026, RF-002 |
| 10-C17 | La sessione salvata per un profilo e un tenant non è trovata con lo stesso profilo e un altro `base_url`, né con un altro profilo sullo stesso tenant: il client solleva `AuthenticationError` con l'invito al login. Un client costruito con il solo `base_url` non legge il portachiavi. | RF-026, RNF-012 |
| 10-C18 | Con profilo `google_oauth2`, nessun token e nessuna sessione, il client solleva `AuthenticationError` il cui messaggio contiene `auth login --google`; se `keyring` non è installato il messaggio contiene anche `pynteracta[google]`. In CLI exit `3`. | RF-026, RF-019, RF-015 |
| 10-C19 | Quando Google risponde `invalid_grant` al rinnovo, la libreria solleva `AuthenticationError` con l'invito al login (CLI: exit `3`), non invoca il browser e lascia intatta la voce nel portachiavi. | RF-026, RF-019 |
| 10-C20 | Quando Google risponde `invalid_client` al rinnovo o allo scambio del codice, la libreria solleva `AuthenticationError` il cui messaggio indica `--replace-client-secret`. | RF-026, RF-019 |
| 10-C21 | Un timeout o un errore di rete verso Google al rinnovo solleva `TransportError` (CLI: exit `7`) dopo una sola richiesta, e la sessione resta nel portachiavi. | RF-019, RNF-008 |
| 10-C22 | Quando la risposta di Google al rinnovo contiene un refresh token, la voce nel portachiavi contiene quello nuovo. | RF-026 |
| 10-C23 | Un login riuscito su un profilo con sessione e token Interacta in cache sostituisce la sessione ed elimina il token in cache: la chiamata successiva usa il token ottenuto dal nuovo scambio. | RF-026, RF-003 |
| 10-C24 | `auth status` mostra profilo, tenant, metodo di autenticazione, id del client, presenza della sessione, email, data del login e presenza del client secret; non fa richieste di rete, non contiene né refresh token né client secret, esce `0` anche senza sessione, e rispetta `--output json` (snapshot). | RF-026, RF-015 |
| 10-C25 | `auth status` su un profilo con service account, e su un sistema senza `keyring` o senza portachiavi, esce `0` e riporta le voci Google come assenti o non leggibili, con il motivo. | RF-026 |
| 10-C26 | `auth status --check` con una sessione valida mostra l'identità ottenuta da Interacta ed esce `0`; con una sessione che Google rifiuta esce `3`. | RF-026, RF-004 |
| 10-C27 | `auth logout` su un profilo con sessione elimina dal portachiavi la sessione di quel profilo e tenant e la cache del token Interacta, lascia il client secret e le sessioni degli altri profili, e non fa richieste di rete. | RF-026, RNF-012 |
| 10-C28 | `auth logout --forget-client-secret` elimina anche il client secret del client del profilo. | RF-026, RNF-012 |
| 10-C29 | `auth logout --revoke` chiama l'endpoint di revoca di Google con il refresh token e poi elimina la sessione; se la revoca fallisce la sessione è eliminata comunque, il comando lo segnala ed esce con il codice dell'errore. | RF-026 |
| 10-C30 | Con un client secret già salvato, `--replace-client-secret` e `--client-secret-stdin` usano il valore nuovo per lo scambio del codice e lo salvano al posto del vecchio solo a login riuscito; se il login fallisce resta il vecchio. | RF-026, RNF-012 |
| 10-C31 | Due profili con lo stesso `google_client_id`: dopo il login del primo, il login del secondo non chiede il client secret. | RF-026, RNF-012 |
| 10-C32 | La funzione di login della libreria, chiamata su un profilo con il client secret come parametro e con Google simulato, salva la stessa sessione della CLI e restituisce l'identità senza scrivere sullo standard output; le funzioni di stato e di logout danno gli stessi esiti di `auth status` e `auth logout`. | RF-026 |
| 10-C33 | Con audit log, `audit_log_bodies`, `audit_log_raw` e un hook attivi, durante login, rinnovo e revoca i valori di refresh token, authorization code, verificatore PKCE, id token, client secret e access token Google non compaiono in log applicativi, audit log, dati passati agli hook né messaggi di eccezione, nemmeno quando Google risponde con un errore. | RNF-001, RNF-012 |
| 10-C34 | Le chiamate al token endpoint, all'endpoint userinfo (da cui la libreria legge l'email dell'account) e all'endpoint di revoca di Google compaiono nell'audit log e arrivano agli hook con metodo, URL e stato, e senza corpo di richiesta né di risposta. | RNF-001, RF-017, RF-018 |
| 10-C35 | L'email dell'account Google non compare nei log applicativi durante login, rinnovo, stato e logout. | RNF-012 |
| 10-C36 | La pagina servita al browser dopo il redirect non contiene authorization code, `state` né token. | RNF-001 |
| 10-C37 | `keyring` non è tra le dipendenze di base del pacchetto ed è nell'extra `google`; `import pynteracta` e i comandi che non usano il login integrato funzionano senza `keyring` installato. | RF-026 |
| 10-C38 | `uv run mkdocs build --strict` passa, e `docs/authentication.md` non afferma più che la libreria non esegue il login Google. | RF-026 |
| 10-C39 | Con `current_profile = "prod"` in `config.toml` e senza `--profile`, `auth login` (integrato, con token statico e con service account) scrive nel profilo `prod` e non crea il profilo `default`; con `--profile X` scrive in `X`, come oggi. | RF-016, RF-026 |
| 10-C40 | Con `current_profile = "prod"`, un `InteractaClient` costruito senza argomenti di profilo usa la sessione Google e la chiave di cache del token del profilo `prod`, le stesse dei comandi della CLI. | RF-016, RF-003, RF-026 |
| 10-C41 | Dopo che un comando ha messo in cache il token Interacta di un profilo `google_oauth2`, `auth logout` sullo stesso profilo elimina quel file di cache; lo elimina anche se è stato scritto con la chiave calcolata prima di questa spec. | RF-003, RNF-002 |
| 10-C42 | Con `--google-client-file` su un file JSON con sezione `installed`, `auth login --google` usa `client_id` e `client_secret` del file per il consenso e lo scambio del codice; a login riuscito il profilo contiene il `google_client_id` del file e il portachiavi il secret del file, al posto di quello eventualmente salvato; se il login fallisce profilo e portachiavi sono identici a prima. Il percorso del file non compare nel profilo, e il file resta identico. | RF-026, RNF-012 |
| 10-C43 | Un file illeggibile o inesistente, non JSON, senza sezione `installed` (anche quando ha la sezione `web`), o senza `client_id` o `client_secret`, fa uscire il comando con `2` e un messaggio che nomina il problema, senza richieste di rete e senza aprire il browser; né il messaggio, né i log, né l'eccezione contengono il valore del client secret o altro contenuto del file. | RF-026, RNF-001, RNF-012 |
| 10-C44 | `--google-client-file` insieme a `--client-secret-stdin`, o a un `--google-client-id` diverso dall'id del file, fa uscire il comando con `2` nominando il conflitto, prima di qualunque richiesta; con un `--google-client-id` uguale il login prosegue. | RF-026 |
| 10-C45 | La funzione di login della libreria, chiamata con il percorso del file del client, salva la stessa sessione, lo stesso id e lo stesso secret della CLI; con un file non valido solleva `ConfigurationError`; con il file e il client secret insieme solleva `ConfigurationError`. | RF-026 |
| 10-C46 | `auth logout --revoke` su un profilo senza sessione Google salvata (con service account o `google_oauth2` senza sessione) stampa una nota che nomina il profilo e dice che non c'è nessuna sessione da revocare, non chiama l'endpoint di revoca ed esce `0`; `--forget-client-secret` senza client secret salvato stampa una nota analoga. Senza questi flag l'output resta quello di oggi. | RF-026, RF-015 |

## Casi limite

- Il browser non si apre (sessione remota, nessun browser predefinito) → l'indirizzo è a
  terminale e il login prosegue se la persona lo visita dalla stessa macchina (10-C02).
- La persona chiude il browser o non risponde → timeout, exit `3`, nulla di salvato (10-C09).
- Interruzione con Ctrl-C durante l'attesa → il listener si chiude e nulla è salvato (10-C09,
  10-C10).
- Una seconda richiesta arriva al listener dopo la prima risposta → non è accettata (10-C10).
- Google non restituisce il refresh token → login fallito, nulla di salvato (10-C09).
- Account Google valido ma non collegato a Interacta → messaggio dedicato, nulla di salvato
  (10-C11).
- Client secret sbagliato al primo login → Google risponde `invalid_client`, il secret non è
  salvato (10-C20, 10-C30).
- Client secret ruotato sulla console Google → `invalid_client` al rinnovo, con l'indicazione
  di `--replace-client-secret` (10-C20).
- Sessione revocata dall'account Google o dall'amministratore → `invalid_grant`, invito al
  login, nessun browser (10-C19).
- Rete assente al rinnovo → `TransportError`, la sessione resta (10-C21).
- `--base-url` che sovrascrive l'indirizzo di un profilo con sessione → la sessione non è usata
  contro il nuovo host (10-C17).
- Variabile d'ambiente con un token scaduto e sessione salvata valida → vince la variabile, e
  l'errore è quello di oggi (10-C16).
- Cambio di account Google sullo stesso profilo → il token Interacta dell'account precedente è
  eliminato dalla cache (10-C23).
- Due processi (per esempio la CLI e, dalla spec 11, il server MCP) rinnovano insieme → ognuno
  ottiene il suo access token Google; il refresh token non cambia, o cambia per entrambi
  (10-C22).
- `config.toml` con un profilo corrente diverso da `default` e login senza `--profile` → il login
  lavora sul profilo corrente (10-C39).
- L'endpoint userinfo non restituisce l'email → la sessione è salvata senza, e `auth status`
  riporta l'account come sconosciuto (10-C03, 10-C24).
- Linux senza sessione grafica → exit `2` con rimando al token statico (10-C06).
- `auth logout` su un profilo `google_oauth2` senza `keyring` installato → elimina la cache del
  token e dice che il portachiavi non è leggibile (10-C25, 10-C27).
- `logout --revoke` senza rete → la sessione locale è eliminata, il comando esce con errore
  (10-C29).
- File del client di tipo "Applicazione web" (sezione `web`) → exit `2` con l'indicazione di
  creare un client "Desktop app" (10-C43).
- File del client con un secret sbagliato o ruotato → Google risponde `invalid_client`, nulla di
  salvato (10-C20, 10-C42).

## Dati personali e segreti

- **Refresh token Google e client secret**: solo nel portachiavi di sistema, il primo per
  profilo e tenant, il secondo per id del client. Restano fino al logout
  (`--forget-client-secret` per il secret) o alla revoca. Mai in `config.toml`, in file, in
  argomenti di riga di comando, in log, audit log, hook o messaggi di eccezione.
- **Authorization code, verificatore PKCE, `state`, id token, access token Google**: vivono
  solo in memoria per la durata del login o del rinnovo; mai salvati né registrati.
- **Email dell'account Google**: salvata nel portachiavi insieme al refresh token, per mostrarla
  in `auth status`; eliminata dal logout. È un dato personale: compare solo nell'output di
  `auth status` (e nell'eventuale file di `--export` scelto dall'operatore), mai nei log
  applicativi.
- **Id del client OAuth**: nel profilo, non è un segreto; negli esempi è finto e riconoscibile.
- **File JSON del client** (`--google-client-file`): appartiene alla persona, che l'ha scaricato;
  la libreria lo legge una volta e non lo copia, non lo modifica e non ne salva il percorso. Il
  suo contenuto non compare in messaggi d'errore, log o eccezioni.
- **Chiamate a Google** (token, userinfo, revoca): registrate con metodo, URL e stato, senza corpi, anche con
  `audit_log_bodies` e `audit_log_raw`. L'indirizzo di consenso stampato a terminale contiene
  `state` e la challenge PKCE, che non sono segreti riutilizzabili.
- **Token Interacta**: nella cache come oggi (RNF-002).

## Requisiti nuovi

Sottorequisiti di RF-026, RF-016, RNF-012 e RNF-001, con id provvisori; entrano nel PRD con il
task di chiusura.

- RF-026a. Il login integrato si avvia con `auth login --google` senza token statico; flag
  `--google-client-id`, `--google-client-file` (id e secret dal JSON del client "Desktop"
  scaricato dalla console), `--client-secret-stdin`, `--replace-client-secret`, `--no-browser`,
  `--login-timeout` (predefinito 300 s); profilo e portachiavi sono scritti solo dopo lo scambio
  riuscito con Interacta; i flag del login integrato insieme a un token statico sono un errore
  d'uso (exit `2`).
- RF-026b. La sessione è distinta per profilo e tenant; il client secret è legato all'id del
  client. Precedenza: token o provider esplicito > variabile d'ambiente > sessione salvata. Un
  client costruito senza profilo non usa la sessione.
- RF-026c. Rinnovo senza browser. `invalid_grant` e sessione assente → `AuthenticationError` con
  l'invito al login; `invalid_client` → `AuthenticationError` con l'indicazione di sostituire il
  secret; rete e timeout → `TransportError` senza nuovo tentativo. Una sessione rifiutata resta
  nel portachiavi finché non è sostituita o eliminata.
- RF-026d. `auth status`: stato del profilo e della sessione senza rete e senza segreti, exit
  `0`; `--check` prova l'autenticazione ed esce `3` se fallisce.
- RF-026e. `auth logout` elimina la sessione Google del profilo senza rete;
  `--forget-client-secret` elimina il secret; `--revoke` revoca presso Google ed elimina
  comunque in locale.
- RF-026f. Funzioni pubbliche di libreria per login, logout e stato su un profilo.
- RF-026g. Extra `pynteracta[google]` (porta `keyring`); senza, il login integrato fallisce
  nominando l'extra.
- RF-016a. Campo di profilo `google_client_id` (`PYNTERACTA_GOOGLE_CLIENT_ID`).
- RF-016b. Senza `--profile`, `auth login` lavora sul profilo corrente di `config.toml`; un
  `InteractaClient` che risolve da sé il profilo usa il nome del profilo corrente per la
  sessione e per la chiave della cache del token.
- RNF-012a. Sono accettati i portachiavi di sistema (macOS, Windows e, senza supporto
  dichiarato, Secret Service e KWallet su Linux); sono rifiutati quelli assenti o che conservano
  in chiaro su file. La voce della sessione contiene refresh token, email dell'account e data
  del login.
- RNF-001c. Le chiamate agli endpoint di Google sono registrate in log, audit log e hook con
  metodo, URL e stato, mai con i corpi, neppure con `audit_log_bodies` e `audit_log_raw`.

Il §6 del PRD va inoltre precisato: tra i dati nel portachiavi c'è l'email dell'account Google.

## Fuori ambito

- Il server MCP → spec 11 (M37), che include `keyring` in `pynteracta[mcp]`.
- Microsoft OAuth2 e username/password (PRD §7).
- Un client OAuth, id o segreto, distribuito con il pacchetto (PRD §7).
- Il rinnovo di un token statico passato dall'esterno: resta a carico di chi lo fornisce.
- Suggerimenti di account o di dominio nel consenso, e il vincolo a un dominio: lo garantisce
  l'app "Internal" del Workspace.
- Più sessioni Google per lo stesso profilo e tenant.
- Il flusso per dispositivi senza browser sulla stessa macchina (device code).
- Retry con backoff verso Google.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Id del client nel campo `google_client_id`, salvabile con `--google-client-id` al login; secret da prompt nascosto o `--client-secret-stdin` | Id solo da `config set`; prompt per entrambi | Un solo comando per il primo login, adatto anche agli script; il secret non passa mai da un argomento, come la password di `users create` |
| Client secret legato all'id del client | Legato a profilo e tenant | Profili di produzione e certificazione con lo stesso client lo chiedono una volta; sostituirlo vale per tutti |
| Sostituzione con `--replace-client-secret` o `--client-secret-stdin`, rimozione con `logout --forget-client-secret` | Comandi dedicati `auth google-client …`; sola rimozione seguita da un nuovo login | Nessun comando in più; la sostituzione avviene solo a login riuscito, quindi il secret nuovo è provato prima di essere salvato |
| Accettati i portachiavi di sistema, anche su Linux; rifiutati quelli assenti o in chiaro | Solo macOS e Windows | Escludere Linux desktop non ha un motivo di sicurezza; il divieto di ripiego su file resta. Precisa RNF-012 (RNF-012a) |
| `auth status` senza rete, exit `0`, con `--check` che prova l'autenticazione | Exit `3` senza sessione; nessun `--check` | Un comando informativo non fallisce; `--check` dà la diagnosi e un codice utile agli script |
| Logout solo locale, `--revoke` facoltativo | Revoca sempre; mai | Il logout funziona offline e non fallisce a metà; la revoca fa decadere il consenso anche altrove, quindi è una scelta esplicita |
| Una sessione rifiutata da Google resta nel portachiavi | Eliminarla al primo `invalid_grant` | Nessuna scrittura nel portachiavi da comandi di lettura né, domani, dal server MCP |
| Chiamate a Google in audit e hook con metodo, URL e stato, mai i corpi | Corpi redatti per chiave; chiamate fuori da audit e hook | Stessa regola dello storage (RNF-011): una chiave nuova di Google non può finire in chiaro, e l'audit mostra comunque tutte le chiamate |
| Extra `pynteracta[google]`, che la spec 11 include in `mcp` | `pynteracta[keyring]`; `google` separato da `mcp` | Nome per funzione, come `yaml` e `parquet`; l'identità prevista del server è Google |
| Funzioni di libreria su un profilo; il client dal profilo usa la sessione da solo | Login anche senza profilo; solo un provider di token | Una sola via per identificare la sessione (profilo e tenant), e `InteractaClient` dal profilo funziona senza altro codice |
| Account non collegato: non resta nulla, nemmeno il secret nuovo; il login integrato scrive solo a esito riuscito | Tenere secret e id del client | Un login fallito non lascia tracce; il flusso con token statico resta com'è per non cambiare un comportamento esistente |
| Email dell'account salvata nel portachiavi e mostrata da `auth status` | Solo data e tenant | Con più account si vede a colpo d'occhio chi è collegato, senza rete; è un dato personale in più, tenuto fuori dai log (10-C35) |
| Senza `--profile`, ogni login lavora sul profilo corrente; il client che risolve da sé il profilo usa quel nome | Profilo corrente solo per il login integrato; lasciare `default` | La sessione deve finire dove i comandi successivi la cercano; correggere tutti i login evita due regole diverse nello stesso comando. Cambia un comportamento esistente solo per chi ha un profilo corrente diverso da `default` |
| Timeout del login 300 s, modificabile; `--no-browser`; pagina di esito in solo testo | Timeout fisso; nessun flag | Il consenso con verifica in due passaggi può richiedere minuti; `--no-browser` copre le sessioni senza browser predefinito |
| Extra mancante con profilo `google_oauth2` senza token: `AuthenticationError` (exit `3`), come oggi; solo `auth login --google` esce `2` | Errore di configurazione in entrambi i casi | Chi non installa l'extra vede lo stesso tipo di errore di oggi, con un messaggio più utile |
| `--google-client-file` legge id e secret dal JSON della console, una volta, senza salvarne il percorso; solo client "Desktop" (`installed`) | Ricordare il percorso nel profilo; accettare anche i client `web` | Il secret resta solo nel portachiavi e il file si può cancellare dopo il login; un client `web` non accetta il redirect su loopback con porta casuale, quindi fallirebbe più tardi e in modo meno chiaro |

## Verifica manuale

I test automatici simulano gli endpoint di Google, il browser e il portachiavi. Restano da
provare a mano, perché dipendono dal browser e dal portachiavi reali della postazione:

- un login completo contro il tenant con il client "Desktop" dell'ente, su macOS (Portachiavi)
  e su Windows (Gestione credenziali): consenso, identità mostrata, voce presente nel
  portachiavi, comando successivo senza token in ambiente;
- il rinnovo dopo la scadenza del token Interacta (un'ora), senza browser;
- `auth logout --revoke` seguito da un comando, che deve chiedere di rifare il login.

Gli esiti si riportano nella spec, senza token né segreti.

## Revisioni

- 2026-11-21, durante il piano: `auth login` senza `--profile` scriveva in `default` mentre gli
  altri comandi usano il profilo corrente, quindi la sessione sarebbe finita sotto un nome che
  nessun comando legge. Scelta del maintainer: profilo corrente per tutti i login e per il
  client che risolve da sé il profilo; nuovi criteri 10-C39 e 10-C40, nuovo RF-016b.
- 2026-11-21, durante il piano: l'email dell'account si legge dall'endpoint userinfo di Google
  (scelta del maintainer, senza scope oltre `email`); 10-C34 e "Dati personali e segreti" citano
  anche quella chiamata. Nessun comportamento nuovo per chi usa la funzione.
- 2026-11-21, durante l'implementazione (T01): il logout di un profilo `google_oauth2` non
  eliminava il file di cache, perché client e logout calcolavano la chiave su indirizzi diversi;
  10-C23 e 10-C27 lo davano per scontato. Scelta del maintainer: correggerlo in questa spec;
  nuovo criterio 10-C41, la chiave si calcola sull'indirizzo dell'API come per il service
  account, e il logout elimina anche la chiave vecchia.
- 2026-11-21, durante la prova manuale (T18): su richiesta del maintainer, id e secret del
  client si possono leggere dal file JSON scaricato dalla console Google
  (`--google-client-file`, parametro corrispondente in libreria). Compatibile con l'ADR 0002: il
  secret non passa come argomento e resta solo nel portachiavi. Nuovi criteri 10-C42–10-C45,
  nuovo task T21.
- 2026-11-21, durante la prova manuale (T18): `auth logout --revoke` lanciato senza `--profile`
  ha agito sul profilo corrente, con service account, e non ha detto che non c'era nulla da
  revocare. Su richiesta del maintainer il logout lo segnala con una nota; nuovo criterio
  10-C46, nuovo task T22.

## Domande aperte

Nessuna.
