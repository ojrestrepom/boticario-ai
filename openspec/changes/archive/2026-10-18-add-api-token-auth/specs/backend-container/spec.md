# Spec Delta

## MODIFIED Requirements

### Requirement: Imagen autocontenida
La imagen SHALL contener la API y el catálogo ya construido, y SHALL servir sin acceso a la red. La imagen final SHALL NOT incluir la base cruda, el ZIP del dataset, el toolchain de Rust ni el código fuente, y SHALL NOT incluir ningún token de API: los tokens llegan siempre por el entorno en tiempo de ejecución.

#### Scenario: Servir sin red
- **WHEN** se ejecuta el contenedor sin acceso a la red y con `API_TOKENS` definido, y se consulta `GET /v1/plants/lavandula-angustifolia` con un token válido
- **THEN** la API responde 200 con el detalle de la planta

#### Scenario: Contenido mínimo
- **WHEN** se inspecciona el sistema de archivos de la imagen final
- **THEN** no existe la base cruda, el ZIP, `cargo`, `rustc` ni el código fuente, y sí existen el binario de la API y la base del catálogo

#### Scenario: Sin tokens en la imagen
- **WHEN** se inspeccionan las capas y la configuración de la imagen
- **THEN** no contienen ningún valor de `API_TOKENS` y la variable no tiene valor por defecto

### Requirement: Arranque con un solo comando
`docker compose up` SHALL arrancar la API publicando el puerto 8080 del anfitrión por defecto, con datos reales del catálogo, siempre que `API_TOKENS` esté definido en el entorno o en el archivo `.env` de la raíz. Sin `API_TOKENS`, `docker compose up` SHALL fallar con un mensaje que indica cómo definirlo y SHALL NOT arrancar una API sin autorización.

#### Scenario: Salud y datos
- **WHEN** se ejecuta `docker compose up` con `API_TOKENS` definido y se consulta `http://localhost:8080/health`
- **THEN** la respuesta es 200

#### Scenario: Búsqueda real
- **WHEN** se consulta `/v1/plants?q=lavand` y `/v1/plants/lavandula-angustifolia` con un token válido
- **THEN** ambas responden 200 y devuelven el listado y el detalle con datos del catálogo real

#### Scenario: Sin token configurado
- **WHEN** se ejecuta `docker compose up` sin `API_TOKENS` en el entorno ni en `.env`
- **THEN** falla antes de arrancar el contenedor con un mensaje que nombra `API_TOKENS`

#### Scenario: Consulta sin token
- **WHEN** se consulta `/v1/plants` sin token en el contenedor en marcha
- **THEN** la respuesta es 401

### Requirement: Configuración por entorno
El puerto publicado y el puerto de escucha SHALL poder cambiarse con la variable `PORT`, el nivel de logs con `RUST_LOG` y los tokens válidos con `API_TOKENS`. La dirección de escucha SHALL ser siempre `0.0.0.0` dentro del contenedor y SHALL NOT depender de la configuración del usuario.

#### Scenario: Otro puerto
- **WHEN** se ejecuta `PORT=9090 docker compose up` y se consulta `http://localhost:9090/health`
- **THEN** la respuesta es 200 y el puerto 8080 del anfitrión no está publicado

#### Scenario: Otro nivel de logs
- **WHEN** se ejecuta el contenedor con `RUST_LOG=warn` y, por separado, con el valor por defecto
- **THEN** con `warn` el log no contiene la línea INFO de arranque («escuchando») y con el valor por defecto sí la contiene

#### Scenario: Tokens por entorno
- **WHEN** se ejecuta el contenedor con `API_TOKENS` de dos tokens válidos
- **THEN** una petición a `/v1/plants` con cualquiera de los dos responde 200 y con otro valor responde 401
