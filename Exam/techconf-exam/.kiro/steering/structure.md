# Struttura del Monorepo (Clean Architecture)

Il progetto è organizzato come monorepo con codice condiviso e servizi indipendenti, seguendo i principi della Clean Architecture: le dipendenze puntano sempre verso il dominio, mai verso l'infrastruttura.

## Layout di alto livello

```
packages/
  common/            # Codice condiviso tra tutti i servizi
services/
  <service_name>/    # Un servizio per dominio (event, user, registration, feedback, notification)
```

## packages/common/
Contiene astrazioni, utility e contratti riutilizzabili da tutti i servizi:
- Tipi e value object condivisi.
- Utility per errori standard, paginazione, gestione date ISO 8601 UTC, generazione UUID v4.
- Client HTTP con timeout preconfigurato (2s).
- Interfacce base per i repository di persistenza.

Non deve dipendere da alcun servizio specifico.

## services/<service_name>/
Ogni servizio è autonomo e rispetta la separazione a livelli:

```
services/<service_name>/
  app.py                 # Composition root: wiring e avvio dell'applicazione Flask
  config.py              # Configurazione (PORT, backend di persistenza, ecc.)
  domain/                # Entità, value object e regole di business (nessuna dipendenza esterna)
  infrastructure/        # Implementazioni concrete: persistenza (Memory/JSON/SQLite), client HTTP
  entrypoints/
    http/                # Adapter HTTP: route Flask, serializzazione, mapping errori
  tests/                 # Unit e integration test del servizio
```

## Regole di dipendenza (Clean Architecture)
- **domain/** non dipende da nessun altro layer. Contiene le regole di business pure.
- **infrastructure/** dipende da `domain/` (implementa le sue interfacce), mai il contrario.
- **entrypoints/http/** dipende da `domain/` (casi d'uso) e usa `infrastructure/` solo tramite wiring in `app.py`.
- **app.py** è il composition root: conosce tutti i layer e collega le implementazioni concrete alle astrazioni.
- **config.py** fornisce la configurazione a partire dall'ambiente (es. `PORT`, selezione backend di persistenza).

## Convenzioni
- Un servizio per dominio funzionale, nominato in modo coerente con la risorsa (es. `event`, `user`).
- Il codice condiviso vive in `packages/common/`; evitare duplicazioni tra servizi.
- I test di ciascun servizio risiedono nella sua cartella `tests/`.
