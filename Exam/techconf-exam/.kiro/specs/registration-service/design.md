# Design — registration-service

## Panoramica

Il `registration-service` collega utenti ed eventi tramite iscrizioni, rispettando capacità e regole di stato. Espone un'API REST su base path `/api/v1/registrations`, ascolta sulla porta `PORT` (default `5003`) ed è la fonte di verità delle iscrizioni.

Ha **due dipendenze di servizio**: verifica l'utente verso lo `user-service` (`USER_SERVICE_URL`) e l'evento verso l'`event-service` (`EVENT_SERVICE_URL`), entrambe con timeout 2s. Dall'evento ricava anche `status`, `capacity` e `price`, necessari alle regole REQ-REG-B03/B05/B06.

Design in **Clean Architecture**. Stack: Flask (HTTP), `requests` (chiamate ai servizi), standard library per la persistenza. Contratto autoritativo: [`contracts/openapi/registration-service.yaml`](../../../contracts/openapi/registration-service.yaml).

## Architettura a livelli

```
services/registration_service/
  app.py                    # Composition root: wiring Flask + backend + client user/event
  config.py                 # PORT, STORAGE_BACKEND, DATA_DIR, USER_SERVICE_URL, EVENT_SERVICE_URL
  domain/
    models.py               # Entità Registration, RegistrationStatus, transizioni
    service.py              # RegistrationService: casi d'uso + regole di business
    repository.py           # RegistrationRepository: interfaccia di persistenza
    directories.py          # Porte UserDirectory ed EventDirectory (con EventInfo)
    errors.py               # Errori di dominio (vedi tabella mapping)
  infrastructure/
    repositories/           # Memory/JSON/SQLite + factory
    users_http.py           # HttpUserDirectory (requests, 2s)
    events_http.py          # HttpEventDirectory (requests, 2s) -> EventInfo(status, capacity, price)
  entrypoints/
    http/
      blueprint.py          # Rotte Flask (incluso /stats), serializzazione
      errors.py             # Mapping errori -> HTTP (400/404/405/409/422/503)
  tests/
```

### Regole di dipendenza

- `domain/` definisce entità, casi d'uso e **tre porte**: `RegistrationRepository`, `UserDirectory`, `EventDirectory`.
- `infrastructure/` implementa le porte: repository concreti e i due client HTTP.
- `entrypoints/http/` adatta HTTP ai casi d'uso.
- `app.py` costruisce repository + `HttpUserDirectory` + `HttpEventDirectory` e li inietta nel `RegistrationService`.

```
RegistrationBlueprint -> RegistrationService -> RegistrationRepository (porta) -> Memory/JSON/SQLite
                                             \-> UserDirectory  (porta) -> HttpUserDirectory --HTTP--> user-service
                                             \-> EventDirectory (porta) -> HttpEventDirectory --HTTP--> event-service
```

## Componenti principali

### RegistrationBlueprint (entrypoints/http)

Blueprint Flask su `/api/v1/registrations` più `/health`. Mappa le operazioni del contratto:

| Operazione | Metodo e path | Note |
|------------|---------------|------|
| `createRegistration` | `POST /api/v1/registrations` | `201` + `Location`; applica REQ-REG-B01..B06 |
| `listRegistrations` | `GET /api/v1/registrations` | filtri `user_id`/`event_id`/`status`, paginazione |
| `registrationStats` | `GET /api/v1/registrations/stats?event_id=` | REQ-REG-B08 |
| `getRegistration` | `GET /api/v1/registrations/{id}` | `404 NOT_FOUND` |
| `updateRegistration` | `PATCH /api/v1/registrations/{id}` | transizione stato (REQ-REG-B07) |
| `putRegistrationNotAllowed` | `PUT /api/v1/registrations/{id}` | `405` |
| `deleteRegistration` | `DELETE /api/v1/registrations/{id}` | `204` |
| `health` | `GET /health` | indipendente dalle dipendenze |

> Nota di routing: `/stats` deve essere registrata prima (o in modo più specifico) di `/{id}` per non essere interpretata come un id.

### RegistrationService (domain)

Dipende da `RegistrationRepository`, `UserDirectory`, `EventDirectory`. Logica chiave della creazione (ordine dei controlli):

```
1. valida payload (user_id/event_id UUID)                     -> 422 VALIDATION_ERROR
2. UserDirectory.exists(user_id)   (REQ-REG-B01)              -> 422 REFERENCE_NOT_FOUND / 503
3. EventDirectory.get(event_id)    (REQ-REG-B02)              -> 422 REFERENCE_NOT_FOUND / 503
4. event.status == "published"     (REQ-REG-B03)              -> 422 EVENT_NOT_OPEN
5. no iscrizione confirmed (user,event) (REQ-REG-B04)         -> 409 ALREADY_REGISTERED
6. confirmed_count(event) < event.capacity (REQ-REG-B05)      -> 409 EVENT_FULL
7. amount = event.price            (REQ-REG-B06)
8. crea Registration(status=confirmed, id, timestamp)
```

Altri casi d'uso: `get`, `list` (filtri + paginazione), `delete` (`NOT_FOUND`), `update_status` (transizione REQ-REG-B07), `stats` (REQ-REG-B08).

