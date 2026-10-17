## MODIFIED Requirements

### Requirement: Endpoint de salud
La API SHALL exponer `GET /health`, fuera del prefijo `/v1`, que informe que el servicio está activo.

#### Scenario: Servicio activo
- **WHEN** un cliente pide `GET /health` con la API en marcha
- **THEN** la API responde 200
