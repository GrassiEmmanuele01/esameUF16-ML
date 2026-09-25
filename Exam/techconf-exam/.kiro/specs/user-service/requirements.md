# Requirements — user-service

## Introduzione

Lo `user-service` è il registro degli utenti della piattaforma TechConf (partecipanti, relatori, organizzatori). Espone un'API REST su base path `/api/v1/users` e ascolta sulla porta `5001` (letta dalla variabile d'ambiente `PORT`, default `5001`).

Il servizio è la fonte di verità per i dati anagrafici degli utenti (`first_name`, `last_name`, `email`, `company`, `role`) ed è referenziato da iscrizioni e feedback.

I requisiti seguono la notazione EARS (Easy Approach to Requirements Syntax). Gli acceptance criteria usano i pattern:
- **Ubiquitous**: "IL SISTEMA DEVE ..."
- **Event-driven**: "QUANDO <evento>, IL SISTEMA DEVE ..."
- **State-driven**: "MENTRE <stato>, IL SISTEMA DEVE ..."
- **Unwanted behavior**: "SE <condizione>, ALLORA IL SISTEMA DEVE ..."

### Standard di piattaforma applicabili
- Base path risorsa: `/api/v1/users`.
- ID risorsa: UUID v4 generato lato server.
- Date in ISO 8601 UTC (`created_at`, `updated_at`).
- Paginazione con `page`, `page_size`, `total`.
- Errori con struttura `{ "error": { "code": <UPPER_SNAKE>, "message": <string> } }`.

### Modello dati (User)
| Campo | Tipo | Obbligatorio | Note |
|-------|------|--------------|------|
| `id` | UUID v4 | sì (server) | Generato lato server |
| `first_name` | string (1–50) | sì | |
| `last_name` | string (1–50) | sì | |
| `email` | string (email) | sì | Univoca case-insensitive, salvata in minuscolo |
| `company` | string (≤100), nullable | no | |
| `role` | enum `attendee`\|`speaker`\|`organizer` | no | |
| `created_at` | ISO 8601 UTC | sì (server) | |
| `updated_at` | ISO 8601 UTC | sì (server) | |

---

## Requirement 1 — Creazione utente

**User Story:** Come organizzatore della piattaforma, voglio creare un nuovo utente fornendo i suoi dati anagrafici, così che possa essere referenziato da iscrizioni e feedback.

### Acceptance Criteria

1. QUANDO viene ricevuta una `POST /api/v1/users` con un body valido contenente `first_name`, `last_name` ed `email`, IL SISTEMA DEVE creare l'utente e rispondere con stato `201`, il corpo dell'utente creato e l'header `Location` con la URL della risorsa.
2. QUANDO viene creato un utente, IL SISTEMA DEVE generare lato server un `id` in formato UUID v4.
3. QUANDO viene creato un utente, IL SISTEMA DEVE valorizzare `created_at` e `updated_at` con lo stesso istante in formato ISO 8601 UTC.
4. QUANDO nel body non è presente il campo `role`, IL SISTEMA DEVE applicare il ruolo predefinito `attendee`.
5. QUANDO nel body non è presente il campo `company`, IL SISTEMA DEVE salvare l'utente con `company` valorizzato a `null`.
6. SE il body non è JSON valido, ALLORA IL SISTEMA DEVE rispondere con stato `400` ed errore `MALFORMED_JSON`.
7. SE mancano campi obbligatori o i valori violano i vincoli (lunghezze `first_name`/`last_name` 1–50, `company` ≤100, formato `email`, `role` fuori enum, campi non ammessi), ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR` senza creare l'utente.

---

## Requirement 2 — Lettura utente

**User Story:** Come consumatore dell'API, voglio recuperare un utente tramite il suo id, così da poterne leggere i dati anagrafici correnti.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/users/{id}` con un id esistente, IL SISTEMA DEVE rispondere con stato `200` e il corpo dell'utente.
2. SE l'id non corrisponde ad alcun utente, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.

---

## Requirement 3 — Aggiornamento utente (PUT / PATCH)

**User Story:** Come organizzatore della piattaforma, voglio aggiornare i dati di un utente esistente, così da mantenere il registro accurato.

### Acceptance Criteria

