# Documentazione di Riferimento — Completa

Riferimento tecnico esaustivo di BikeMaster, generato direttamente dal codice sorgente (`bike_analyzer/`) per garantire accuratezza.

| Documento | Contenuto |
|---|---|
| [api-reference.md](./api-reference.md) | Tutti i 138 endpoint REST (router, admin, BM2) con metodo, path e autenticazione |
| [database-schema.md](./database-schema.md) | Schema completo del database: tabelle, colonne, indici, migrazioni Alembic, multi-tenancy |
| [domain-models.md](./domain-models.md) | Entità di dominio (core) e modelli BikeMaster 2.0 (BM2) campo per campo |
| [configuration.md](./configuration.md) | Tutte le variabili d'ambiente / impostazioni (`settings.py`) |
| [engines-and-analytics.md](./engines-and-analytics.md) | Engine BM2 (9 algoritmi) e motore analytics classico |

## Come è organizzata

- **Overview e visione:** [../../README.md](../../README.md) (root) e [../ARCHITECTURE.md](../ARCHITECTURE.md)
- **Riferimenti puntuali:** questa cartella (`docs/reference/`)
- **BM2 (approfondimenti):** [../bm2/](../bm2/), [../BM2_ENGINE_ARCHITECTURE.md](../BM2_ENGINE_ARCHITECTURE.md), [../BM2_ALGORITHMS.md](../BM2_ALGORITHMS.md)
- **Guide operative:** [../DEVELOPMENT.md](../DEVELOPMENT.md), [../deployment.md](../deployment.md), [../testing.md](../testing.md)

> I documenti in questa cartella sono derivati dal codice reale. In caso di divergenze note tra layer (es. schema sync SQLite vs Alembic/PostgreSQL) sono segnalate esplicitamente nei singoli documenti.
