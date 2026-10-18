# Proposal

## Why

Hoy el backend se despliega en Cloud Run en cada push a `main` sin que corra ninguna prueba antes: un `cargo test` en rojo, un `clippy` con advertencias o un `openapi.json` desactualizado llegan a producción, y el diseño de `deploy-backend-cloud-run` dejó anotado ese riesgo y la CI del backend como cambio posterior. Además, los logs de la API llegan a Cloud Logging con códigos de color ANSI (`^[[2m2026-10-17T03:34:39Z^[[0m ^[[32m INFO^[[0m …`) porque `tracing_subscriber::fmt()` los emite aunque stdout no sea una terminal, y eso estorba al leerlos y al filtrarlos.

## What Changes

- Nuevo workflow reutilizable `.github/workflows/backend-ci.yml` que instala el Rust exacto de `mise.toml` y corre, desde `backend/`, `cargo fmt --check`, `cargo clippy --workspace --all-targets --locked -- -D warnings` y `cargo test --workspace --locked`. Corre en `pull_request` y en `push` a ramas distintas de `main` (con filtros de ruta, como `flutter.yml`) y se puede invocar con `workflow_call`.
- `.github/workflows/deploy-backend.yml` llama a ese workflow como job previo (`verify`) y el job `deploy` pasa a depender de él con `needs`: si las verificaciones fallan, no se construye ni se publica imagen ni se despliega. Así las verificaciones corren una sola vez por push a `main` y la definición vive en un solo sitio. Los permisos pasan a ser por job: `verify` solo lee el repositorio y `deploy` conserva `id-token: write`.
- `mise.toml` se añade a los filtros de ruta del despliegue, porque cambia el compilador de la imagen y de las pruebas.
- La API deja de escribir secuencias ANSI en sus logs cuando stdout no es una terminal o cuando `NO_COLOR` tiene un valor no vacío; en una terminal local conserva los colores. La decisión se toma en una función pura con prueba unitaria y una prueba de integración que arranca el binario con stdout redirigido.
- La deriva de `backend/openapi.json` no necesita un paso nuevo: ya la vigila un test del workspace (`catalog-api/src/openapi.rs:58-65`), que `cargo test` ejecuta.
- Documentación (como tareas): `backend/README.md`, `README.md` y `docs/deploy/cloud-run.md` describen la CI, la puerta del despliegue y el formato de los logs.
- Sin cambios en la API, en la app, en el `Dockerfile` ni en la infraestructura de GCP.

## Capabilities

### New Capabilities

- `backend-ci`: verificaciones reproducibles del backend en integración continua (formato, lint, pruebas y deriva del documento OpenAPI), con el toolchain fijado por `mise.toml`, ejecutables como puerta de otro workflow.

### Modified Capabilities

- `backend-deployment`: el requisito «Despliegue automático con verificación posterior» exige que las verificaciones del backend pasen antes de construir, publicar y desplegar, y añade `mise.toml` a los disparadores.
- `catalog-api`: nuevo requisito sobre el formato de los logs sin secuencias ANSI fuera de una terminal.

## Impact

- Se crea `.github/workflows/backend-ci.yml` y se modifica `.github/workflows/deploy-backend.yml`.
- Se toca en `backend/catalog-api`: `src/main.rs` (inicialización de `tracing`), un módulo nuevo o una función pública en `src/` para decidir el color, y tests nuevos (unitario y de integración).
- Documentación: `backend/README.md`, `README.md` y `docs/deploy/cloud-run.md`.
- Dependencias nuevas de CI, fijadas por SHA: `jdx/mise-action` y `Swatinem/rust-cache`. Sin dependencias nuevas de Cargo.
- Costo: minutos de GitHub Actions del repositorio privado (cuota gratuita de la cuenta) y caché de Actions, que comparte el límite de 10 GB con la caché de capas de Docker; sin costo en GCP.
- Fuera de alcance: autenticación o límite de tasa de la API (otro cambio), logs JSON estructurados, auditoría de dependencias, protección de ramas y entornos de despliegue.
