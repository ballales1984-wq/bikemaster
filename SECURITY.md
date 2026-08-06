# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Se trovi una vulnerabilità di sicurezza in BikeMaster, ti preghiamo di
segnalarla privatamente invece di aprire una issue pubblica.

**Email:** security@bikemaster.example (sostituire con il canale ufficiale)

Includi nella segnalazione:
- Descrizione della vulnerabilità
- Passi per riprodurre
- Impatto potenziale
- eventuali suggerimenti per la mitigazione

Risponderemo entro 48 ore e forniremo aggiornamenti sul progresso della
risoluzione.

## Security Best Practices

- **Non committare segreti**: API keys, token, password non devono mai essere
  inclusi nel repository. Usa variabili d'ambiente e secret manager.
- **Dipendenze**: aggiorna regolarmente le dipendenze Python e Node.js per
  ridurre l'esposizione a vulnerabilità note.
- **OAuth**: usa sempre HTTPS in produzione; gli OAuth callback devono essere
  protetti e con validazione dello state parameter.
- **CORS**: configura `CORS_ORIGINS` in produzione per permettere solo domini
  autorizzati.
- **Database**: usa connessioni TLS a PostgreSQL in produzione; ruota le
  credenziali periodicamente.
