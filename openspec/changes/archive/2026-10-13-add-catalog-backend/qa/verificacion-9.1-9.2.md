# Verificación 9.1 y 9.2: workspace y extremo a extremo

Fecha: 2026-10-12. Versiones: `rustc 1.99.0 (b940084d7 2026-09-28)`, `cargo 1.99.0 (5f94df478 2026-08-27)` (vía `mise exec`).

## 9.1 Verificación del workspace

Comandos ejecutados desde `backend/`, al final de la tarea (después de añadir la prueba de la Parte B):

| Comando | Resultado |
|---|---|
| `mise exec -- cargo fmt --all --check` | código 0 |
| `mise exec -- cargo clippy --all-targets --workspace -- -D warnings` | código 0, sin avisos |
| `mise exec -- cargo test --workspace` | código 0: 139 pruebas pasan, 3 ignoradas (`real_catalog`, `asset_crosscheck`, `real_build`, que necesitan `data/` y se corren con `--ignored`) |
| `git diff --stat -- backend/Cargo.lock` | una línea añadida: `catalog-api` pasa a depender (solo en desarrollo) de `catalog-ingest`; es el cambio esperado de la feature `test-fixtures` |
| `cargo tree -p catalog-api --edges normal` | no muestra `catalog-ingest` (0 coincidencias): `test_support` no se compila en producción |
| `cargo tree -p catalog-api --edges dev` | muestra `catalog-ingest` (1 coincidencia) |

## 9.2 Prueba de extremo a extremo

### Parte A: binarios reales

Comandos desde la raíz, con `mise exec -- cargo run --release --manifest-path backend/Cargo.toml -p catalog-ingest -- <orden>`:

| Orden | Resultado |
|---|---|
| `download` | `usda: ya estaba y está verificado: data/.cache/Duke-Source-CSV.zip` (sin descarga) |
| `build` | fuentes: 1, plantas: 2376, hash `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, 533 ms |
| `rederive` | fuentes: 1, plantas: 2376, hash `48d71b6b0221787add6a8474b6a6b1b6567915d435cb3d1660e8335da3a5812d`, 249 ms |

Los hashes de `build` y `rederive` coinciden.

La API se arrancó con `PORT=18095 cargo run --release -p catalog-api` en segundo plano y se consultó con `curl` en `http://127.0.0.1:18095`:

| Ruta | Código | Content-Type | Resumen |
|---|---|---|---|
| `GET /healthz` | 200 | `application/json` | `{"status":"ok"}` |
| `GET /v1/sources` | 200 | `application/json` | una fuente (`usda`) con licencia, cita y URL |
| `GET /v1/plants` | 200 | `application/json` | `total` 2376, `limit` 20, `offset` 0; primeros ids `abelmoschus-esculentus`, `abelmoschus-manihot`, `abelmoschus-moschatus`; cada elemento trae `id`, `scientificName`, `commonNames`, `family` |
| `GET /v1/plants?q=lavand` | 200 | `application/json` | `total` 7: `lavandula-angustifolia`, `lavandula-latifolia`, `lavandula-sp`, `lavandula-spica`, `lavandula-x-hybrida`, `lavandula-x-intermedia`, `rosmarinus-x-lavandulaceus` |
| `GET /v1/plants?limit=5&offset=2370` | 200 | `application/json` | `total` 2376; últimos 5: `zizyphus-oenoplia`, `zizyphus-rugosa`, `zizyphus-spina-christi`, `zizyphus-trinervia`, `zizyphus-vulgaris-var-spinosus` |
| `GET /v1/plants?limit=5&offset=5000` | 200 | `application/json` | `{"items":[],"total":2376,"limit":5,"offset":5000}` |
| `GET /v1/plants/lavandula-angustifolia` | 200 | `application/json` | 10 usos, 4 partes, 2 nombres, familia Lamiaceae (fuente `usda`) |
| `GET /v1/plants/eucalyptus-globulus` | 200 | `application/json` | 49 usos (41 actividades distintas), 15 partes, 4 nombres, familia Myrtaceae |
| `GET /v1/plants/rosmarinus-officinalis` | 200 | `application/json` | 59 usos (46 actividades distintas), 9 partes, 2 nombres, familia Lamiaceae |
| `GET /v1/plants/matricaria-recutita` | 200 | `application/json` | 0 usos, 3 partes, 4 nombres, familia Asteraceae |
| `GET /v1/plants/mentha-x-piperita-subsp-nothosubsp-piperita` | 200 | `application/json` | 0 usos, 5 partes, 2 nombres, familia Lamiaceae |
| `GET /v1/plants/no-existe` | 404 | `application/problem+json` | `detail`: "no existe una planta con ese identificador", `instance` `/v1/plants/no-existe` |
| `GET /v1/plants?limit=0` | 400 | `application/problem+json` | `detail`: "limit debe estar entre 1 y 100", `param` `limit` |
| `POST /v1/plants` | 405 | `application/problem+json` | `detail`: "método no permitido: la API es de solo lectura" |
| `GET /openapi.json` | 200 | `application/json` | documento OpenAPI 3.1.0 "Boticario AI Catalog API" |

