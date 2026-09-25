# Design — user-service

## Panoramica

Lo `user-service` è il registro degli utenti della piattaforma TechConf (partecipanti, relatori, organizzatori). Espone un'API REST su base path `/api/v1/users`, ascolta sulla porta letta dalla variabile d'ambiente `PORT` (default `5001`) ed è la fonte di verità per i dati anagrafici (`first_name`, `last_name`, `email`, `company`, `role`).

Il design segue i principi della **Clean Architecture**: le dipendenze puntano sempre verso il dominio, mai verso l'infrastruttura. Il servizio non introduce dipendenze esterne oltre a Flask (esposizione HTTP) e alla standard library di Python 3.12 (persistenza), coerentemente con lo stack di piattaforma.

Il contratto HTTP autoritativo è definito in [`contracts/openapi/user-service.yaml`](../../../contracts/openapi/user-service.yaml): tutte le route, gli status code, gli schemi di request/response e la forma degli errori derivano da quel documento OpenAPI 3.0.

## Architettura a livelli

```
services/user/
  app.py                 # Composition root: wiring Flask + selezione backend
  config.py              # PORT, STORAGE_BACKEND, DATA_DIR
  domain/
    models.py            # Entità User, value object, regole di business pure
    service.py           # UserService: casi d'uso (create/get/list/update/delete)
    repository.py        # UserRepository: interfaccia astratta di persistenza
    errors.py            # Eccezioni di dominio (NotFound, EmailConflict, Validation)
  infrastructure/
    persistence/
      memory.py          # MemoryUserRepository
      json_store.py      # JsonUserRepository (file .json in DATA_DIR)
      sqlite_store.py    # SqliteUserRepository (sqlite3 in DATA_DIR)
      factory.py         # build_repository(config) -> UserRepository
  entrypoints/
    http/
      blueprint.py       # UserBlueprint: route Flask, serializzazione, mapping errori
  tests/                 # Unit test del servizio
```

### Regole di dipendenza

- `domain/` non dipende da nessun altro layer. Contiene entità, casi d'uso e l'interfaccia `UserRepository`.
- `infrastructure/` dipende da `domain/` (implementa `UserRepository`), mai il contrario.
- `entrypoints/http/` dipende dai casi d'uso in `domain/` e non conosce l'implementazione concreta della persistenza.
- `app.py` è il composition root: legge la configurazione, costruisce il repository concreto e lo inietta nel `UserService`, che a sua volta viene collegato allo `UserBlueprint`.

```
UserBlueprint  ->  UserService  ->  UserRepository (interfaccia)
   (HTTP)          (casi d'uso)          ^
                                         |  implementata da
                        Memory / JSON / SQLite (infrastructure)
```

## Componenti principali

### UserBlueprint (entrypoints/http)

Flask `Blueprint` registrato sul base path `/api/v1/users`, più la route `/health`. Responsabilità:

- **Routing**: mappa le operazioni OpenAPI sui metodi HTTP.

  | Operazione OpenAPI | Metodo e path | Handler |
  |--------------------|---------------|---------|
  | `createUser` | `POST /api/v1/users` | crea utente, `201` + header `Location` |
  | `listUsers` | `GET /api/v1/users` | lista paginata con filtri `role`/`email` |
  | `getUser` | `GET /api/v1/users/{id}` | dettaglio utente |
  | `replaceUser` | `PUT /api/v1/users/{id}` | sostituzione |
  | `updateUser` | `PATCH /api/v1/users/{id}` | aggiornamento parziale |
  | `deleteUser` | `DELETE /api/v1/users/{id}` | eliminazione, `204` |
  | `health` | `GET /health` | `{ "status": "ok", "service": "user-service" }` |

