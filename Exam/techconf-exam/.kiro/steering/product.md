# TechConf — Dominio di Prodotto

TechConf è una piattaforma per la gestione di conferenze tecnologiche. Copre l'intero ciclo di vita di un evento: dalla creazione della conferenza alla raccolta del feedback dei partecipanti, passando per la gestione degli utenti, delle iscrizioni e delle notifiche.

## Domini funzionali

### Eventi (Event)
Rappresentano le conferenze e le sessioni tech. Ogni evento ha metadati come titolo, descrizione, date di inizio/fine, luogo (fisico o virtuale) e capacità massima di partecipanti. Gli eventi sono la risorsa centrale attorno a cui ruotano iscrizioni e feedback.

### Utenti (User)
Rappresentano le persone che interagiscono con la piattaforma: relatori, partecipanti e organizzatori. Contengono i dati anagrafici essenziali (nome, email) e sono referenziati da iscrizioni e feedback.

### Iscrizioni (Registration)
Collegano un utente a un evento. Gestiscono lo stato dell'iscrizione (es. confermata, in attesa, annullata), rispettando i vincoli di capacità dell'evento. Sono il ponte tra la domanda (utenti) e l'offerta (eventi).

### Feedback
Consente ai partecipanti di valutare gli eventi a cui si sono iscritti, tipicamente con un punteggio e un commento testuale. Il feedback è collegato sia all'utente sia all'evento e permette agli organizzatori di misurare la qualità delle conferenze.

### Notifiche (Notification)
Gestiscono la comunicazione verso gli utenti in risposta a eventi del sistema (conferma iscrizione, promemoria, richiesta di feedback). Forniscono un canale asincrono di messaggistica applicativa.

## Relazioni chiave
- Un **utente** può iscriversi a molti **eventi** (tramite **iscrizioni**).
- Un **evento** riceve molte **iscrizioni**, limitate dalla capacità.
- Un **feedback** è sempre legato a una coppia utente–evento.
- Le **notifiche** vengono generate a seguito di azioni sulle altre risorse.

## Obiettivi di prodotto
- Offrire un'esperienza fluida di scoperta e iscrizione agli eventi.
- Fornire agli organizzatori strumenti per misurare l'engagement e la soddisfazione.
- Mantenere gli utenti informati tramite notifiche tempestive e pertinenti.
