# Proposal

## Why

El backend es la capa que consolida la información del catálogo y decide qué entregar al cliente. La consolidación será un tema central (más adelante con lógica o IA que elija la información adecuada) y el cliente, ya sea la app Flutter o una interfaz web, debe recibir una sola respuesta sin saber de qué datasets salió cada dato. Hoy la API expone la procedencia por campo (`sources` en cada nombre, parte y uso, y la familia como `{ value, sources }`) y la lista de datasets en `/v1/sources`, lo que rompe esa abstracción y ata al cliente a la estructura de las fuentes. Conviene quitarlo ahora, mientras la API no tiene consumidores (la app Flutter todavía no la usa) y el cambio no cuesta nada a nadie.

## What Changes

- **BREAKING**: eliminar de la respuesta de detalle de planta el campo `sources` de cada nombre, parte y uso, y hacer que `family` sea un texto o `null` (`family: string | null`) en lugar de `{ value, sources }`.
- **BREAKING**: eliminar el endpoint `GET /v1/sources` y su DTO. La ruta pasa a responder 404 como cualquier ruta desconocida.
- Convertir `catalog_core::domain::Plant` en el modelo plano que sirve la API (sin atribución) y mover `Attributed<T>` a `catalog-ingest`, donde `consolidate.rs` construirá un tipo propio con atribución para escribir las tablas.
- Quitar `list_sources` del trait `CatalogRepository` y dejar de consultar las tablas de atribución de nombres, partes y usos en `catalog-api`.
- Regenerar `backend/openapi.json` sin `SourceDto`, `FamilyDto` ni `sources`.
- Modificar la spec `catalog-api`: «Detalle de planta», «Independencia de la fuente de datos» y «Compatibilidad dentro de `/v1`» (excepción acotada para el periodo sin consumidores); eliminar «Consulta de fuentes»; y quitar «y sus fuentes» del `## Purpose` editando la spec principal directamente.
- Actualizar `README.md`, `backend/README.md` y `docs/data/modelo-de-datos.md` para reflejar que la procedencia es interna al backend.
- Se conserva íntegra la procedencia dentro del backend: la tabla `source`, la capa de enlace `plant_source_id` y las tablas de atribución siguen escribiéndose en la ingesta. Sin cambios en el esquema de la base, en su hash de contenido, ni en la app Flutter.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `catalog-api`: el detalle de planta deja de indicar la fuente de cada dato y la familia es un texto; se elimina «Consulta de fuentes»; la independencia de la fuente se verifica con una respuesta consolidada sin origen; la regla de compatibilidad en `/v1` admite una excepción explícita mientras no haya consumidores.

`catalog-ingest` no cambia: sus requisitos «Consolidación multi-fuente con atribución», «Resolución de campos de valor único» y «Procedencia de cada dato» hablan únicamente de lo que contiene la base, que no se modifica.

## Impact

- Código: `catalog-core` (`domain.rs`, `repository.rs`), `catalog-ingest` (`consolidate.rs`, `write.rs` y el nuevo hogar de `Attributed`), `catalog-api` (`repository.rs`, `dto.rs`, `http.rs`, `async_catalog.rs`, `openapi.rs`, `test_support.rs` y los tests `fixture_end_to_end.rs`, `shutdown.rs` y `source_independence.rs`) y `backend/openapi.json`.
- Contrato: cambio incompatible de `/v1` sin consumidores conocidos.
- Datos: ninguno. La base y su hash no cambian.
- Documentación: `README.md`, `backend/README.md`, `docs/data/modelo-de-datos.md` y el `## Purpose` de `openspec/specs/catalog-api/spec.md`.
- Fuera de alcance: la lógica o IA de selección de información y cómo atribuir un dataset con licencia que exija atribución (CC BY u otra), que se resolverá entonces con un dato neutro de créditos y no con una lista de datasets.