Apagado: `kill -INT` al proceso `backend/target/release/catalog-api` (localizado con `lsof -ti tcp:18095`). El log muestra `apagado completado`, y `lsof -ti tcp:18095` queda vacío.

Arranque sin base: `CATALOG_DB=/tmp/no-existe.db backend/target/release/catalog-api` termina con código de salida 1 y el mensaje `no se pudo arrancar: no existe la base del catálogo en /tmp/no-existe.db; constrúyela con `catalog-ingest build``.

### Parte B: fuentes de fixture servidas por la API

Prueba nueva `backend/catalog-api/tests/fixture_end_to_end.rs` (corre en `cargo test --workspace`, sin red y sin tocar `data/`). Construye dos ZIP de fixture (`alpha` y `beta`, ninguna es USDA), los importa con `import_raw` a un `raw.db` temporal, llama a `rederive` con un `AdapterRegistry` que solo registra `FixtureAdapter` y una `SourcesConfig` con ambas, abre el `catalog.db` con `SqliteCatalogRepository` y consulta el router con `oneshot`. Resultado: PASS. Comprueba que:

- `rederive` informa 2 fuentes y 2 plantas.
- `/healthz` responde 200 con `status` `ok`.
- `/v1/sources` devuelve exactamente `alpha` y `beta`.
- `/v1/plants` devuelve `total` 2 con `lavandula-angustifolia` y `matricaria-chamomilla`.
- El detalle de `lavandula-angustifolia` (planta compartida) atribuye a ambas fuentes los datos compartidos (parte `Flower`, uso `Sedative`) y a una sola los propios (`Leaf` a `alpha`, `Root` a `beta`).

Para exponer los fixtures, `catalog-ingest` declara la feature `test-fixtures` (`[features] test-fixtures = ["dep:tempfile"]`, con `tempfile` como dependencia opcional) y `pub mod test_support` bajo `#[cfg(any(test, feature = "test-fixtures"))]`; `catalog-api` la activa solo como `dev-dependency`.

## Desvíos

- El detalle de la planta no tiene un campo `sources` de nivel superior: las fuentes se informan por elemento (familia, nombres, partes y usos). La prueba de la Parte B comprueba la atribución a ambas fuentes en las partes y los usos compartidos.
- Los conteos de usos de `eucalyptus-globulus` (49) y `rosmarinus-officinalis` (59) corresponden al número de usos devueltos; las actividades distintas son 41 y 46. Los demás conteos (10/4, 15, 9, 0/3, 0/5) coinciden con lo esperado.
- `test_support` de `catalog-ingest` lleva `#![allow(missing_docs)]` porque, al volverse público bajo la feature, el `deny(missing_docs)` del crate exigiría documentar todos los ayudantes de prueba.
- `backend/Cargo.lock` cambió en una línea por la nueva dev-dependency, como se esperaba.
