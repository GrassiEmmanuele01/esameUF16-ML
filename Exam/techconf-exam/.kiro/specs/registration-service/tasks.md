# Implementation Plan — registration-service

Piano incrementale per il `registration-service` (porta 5003). Task atomici e sequenziali; ciascuno indica i requisiti coperti (vedi `requirements.md`) e si basa sul `design.md`. Riusa `packages/common/`.

- [x] 1. Setup del servizio e configurazione
  - Scheletro `services/registration_service/` (Clean Architecture): `domain/`, `infrastructure/repositories/`, `entrypoints/http/`, `tests/` con `__init__.py`.
  - `config.py`: `PORT` (default `5003`), `STORAGE_BACKEND`, `DATA_DIR`, `USER_SERVICE_URL` (default `http://localhost:5001`), `EVENT_SERVICE_URL` (default `http://localhost:5002`).
  - _Requirements: Standard di piattaforma (PORT, base path); Requirement 15 (health)_

- [x] 2. Entità di dominio, stati ed eccezioni
  - `domain/models.py`: entità `Registration`, enum `RegistrationStatus` (`confirmed`/`cancelled`), transizioni consentite (`confirmed → cancelled`) e `can_transition`.
  - `domain/errors.py`: `NotFound` (404 `NOT_FOUND`), `ReferenceNotFound` (422), `EventNotOpen` (422 `EVENT_NOT_OPEN`), `AlreadyRegistered` (409 `ALREADY_REGISTERED`), `EventFull` (409 `EVENT_FULL`), `InvalidStatusTransition` (422), `DependencyUnavailable` (503).
  - _Requirements: 1.2, REQ-REG-B03, REQ-REG-B04, REQ-REG-B05, REQ-REG-B07_

- [x] 3. Porte di dominio (interfacce)
  - `domain/repository.py`: `RegistrationRepository` (`add`, `get`, `update`, `delete`, `list(user_id, event_id, status, page, page_size) -> (items, total)`, `count_confirmed(event_id) -> int`, `find_confirmed(user_id, event_id) -> Registration | None`).
  - `domain/directories.py`: `UserDirectory.exists(user_id) -> bool`; `EventDirectory.get(event_id) -> EventInfo | None` con `EventInfo(status, capacity, price)`. None su 404, `DependencyUnavailable` su indisponibilità.
  - _Requirements: REQ-REG-B01, REQ-REG-B02, REQ-REG-B04, REQ-REG-B05_

- [x] 4. Casi d'uso RegistrationService (regole di business)
  - `domain/service.py`: `RegistrationService` dipendente da repository + `UserDirectory` + `EventDirectory`.
  - 4.1 `create_registration`: validazione, esistenza user (B01) ed event (B02), event `published` (B03), no doppia confermata (B04), capienza (B05), `amount=event.price` (B06), `status=confirmed`, id/timestamp.
    - _Requirements: 1.1, 1.2, 1.4, REQ-REG-B01..B06_
  - 4.2 `get` / `list` / `delete`: con `NotFound`; filtri e paginazione.
    - _Requirements: 2.1, 2.2, 3.1–3.5, 4.1, 4.2_
  - 4.3 `update_status` (PATCH): transizione `confirmed → cancelled` (B07), no-op sullo stesso stato, `INVALID_STATUS_TRANSITION` altrimenti, `updated_at`.
    - _Requirements: 12.1–12.4, REQ-REG-B07_
  - 4.4 `stats(event_id)`: recupera evento (404 `NOT_FOUND` se assente), `confirmed=count_confirmed`, `available=capacity-confirmed` (B08).
    - _Requirements: 13.1–13.4, REQ-REG-B08_

- [x] 5. Backend di persistenza
  - `infrastructure/repositories/`: `MemoryRegistrationRepository`, `JsonRegistrationRepository` (`registrations.json`, scrittura atomica), `SqliteRegistrationRepository` (`registrations.db`) + `factory.build_repository`.
  - Implementare `count_confirmed` e `find_confirmed` su tutti i backend.
  - _Requirements: Standard di piattaforma; 3.x, REQ-REG-B04, REQ-REG-B05_

