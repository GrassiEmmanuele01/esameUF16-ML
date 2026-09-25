# Design — event-service

## Panoramica

L'`event-service` gestisce le conferenze (eventi) di TechConf con il loro ciclo di vita e la capacità. Espone un'API REST su base path `/api/v1/events`, ascolta sulla porta letta da `PORT` (default `5002`) ed è la fonte di verità dei dati degli eventi.

A differenza dello `user-service`, l'event-service ha una **dipendenza di servizio**: per validare l'`organizer_id` effettua una chiamata HTTP allo `user-service` (URL da `USER_SERVICE_URL`, timeout 2s). Questa dipendenza introduce le regole di business REQ-EVT-B01/B02 e la gestione dell'indisponibilità REQ-EVT-B05.

Il design segue la **Clean Architecture**: le dipendenze puntano verso il dominio. Stack: Flask (HTTP), `requests` (chiamate verso user-service), standard library per la persistenza (Memory/JSON/SQLite). Il contratto autoritativo è [`contracts/openapi/event-service.yaml`](../../../contracts/openapi/event-service.yaml).

## Architettura a livelli

```
services/event_service/
  app.py                    # Composition root: wiring Flask + backend + client user
  config.py                 # PORT, STORAGE_BACKEND, DATA_DIR, USER_SERVICE_URL
  domain/
    models.py               # Entità Event, EventStatus, transizioni consentite
    service.py              # EventService: casi d'uso
    repository.py           # EventRepository: interfaccia di persistenza
    users.py                # UserDirectory: porta (interfaccia) verso lo user-service
    errors.py               # Errori: EventNotFound, ReferenceNotFound, InvalidOrganizer,
                            #         InvalidStatusTransition, DependencyUnavailable
  infrastructure/
    repositories/           # Memory/JSON/SQLite + factory (come user-service)
    users_http.py           # HttpUserDirectory: implementazione requests (timeout 2s)
  entrypoints/
    http/
      blueprint.py          # Rotte Flask, serializzazione
      errors.py             # Mapping errori -> HTTP (400/404/422/503)
  tests/                    # Unit test del servizio
```

### Regole di dipendenza

