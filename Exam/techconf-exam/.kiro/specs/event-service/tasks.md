# Implementation Plan — event-service

Piano di sviluppo incrementale per l'`event-service` (porta 5002). Task atomici e sequenziali; ciascuno indica i requisiti coperti (vedi `requirements.md`) e si basa sul `design.md`. Il servizio riusa `packages/common/` già presente.

- [ ] 1. Setup del servizio e configurazione
  - Creare lo scheletro `services/event_service/` (Clean Architecture): `domain/`, `infrastructure/repositories/`, `entrypoints/http/`, `tests/` con `__init__.py`.
  - Implementare `config.py`: `PORT` (default `5002`), `STORAGE_BACKEND`, `DATA_DIR`, `USER_SERVICE_URL` (default `http://localhost:5001`).
  - _Requirements: Standard di piattaforma (PORT, base path); Requirement 11 (health)_

- [ ] 2. Entità di dominio, stati ed eccezioni
  - `domain/models.py`: entità `Event`, enum `EventStatus` (`draft`/`published`/`cancelled`), mappa delle transizioni consentite e helper `can_transition(from, to)`.
  - `domain/errors.py`: `EventNotFound` (404 `EVENT_NOT_FOUND`), `ReferenceNotFound` (422 `REFERENCE_NOT_FOUND`), `InvalidOrganizer` (422 `INVALID_ORGANIZER`), `InvalidStatusTransition` (422 `INVALID_STATUS_TRANSITION`), `DependencyUnavailable` (503 `DEPENDENCY_UNAVAILABLE`).
  - _Requirements: 1.2, 1.3, REQ-EVT-B04_

- [ ] 3. Porte di dominio (interfacce)
  - `domain/repository.py`: interfaccia `EventRepository` (`add`, `get`, `update`, `delete`, `list(status, city, page, page_size) -> (items, total)`).
  - `domain/users.py`: porta `UserDirectory` con `get_role(user_id) -> str | None` (None su 404, solleva `DependencyUnavailable` su indisponibilità).
  - _Requirements: REQ-EVT-B01, REQ-EVT-B05_

- [ ] 4. Validazione dei payload (regole di schema e date)
  - `domain/validators.py`: `validate_create`/`validate_update` secondo `EventCreate`/`EventUpdate` (title 3–120, description ≤2000, venue ≤100, city ≤60, capacity 1–10000, price ≥0, formato date, `additionalProperties:false`).
  - Implementare la coerenza date `end_date >= start_date`, combinando in PATCH il valore fornito con quello persistito.
  - _Requirements: 1.5, 3.5, REQ-EVT-B03_

- [ ] 5. Casi d'uso EventService (logica di dominio)
  - `domain/service.py`: `EventService` dipendente da `EventRepository` e `UserDirectory`.
  - 5.1 `create_event`: validazione, coerenza date, verifica organizzatore (esistenza + ruolo), default `status=draft`, `id`/timestamp.
    - _Requirements: 1.1, 1.2, 1.3, 1.5, REQ-EVT-B01, REQ-EVT-B02, REQ-EVT-B03, REQ-EVT-B05_
  - 5.2 `get_event` / `delete_event`: con `EventNotFound`.
    - _Requirements: 2.1, 2.2, 4.1, 4.2_
  - 5.3 `replace_event` / `update_event`: ri-validazione; ri-verifica organizzatore se cambia `organizer_id`; controllo transizione se cambia `status`; `updated_at` aggiornato, `id`/`created_at` invariati.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, REQ-EVT-B01, REQ-EVT-B02, REQ-EVT-B03, REQ-EVT-B04, REQ-EVT-B05_
  - 5.4 `list_events`: filtri `status`/`city`, default paginazione, `total` prima della paginazione.
    - _Requirements: 5.1–5.6_

- [ ] 6. Backend di persistenza
  - `infrastructure/repositories/`: `MemoryEventRepository`, `JsonEventRepository` (`DATA_DIR/events.json`, scrittura atomica), `SqliteEventRepository` (`DATA_DIR/events.db`) e `factory.build_repository(config)`.
  - _Requirements: Standard di piattaforma (selezione backend); 5.x_