- [x] 6. Client HTTP verso le dipendenze
  - `infrastructure/users_http.py`: `HttpUserDirectory.exists` (`GET {USER_SERVICE_URL}/api/v1/users/{id}`, timeout 2s; 404->False; conn/5xx->`DependencyUnavailable`).
  - `infrastructure/events_http.py`: `HttpEventDirectory.get` (`GET {EVENT_SERVICE_URL}/api/v1/events/{id}`, timeout 2s; 200->`EventInfo(status,capacity,price)`; 404->None; conn/5xx->`DependencyUnavailable`).
  - _Requirements: REQ-REG-B01, REQ-REG-B02, REQ-REG-B03, REQ-REG-B06, Requirement 14_

- [x] 7. HTTP: serializzazione, mapping errori e rotte
  - `entrypoints/http/errors.py`: mapping eccezioni -> struttura d'errore uniforme e status (400/404/405/409/422/503).
  - `entrypoints/http/blueprint.py`: `POST`, `GET` (lista + filtri), `GET /stats`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `PUT /{id}` -> 405, e `GET /health`. Registrare `/stats` prima di `/{id}`.
  - _Requirements: 1.1, 1.3, 2.x, 3.x, 4.x, 5.1, 13.x, 15.x, REQ-REG-B07, REQ-REG-B08_

- [x] 8. Wiring finale (composition root)
  - `app.py`: `create_app`/`load_config`, `build_repository`, `HttpUserDirectory(USER_SERVICE_URL)`, `HttpEventDirectory(EVENT_SERVICE_URL)`, `RegistrationService`, blueprint + error handler, avvio su `PORT`.
  - Dichiarare `registration` in `services.yaml`.
  - _Requirements: Standard di piattaforma (PORT, backend, *_SERVICE_URL)_

- [x] 9. Unit test del dominio (RegistrationService)
  - `tests/`: casi d'uso con `MemoryRegistrationRepository` e `FakeUserDirectory`/`FakeEventDirectory` (esistenza, stato evento, capacità, prezzo, indisponibilità).
  - Verificare REQ-REG-B01..B08: `REFERENCE_NOT_FOUND`, `EVENT_NOT_OPEN`, `ALREADY_REGISTERED`, `EVENT_FULL`, `amount=price`, transizione e liberazione posto, `/stats`.
  - _Requirements: 1.x, 2.x, 3.x, 4.x, 12.x, 13.x, REQ-REG-B01..B08_

- [x] 10. Unit test dei backend di persistenza (parametrizzati)
  - Suite parametrizzata sui tre backend con `tmp_path`: CRUD, filtri, paginazione, `count_confirmed`, `find_confirmed`, persistenza.
  - _Requirements: 3.x, REQ-REG-B04, REQ-REG-B05_

- [x] 11. Unit test dei client HTTP (responses)
  - Mock con **`responses`** di user-service ed event-service: 200/404/5xx e connessione non disponibile -> `DependencyUnavailable`; `EventInfo` estratto correttamente; timeout 2s.
  - _Requirements: REQ-REG-B01, REQ-REG-B02, REQ-REG-B03, REQ-REG-B06, Requirement 14_

- [x] 12. Unit test HTTP + validazione contratto
  - Test con il test client di Flask (porte doppie) e `assert_matches_contract` contro `registration-service.yaml`: 201/Location/amount, 409 (`ALREADY_REGISTERED`/`EVENT_FULL`), 422 (`REFERENCE_NOT_FOUND`/`EVENT_NOT_OPEN`/`INVALID_STATUS_TRANSITION`/`VALIDATION_ERROR`), 503, 405 su PUT, `/stats` 200 e 404, paginazione/filtri.
  - Coverage con soglia `--cov-fail-under=80`.
  - _Requirements: tutti i precedenti (conformità al contratto e coverage ≥ 80%)_

- [x] 13. Accettazione (opzionale, richiede services.yaml)
  - Eseguire `tests/integration/test_registration.py` (IT-R01..IT-R10) con `user`, `event`, `registration` dichiarati, inclusa la resilienza (IT-R10 -> 503).
  - _Requirements: REQ-REG-B01..B08 (verifica end-to-end)_
