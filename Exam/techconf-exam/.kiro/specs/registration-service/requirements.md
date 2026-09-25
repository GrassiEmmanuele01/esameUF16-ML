# Requirements — registration-service

## Introduzione

Il `registration-service` gestisce le iscrizioni degli utenti agli eventi della piattaforma TechConf. Espone un'API REST su base path `/api/v1/registrations` e ascolta sulla porta `5003` (letta dalla variabile d'ambiente `PORT`, default `5003`).

L'iscrizione è il ponte tra utenti ed eventi: collega uno `user_id` a un `event_id`, rispettando i vincoli di capacità dell'evento. Il servizio ha **due dipendenze di servizio**: verifica l'utente verso lo `user-service` e l'evento verso l'`event-service` (chiamate HTTP con timeout 2s).

I requisiti seguono la notazione EARS (Easy Approach to Requirements Syntax). Gli acceptance criteria usano i pattern:
- **Ubiquitous**: "IL SISTEMA DEVE ..."
- **Event-driven**: "QUANDO <evento>, IL SISTEMA DEVE ..."
- **State-driven**: "MENTRE <stato>, IL SISTEMA DEVE ..."
- **Unwanted behavior**: "SE <condizione>, ALLORA IL SISTEMA DEVE ..."

### Standard di piattaforma applicabili
- Base path risorsa: `/api/v1/registrations`.
- ID risorsa: UUID v4 generato lato server.
- Timestamp (`created_at`, `updated_at`) in ISO 8601 UTC.
- Paginazione con `page`, `page_size`, `total`.
- Errori con struttura `{ "error": { "code": <UPPER_SNAKE>, "message": <string> } }`.
- Chiamate HTTP verso altri servizi con **timeout di 2 secondi**; URL da `USER_SERVICE_URL` ed `EVENT_SERVICE_URL`.

### Modello dati (Registration)
| Campo | Tipo | Obbligatorio | Note |
|-------|------|--------------|------|
| `id` | UUID v4 | sì (server) | Generato lato server |
| `user_id` | UUID v4 | sì | Riferimento a un utente esistente |
| `event_id` | UUID v4 | sì | Riferimento a un evento esistente e `published` |
| `amount` | number | sì (server) | Copiato dal `price` dell'evento |
| `status` | enum `confirmed`\|`cancelled` | sì (server) | Default `confirmed` alla creazione |
| `created_at` | ISO 8601 UTC | sì (server) | |
| `updated_at` | ISO 8601 UTC | sì (server) | |

---

## Requirement 1 — Creazione iscrizione

**User Story:** Come partecipante, voglio iscrivermi a un evento pubblicato, così da assicurarmi un posto.

### Acceptance Criteria

1. QUANDO viene ricevuta una `POST /api/v1/registrations` con `user_id` ed `event_id` validi e superate le regole di business, IL SISTEMA DEVE creare l'iscrizione con `status=confirmed`, rispondere con stato `201`, il corpo creato e l'header `Location`.
2. QUANDO viene creata un'iscrizione, IL SISTEMA DEVE generare lato server un `id` UUID v4 e valorizzare `created_at`/`updated_at` con lo stesso istante ISO 8601 UTC.
3. SE il body non è JSON valido, ALLORA IL SISTEMA DEVE rispondere con stato `400` ed errore `MALFORMED_JSON`.
4. SE mancano `user_id`/`event_id` o non sono UUID validi o sono presenti campi non ammessi, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR`.

---

## Requirement 2 — Lettura iscrizione

**User Story:** Come consumatore dell'API, voglio recuperare un'iscrizione tramite id, così da leggerne lo stato corrente.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/registrations/{id}` con un id esistente, IL SISTEMA DEVE rispondere con stato `200` e il corpo dell'iscrizione.
2. SE l'id non corrisponde ad alcuna iscrizione, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.

---

## Requirement 3 — Lista iscrizioni con filtri e paginazione