- [ ] 7. Client HTTP verso user-service
  - `infrastructure/users_http.py`: `HttpUserDirectory` con `requests`, `GET {USER_SERVICE_URL}/api/v1/users/{id}` e **timeout esplicito 2s**.
  - `200` -> ruolo; `404` -> None; `RequestException`/`5xx` -> `DependencyUnavailable`.
  - _Requirements: REQ-EVT-B01, REQ-EVT-B02, REQ-EVT-B05_

- [ ] 8. HTTP: serializzazione, mapping errori e rotte
  - `entrypoints/http/errors.py`: mapping eccezioni -> struttura d'errore uniforme e status (400/404/422/503).
  - `entrypoints/http/blueprint.py`: rotte `POST/GET/GET{id}/PUT/PATCH/DELETE` su `/api/v1/events` (`Location` sul 201, `204` sul delete, paginazione, filtri `status`/`city`) e `GET /health` (indipendente da user-service).
  - _Requirements: 1.1, 1.4, 2.1, 2.2, 3.x, 4.x, 5.x, 11.1, 11.2, REQ-EVT-B01, REQ-EVT-B02, REQ-EVT-B04, REQ-EVT-B05_

- [ ] 9. Wiring finale (composition root)
  - `app.py`: `create_app`/`load_config`, `build_repository`, `HttpUserDirectory(USER_SERVICE_URL)`, `EventService`, registrazione blueprint + error handler, avvio su `PORT`.
  - Dichiarare `event` in `services.yaml` per la suite di integrazione.
  - _Requirements: Standard di piattaforma (PORT, selezione backend, USER_SERVICE_URL)_

- [ ] 10. Unit test del dominio (EventService)
  - `tests/`: casi d'uso con `MemoryEventRepository` e `FakeUserDirectory` (organizzatore valido/ruolo errato/non trovato/dipendenza offline).
  - Verificare default `status=draft`, coerenza date (REQ-EVT-B03), transizioni (REQ-EVT-B04), REFERENCE_NOT_FOUND/INVALID_ORGANIZER/DEPENDENCY_UNAVAILABLE.
  - _Requirements: 1.x, 2.x, 3.x, 4.x, 5.x, REQ-EVT-B01..B05_

- [ ] 11. Unit test dei backend di persistenza (parametrizzati)
  - Suite parametrizzata sui tre backend con `tmp_path`: CRUD, filtri `status`/`city`, paginazione, persistenza.
  - _Requirements: 5.x_

- [ ] 12. Unit test del client user-service (responses)
  - Mock delle chiamate `requests` con **`responses`**: 200 (ruolo), 404 (None), 5xx e connessione non disponibile -> `DependencyUnavailable`; verifica del timeout 2s.
  - _Requirements: REQ-EVT-B01, REQ-EVT-B02, REQ-EVT-B05_

- [ ] 13. Unit test HTTP + validazione contratto
  - Test con il test client di Flask (con `UserDirectory` doppio) e `assert_matches_contract` contro `event-service.yaml`: 201/Location, 400, 404, 422 (`VALIDATION_ERROR`/`REFERENCE_NOT_FOUND`/`INVALID_ORGANIZER`/`INVALID_STATUS_TRANSITION`), 503 (`DEPENDENCY_UNAVAILABLE`), paginazione e filtri.
  - Coverage con soglia `--cov-fail-under=80`.
  - _Requirements: tutti i precedenti (conformità al contratto e coverage ≥ 80%)_

- [ ] 14. Accettazione (opzionale, richiede services.yaml)
  - Eseguire `tests/integration/test_event.py` (IT-E01..IT-E08) con `user` ed `event` dichiarati in `services.yaml`, inclusa la resilienza (IT-E08 -> 503).
  - _Requirements: REQ-EVT-B01..B05 (verifica end-to-end)_
