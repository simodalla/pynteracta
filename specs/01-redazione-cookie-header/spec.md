# 01 – Redazione di cookie e header sensibili nei log e nei hook

Stato: chiusa
Branch: `m27_redazione_cookie_header`
Requisiti del PRD: RNF-001, RF-017, RF-018
Dipende da: nessuna

Chiude la violazione nota **P-01** della [linea di partenza](../00-partenza/partenza.md).

## Scopo

Chi attiva l'audit log, o registra un hook di risposta, non deve mai trovare un segreto negli
header: oggi il cookie di refresh che Interacta restituisce al login (`Set-Cookie:
interacta_auth_refresh_token=…`) finisce in chiaro nell'audit log e in `ResponseInfo.headers`.
Con questa spec i cookie e gli header con nome sensibile sono redatti ovunque gli header passano,
con la stessa garanzia già data per `Authorization` e per i JWT dalla v0.9.3.

## Comportamento attuale

La redazione degli header sostituisce con `***REDACTED***` il valore dell'header `Authorization`
(maiuscole indifferenti) e ogni sottostringa a forma di JWT (`eyJ…`) in qualunque altro header.
Si applica agli header di richiesta e di risposta prima che raggiungano i hook (`RequestInfo`,
`ResponseInfo`) e gli eventi `audit.request` / `audit.response` su console e file, e a ogni evento
di log con chiave `headers` tramite il processore structlog. Tutto il resto passa in chiaro: un
cookie con valore esadecimale, un `X-Api-Key`, un `Proxy-Authorization` con credenziali Basic.
`--audit-raw` toglie la redazione solo sul canale di logging dell'audit, non nel transport.

Il test esistente `test_response_headers_are_redacted_in_both_channels` usa un cookie innocuo e
verifica solo che il JWT sparisca: non copre P-01.

## Comportamento

Quando una risposta o una richiesta porta header sensibili, chi li osserva (hook, audit log su
console o file, qualunque evento di log con `headers`) li vede così:

- **Cookie** (`Set-Cookie` in risposta, `Cookie` in richiesta): ogni cookie conserva il **nome** e
  gli **attributi** (`Secure`, `HttpOnly`, `SameSite`, `Path`, `Domain`, `Expires`, `Max-Age`…) e
  perde il **valore**, sostituito da `***REDACTED***`. Vale per tutti i cookie, qualunque sia il
  nome. Se la risposta porta più `Set-Cookie`, tutti sono trattati, anche quando il trasporto li
  presenta uniti in un solo valore separato da virgole e un attributo `Expires` contiene a sua
  volta una virgola. Se un header cookie non si lascia analizzare con certezza (per esempio senza
  `=`), l'intero valore diventa `***REDACTED***`: in dubbio si redige, mai si lascia passare.
- **Header redatti per nome**, intero valore sostituito da `***REDACTED***` qualunque sia la forma
  del valore: `Authorization`, `Proxy-Authorization`, e ogni header il cui nome contiene `token`,
  `secret`, `password` o `api-key` (maiuscole e separatori `-`/`_` indifferenti: `X-Api-Key`,
  `X-Auth-Token`, `X-Refresh-Token`, `x_secret`…).