1. QUANDO viene ricevuta una `PUT /api/v1/users/{id}` valida su un utente esistente, IL SISTEMA DEVE sostituire i campi modificabili dell'utente e rispondere con stato `200` e il corpo aggiornato.
2. QUANDO viene ricevuta una `PATCH /api/v1/users/{id}` valida su un utente esistente, IL SISTEMA DEVE aggiornare solo i campi presenti nel body e lasciare invariati gli altri, rispondendo con stato `200` e il corpo aggiornato.
3. QUANDO un utente viene aggiornato con successo, IL SISTEMA DEVE aggiornare `updated_at` all'istante corrente in ISO 8601 UTC e lasciare invariati `id` e `created_at`.
4. SE l'id non corrisponde ad alcun utente, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.
5. SE il body viola i vincoli di validazione, ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR` senza modificare l'utente.

---

## Requirement 4 — Eliminazione utente

**User Story:** Come organizzatore della piattaforma, voglio eliminare un utente, così da rimuovere le anagrafiche non più necessarie.

### Acceptance Criteria

1. QUANDO viene ricevuta una `DELETE /api/v1/users/{id}` su un utente esistente, IL SISTEMA DEVE eliminare l'utente e rispondere con stato `204` senza corpo.
2. SE l'id non corrisponde ad alcun utente, ALLORA IL SISTEMA DEVE rispondere con stato `404` ed errore `NOT_FOUND`.

---

## Requirement 5 — REQ-USR-B01: Univocità email case-insensitive

**User Story:** Come amministratore della piattaforma, voglio che ogni indirizzo email identifichi al più un utente indipendentemente da maiuscole/minuscole, così da evitare account duplicati.

### Acceptance Criteria

1. IL SISTEMA DEVE trattare l'email come identificatore univoco confrontandola in modo case-insensitive (es. `Mario@Example.com` e `mario@example.com` sono considerate uguali).
2. SE una `POST /api/v1/users` fornisce un'email già presente (confronto case-insensitive), ALLORA IL SISTEMA DEVE rispondere con stato `409` ed errore `EMAIL_ALREADY_EXISTS` senza creare l'utente.
3. SE una `PUT` o `PATCH /api/v1/users/{id}` imposta un'email già usata da un altro utente (confronto case-insensitive), ALLORA IL SISTEMA DEVE rispondere con stato `409` ed errore `EMAIL_ALREADY_EXISTS` senza modificare l'utente.
4. QUANDO una `PUT` o `PATCH` imposta un'email che coincide (case-insensitive) con quella già posseduta dallo stesso utente, IL SISTEMA DEVE considerare l'operazione valida e NON DEVE sollevare il conflitto `EMAIL_ALREADY_EXISTS`.

---

## Requirement 6 — REQ-USR-B02: Normalizzazione email in minuscolo

**User Story:** Come amministratore della piattaforma, voglio che le email siano memorizzate sempre in minuscolo, così da garantire un formato coerente e confronti affidabili.

### Acceptance Criteria

1. QUANDO un utente viene creato, IL SISTEMA DEVE salvare il campo `email` convertito interamente in minuscolo, indipendentemente dal case fornito in input.
2. QUANDO l'email di un utente viene aggiornata tramite `PUT` o `PATCH`, IL SISTEMA DEVE salvare il valore convertito in minuscolo.
3. IL SISTEMA DEVE restituire nelle risposte l'email nella sua forma normalizzata in minuscolo.
4. IL SISTEMA DEVE applicare il controllo di univocità (REQ-USR-B01) sulla forma normalizzata in minuscolo.

---

## Requirement 7 — REQ-USR-B03: Lista utenti con filtri e paginazione

**User Story:** Come consumatore dell'API, voglio elencare gli utenti filtrando per ruolo ed email con supporto alla paginazione, così da trovare rapidamente gli utenti di interesse.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /api/v1/users`, IL SISTEMA DEVE rispondere con stato `200` e un oggetto paginato contenente `items`, `page`, `page_size` e `total`.
2. QUANDO non vengono forniti `page` e `page_size`, IL SISTEMA DEVE applicare i valori predefiniti `page=1` e `page_size=20`.
3. QUANDO viene fornito il parametro di query `role`, IL SISTEMA DEVE restituire solo gli utenti il cui `role` coincide con il valore richiesto.
4. QUANDO viene fornito il parametro di query `email`, IL SISTEMA DEVE filtrare gli utenti per email in modo case-insensitive.
5. QUANDO vengono forniti sia `role` sia `email`, IL SISTEMA DEVE restituire solo gli utenti che soddisfano entrambi i filtri.
6. QUANDO sono applicati dei filtri, IL SISTEMA DEVE calcolare `total` come numero di utenti che soddisfano i filtri (prima della paginazione), non come numero totale di utenti nel sistema.
7. SE i parametri di paginazione o filtro non sono validi (es. `page` < 1, `page_size` fuori dall'intervallo 1–100, `role` fuori enum), ALLORA IL SISTEMA DEVE rispondere con stato `422` ed errore `VALIDATION_ERROR`.

---

## Requirement 8 — Health check

**User Story:** Come sistema di monitoraggio, voglio verificare lo stato di salute del servizio, così da rilevarne l'indisponibilità.

### Acceptance Criteria

1. QUANDO viene ricevuta una `GET /health`, IL SISTEMA DEVE rispondere con stato `200` e un corpo `{ "status": "ok", "service": "user-service" }`.
