## Purpose

Define las verificaciones automáticas del backend en integración continua: formato, lint, pruebas y coherencia del documento OpenAPI, con el mismo toolchain que usa el desarrollo local y la imagen, y reutilizables como puerta previa del despliegue.

## ADDED Requirements

### Requirement: Verificaciones del backend en CI
La integración continua SHALL ejecutar sobre el workspace del backend la comprobación de formato, el análisis estático con las advertencias tratadas como errores y las pruebas de todos los crates, todo con el `Cargo.lock` versionado (`--locked`). Las pruebas SHALL ejecutarse sin red y sin el dataset descargado: las pruebas que necesitan `data/build/` SHALL seguir marcadas como ignoradas. Un fallo de cualquier verificación SHALL hacer fallar la ejecución. Las pruebas incluidas SHALL comprobar que `backend/openapi.json` coincide con el documento generado por el código y que la versión de Rust del `Dockerfile` coincide con la de `mise.toml`.

#### Scenario: Backend en orden
- **WHEN** el formato, el lint y las pruebas del backend pasan
- **THEN** la ejecución termina en éxito

#### Scenario: Código sin formatear
- **WHEN** un archivo Rust del backend no cumple el formato de `cargo fmt`
- **THEN** la ejecución falla en la comprobación de formato

#### Scenario: Advertencia de lint
- **WHEN** `clippy` emite una advertencia sobre cualquier destino del workspace
- **THEN** la ejecución falla

#### Scenario: Prueba fallida
- **WHEN** una prueba del workspace falla
- **THEN** la ejecución falla

#### Scenario: Documento OpenAPI desactualizado
- **WHEN** el código cambia el contrato de la API y `backend/openapi.json` no se regenera
- **THEN** la ejecución falla con el mensaje que indica cómo regenerarlo

#### Scenario: Versiones de Rust divergentes
- **WHEN** la versión de Rust del `Dockerfile` difiere de la de `mise.toml`
- **THEN** la ejecución falla indicando ambas versiones

#### Scenario: Sin red ni dataset
- **WHEN** la ejecución corre en un entorno limpio sin `data/build/` y sin acceso a las fuentes de datos
- **THEN** las pruebas pasan y las que necesitan el dataset figuran como ignoradas

### Requirement: Toolchain de CI idéntico al fijado
La integración continua SHALL instalar la versión de Rust fijada en `mise.toml` y SHALL NOT repetir esa versión en el workflow. SHALL disponer de los componentes de formato y lint con esa misma versión. Los comandos SHALL ejecutarse con ese toolchain y no con el que traiga el runner.

#### Scenario: Versión efectiva
- **WHEN** la ejecución corre sus comandos de Cargo
- **THEN** el compilador efectivo es la versión que fija `mise.toml`

#### Scenario: Cambio de versión en un solo sitio
- **WHEN** se cambia la versión de Rust en `mise.toml` y en el `Dockerfile`
- **THEN** la integración continua usa la nueva versión sin editar el workflow

### Requirement: Disparadores y reutilización de las verificaciones
Las verificaciones SHALL definirse en un único workflow que pueda ejecutarse por sí mismo y ser invocado por otro workflow. SHALL ejecutarse en cada `pull_request` y en cada `push` a una rama distinta de `main` que modifique el backend, `data/migrations/`, el `Dockerfile`, `mise.toml` o el propio workflow, y SHALL NOT ejecutarse por cambios que solo afecten a la app, la documentación u OpenSpec. En `main` SHALL ejecutarse a través del workflow de despliegue, de modo que un mismo `push` a `main` ejecute las verificaciones una sola vez.

#### Scenario: Pull request con cambio del backend
- **WHEN** se abre o se actualiza un pull request que modifica `backend/`
- **THEN** las verificaciones se ejecutan y su resultado queda en el pull request

#### Scenario: Rama de trabajo
- **WHEN** se hace `push` a una rama distinta de `main` con un cambio bajo `backend/`
- **THEN** las verificaciones se ejecutan

#### Scenario: Cambio ajeno al backend
- **WHEN** un `push` o un pull request solo modifica `app/`, `docs/` u `openspec/`
- **THEN** las verificaciones no se ejecutan

#### Scenario: Sin ejecución duplicada en main
- **WHEN** se hace `push` a `main` con un cambio del backend
- **THEN** las verificaciones se ejecutan una sola vez, dentro del workflow de despliegue

#### Scenario: Ejecución obsoleta
- **WHEN** llega un nuevo `push` a una rama distinta de `main` mientras sus verificaciones anteriores siguen en curso
- **THEN** las ejecuciones anteriores de esa rama se cancelan

### Requirement: Permisos mínimos y acciones fijadas en la CI del backend
El workflow de verificaciones SHALL limitar sus permisos a la lectura del contenido del repositorio y SHALL NOT solicitar `id-token: write` ni acceder a credenciales de Google Cloud. Cada acción de terceros SHALL fijarse por SHA con un comentario de versión. SHALL tener un tiempo máximo de ejecución.

#### Scenario: Sin credenciales de nube
- **WHEN** se revisa el workflow de verificaciones
- **THEN** sus permisos son solo `contents: read` y no usa secretos de Google Cloud

#### Scenario: Acciones fijadas
- **WHEN** se revisa el workflow de verificaciones
- **THEN** cada acción de terceros está fijada por SHA con un comentario de versión

#### Scenario: Tiempo máximo
- **WHEN** una ejecución se queda colgada
- **THEN** el límite de tiempo del job la termina en fallo
