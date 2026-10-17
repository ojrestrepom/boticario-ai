## MODIFIED Requirements

### Requirement: Arranque con un solo comando
`docker compose up` SHALL arrancar la API publicando el puerto 8080 del anfitrión por defecto, con datos reales del catálogo.

#### Scenario: Salud y datos
- **WHEN** se ejecuta `docker compose up` y se consulta `http://localhost:8080/health`
- **THEN** la respuesta es 200

#### Scenario: Búsqueda real
- **WHEN** se consulta `/v1/plants?q=lavand` y `/v1/plants/lavandula-angustifolia`
- **THEN** ambas responden 200 y devuelven el listado y el detalle con datos del catálogo real

### Requirement: Configuración por entorno
El puerto publicado y el puerto de escucha SHALL poder cambiarse con la variable `PORT`, y el nivel de logs con `RUST_LOG`. La dirección de escucha SHALL ser siempre `0.0.0.0` dentro del contenedor y SHALL NOT depender de la configuración del usuario.

#### Scenario: Otro puerto
- **WHEN** se ejecuta `PORT=9090 docker compose up` y se consulta `http://localhost:9090/health`
- **THEN** la respuesta es 200 y el puerto 8080 del anfitrión no está publicado

#### Scenario: Otro nivel de logs
- **WHEN** se ejecuta el contenedor con `RUST_LOG=warn` y, por separado, con el valor por defecto
- **THEN** con `warn` el log no contiene la línea INFO de arranque («escuchando») y con el valor por defecto sí la contiene
