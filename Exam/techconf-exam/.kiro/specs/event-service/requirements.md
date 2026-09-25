# Requirements — event-service

## Introduzione

L'`event-service` gestisce le conferenze (eventi) della piattaforma TechConf, con il loro ciclo di vita e la capacità. Espone un'API REST su base path `/api/v1/events` e ascolta sulla porta `5002` (letta dalla variabile d'ambiente `PORT`, default `5002`).

L'evento è la risorsa centrale attorno a cui ruotano iscrizioni e feedback. Ogni evento è associato a un **organizzatore**, la cui esistenza e ruolo sono verificati verso lo `user-service` tramite chiamata HTTP (dipendenza di servizio).

I requisiti seguono la notazione EARS (Easy Approach to Requirements Syntax). Gli acceptance criteria usano i pattern:
- **Ubiquitous**: "IL SISTEMA DEVE ..."
- **Event-driven**: "QUANDO <evento>, IL SISTEMA DEVE ..."
- **State-driven**: "MENTRE <stato>, IL SISTEMA DEVE ..."
- **Unwanted behavior**: "SE <condizione>, ALLORA IL SISTEMA DEVE ..."

### Standard di piattaforma applicabili
- Base path risorsa: `/api/v1/events`.
- ID risorsa: UUID v4 generato lato server.
- Date di dominio (`start_date`, `end_date`) in formato `date` (ISO 8601, `YYYY-MM-DD`); timestamp (`created_at`, `updated_at`) in ISO 8601 UTC.
- Paginazione con `page`, `page_size`, `total`.
- Errori con struttura `{ "error": { "code": <UPPER_SNAKE>, "message": <string> } }`.
- Chiamate HTTP verso altri servizi con **timeout di 2 secondi** e URL letto dalla variabile d'ambiente `USER_SERVICE_URL`.

### Modello dati (Event)
| Campo | Tipo | Obbligatorio | Note |
|-------|------|--------------|------|
| `id` | UUID v4 | sì (server) | Generato lato server |
| `title` | string (3–120) | sì | |
| `description` | string (≤2000), nullable | no | |
| `organizer_id` | UUID v4 | sì | Riferimento a un utente con ruolo `organizer` |
| `venue` | string (≤100) | sì | |
| `city` | string (≤60) | sì | |
| `start_date` | date (YYYY-MM-DD) | sì | |
| `end_date` | date (YYYY-MM-DD) | sì | `end_date >= start_date` |
| `capacity` | integer (1–10000) | sì | |
| `price` | number (≥0) | sì | |
| `status` | enum `draft`\|`published`\|`cancelled` | no | Default `draft` |
| `created_at` | ISO 8601 UTC | sì (server) | |
| `updated_at` | ISO 8601 UTC | sì (server) | |

---

## Requirement 1 — Creazione evento

**User Story:** Come organizzatore, voglio creare un nuovo evento fornendo i suoi metadati, così che i partecipanti possano scoprirlo e iscriversi.

### Acceptance Criteria

1. QUANDO viene ricevuta una `POST /api/v1/events` con un body valido e un `organizer_id` valido, IL SISTEMA DEVE creare l'evento e rispondere con stato `201`, il corpo dell'evento creato e l'header `Location` con la URL della risorsa.
2. QUANDO viene creato un evento, IL SISTEMA DEVE generare lato server un `id` in formato UUID v4 e valorizzare `created_at`/`updated_at` con lo stesso istante ISO 8601 UTC.
3. QUANDO nel body non è presente il campo `status`, IL SISTEMA DEVE creare l'evento con `status` predefinito `draft`.
4. SE il body non è JSON valido, ALLORA IL SISTEMA DEVE rispondere con stato `400` ed errore `MALFORMED_JSON`.
5. SE mancano campi obbligatori o i valori violano i vincoli di schema (lunghezze, `capacity` 1–10000, `price` ≥ 0, formati), ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR` senza creare l'evento.

---

## Requirement 2 — Lettura evento

**User Story:** Come consumatore dell'API, voglio recuperare un evento tramite il suo id, così da leggerne i dettagli correnti.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/events/{id}` con un id esistente, IL SISTEMA DEVE rispondere con stato `200` e il corpo dell'evento.
2. SE l'id non corrisponde ad alcun evento, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `EVENT_NOT_FOUND`.

---

## Requirement 3 — Aggiornamento evento (PUT / PATCH)

**User Story:** Come organizzatore, voglio aggiornare i dati di un evento esistente, così da mantenerlo accurato.

### Acceptance Criteria

1. QUANDO viene ricevuta una `PUT /api/v1/events/{id}` valida su un evento esistente, IL SISTEMA DEVE sostituire i campi modificabili e rispondere con stato `200` e il corpo aggiornato.
2. QUANDO viene ricevuta una `PATCH /api/v1/events/{id}` valida su un evento esistente, IL SISTEMA DEVE aggiornare solo i campi presenti nel body, rispondendo con stato `200` e il corpo aggiornato.
3. QUANDO un evento viene aggiornato con successo, IL SISTEMA DEVE aggiornare `updated_at` all'istante corrente in ISO 8601 UTC e lasciare invariati `id` e `created_at`.
4. SE l'id non corrisponde ad alcun evento, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `EVENT_NOT_FOUND`.
5. SE il body viola i vincoli di validazione, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR` senza modificare l'evento.

---

## Requirement 4 — Eliminazione evento

**User Story:** Come organizzatore, voglio eliminare un evento, così da rimuovere le conferenze non più necessarie.

### Acceptance Criteria

1. QUANDO viene ricevuta una `DELETE /api/v1/events/{id}` su un evento esistente, IL SISTEMA DEVE eliminare l'evento e rispondere con stato `204` senza corpo.
2. SE l'id non corrisponde ad alcun evento, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `EVENT_NOT_FOUND`.

---

## Requirement 5 — Lista eventi con filtri e paginazione

**User Story:** Come consumatore dell'API, voglio elencare gli eventi filtrando per stato e città con paginazione, così da trovare rapidamente le conferenze di interesse.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/events`, IL SISTEMA DEVE rispondere con stato `200` e un oggetto paginato con `items`, `page`, `page_size` e `total`.
2. QUANDO non vengono forniti `page` e `page_size`, IL SISTEMA DEVE applicare i valori predefiniti `page=1` e `page_size=20`.
3. QUANDO viene fornito il parametro `status`, IL SISTEMA DEVE restituire solo gli eventi con quello stato.
4. QUANDO viene fornito il parametro `city`, IL SISTEMA DEVE restituire solo gli eventi di quella città.
5. QUANDO sono applicati dei filtri, IL SISTEMA DEVE calcolare `total` come numero di eventi che soddisfano i filtri prima della paginazione.
6. SE i parametri di paginazione o filtro non sono validi (es. `page` < 1, `page_size` fuori 1–100, `status` fuori enum), ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR`.

---

## Requirement 6 — REQ-EVT-B01: Verifica dell'organizer_id verso user-service

**User Story:** Come piattaforma, voglio che ogni evento sia associato a un utente realmente esistente, così da garantire l'integrità referenziale tra eventi e utenti.

### Acceptance Criteria

1. QUANDO viene creato un evento (`POST`) o ne viene modificato l'`organizer_id` (`PUT`/`PATCH`), IL SISTEMA DEVE verificare l'esistenza dell'utente effettuando una `GET {USER_SERVICE_URL}/api/v1/users/{organizer_id}` con timeout di 2 secondi.
2. QUANDO lo `user-service` risponde `200` per l'`organizer_id` indicato, IL SISTEMA DEVE considerare il riferimento valido e proseguire con l'operazione.
3. SE lo `user-service` risponde `404` per l'`organizer_id` indicato, ALLORA IL SISTEMA DEVE rifiutare l'operazione con stato `422` ed errore `REFERENCE_NOT_FOUND` senza creare/modificare l'evento.
4. QUANDO un aggiornamento (`PUT`/`PATCH`) non modifica l'`organizer_id`, IL SISTEMA PUÒ omettere la verifica del riferimento già validato in creazione.

---

## Requirement 7 — REQ-EVT-B02: L'organizzatore deve avere ruolo `organizer`

**User Story:** Come piattaforma, voglio che solo utenti con ruolo `organizer` possano essere associati come organizzatori di un evento, così da rispettare le regole di autorizzazione del dominio.

### Acceptance Criteria

1. QUANDO la verifica dell'`organizer_id` verso lo `user-service` ha successo, IL SISTEMA DEVE controllare che l'utente restituito abbia `role == "organizer"`.
2. SE l'utente referenziato esiste ma ha un ruolo diverso da `organizer` (es. `attendee`, `speaker`), ALLORA IL SISTEMA DEVE rifiutare l'operazione con stato `422` ed errore `INVALID_ORGANIZER` senza creare/modificare l'evento.

---

## Requirement 8 — REQ-EVT-B03: Coerenza delle date (end_date >= start_date)

**User Story:** Come organizzatore, voglio che il sistema impedisca eventi con date incoerenti, così da evitare conferenze che finiscono prima di iniziare.

### Acceptance Criteria

1. QUANDO viene creato o aggiornato un evento con `start_date` ed `end_date` valorizzati, IL SISTEMA DEVE verificare che `end_date >= start_date`.
2. SE `end_date` è precedente a `start_date`, ALLORA IL SISTEMA DEVE rifiutare l'operazione con stato `422` ed errore `VALIDATION_ERROR` senza creare/modificare l'evento.
3. QUANDO `end_date` è uguale a `start_date` (evento di un solo giorno), IL SISTEMA DEVE considerare le date valide.
4. QUANDO in un `PATCH` viene fornita una sola delle due date, IL SISTEMA DEVE valutare la coerenza combinando il valore fornito con quello già persistito.

---

## Requirement 9 — REQ-EVT-B04: Transizioni di stato del ciclo di vita

**User Story:** Come organizzatore, voglio che lo stato di un evento evolva solo secondo transizioni consentite, così da mantenere un ciclo di vita coerente.

### Contesto
Stati previsti: `draft`, `published`, `cancelled`. Transizioni consentite:
- `draft` → `published`
- `draft` → `cancelled`
- `published` → `cancelled`

Ogni altra transizione (es. `published` → `draft`, `cancelled` → *qualsiasi*) non è consentita. La transizione verso lo stesso stato (no-op) è considerata valida.

### Acceptance Criteria

1. QUANDO un aggiornamento (`PUT`/`PATCH`) richiede un cambio di `status` incluso tra le transizioni consentite, IL SISTEMA DEVE applicare il nuovo stato e rispondere con stato `200`.
2. SE un aggiornamento richiede una transizione di stato non consentita, ALLORA IL SISTEMA DEVE rifiutare l'operazione con stato `422` ed errore `INVALID_STATUS_TRANSITION` senza modificare l'evento.
3. QUANDO il `status` fornito coincide con quello corrente, IL SISTEMA DEVE considerare l'operazione valida e non alterare il ciclo di vita.

---

## Requirement 10 — REQ-EVT-B05: Indisponibilità dello user-service

**User Story:** Come piattaforma, voglio che l'indisponibilità dello `user-service` sia segnalata in modo esplicito, così che il client possa distinguere un guasto temporaneo da un errore di validazione.

### Acceptance Criteria

1. SE, durante la verifica dell'`organizer_id`, lo `user-service` è irraggiungibile (connessione rifiutata, timeout di 2 secondi superato o errore di rete), ALLORA IL SISTEMA DEVE rispondere con stato `503` ed errore `DEPENDENCY_UNAVAILABLE`.
2. SE lo `user-service` risponde con un errore server (`5xx`), ALLORA IL SISTEMA DEVE rispondere con stato `503` ed errore `DEPENDENCY_UNAVAILABLE`.
3. QUANDO si verifica l'indisponibilità della dipendenza, IL SISTEMA NON DEVE creare o modificare l'evento.

---

## Requirement 11 — Health check

**User Story:** Come sistema di monitoraggio, voglio verificare lo stato di salute del servizio, così da rilevarne l'indisponibilità.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /health`, IL SISTEMA DEVE rispondere con stato `200` e un corpo `{ "status": "ok", "service": "event-service" }`.
2. IL health check NON DEVE dipendere dalla raggiungibilità dello `user-service`.

---

## Riepilogo regole di business

| Regola | Descrizione | Errore | Stato |
|--------|-------------|--------|-------|
| REQ-EVT-B01 | `organizer_id` verificato via HTTP verso user-service | `REFERENCE_NOT_FOUND` | 422 |
| REQ-EVT-B02 | L'organizzatore deve avere `role == organizer` | `INVALID_ORGANIZER` | 422 |
| REQ-EVT-B03 | `end_date >= start_date` | `VALIDATION_ERROR` | 422 |
| REQ-EVT-B04 | Transizioni di stato consentite | `INVALID_STATUS_TRANSITION` | 422 |
| REQ-EVT-B05 | user-service offline/5xx | `DEPENDENCY_UNAVAILABLE` | 503 |