### Porte verso l'esterno

- **RegistrationRepository** — `add`, `get`, `update`, `delete`, `list(user_id, event_id, status, page, page_size) -> (items, total)`, e un helper `count_confirmed(event_id) -> int` e `find_confirmed(user_id, event_id) -> Registration | None` per le regole B04/B05.
- **UserDirectory** — `exists(user_id) -> bool` (False su 404, `DependencyUnavailable` su indisponibilità).
- **EventDirectory** — `get(event_id) -> EventInfo | None` dove `EventInfo` espone `status`, `capacity`, `price`; `None` su 404, `DependencyUnavailable` su indisponibilità.

Isolare le due dipendenze dietro porte consente di testare i casi d'uso con doppi in memoria.

## Regole di business e mapping errori

| Regola | Esito | Eccezione | Status / code |
|--------|-------|-----------|---------------|
| REQ-REG-B01 | user 404 | `ReferenceNotFound` | 422 `REFERENCE_NOT_FOUND` |
| REQ-REG-B02 | event 404 | `ReferenceNotFound` | 422 `REFERENCE_NOT_FOUND` |
| REQ-REG-B03 | event non published | `EventNotOpen` | 422 `EVENT_NOT_OPEN` |
| REQ-REG-B04 | doppia confermata | `AlreadyRegistered` | 409 `ALREADY_REGISTERED` |
| REQ-REG-B05 | capienza raggiunta | `EventFull` | 409 `EVENT_FULL` |
| REQ-REG-B06 | amount = price | — | — |
| REQ-REG-B07 | cancelled→confirmed | `InvalidStatusTransition` | 422 `INVALID_STATUS_TRANSITION` |
| REQ-REG-B08 | stats evento assente | `NotFound` | 404 `NOT_FOUND` |
| dipendenze | offline / 5xx | `DependencyUnavailable` | 503 `DEPENDENCY_UNAVAILABLE` |
| — | body malformato | `MalformedJson` | 400 `MALFORMED_JSON` |
| — | id inesistente | `NotFound` | 404 `NOT_FOUND` |
| — | PUT | (Flask) | 405 `METHOD_NOT_ALLOWED` |

### Transizioni di stato (REQ-REG-B07)

```
confirmed -> {cancelled}
cancelled -> {}          # terminale
```

Transizione verso lo stesso stato = no-op valido. Alla transizione `confirmed → cancelled` il posto è liberato automaticamente, perché `count_confirmed` conta solo le iscrizioni `confirmed`.

## Client HTTP (infrastructure)

- `HttpUserDirectory.exists(id)`: `GET {USER_SERVICE_URL}/api/v1/users/{id}` (timeout 2s) → `True` su 200, `False` su 404, `DependencyUnavailable` su connessione/timeout/5xx.
- `HttpEventDirectory.get(id)`: `GET {EVENT_SERVICE_URL}/api/v1/events/{id}` (timeout 2s) → `EventInfo(status, capacity, price)` su 200, `None` su 404, `DependencyUnavailable` su connessione/timeout/5xx.

## Persistenza

Tre backend intercambiabili (Memory/JSON in `DATA_DIR/registrations.json`/SQLite in `DATA_DIR/registrations.db`) via factory, solo standard library. Il conteggio delle iscrizioni confermate e la ricerca della coppia (user,event) sono esposti dal repository per supportare B04/B05 in modo efficiente su ogni backend.

### Configurazione (`config.py`)

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `PORT` | Porta di ascolto | `5003` |
| `STORAGE_BACKEND` | `memory` \| `json` \| `sqlite` | `memory` |
| `DATA_DIR` | Directory file JSON/SQLite | `./data` |
| `USER_SERVICE_URL` | URL base user-service | `http://localhost:5001` |
| `EVENT_SERVICE_URL` | URL base event-service | `http://localhost:5002` |

## Strategia di test

- **Dominio (`RegistrationService`)**: casi d'uso con `MemoryRegistrationRepository` e doppi `FakeUserDirectory`/`FakeEventDirectory` che simulano esistenza, stato evento, capacità, prezzo e indisponibilità. Copre REQ-REG-B01..B08.
- **Persistenza**: suite parametrizzata sui tre backend con `tmp_path`, incluse le query `count_confirmed` e `find_confirmed`.
- **Client (`HttpUserDirectory`/`HttpEventDirectory`)**: test con **`responses`** — 200/404/5xx e connessione non disponibile → `DependencyUnavailable`; verifica timeout 2s.
- **Entrypoint HTTP**: test con il test client di Flask (porte sostituite da doppi) e `assert_matches_contract` contro `registration-service.yaml`: 201/Location/amount, 409 (`ALREADY_REGISTERED`/`EVENT_FULL`), 422 (`REFERENCE_NOT_FOUND`/`EVENT_NOT_OPEN`/`INVALID_STATUS_TRANSITION`/`VALIDATION_ERROR`), 503, 405 su PUT, `/stats` 200 e 404.
- **Coverage** con soglia `--cov-fail-under=80`.
- **Accettazione**: `tests/integration/test_registration.py` (IT-R01..IT-R10) con `user`, `event`, `registration` dichiarati in `services.yaml`.
