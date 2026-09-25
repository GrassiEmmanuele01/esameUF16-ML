# Implementation Plan — user-service

Piano di sviluppo incrementale per lo `user-service`. I task sono atomici, sequenziali e ciascuno indica i requisiti coperti (vedi `requirements.md`) e si basa sul `design.md`. Ogni task lascia il codice in uno stato compilabile e testabile.

- [ ] 1. Setup del servizio e configurazione
  - Creare lo scheletro `services/user/` secondo la struttura Clean Architecture: cartelle `domain/`, `infrastructure/persistence/`, `entrypoints/http/`, `tests/` con i relativi `__init__.py`.
  - Implementare `config.py` che legge `PORT` (default `5001`), `STORAGE_BACKEND` (`memory`|`json`|`sqlite`, default `memory`) e `DATA_DIR` (default `./data`) dall'ambiente.
  - Creare `app.py` come composition root minimale (Flask app factory) che verrà completato al task 8.
  - _Requirements: Standard di piattaforma (PORT, base path); Requirement 8 (health, completato al task 7)_

- [ ] 2. Entità di dominio ed eccezioni
  - Implementare in `domain/models.py` l'entità `User` con i campi `id`, `first_name`, `last_name`, `email`, `company`, `role`, `created_at`, `updated_at` e i valori di default (`role=attendee`, `company=null`).
  - Implementare in `domain/errors.py` le eccezioni di dominio: `MalformedJson`, `UserNotFound`, `EmailAlreadyExists`, `ValidationError`.
  - Aggiungere utility per generazione UUID v4 lato server e timestamp ISO 8601 UTC (riuso da `packages/common/` se disponibile).
  - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [ ] 3. Interfaccia UserRepository (astrazione di persistenza)
  - Definire in `domain/repository.py` l'interfaccia astratta `UserRepository` (`abc.ABC`) con i metodi `add`, `get`, `find_by_email`, `update`, `delete` e `list(role, email, page, page_size) -> (items, total)`.
  - Documentare che `find_by_email` e i filtri operano sull'email normalizzata (minuscolo) per supportare l'univocità case-insensitive.
  - _Requirements: REQ-USR-B01, REQ-USR-B03_

- [ ] 4. Casi d'uso UserService (logica di dominio)
  - Implementare in `domain/service.py` la classe `UserService` che dipende solo da `UserRepository`.
  - 4.1 `create_user`: validazione vincoli, normalizzazione email in minuscolo, controllo univocità case-insensitive, default `role`/`company`, generazione `id` UUID v4, `created_at`/`updated_at` allo stesso istante ISO 8601 UTC.
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, REQ-USR-B01, REQ-USR-B02_
  - 4.2 `get_user` / `delete_user`: recupero ed eliminazione con `UserNotFound` se assente.
    - _Requirements: 2.1, 2.2, 4.1, 4.2_
  - 4.3 `replace_user` (PUT) e `update_user` (PATCH): ri-validazione, normalizzazione email, controllo univocità escludendo l'utente stesso, aggiornamento `updated_at` mantenendo `id`/`created_at`.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, REQ-USR-B01, REQ-USR-B02_
  - 4.4 `list_users`: filtri `role`/`email` (email case-insensitive), default `page=1`/`page_size=20`, `total` calcolato sull'insieme filtrato prima della paginazione, validazione parametri.
    - _Requirements: REQ-USR-B03 (7.1–7.7)_

- [ ] 5. Backend di persistenza (implementazioni concrete)
  - 5.1 `infrastructure/persistence/memory.py`: `MemoryUserRepository` basato su `dict` con indice sull'email normalizzata.
    - _Requirements: REQ-USR-B01, REQ-USR-B02, REQ-USR-B03_
  - 5.2 `infrastructure/persistence/json_store.py`: `JsonUserRepository` su file `.json` in `DATA_DIR`, con scrittura atomica (file temporaneo + replace).
    - _Requirements: REQ-USR-B01, REQ-USR-B02, REQ-USR-B03_
  - 5.3 `infrastructure/persistence/sqlite_store.py`: `SqliteUserRepository` su database `sqlite3` in `DATA_DIR`, con indice univoco sull'email normalizzata.
    - _Requirements: REQ-USR-B01, REQ-USR-B02, REQ-USR-B03_
  - 5.4 `infrastructure/persistence/factory.py`: `build_repository(config)` che seleziona il backend da `STORAGE_BACKEND` e crea `DATA_DIR` per JSON/SQLite.
    - _Requirements: Standard di piattaforma (selezione backend via configurazione)_

