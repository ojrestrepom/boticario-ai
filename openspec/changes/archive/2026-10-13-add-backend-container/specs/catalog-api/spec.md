# Spec Delta

## ADDED Requirements

### Requirement: Apagado ordenado con tiempo máximo
Al recibir SIGTERM o Ctrl-C, la API SHALL dejar de aceptar conexiones nuevas y esperar a las peticiones en curso como máximo 2 s. La API SHALL terminar con código 0 tanto si todas las peticiones terminaron como si se agotó el plazo. Al terminar SHALL registrar «apagado completado»; si se agotó el plazo, SHALL registrar antes un aviso de apagado forzado por conexiones abiertas tras 2 s.

#### Scenario: Conexiones inactivas
- **WHEN** la API no tiene peticiones en curso y recibe SIGTERM
- **THEN** termina de inmediato con código 0 y el log contiene «apagado completado»

#### Scenario: Conexión colgada
- **WHEN** un cliente mantiene una conexión abierta con cabeceras incompletas y la API recibe SIGTERM
- **THEN** la API termina al agotarse el plazo de 2 s con código 0, y el log contiene el aviso de apagado forzado y «apagado completado»
