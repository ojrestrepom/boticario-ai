# Backend: desarrollo nativo

Esta guía es para quien quiera modificar el código Rust del backend o ejecutarlo sin Docker. Para solo ejecutar el backend basta el [README de la raíz](../README.md#backend-catálogo-y-api), que usa Docker y no necesita nada de lo que se describe aquí.

El backend construye una base SQLite neutral con las plantas del catálogo y la sirve en modo de solo lectura. El modelo de datos y cómo añadir un dataset están en la [guía del modelo de datos](../docs/data/modelo-de-datos.md).

Los comandos de las secciones 2 a 4 se ejecutan desde la raíz del repositorio (usan `--manifest-path backend/Cargo.toml`). Los de la sección 5 y los de la sección 6 se ejecutan desde `backend/`. Cada bloque de código indica su directorio.

## 1. Prerrequisitos

- [`mise`](https://mise.jdx.dev) instalado. Desde la raíz, `mise install` instala Rust **1.99.0**, la versión fijada en [`mise.toml`](../mise.toml).
- Un compilador de C del sistema (en macOS, las Command Line Tools), porque SQLite se compila embebido.
- `diesel_cli` solo si se cambia el esquema: `mise exec -- cargo install diesel_cli --no-default-features --features sqlite-bundled`.
- La versión de Rust de [`mise.toml`](../mise.toml) debe coincidir con la de la imagen base del [`Dockerfile`](../Dockerfile) de la raíz: el test `toolchain_pin` de `catalog-core` ([`catalog-core/tests/toolchain_pin.rs`](catalog-core/tests/toolchain_pin.rs)) falla si divergen, así que al subir la versión hay que cambiar los dos archivos.

Desde la raíz del repositorio:

```bash
mise install
```

## 2. Construir el catálogo

La descarga es el único paso que usa la red. `build` y `rederive` nunca la tocan. Desde la raíz del repositorio:

```bash
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- download
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- build
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- rederive
```

- `download` baja y verifica el ZIP de USDA en `data/.cache/Duke-Source-CSV.zip`; si ya está verificado, no lo vuelve a descargar.
- `build` verifica el ZIP, importa la capa cruda a `data/build/raw.db` y escribe la base neutral `data/build/catalog.db`. Imprime el número de fuentes y de plantas y el hash del contenido.
- `rederive` rehace `data/build/catalog.db` desde `data/build/raw.db`, sin el ZIP y sin red. Sirve para probar un cambio en la derivación o en las reglas de consolidación.

Las fuentes activas y su prioridad se leen de [`data/sources.toml`](../data/sources.toml). Con `--data-dir <ruta>` se usa otro directorio de datos.

## 3. Ejecutar la API

Desde la raíz del repositorio:

```bash
mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-api
```

La API se niega a arrancar si no encuentra la base. Se configura con argumentos y variables de entorno:

| Nombre | Por defecto | Uso |
|---|---|---|
| `CATALOG_DB` (o `--db <ruta>`) | `data/build/catalog.db` | Ruta de la base; el argumento tiene prioridad. |
| `HOST` | `127.0.0.1` | Dirección de escucha. |
| `PORT` | `8080` | Puerto de escucha. |
| `RUST_LOG` | `info` | Filtro de logs. |

Endpoints, todos `GET`:

- `/health`: estado del servicio.
- `/v1/plants`: lista paginada, con búsqueda opcional por `q`.
- `/v1/plants/{id}`: detalle de una planta.
- `/openapi.json`: el contrato OpenAPI.

```bash
curl 'http://127.0.0.1:8080/v1/plants?q=lavand'
```

## 4. Contrato OpenAPI

[`openapi.json`](openapi.json) se genera desde el código de la API y la misma API lo sirve en `/openapi.json`. Tras cambiar rutas o DTO, se regenera desde la raíz del repositorio con:

```bash
mise exec -- cargo run --manifest-path backend/Cargo.toml -p catalog-api -- --openapi > backend/openapi.json
```

Un test falla si el archivo está desactualizado respecto al código.

## 5. Verificación

Desde `backend/`:

```bash
mise exec -- cargo fmt --all --check
mise exec -- cargo clippy --all-targets --workspace -- -D warnings
mise exec -- cargo test --workspace
```

Los tests marcados `#[ignore]` necesitan la salida real de `build` en `data/build/` (el fixture JSON que compara uno de ellos ya vive en `catalog-ingest/tests/fixtures/`). También desde `backend/`:

```bash
mise exec -- cargo test --workspace -- --ignored
```

### Integración continua

El workflow [`.github/workflows/backend-ci.yml`](../.github/workflows/backend-ci.yml) verifica el backend con tres pasos en serie: formato, clippy sin advertencias y las pruebas del workspace. Corre en cada pull request y en cada push a una rama distinta de `main` que toque `backend/`, `data/migrations/`, el `Dockerfile`, `mise.toml` o el propio workflow. El toolchain sale de [`mise.toml`](../mise.toml): la CI instala con mise esa versión de Rust, la misma que se usa en local. El comando local equivalente, desde `backend/`:

```bash
mise exec -- cargo fmt --check && mise exec -- cargo clippy --workspace --all-targets --locked -- -D warnings && mise exec -- cargo test --workspace --locked
```

## 6. Cambiar el esquema

1. Editar la migración de [`data/migrations/`](../data/migrations/).
2. Subir `SCHEMA_VERSION` en [`catalog-core/src/version.rs`](catalog-core/src/version.rs).
3. Regenerar [`catalog-core/src/schema.rs`](catalog-core/src/schema.rs) con Diesel, desde `backend/`, sobre una base temporal; [`diesel.toml`](diesel.toml) fija la carpeta de migraciones y la ruta del archivo generado: `DATABASE_URL=/tmp/esquema.db mise exec -- diesel migration run`.
4. Reconstruir el catálogo con `rederive` o `build` (sección 2).

La base no se migra: se regenera entera en cada construcción.