- `domain/` non dipende da altri layer. Definisce le entità, i casi d'uso e **due porte**: `EventRepository` (persistenza) e `UserDirectory` (verifica organizzatore).
- `infrastructure/` implementa le porte: i repository concreti e `HttpUserDirectory` (client `requests`).
- `entrypoints/http/` adatta HTTP ai casi d'uso; non conosce le implementazioni concrete.
- `app.py` costruisce repository e `HttpUserDirectory` (con l'URL da config) e li inietta nell'`EventService`.

```
EventBlueprint -> EventService -> EventRepository (porta)   -> Memory/JSON/SQLite
                              \-> UserDirectory   (porta)   -> HttpUserDirectory --HTTP--> user-service
```

## Componenti principali

### EventBlueprint (entrypoints/http)

Blueprint Flask su `/api/v1/events` più `/health`. Mappa le operazioni del contratto:

| Operazione | Metodo e path | Note |
|------------|---------------|------|
| `createEvent` | `POST /api/v1/events` | `201` + `Location`; verifica organizzatore |
| `listEvents` | `GET /api/v1/events` | paginazione + filtri `status`/`city` |
| `getEvent` | `GET /api/v1/events/{id}` | `404` se assente |
| `replaceEvent` | `PUT /api/v1/events/{id}` | verifica organizzatore + transizione |
| `updateEvent` | `PATCH /api/v1/events/{id}` | parziale; verifica se cambia organizzatore/stato |
| `deleteEvent` | `DELETE /api/v1/events/{id}` | `204` |
| `health` | `GET /health` | non dipende da user-service |

### EventService (domain)

Orchestra i casi d'uso e dipende solo dalle porte `EventRepository` e `UserDirectory`. Logica chiave:

- **create_event**: valida lo schema, verifica `end_date >= start_date` (REQ-EVT-B03), verifica l'organizzatore tramite `UserDirectory` (REQ-EVT-B01/B02), imposta `status` default `draft` (o quello fornito, se ammesso), genera `id`/timestamp.
- **replace_event / update_event**: ri-validazione; se cambia `organizer_id` ri-verifica l'organizzatore; se cambia `status` applica il controllo di transizione (REQ-EVT-B04); ricalcola la coerenza date combinando i valori nuovi con quelli persistiti.
- **list_events / get_event / delete_event**: filtri, dettaglio ed eliminazione con `EventNotFound`.

### Porte verso l'esterno

- **EventRepository** — interfaccia di persistenza analoga a quella dello user-service (`add`, `get`, `update`, `delete`, `list(status, city, page, page_size) -> (items, total)`).
- **UserDirectory** — porta di dominio per la verifica dell'organizzatore:

  ```python
  class UserDirectory(ABC):
      def get_role(self, user_id: str) -> str | None: ...
      # Restituisce il ruolo dell'utente, None se lo user-service risponde 404.
      # Solleva DependencyUnavailable se lo user-service è irraggiungibile o 5xx.
  ```

  Isolare la dipendenza dietro una porta permette di testare i casi d'uso con un doppio in memoria, senza rete.

## Verifica dell'organizzatore e regole di business

Il flusso di verifica (create e update che tocca `organizer_id`) è:

```
1. GET {USER_SERVICE_URL}/api/v1/users/{organizer_id}  (timeout 2s)
2. connessione rifiutata / timeout / 5xx  -> DependencyUnavailable  -> 503 DEPENDENCY_UNAVAILABLE  (REQ-EVT-B05)
3. 404                                     -> ReferenceNotFound      -> 422 REFERENCE_NOT_FOUND      (REQ-EVT-B01)
4. 200 e role != "organizer"               -> InvalidOrganizer       -> 422 INVALID_ORGANIZER        (REQ-EVT-B02)
5. 200 e role == "organizer"               -> ok, prosegue
```

### Transizioni di stato (REQ-EVT-B04)

Definite nel dominio come mappa delle transizioni consentite:

```
draft     -> {published, cancelled}
published -> {cancelled}
cancelled -> {}            # stato terminale
```

La transizione verso lo stesso stato è un no-op valido. Ogni transizione non ammessa solleva `InvalidStatusTransition` → `422 INVALID_STATUS_TRANSITION`.

### Mapping errori

| Eccezione di dominio | Status | `code` |
|----------------------|--------|--------|
| `MalformedJson` | 400 | `MALFORMED_JSON` |
| `EventNotFound` | 404 | `EVENT_NOT_FOUND` |
| `ValidationError` (schema, date) | 422 | `VALIDATION_ERROR` |
| `ReferenceNotFound` | 422 | `REFERENCE_NOT_FOUND` |
| `InvalidOrganizer` | 422 | `INVALID_ORGANIZER` |
| `InvalidStatusTransition` | 422 | `INVALID_STATUS_TRANSITION` |
| `DependencyUnavailable` | 503 | `DEPENDENCY_UNAVAILABLE` |

## Client HTTP verso user-service (infrastructure)

`HttpUserDirectory` implementa `UserDirectory` con `requests`:
- URL base da `USER_SERVICE_URL`; chiamata `GET /api/v1/users/{id}` con **timeout esplicito di 2 secondi**.
- `200` → estrae `role` dal body; `404` → `None`.
- `requests.exceptions.RequestException` (connessione/timeout) o risposta `5xx` → `DependencyUnavailable`.

## Persistenza

Identica per struttura allo user-service: tre backend intercambiabili (Memory/JSON in `DATA_DIR/events.json`/SQLite in `DATA_DIR/events.db`) selezionati via `STORAGE_BACKEND` da una factory, solo standard library.

### Configurazione (`config.py`)

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `PORT` | Porta di ascolto | `5002` |
| `STORAGE_BACKEND` | `memory` \| `json` \| `sqlite` | `memory` |
| `DATA_DIR` | Directory file JSON/SQLite | `./data` |
| `USER_SERVICE_URL` | URL base dello user-service | `http://localhost:5001` |

## Strategia di test

### Unit test (pytest)

- **Dominio (`EventService`)**: casi d'uso con `MemoryEventRepository` e un `FakeUserDirectory` in memoria che simula gli esiti (organizzatore valido, ruolo errato, non trovato, dipendenza non disponibile). Copre REQ-EVT-B01..B05, default `status=draft`, coerenza date, transizioni.
- **Persistenza**: suite parametrizzata sui tre backend (come user-service), con `tmp_path`.
- **Client user (`HttpUserDirectory`)**: test con la libreria **`responses`** per mockare le chiamate `requests` — 200/404/5xx e connessione non disponibile (timeout) → `DependencyUnavailable`.
- **Entrypoint HTTP**: test con il test client di Flask, con `UserDirectory` sostituito da un doppio, per verificare status code e mapping errori (inclusi `422 REFERENCE_NOT_FOUND`/`INVALID_ORGANIZER`/`INVALID_STATUS_TRANSITION` e `503 DEPENDENCY_UNAVAILABLE`).

### Copertura e contratto

- Coverage con `pytest` e soglia `--cov-fail-under=80`.
- Ogni risposta HTTP negli unit test è validata con `assert_matches_contract` di [`contracts/validator.py`](../../../contracts/validator.py) contro `event-service.yaml`.
- La suite di accettazione `tests/integration/test_event.py` (IT-E01..IT-E08) verifica gli scenari service→service e di resilienza; richiede `services.yaml` con `user` ed `event` dichiarati.