**User Story:** Come consumatore dell'API, voglio elencare le iscrizioni filtrando per utente, evento e stato con paginazione.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/registrations`, IL SISTEMA DEVE rispondere con stato `200` e un oggetto paginato con `items`, `page`, `page_size` e `total`.
2. QUANDO non vengono forniti `page`/`page_size`, IL SISTEMA DEVE applicare i default `page=1` e `page_size=20`.
3. QUANDO vengono forniti `user_id`, `event_id` o `status`, IL SISTEMA DEVE filtrare le iscrizioni di conseguenza (combinando i filtri presenti).
4. QUANDO sono applicati dei filtri, IL SISTEMA DEVE calcolare `total` sull'insieme filtrato prima della paginazione.
5. SE i parametri non sono validi (es. `page` < 1, `page_size` fuori 1–100, `status` fuori enum), ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR`.

---

## Requirement 4 — Eliminazione iscrizione

**User Story:** Come amministratore, voglio eliminare un'iscrizione, così da rimuovere dati non più necessari.

### Acceptance Criteria

1. QUANDO viene ricevuta una `DELETE /api/v1/registrations/{id}` su un'iscrizione esistente, IL SISTEMA DEVE eliminarla e rispondere con stato `204` senza corpo.
2. SE l'id non corrisponde ad alcuna iscrizione, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.

---

## Requirement 5 — Metodo non consentito (PUT)

**User Story:** Come piattaforma, voglio impedire la sostituzione totale di un'iscrizione, così da preservare l'integrità dei dati generati lato server.

### Acceptance Criteria

1. QUANDO viene ricevuta una `PUT /api/v1/registrations/{id}`, IL SISTEMA DEVE rispondere con stato `405` (metodo non consentito).

---

## Requirement 6 — REQ-REG-B01: Esistenza dell'utente verso user-service

**User Story:** Come piattaforma, voglio che ogni iscrizione riferisca un utente realmente esistente, così da garantire l'integrità referenziale.

### Acceptance Criteria

1. QUANDO viene creata un'iscrizione, IL SISTEMA DEVE verificare l'esistenza dell'utente con `GET {USER_SERVICE_URL}/api/v1/users/{user_id}` (timeout 2s).
2. SE lo `user-service` risponde `404` per lo `user_id`, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `REFERENCE_NOT_FOUND` senza creare l'iscrizione.

---

## Requirement 7 — REQ-REG-B02: Esistenza dell'evento verso event-service

**User Story:** Come piattaforma, voglio che ogni iscrizione riferisca un evento realmente esistente.

### Acceptance Criteria

1. QUANDO viene creata un'iscrizione, IL SISTEMA DEVE recuperare l'evento con `GET {EVENT_SERVICE_URL}/api/v1/events/{event_id}` (timeout 2s).
2. SE l'`event-service` risponde `404` per l'`event_id`, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `REFERENCE_NOT_FOUND` senza creare l'iscrizione.

---

## Requirement 8 — REQ-REG-B03: L'evento deve essere `published`

**User Story:** Come piattaforma, voglio consentire iscrizioni solo a eventi pubblicati, così da evitare iscrizioni a bozze o eventi annullati.

### Acceptance Criteria

1. QUANDO l'evento referenziato viene recuperato con successo, IL SISTEMA DEVE verificare che il suo `status` sia `published`.
2. SE l'evento esiste ma non è `published` (es. `draft`, `cancelled`), ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `EVENT_NOT_OPEN` senza creare l'iscrizione.

---

## Requirement 9 — REQ-REG-B04: Nessuna doppia iscrizione confermata

**User Story:** Come piattaforma, voglio impedire che lo stesso utente sia iscritto due volte allo stesso evento, così da evitare duplicati.

### Acceptance Criteria

1. QUANDO esiste già un'iscrizione `confirmed` per la coppia (`user_id`, `event_id`), IL SISTEMA DEVE impedire una nuova iscrizione confermata rispondendo con stato `409` ed errore `ALREADY_REGISTERED`.
2. QUANDO l'unica iscrizione preesistente per la coppia è in stato `cancelled`, IL SISTEMA DEVE consentire una nuova iscrizione confermata.

---

## Requirement 10 — REQ-REG-B05: Capienza dell'evento

**User Story:** Come piattaforma, voglio impedire iscrizioni oltre la capacità dell'evento, così da rispettare i limiti di posti.

### Acceptance Criteria

1. QUANDO viene creata un'iscrizione, IL SISTEMA DEVE contare le iscrizioni `confirmed` esistenti per l'evento e confrontarle con la `capacity` dell'evento.
2. SE il numero di iscrizioni `confirmed` ha già raggiunto la `capacity`, ALLORA IL SISTEMA DEVE rispondere con stato `409` ed errore `EVENT_FULL` senza creare l'iscrizione.
3. QUANDO un'iscrizione `confirmed` passa a `cancelled`, IL SISTEMA DEVE liberare il posto, rendendolo disponibile per nuove iscrizioni.

---

## Requirement 11 — REQ-REG-B06: `amount` derivato dal prezzo dell'evento

**User Story:** Come piattaforma, voglio che l'importo dell'iscrizione rifletta il prezzo dell'evento al momento dell'iscrizione, così da avere un dato coerente.

### Acceptance Criteria

1. QUANDO viene creata un'iscrizione, IL SISTEMA DEVE valorizzare `amount` con il `price` dell'evento recuperato dall'`event-service`.
2. IL SISTEMA NON DEVE accettare `amount` dal client: il valore è sempre determinato lato server.

---

## Requirement 12 — REQ-REG-B07: Transizione confirmed → cancelled

**User Story:** Come partecipante, voglio poter annullare la mia iscrizione, così da liberare il posto; una volta annullata, non deve poter tornare confermata.

### Contesto
Stati: `confirmed`, `cancelled`. Transizioni consentite: `confirmed → cancelled`. La transizione `cancelled → confirmed` non è consentita. La transizione verso lo stesso stato è un no-op valido.

### Acceptance Criteria

1. QUANDO viene ricevuta una `PATCH /api/v1/registrations/{id}` con `status=cancelled` su un'iscrizione `confirmed`, IL SISTEMA DEVE impostare lo stato a `cancelled`, aggiornare `updated_at` e rispondere con stato `200`.
2. SE una `PATCH` richiede la transizione `cancelled → confirmed`, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `INVALID_STATUS_TRANSITION` senza modificare l'iscrizione.
3. SE l'id non corrisponde ad alcuna iscrizione, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.
4. QUANDO lo `status` richiesto coincide con quello corrente, IL SISTEMA DEVE considerare l'operazione valida (no-op).

---

## Requirement 13 — REQ-REG-B08: Endpoint statistiche `/stats`

**User Story:** Come organizzatore, voglio conoscere capienza, iscritti confermati e posti disponibili di un evento, così da monitorarne il riempimento.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/registrations/stats?event_id={id}` per un evento esistente, IL SISTEMA DEVE rispondere con stato `200` e un corpo con `event_id`, `capacity`, `confirmed` e `available`.
2. IL SISTEMA DEVE calcolare `confirmed` come numero di iscrizioni in stato `confirmed` per l'evento, e `available` come `capacity - confirmed`.
3. SE l'evento non esiste (l'`event-service` risponde `404`), ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.
4. SE il parametro `event_id` è assente o non è un UUID valido, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR`.

---

## Requirement 14 — Indisponibilità delle dipendenze

**User Story:** Come piattaforma, voglio segnalare esplicitamente l'indisponibilità di user-service o event-service.

### Acceptance Criteria

1. SE, durante la verifica dei riferimenti, lo `user-service` o l'`event-service` è irraggiungibile (connessione/timeout 2s) o risponde `5xx`, ALLORA IL SISTEMA DEVE rispondere con stato `503` ed errore `DEPENDENCY_UNAVAILABLE`.
2. QUANDO si verifica l'indisponibilità di una dipendenza, IL SISTEMA NON DEVE creare l'iscrizione.

---

## Requirement 15 — Health check

**User Story:** Come sistema di monitoraggio, voglio verificare lo stato di salute del servizio.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /health`, IL SISTEMA DEVE rispondere con stato `200` e un corpo `{ "status": "ok", "service": "registration-service" }`.
2. IL health check NON DEVE dipendere dalla raggiungibilità delle dipendenze.

---

## Riepilogo regole di business

| Regola | Descrizione | Errore | Stato |
|--------|-------------|--------|-------|
| REQ-REG-B01 | `user_id` esistente (user-service) | `REFERENCE_NOT_FOUND` | 422 |
| REQ-REG-B02 | `event_id` esistente (event-service) | `REFERENCE_NOT_FOUND` | 422 |
| REQ-REG-B03 | Evento in stato `published` | `EVENT_NOT_OPEN` | 422 |
| REQ-REG-B04 | Nessuna doppia iscrizione `confirmed` | `ALREADY_REGISTERED` | 409 |
| REQ-REG-B05 | Capienza evento non superata | `EVENT_FULL` | 409 |
| REQ-REG-B06 | `amount` = `price` dell'evento (server) | — | — |
| REQ-REG-B07 | Transizione `confirmed → cancelled` | `INVALID_STATUS_TRANSITION` | 422 |
| REQ-REG-B08 | Endpoint `/stats` (capacity/confirmed/available) | `NOT_FOUND` se evento assente | 200 / 404 |
| (dipendenze) | user/event-service offline o 5xx | `DEPENDENCY_UNAVAILABLE` | 503 |
