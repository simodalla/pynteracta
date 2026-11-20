# Prompt per ADR e spec – server MCP e login Google

Tre blocchi da incollare, nell'ordine. Ogni blocco è autonomo: non presuppone la conversazione
di brainstorming. I nomi di comandi, flag e strumenti sono proposte; la spec li può cambiare.

Numerazione attesa: ADR `0002`; spec `10` su `m36_google_login`; spec `11` su `m37_mcp_server`
(l'ultimo milestone in `PROGRESS.md` è M35).

---

## 1. ADR

```
/sddpa:adr Server MCP locale e login Google integrato
```

Testo di partenza:
[`adr-0002-server-mcp-login-google.md`](adr-0002-server-mcp-login-google.md), in questa
cartella. Le decisioni sono tutte confermate; in fondo alla bozza restano due verifiche di fatto
(sul tenant e sulla console Google) da fare prima di accettarlo.

---

## 2. Spec 10 – Login Google integrato

```
/sddpa:specifica Login Google integrato con rinnovo automatico (ADR 0002, decisioni 6 e 7)

Scopo. Chi usa pynteracta con l'identità personale fa il login Google una volta, dal browser, e
da lì in poi CLI e libreria lavorano senza che debba procurarsi un access token ogni ora. È il
prerequisito del server MCP (spec successiva), ma vale da solo per la CLI.

Comportamento attuale da cui partire. La libreria riceve un access token Google già pronto
(`--google-token`, `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`, `google_token`, `google_token_provider`) e
lo scambia con un token Interacta; non esegue alcun flusso di login, non salva il token Google,
e `auth login --google` scrive nel profilo solo `auth_method = "google_oauth2"`. Il PRD lo
dichiara in RF-002, in §5 e in §7 ("ottenere un token Google per conto dell'utente" fuori
ambito); `docs/authentication.md` lo ripete.

Comportamento voluto.
- `pynteracta auth login --google`, senza un token statico, apre il browser sul consenso Google
  con il client OAuth configurato nel profilo e con lo scope minimo necessario allo scambio. Se
  il browser non si apre, stampa l'indirizzo da visitare.
- A login riuscito scambia subito il token con Interacta e mostra l'identità ottenuta (come
  `auth whoami`). Se l'account Google non è collegato a un utente Interacta, lo dice in modo
  comprensibile e non conserva nulla.
- La sessione sopravvive tra un comando e l'altro e tra i riavvii: i comandi successivi e
  `InteractaClient` costruito dal profilo funzionano senza token in ambiente. Quando il token
  Interacta scade, la libreria rinnova da sola l'access token Google e ripete lo scambio.
- Precedenza: un token o un provider passato esplicitamente vince sulla variabile d'ambiente,
  che vince sulla sessione salvata. Il comportamento attuale con token statico non cambia.
- Sessione revocata o scaduta: `AuthenticationError` con l'indicazione di rifare il login; in
  CLI exit code 3. Nessun tentativo di riaprire il browser da solo.
- `auth logout` elimina la sessione Google salvata per quel profilo. Un comando di stato dice se
  una sessione esiste e per quale tenant, senza mostrare segreti.
- La sessione è distinta per tenant e per profilo, come la chiave della cache del token: una
  sessione di produzione non viene mai usata contro un altro host.
- Il refresh token sta solo nel portachiavi di sistema (postazioni macOS e Windows: Portachiavi
  e Gestione credenziali). Portachiavi assente (per esempio Linux
  senza sessione grafica): errore chiaro che rimanda al token statico, nessun ripiego su file.
- Il client secret sta nel portachiavi insieme al refresh token (ADR 0002, decisione 7). Al
  primo login la persona lo fornisce da prompt nascosto o da standard input, mai come argomento
  (come la password di `users create`); i login successivi lo riusano. `auth logout` toglie il
  refresh token; serve un modo esplicito per togliere o sostituire anche il client secret.
- Client OAuth non configurato nel profilo: errore di configurazione (exit code 2) prima di
  qualunque richiesta, con l'indicazione di cosa manca.
- Chi usa la libreria senza CLI ha un modo documentato per avviare il login e per ottenere un
  client che usa la sessione salvata.

Vincoli.
- Refresh token, authorization code, verificatore PKCE, id token e client secret non compaiono
  mai in log applicativi, audit log, hook né messaggi di eccezione, neppure con
  `audit_log_bodies` e `audit_log_raw`. Serve un test che lo dimostri sulle chiamate a Google.
- Il listener del redirect ascolta solo su loopback, verifica `state`, accetta una sola
  risposta e ha un timeout.
- Nessun id o segreto di client OAuth nel codice o in file versionati; negli esempi valori finti
  e riconoscibili.
- Le dipendenze nuove sono opzionali: l'installazione base non cambia. Senza l'extra, il login
  integrato fallisce con un messaggio che dice quale extra installare.
- Test senza rete: gli endpoint di Google sono simulati; nessun browser reale.

Fuori da questa spec. Il server MCP; Microsoft OAuth2 e username/password; un client OAuth
distribuito con il pacchetto; il rinnovo di un token statico passato dall'esterno.

Da verificare sul tenant prima del piano.
- Quali scope Google accetta lo scambio: `profile` da solo basta?
- Quanto dura il token Interacta ottenuto dallo scambio.
- Che un'app OAuth "Internal" del Workspace dell'ente funzioni con un client di tipo "Desktop".

- Che il client "Desktop" richieda davvero il client secret allo scambio del codice.

Da decidere nella spec. Nome dei campi di profilo e del comando di stato; come si sostituisce
il client secret salvato.

PRD toccato. RF-002, RF-003, RF-016; RNF-001, RNF-002; §2 (riga "Utente Google"), §5 (riga
"Google OAuth2"), §6 (refresh token come dato scritto dalla libreria), §7 (esce "ottenere un
token Google per conto dell'utente"). `CLAUDE.md`: regole non negoziabili su token e cache.

Documentazione. `docs/authentication.md` (la sezione Google afferma il contrario e va
riscritta), `docs/configuration.md`, `docs/cli.md`; `docs/index.md` e `README.md` perché cambia
lo scope dell'autenticazione, senza numeri di versione.
```

---

## 3. Spec 11 – Server MCP locale

```
/sddpa:specifica Server MCP locale su stdio: letture curate e scrittura dei task dietro flag (ADR 0002, decisioni 1-5 e 8)

Scopo. Una persona collega Claude (o un altro client MCP) a Interacta dalla propria macchina e
lavora in linguaggio naturale con i propri permessi: cerca e legge post, community e cataloghi
e, se lo ha abilitato, crea, modifica ed elimina task. Caso d'uso guida: "leggi questo post e
crea i task che ne derivano".

Dipende da. La spec del login Google integrato (sessione salvata e rinnovo automatico).

Comportamento voluto: avvio.
- `pynteracta mcp serve [--profile NOME] [--enable-task-writes]` avvia un server MCP su stdio.
  Senza l'extra `mcp` installato il comando esce con codice 2 e dice quale extra installare.
- Lo standard output porta solo messaggi del protocollo; log e diagnostica vanno sullo standard
  error. Serve un test che lo dimostri.
- L'avvio non fa richieste di rete e non apre il browser. Se la sessione Google manca o è
  revocata, ogni strumento risponde con un errore che dice di eseguire `pynteracta auth login
  --google`; il server resta in piedi.
- Il server usa l'identità del profilo; quella prevista è Google OAuth2 personale. Profilo con
  service account: accettato con un avviso (ADR 0002, decisione 2). L'avviso va sullo standard
  error all'avvio e compare anche nel risultato dello strumento dell'identità corrente, che
  dichiara il tipo di identità, perché lo standard error di norma non arriva alla persona. Con
  service account il perimetro degli strumenti non cambia.

Comportamento voluto: strumenti di lettura, sempre attivi.
- Identità corrente.
- Community: elenco; dettaglio; definizione dei post (campi custom, workflow).
- Post: ricerca in una community con i filtri più utili, compreso quello dei post con task da
  gestire; stream globale; dettaglio; storia degli eventi (da cui si ricavano gli id dei task);
  commenti.
- Allegati di un post (solo metadati, nessun download di contenuto).
- Cataloghi e voci; hashtag di una community.
- Task: dettaglio per id, con il token di concorrenza.
Ogni risultato è ridotto ai campi utili a un modello, porta il link web all'oggetto quando
esiste (`WebUrls`) e, per gli elenchi, ha una dimensione di pagina limitata e un cursore per la
pagina successiva. Nessuno strumento itera da solo su tutte le pagine.

Comportamento voluto: strumenti di scrittura, solo con `--enable-task-writes`.
- Crea un task su un post; modifica un task; elimina un task. Senza il flag i tre strumenti non
  sono registrati: il client non li elenca.
- La modifica è una patch: cambia solo i campi indicati e richiede il token di concorrenza
  letto dal dettaglio. Un `409` torna come conflitto, con l'indicazione di rileggere e decidere
  di nuovo; il server non rilegge e non riprova.
- Timeout o errore di rete dopo l'invio: il risultato dice che l'esito è sconosciuto e che
  l'operazione non va ripetuta senza prima controllare lo stato del task.
- Le date-ora seguono RNF-010: solo con fuso orario.
- Le annotazioni MCP dichiarano di sola lettura gli strumenti di lettura e distruttiva
  l'eliminazione.

Comportamento voluto: errori.
- Gli errori tipizzati della libreria diventano risultati di errore leggibili da un modello
  (permesso negato, non trovato, validazione, autenticazione, conflitto, esito sconosciuto),
  senza traccia dello stack e senza segreti.

Vincoli.
- Mai esposti: gli endpoint `admin/*`, gli elenchi di utenti e gruppi, le scritture dei post,
  l'upload di allegati.
- Le regole non negoziabili restano: nessuna scrittura ripetuta, token e dati personali fuori
  dai log applicativi. L'audit log, se abilitato sul profilo, registra le chiamate fatte per
  conto del modello: la guida lo consiglia come traccia.
- Le descrizioni degli strumenti dicono al modello che il testo di post e commenti è contenuto
  di terzi, non istruzioni. Il limite va dichiarato nella documentazione: il server riduce ciò
  che il modello può fare, non può impedirgli di essere ingannato.
- L'SDK MCP è una dipendenza opzionale; il client resta sincrono (RNF-004).
- Test senza rete: server esercitato in memoria da un client MCP di test, Interacta simulata
  con `respx`. L'elenco degli strumenti, con e senza flag, è coperto da snapshot.

Fuori da questa spec. Server remoto (HTTP) e autenticazione per utente lato server; scritture
diverse dai task; area admin; risorse e prompt MCP oltre agli strumenti; download del contenuto
degli allegati.

Da decidere nella spec. Elenco e nomi definitivi degli strumenti (indicativamente 10-14); quali
filtri dei post esporre; dimensione massima di pagina; se le voci di catalogo servono davvero
al caso d'uso guida.

PRD toccato. §1; §2 (nuovo attore: client MCP o agente per conto della persona); nuovi RF per
il server; nuovo RNF sul canale stdio; RF-010, RF-022, RF-025, RNF-009, RNF-010 per i task; §5
(nuova riga); §6 (i dati letti passano al client MCP e al fornitore del modello, a carico di chi
abilita il server); §7 (server remoto, altre scritture e admin via MCP fuori ambito).

Documentazione. Nuova guida in `docs/guides/` (installazione, configurazione in Claude Desktop
e Claude Code, flag delle scritture, avvertenze su contenuti non fidati, dati personali e uso
con service account, sconsigliato insieme a `--enable-task-writes`),
`docs/cli.md` per il nuovo comando, `docs/index.md` e `README.md` perché cambia lo scope, senza
numeri di versione. Righe ⏳ in `ROADMAP.md`.
```