- **Parsing e validazione input**: intercetta il body non-JSON restituendo `400 MALFORMED_JSON`; delega la validazione dei vincoli al dominio.
- **Serializzazione**: converte l'entità `User` nello schema `User` del contratto (date in ISO 8601 UTC, `company` nullable).
- **Mapping errori**: traduce le eccezioni di dominio negli status code e nel formato d'errore uniforme `{ "error": { "code": <UPPER_SNAKE>, "message": ... } }`.

  | Eccezione di dominio | Status | `code` |
  |----------------------|--------|--------|
  | `MalformedJson` | 400 | `MALFORMED_JSON` |
  | `UserNotFound` | 404 | `NOT_FOUND` |
  | `EmailAlreadyExists` | 409 | `EMAIL_ALREADY_EXISTS` |
  | `ValidationError` | 422 | `VALIDATION_ERROR` |

Il blueprint non contiene logica di business: si limita ad adattare HTTP ai casi d'uso.

### UserService (domain)

Contiene i casi d'uso ed è agnostico rispetto ad HTTP e alla persistenza. Dipende esclusivamente dall'interfaccia `UserRepository`. Responsabilità principali:

- **create_user(payload)**: valida i vincoli, normalizza l'email in minuscolo (REQ-USR-B02), verifica l'univocità case-insensitive (REQ-USR-B01), applica i default (`role=attendee`, `company=null`), genera `id` UUID v4 lato server e imposta `created_at`/`updated_at` allo stesso istante ISO 8601 UTC.
- **get_user(id)**: recupera l'utente o solleva `UserNotFound`.
- **list_users(page, page_size, role, email)**: applica i filtri, calcola `total` sull'insieme filtrato (prima della paginazione) e restituisce la pagina richiesta con i default `page=1`, `page_size=20`.
- **replace_user(id, payload)** / **update_user(id, payload)**: sostituzione totale (PUT) o parziale (PATCH), con ri-validazione, normalizzazione email, controllo univocità (escludendo l'utente stesso) e aggiornamento di `updated_at` mantenendo invariati `id` e `created_at`.
- **delete_user(id)**: elimina o solleva `UserNotFound`.

Le regole di validazione (lunghezze `first_name`/`last_name` 1–50, `company` ≤100, formato `email`, `role` nell'enum, rifiuto di campi non ammessi) e la logica dell'univocità email vivono qui, così da essere indipendenti dal framework HTTP e dal backend di persistenza.

### UserRepository (domain) e implementazioni (infrastructure)

`UserRepository` è l'interfaccia astratta (basata su `abc.ABC`) che definisce il contratto di persistenza, senza conoscere alcun backend concreto:

```python
class UserRepository(ABC):
    def add(self, user: User) -> None: ...
    def get(self, user_id: str) -> User | None: ...
    def find_by_email(self, email: str) -> User | None: ...   # confronto già normalizzato
    def update(self, user: User) -> None: ...
    def delete(self, user_id: str) -> bool: ...
    def list(self, *, role: str | None, email: str | None,
             page: int, page_size: int) -> tuple[list[User], int]: ...  # (items, total)
```

Il `UserService` dipende solo da questa astrazione; il backend concreto è scelto a runtime dal composition root, senza impatto sulla logica di dominio.

## Astrazione dei backend di persistenza

Il backend è selezionabile via configurazione (`STORAGE_BACKEND`) e costruito da `infrastructure/persistence/factory.py`. Sono previsti tre backend intercambiabili, tutti basati sulla sola standard library (nessun ORM di terze parti):

### 1. Memory (`MemoryUserRepository`)

- Store in memoria basato su un `dict` (chiave = `id`), con un indice ausiliario sull'email normalizzata per l'univocità.
- Nessuna persistenza tra riavvii: utile per test e sviluppo rapido. È il default.

### 2. JSON (`JsonUserRepository`)

- Persistenza su un file `.json` collocato in `DATA_DIR` (es. `DATA_DIR/users.json`), gestito con il modulo `json`.
- Ad ogni scrittura l'intero stato viene serializzato su file; in lettura viene caricato in memoria. Le scritture sono effettuate in modo atomico (scrittura su file temporaneo e sostituzione) per evitare corruzione.

### 3. SQLite (`SqliteUserRepository`)

- Persistenza relazionale tramite il modulo `sqlite3`, su un file di database in `DATA_DIR` (es. `DATA_DIR/users.db`).
- Tabella `users` con colonna `id` come chiave primaria e un indice univoco sull'email normalizzata, così da far rispettare l'univocità case-insensitive a livello di storage.

### Configurazione (`config.py`)

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `PORT` | Porta di ascolto del servizio | `5001` |
| `STORAGE_BACKEND` | `memory` \| `json` \| `sqlite` | `memory` |
| `DATA_DIR` | Directory dei file di persistenza (JSON/SQLite) | `./data` |

`build_repository(config)` legge `STORAGE_BACKEND`; per `json` e `sqlite` crea `DATA_DIR` se assente e istanzia il repository puntando al file corrispondente. Cambiare backend non richiede modifiche al dominio né agli entrypoint HTTP.

## Riferimento al contratto

Il file [`contracts/openapi/user-service.yaml`](../../../contracts/openapi/user-service.yaml) è l'unica fonte autoritativa dell'interfaccia HTTP. Il design vi si allinea su:

- **Schemi**: `UserCreate`, `UserUpdate`, `User`, `UserPage`, `Role`, `Error`, `Health` (con `additionalProperties: false`, motivo per cui il servizio rifiuta i campi non ammessi con `422`).
- **Status code** dichiarati per operazione (`201`, `200`, `204`, `400`, `404`, `409`, `422`).
- **Paginazione**: parametri `page` (≥1, default 1) e `page_size` (1–100, default 20) e risposta con `items`, `page`, `page_size`, `total`.
- **Identificatori e date**: `id` UUID v4 lato server, `created_at`/`updated_at` in ISO 8601 UTC.

Ogni scostamento dal contratto è considerato un difetto: il contratto prevale sull'implementazione.

## Strategia di test

### Unit test (pytest)

Risiedono in `services/user/tests/` ed esercitano ciascun layer in isolamento:

- **Dominio (`UserService`)**: casi d'uso e regole di business con un `MemoryUserRepository` come doppio di test veloce — default, univocità email case-insensitive, normalizzazione in minuscolo, validazioni (422), gestione `404`/`409`, filtri e calcolo di `total` sull'insieme filtrato.
- **Persistenza (`UserRepository`)**: una suite di test parametrizzata riutilizzata sui tre backend (Memory, JSON, SQLite) per garantire un comportamento identico; i backend JSON/SQLite usano una `DATA_DIR` temporanea (fixture `tmp_path`).
- **Entrypoint HTTP (`UserBlueprint`)**: test con il test client di Flask che verificano routing, status code, header `Location`, gestione del body malformato e mapping degli errori.

Le chiamate HTTP verso sistemi esterni (se presenti) vengono mockate con la libreria `responses`; il timeout esplicito di 2s sulle chiamate `requests` resta parte dello standard di piattaforma.

### Copertura (coverage ≥ 80%)

La copertura di riga è misurata con `pytest` (plugin `coverage`) sul package del servizio e deve essere **≥ 80%**. La soglia è pensata come gate: build/verifica falliscono se la copertura scende sotto la soglia.

```
pytest services/user/tests --cov=services/user --cov-report=term-missing --cov-fail-under=80
```

### Validazione del contratto

Oltre agli unit test, il servizio è verificato contro il contratto OpenAPI:

- La suite di accettazione in `tests/integration/` avvia il servizio (via `services.yaml`) e valida ogni risposta con `assert_matches_contract(...)` di [`contracts/validator.py`](../../../contracts/validator.py), che confronta status code e body con lo schema dichiarato in `user-service.yaml`.
- I test coprono i percorsi felici e i casi d'errore (`400`, `404`, `409`, `422`), assicurando che status code, header e forma del payload rispettino il contratto.

Il servizio è considerato conforme quando: gli unit test passano, la copertura è ≥ 80% e tutte le risposte superano la validazione del contratto.