- [ ] 6. Serializzazione e mapping errori (HTTP adapter)
  - Implementare in `entrypoints/http/` le funzioni di serializzazione dell'entità `User` verso lo schema `User` del contratto (date ISO 8601 UTC, `company` nullable).
  - Implementare il mapping delle eccezioni di dominio nella struttura d'errore uniforme `{ "error": { "code": <UPPER_SNAKE>, "message": ... } }` con i relativi status code (400/404/409/422).
  - _Requirements: 1.6, 1.7, 2.2, 3.4, 3.5, 4.2, REQ-USR-B01_

- [ ] 7. Rotte HTTP (UserBlueprint)
  - Implementare in `entrypoints/http/blueprint.py` il `UserBlueprint` registrato su `/api/v1/users`.
  - 7.1 `POST /api/v1/users`: creazione con `201`, body dell'utente creato e header `Location`; `400` su JSON malformato; `422` su validazione; `409` su email duplicata.
    - _Requirements: 1.1, 1.6, 1.7, REQ-USR-B01_
  - 7.2 `GET /api/v1/users` e `GET /api/v1/users/{id}`: lista paginata con filtri e dettaglio, `404` se assente.
    - _Requirements: 2.1, 2.2, REQ-USR-B03_
  - 7.3 `PUT` e `PATCH /api/v1/users/{id}`: aggiornamento con `200`, `404`, `409`, `422`.
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, REQ-USR-B01_
  - 7.4 `DELETE /api/v1/users/{id}`: `204` senza corpo, `404` se assente.
    - _Requirements: 4.1, 4.2_
  - 7.5 `GET /health`: risposta `{ "status": "ok", "service": "user-service" }`.
    - _Requirements: 8.1_

- [ ] 8. Wiring finale (composition root)
  - Completare `app.py`: leggere la configurazione, costruire il repository concreto via `build_repository`, istanziare `UserService`, registrare `UserBlueprint` e avviare Flask sulla porta `PORT`.
  - Registrare il servizio in `services.yaml` per la suite di integrazione.
  - _Requirements: Standard di piattaforma (PORT, selezione backend)_

- [ ] 9. Unit test del dominio (UserService)
  - Scrivere in `services/user/tests/` gli unit test dei casi d'uso usando `MemoryUserRepository`: default, validazioni (422), `404`/`409`, aggiornamento `updated_at`, filtri e calcolo di `total`.
  - Verificare esplicitamente univocità email case-insensitive e normalizzazione in minuscolo.
  - _Requirements: 1.1–1.7, 2.x, 3.x, 4.x, REQ-USR-B01, REQ-USR-B02, REQ-USR-B03_

- [ ] 10. Unit test dei backend di persistenza (parametrizzati)
  - Scrivere una suite parametrizzata riutilizzata sui tre backend (Memory, JSON, SQLite) per garantire comportamento identico; JSON/SQLite usano una `DATA_DIR` temporanea (`tmp_path`).
  - Coprire round-trip CRUD, univocità sull'email normalizzata e filtri/paginazione.
  - _Requirements: REQ-USR-B01, REQ-USR-B02, REQ-USR-B03_

- [ ] 11. Unit test dell'entrypoint HTTP (Flask test client)
  - Verificare routing, status code, header `Location`, body malformato (`400`) e mapping degli errori con il test client di Flask.
  - _Requirements: 1.1, 1.6, 1.7, 2.1, 2.2, 3.x, 4.x, 8.1_

- [ ] 12. Copertura e validazione del contratto
  - Configurare l'esecuzione di `pytest` con coverage sul package del servizio e soglia `--cov-fail-under=80`.
  - Eseguire la suite di accettazione in `tests/integration/` che valida le risposte con `assert_matches_contract` di `contracts/validator.py` contro `contracts/openapi/user-service.yaml`.
  - _Requirements: tutti i precedenti (verifica di conformità al contratto e coverage ≥ 80%)_