- **Tutto il resto resta com'è**: `Content-Type`, `Content-Length`, `Date`, `X-Request-Id`,
  `WWW-Authenticate` (porta lo schema e la descrizione dell'errore, non segreti), `User-Agent`; e
  i JWT in qualunque header continuano a essere redatti come oggi.

Cosa resta uguale: la redazione avviene dentro il transport, prima di hook e logging, quindi vale
senza alcuna configurazione; `--audit-raw` continua a togliere la redazione solo sul canale di
logging, e non riporta in chiaro cookie e header redatti dal transport; i body seguono le regole
di oggi.

Nel sito, la pagina "Audit Logging" ("Redaction guarantees" ed esempio di evento) descrive le
nuove garanzie.

## Criteri di accettazione

| Id | Criterio | Requisiti |
|---|---|---|
| 01-C01 | Quando una risposta porta `Set-Cookie: a=1; Secure; HttpOnly`, il hook di risposta e l'evento `audit.response` ricevono negli header `a=***REDACTED***; Secure; HttpOnly`, e la stringa `1` come valore del cookie non compare. | RNF-001, RF-017, RF-018 |
| 01-C02 | Quando una risposta porta due `Set-Cookie`, uno con `Expires=Thu, 02-Jul-2026 16:06:04 GMT`, entrambi i valori sono `***REDACTED***` e i due nomi e tutti gli attributi, virgola di `Expires` compresa, restano nell'output. | RNF-001, RF-017 |
| 01-C03 | Quando una richiesta porta `Cookie: a=1; b=2`, il hook di richiesta e l'evento `audit.request` ricevono `a=***REDACTED***; b=***REDACTED***`. | RNF-001, RF-017, RF-018 |
| 01-C04 | Quando un header `Set-Cookie` o `Cookie` non contiene `=`, il suo intero valore è `***REDACTED***`. | RNF-001 |
| 01-C05 | Quando una richiesta o una risposta porta `Authorization`, `authorization` o `Proxy-Authorization` con un valore non a forma di JWT (per esempio `Basic dXNlcjpwYXNz`), l'intero valore è `***REDACTED***`. | RNF-001 |
| 01-C06 | Quando un header si chiama `X-Api-Key`, `X-Auth-Token`, `X-Refresh-Token` o `X-Secret` (in qualunque combinazione di maiuscole), l'intero valore è `***REDACTED***`. | RNF-001 |
| 01-C07 | Quando gli header sono `Content-Type`, `X-Request-Id`, `WWW-Authenticate: Bearer error="invalid_token"` e `Date`, i valori arrivano invariati a hook e audit log. | RNF-001 |
| 01-C08 | Quando un header con nome non sensibile (`X-Custom`) contiene un JWT, il JWT è `***REDACTED***` come prima di questa spec. | RNF-001 |
| 01-C09 | Quando un evento di log passa dal processore structlog con `headers={"Set-Cookie": "a=1; Secure", "X-Api-Key": "k"}`, l'evento emesso contiene `a=***REDACTED***; Secure` e `X-Api-Key: ***REDACTED***`; lo stesso evento scritto dall'handler di file dell'audit ha lo stesso contenuto. | RNF-001, RF-017 |
| 01-C10 | Quando una risposta ha la forma del login reale (`Set-Cookie: interacta_auth_refresh_token=<64 esadecimali finti>; Secure; HttpOnly; SameSite=Strict; Path=/portal/api/core/auth/refresh-token/; Expires=…`) e sono attivi audit su console, audit su file e un hook di risposta, il valore esadecimale non compare in nessuno dei tre canali, né quando `audit_raw` è attivo. | RNF-001, RF-017, RF-018 |
| 01-C11 | La pagina `docs/logging.md` elenca cookie e header per nome tra le garanzie di redazione e il suo esempio di `audit.response` mostra un `Set-Cookie` redatto; `uv run mkdocs build --strict` e `tests/unit/test_docs_snippets.py` sono verdi. | RF-017 |

## Casi limite

- Più `Set-Cookie` uniti in un valore con virgole, con `Expires` che contiene una virgola → ogni
  valore redatto, nomi e attributi intatti (01-C02).
- Header cookie senza `=` o altrimenti non analizzabile → intero valore redatto (01-C04).
- Cookie con valore vuoto (`a=; Path=/`) → `a=***REDACTED***; Path=/` (01-C01, stessa regola).
- Nome di header con `_` al posto di `-` (`x_api_key`) o maiuscole miste → redatto per nome
  (01-C06).
- `WWW-Authenticate` con `error="invalid_token"`: il nome non contiene `token`, il valore non è un
  JWT → invariato (01-C07). Il warning `auth.token_invalidated_by_server` continua a loggarlo.
- Header con nome sensibile e valore vuoto → `***REDACTED***` comunque (01-C05/01-C06).
- `audit_raw` attivo → cookie e header restano redatti perché la redazione sta nel transport
  (01-C10); l'avviso `audit.redaction_disabled` resta.
- Mapping di header con chiavi duplicate (httpx `Headers`) → si lavora sulla vista unita per chiave,
  come oggi; nessuna coppia va persa (01-C02).

## Dati personali e segreti

Passano: cookie di sessione e di refresh del tenant, credenziali `Basic`, chiavi API e token in
header custom, tutti provenienti dal server o dal chiamante. Non si salva nulla di nuovo: l'audit
log (console o file rotante) e i hook ricevono solo valori già redatti. Non deve mai comparire, in
nessun canale: il valore di un cookie, il valore di un header redatto per nome, un JWT. Nessun dato
personale è coinvolto oltre a quelli già nei body (eccezione dell'audit log, regola non
negoziabile).

## Requisiti nuovi

- RNF-001a (precisazione di RNF-001): la redazione prima di log, audit log e hook copre anche il
  valore di ogni cookie (`Cookie`, `Set-Cookie`), tenendo nome e attributi, e l'intero valore degli
  header `Authorization`, `Proxy-Authorization` e di quelli il cui nome contiene `token`, `secret`,
  `password` o `api-key`. Entra nel PRD con il task di chiusura, insieme alla conferma di RF-017,
  RF-018 e RNF-001 data dal maintainer il 2026-10-08.

## Fuori ambito

- Il cookie jar di `httpx.Client`, che conserva in memoria il cookie di refresh e lo rispedirebbe
  solo al path `refresh-token`, mai chiamato dalla libreria: non espone nulla nei log né nei hook;
  spec a parte se si vuole svuotarlo o disattivarlo.
- `--audit-raw`: resta un bypass del solo canale di logging, come documentato.
- La redazione dei dati personali nei body (eccezione dell'audit log).
- La release: la correzione è un `fix(security)` e semantic-release calcolerà la patch 0.9.5
  insieme alla prossima spec.
- L'`audit.log` già scritto in locale dal maintainer, fuori dal repository.

## Decisioni

| Decisione | Alternative scartate | Motivo |
|---|---|---|
| Cookie: valore redatto, nome e attributi conservati, per tutti i cookie | Intero header redatto; solo i cookie con nome "sensibile" | Chi legge l'audit log vede quale cookie e con quali flag, mai il valore; non dipende da come il server chiama i cookie |
| Header redatti per nome: lista fissa (`Authorization`, `Proxy-Authorization`) più pattern sul nome (`token`, `secret`, `password`, `api-key`) | Solo lista fissa; solo `Authorization` come oggi | Simmetrico con la redazione delle chiavi dei body; copre header custom con token non JWT |
| In dubbio si redige l'intero valore | Lasciar passare ciò che non si riconosce | Un errore di parsing non deve mai produrre un passaggio in chiaro |
| Cookie jar fuori ambito | Criterio "nessun cookie conservato" in questa spec | Non riguarda i log; decisione e test a parte |
| Release rimandata alla prossima spec | Tag 0.9.5 subito dopo la chiusura | Scelta del maintainer |
| Riga `0.9.5 ⏳ M27` in ROADMAP aperta con la spec; sezione M27 in PROGRESS alla verifica | Riga solo alla release | Voce di checklist del progetto |

## Verifica manuale

Nessuna.

## Domande aperte

Nessuna.
