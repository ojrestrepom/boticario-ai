# Spec Delta

## MODIFIED Requirements

### Requirement: Imagen autocontenida
La imagen SHALL contener la API y el catálogo ya construido, y SHALL servir sin acceso a la red. La imagen final SHALL NOT incluir la base cruda, el ZIP del dataset, el toolchain de Rust ni el código fuente.

#### Scenario: Servir sin red
- **WHEN** se ejecuta el contenedor sin acceso a la red y se consulta `GET /v1/plants/lavandula-angustifolia`
- **THEN** la API responde 200 con el detalle de la planta

#### Scenario: Contenido mínimo
- **WHEN** se inspecciona el sistema de archivos de la imagen final
- **THEN** no existe la base cruda, el ZIP, `cargo`, `rustc` ni el código fuente, y sí existen el binario de la API y la base del catálogo

### Requirement: Arranque con un solo comando
`docker compose up` SHALL arrancar la API publicando el puerto 8080 del anfitrión por defecto, con datos reales del catálogo.

#### Scenario: Salud y datos
- **WHEN** se ejecuta `docker compose up` y se consulta `http://localhost:8080/healthz`
- **THEN** la respuesta es 200

#### Scenario: Búsqueda real
- **WHEN** se consulta `/v1/plants?q=lavand` y `/v1/plants/lavandula-angustifolia`
- **THEN** ambas responden 200 y devuelven el listado y el detalle con datos del catálogo real
