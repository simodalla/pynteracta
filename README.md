PYnteracta, utility e wrapper per api di Interacta
---------------------------------------------------

Utility e libreria wrapper open-source in linguaggio Python per l'interfacciamento con le api rest
di [Interacta](https://catalogocloud.agid.gov.it/service/1892).


Installazione
-------------

```
python -m pip install pynteracta
```

Utilizzo utility command line
-----------------------------

Pynteracta ha un'interfaccia a riga di comando per verificare l'accesso all'ambiente di prova
Playgroud o ad un ambiente di produzione di Interacta.

Accesso e lista dei post della community di default dell'ambiente Playgroud di Interacta.

    $ pynteracta playground

    Connessione all'ambiente Playground di Interacta...
    Login effettuato con successo!
    Elenco dei post:
    ┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃ Id  ┃ Titolo                                ┃ Descrizione                           ┃
    ┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
    │ 599 │ Il mio primo post su Interacta        │ Questo è il mio primo post di         │
    │     │                                       │ Interacta e lo sto creando tramite le │
    │     │                                       │ Interacta External API.               │
    │     │                                       │                                       │
    │ 598 │ Benvenuto nel Playground di Interacta │ Interacta Playground è un ambiente    │
    │     │                                       │ pensato per permetterti di testare le │
    │     │                                       │ nostre API e verificare con i tuoi    │
    │     │                                       │ occhi i risultati delle tue chiamate. │
    │     │                                       │                                       │
    │     │                                       │ Si tratta di un ambiente condiviso,   │
    │     │                                       │ quindi utilizza un linguaggio....     │
    │     │                                       │                                       │
    └─────┴───────────────────────────────────────┴───────────────────────────────────────┘

Accesso e lista dei post della community di default di un ambiente di produzione di Interacta.

Sono supportati due metodi di accesso:

- [Username/Password](https://injenia.atlassian.net/wiki/spaces/IEAD/pages/3624075265/Autenticazione#Autenticazione-per-mezzo-di-Username-%2F-Password%3A)
```
    $ pynteracta login --base-url **URL_PRODUZIONE** --user **UTENTE**
    Password: ****
    Connessione all'instanza Interacta **URL_PRODUZIONE** con 'username/password' ...
    Login effettuato con successo!
```

- [Service Account](https://injenia.atlassian.net/wiki/spaces/IEAD/pages/3624075265/Autenticazione#Autenticazione-via-Service-Account-(Server-to-Server))
```
    $ pynteracta login --base-url **URL_PRODUZIONE** --service-account-file **PATH**
    Password: ****
    Connessione all'instanza Interacta **URL_PRODUZIONE** con 'service account' ...
    Login effettuato con successo!
```

Recupero lista dei primi 10 post della community identificata dall'id passata come parametro

    $ pynteracta --base-url **URL_PRODUZIONE** list-posts **COMMUNITY-ID**

Logout da un ambiente di produzione

    $ pynteracta logout
