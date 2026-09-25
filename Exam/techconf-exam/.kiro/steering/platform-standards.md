# Standard di Piattaforma

Regole trasversali valide per tutti i servizi TechConf. Ogni servizio deve rispettarle per garantire coerenza e interoperabilità.

## Routing e versioning
- Base path di ogni risorsa: `/api/v1/<risorsa>`.
- Il versioning dell'API è espresso nel path (`v1`).
- Esempi: `/api/v1/events`, `/api/v1/users`, `/api/v1/registrations`, `/api/v1/feedback`, `/api/v1/notifications`.

## Identificatori
- Gli ID delle risorse sono **UUID v4** generati **lato server**.
- Il client non fornisce mai l'ID in fase di creazione.

## Date e orari
- Tutte le date/orari sono in formato **ISO 8601** con timezone **UTC** (es. `2026-09-25T14:30:00Z`).
- Nessuna data deve essere serializzata senza indicazione esplicita del fuso orario UTC.

## Paginazione
Le collezioni sono paginate tramite parametri di query:
- `page`: numero di pagina (1-based).
- `page_size`: numero di elementi per pagina.
- La risposta include `total`: numero totale di elementi disponibili.

Esempio di risposta:
```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

## Struttura degli errori
Gli errori seguono una struttura uniforme:
```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "Descrizione leggibile dell'errore"
}
```
- `code`: identificatore in **UPPER_SNAKE_CASE**.
- `message`: messaggio human-readable.

## Chiamate HTTP
- Tutte le chiamate HTTP tra servizi usano un **timeout di 2 secondi**.
- Il timeout deve essere sempre impostato esplicitamente sulle chiamate `requests`.

## Configurazione di rete
- La porta di ascolto di ciascun servizio è letta dalla variabile d'ambiente **`PORT`**.
- Il servizio non deve avere porte hardcoded al di fuori di un eventuale default di fallback.
