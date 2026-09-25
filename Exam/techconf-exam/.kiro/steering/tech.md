# Stack Tecnologico

## Linguaggio e runtime
- **Python 3.12** come unica versione di riferimento per tutti i servizi.

## Framework e librerie applicative
- **Flask** per l'esposizione delle API HTTP (entrypoints).
- **requests** per le chiamate HTTP tra servizi e verso sistemi esterni.

## Testing
- **pytest** come test runner per unit e integration test.
- **responses** per il mocking delle chiamate HTTP effettuate con `requests` nei test.

## Persistenza
La persistenza si basa esclusivamente sulla **libreria standard** di Python, con backend intercambiabili:
- **Memory**: store in memoria (dizionari/strutture native), utile per test e sviluppo rapido.
- **JSON**: persistenza su file `.json` tramite il modulo `json`.
- **SQLite**: persistenza relazionale tramite il modulo `sqlite3`.

Il backend di persistenza deve essere selezionabile via configurazione, senza introdurre dipendenze esterne (no ORM di terze parti).

## Linee guida
- Nessuna dipendenza esterna oltre a Flask, requests, pytest e responses.
- Il codice deve essere compatibile con l'interprete standard CPython 3.12.
- Preferire soluzioni della standard library rispetto a librerie di terze parti quando possibile.
